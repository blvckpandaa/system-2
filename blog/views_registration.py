import logging

from django.contrib import messages
from django.contrib.auth import get_user_model, login
from django.core.cache import cache
from django.shortcuts import redirect, render

from smtplib import SMTPAuthenticationError, SMTPException

from .email_utils import VERIFICATION_CODE_TTL_MINUTES, issue_verification_code
from .forms import EmailVerificationForm, ResendVerificationForm
from .models import EmailVerification

logger = logging.getLogger(__name__)
User = get_user_model()

SESSION_PENDING_USER_KEY = "pending_verification_user_id"
RESEND_LIMIT = 3
RESEND_WINDOW = 15 * 60


def start_email_verification_session(request, user, message=None):
    """Запоминает пользователя в сессии для экрана /verify-email/."""
    request.session[SESSION_PENDING_USER_KEY] = user.pk
    if message:
        messages.info(request, message)


def _get_pending_user(request):
    user_id = request.session.get(SESSION_PENDING_USER_KEY)
    if not user_id:
        return None
    return User.objects.filter(pk=user_id, is_active=False).first()


def _resend_verification_code(request, user):
    """Отправляет новый код на email пользователя из сессии. Возвращает redirect на verify_email."""
    cache_key = f"verify_resend:{user.email.lower()}"
    if cache.get(cache_key, 0) >= RESEND_LIMIT:
        messages.error(request, "Слишком много запросов. Попробуйте через 15 минут.")
        return redirect("verify_email")

    try:
        issue_verification_code(user)
    except (SMTPAuthenticationError, SMTPException, OSError) as exc:
        logger.exception("Failed to resend verification email: %s", exc)
        messages.error(
            request,
            "Не удалось отправить письмо. Попробуйте позже или обратитесь в поддержку.",
        )
        return redirect("verify_email")

    cache.set(cache_key, cache.get(cache_key, 0) + 1, timeout=RESEND_WINDOW)
    start_email_verification_session(request, user)
    messages.success(request, f"Новый код отправлен на {user.email}.")
    return redirect("verify_email")


def verify_email_view(request):
    user = _get_pending_user(request)
    if not user:
        messages.warning(
            request,
            "Войдите с логином и паролем — откроется экран подтверждения email.",
        )
        return redirect("login")

    masked_email = user.email
    if "@" in masked_email:
        local, domain = masked_email.split("@", 1)
        if len(local) > 2:
            masked_email = f"{local[0]}***{local[-1]}@{domain}"

    if request.method == "POST":
        if request.POST.get("action") == "resend":
            return _resend_verification_code(request, user)

        form = EmailVerificationForm(request.POST)
        if form.is_valid():
            code = form.cleaned_data["code"]
            try:
                verification = user.email_verification
            except EmailVerification.DoesNotExist:
                messages.error(request, "Код не найден. Нажмите «Отправить код снова».")
                form = EmailVerificationForm()
                return render(
                    request,
                    "auth/verify_email.html",
                    {"form": form, "masked_email": masked_email, "ttl_minutes": VERIFICATION_CODE_TTL_MINUTES},
                )

            if verification.is_expired():
                messages.error(request, "Срок действия кода истёк. Нажмите «Отправить код снова».")
                form = EmailVerificationForm()
                return render(
                    request,
                    "auth/verify_email.html",
                    {"form": form, "masked_email": masked_email, "ttl_minutes": VERIFICATION_CODE_TTL_MINUTES},
                )

            verification.attempts += 1
            verification.save(update_fields=["attempts"])

            if verification.attempts > 5:
                messages.error(request, "Слишком много попыток. Нажмите «Отправить код снова».")
                form = EmailVerificationForm()
                return render(
                    request,
                    "auth/verify_email.html",
                    {"form": form, "masked_email": masked_email, "ttl_minutes": VERIFICATION_CODE_TTL_MINUTES},
                )

            if verification.code != code:
                messages.error(request, "Неверный код. Проверьте письмо и попробуйте снова.")
            else:
                user.is_active = True
                user.save(update_fields=["is_active"])
                verification.delete()
                request.session.pop(SESSION_PENDING_USER_KEY, None)
                login(request, user, backend="django.contrib.auth.backends.ModelBackend")
                messages.success(request, "Email подтверждён. Добро пожаловать!")
                logger.info("Email verified for user id=%s", user.pk)
                return redirect("index")
    else:
        form = EmailVerificationForm()

    return render(
        request,
        "auth/verify_email.html",
        {
            "form": form,
            "masked_email": masked_email,
            "ttl_minutes": VERIFICATION_CODE_TTL_MINUTES,
        },
    )


def resend_verification_view(request):
    """Повторная отправка, если сессия подтверждения потеряна — нужен email."""
    if request.method == "POST":
        form = ResendVerificationForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data["email"].strip().lower()
            user = User.objects.filter(email__iexact=email, is_active=False).first()
            if not user:
                messages.info(
                    request,
                    "Если этот email зарегистрирован и не подтверждён, на него отправлен код.",
                )
                return redirect("login")

            start_email_verification_session(request, user)
            return _resend_verification_code(request, user)
    else:
        form = ResendVerificationForm()

    return render(request, "auth/resend_verification.html", {"form": form})
