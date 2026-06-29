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


def _get_pending_user(request):
    user_id = request.session.get(SESSION_PENDING_USER_KEY)
    if not user_id:
        return None
    return User.objects.filter(pk=user_id, is_active=False).first()


def verify_email_view(request):
    user = _get_pending_user(request)
    if not user:
        messages.warning(request, "Сначала зарегистрируйтесь или запросите код повторно.")
        return redirect("register")

    masked_email = user.email
    if "@" in masked_email:
        local, domain = masked_email.split("@", 1)
        if len(local) > 2:
            masked_email = f"{local[0]}***{local[-1]}@{domain}"

    if request.method == "POST":
        form = EmailVerificationForm(request.POST)
        if form.is_valid():
            code = form.cleaned_data["code"]
            try:
                verification = user.email_verification
            except EmailVerification.DoesNotExist:
                messages.error(request, "Код не найден. Запросите новый.")
                return redirect("resend_verification")

            if verification.is_expired():
                messages.error(
                    request,
                    "Срок действия кода истёк. Запросите новый код.",
                )
                return redirect("resend_verification")

            verification.attempts += 1
            verification.save(update_fields=["attempts"])

            if verification.attempts > 5:
                messages.error(request, "Слишком много попыток. Запросите новый код.")
                return redirect("resend_verification")

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
    if request.method == "POST":
        form = ResendVerificationForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data["email"].strip().lower()
            cache_key = f"verify_resend:{email}"
            if cache.get(cache_key, 0) >= RESEND_LIMIT:
                messages.error(request, "Слишком много запросов. Попробуйте через 15 минут.")
                return render(request, "auth/resend_verification.html", {"form": form})

            user = User.objects.filter(email__iexact=email, is_active=False).first()
            if not user:
                messages.info(
                    request,
                    "Если этот email зарегистрирован и не подтверждён, на него отправлен код.",
                )
                return redirect("login")

            try:
                issue_verification_code(user)
            except (SMTPAuthenticationError, SMTPException, OSError) as exc:
                logger.exception("Failed to resend verification email: %s", exc)
                messages.error(
                    request,
                    "Не удалось отправить письмо. Попробуйте позже или обратитесь в поддержку.",
                )
                return render(request, "auth/resend_verification.html", {"form": form})

            cache.set(cache_key, cache.get(cache_key, 0) + 1, timeout=RESEND_WINDOW)
            request.session[SESSION_PENDING_USER_KEY] = user.pk
            messages.success(request, f"Новый код отправлен на {email}.")
            return redirect("verify_email")
    else:
        form = ResendVerificationForm()

    return render(request, "auth/resend_verification.html", {"form": form})
