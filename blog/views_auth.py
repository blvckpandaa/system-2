import logging
from smtplib import SMTPAuthenticationError, SMTPException

from django.contrib import messages
from django.utils import timezone

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.views import PasswordResetView
from django.core.cache import cache
from django.http import HttpResponse
from django.shortcuts import redirect
from django.urls import reverse

from .forms import BrandedPasswordResetForm
from .models import PasswordResetAttempt

logger = logging.getLogger(__name__)

User = get_user_model()

def get_client_ip(request):
    xff = request.META.get("HTTP_X_FORWARDED_FOR")
    if xff:
        return xff.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


class BrandedPasswordResetView(PasswordResetView):
    form_class = BrandedPasswordResetForm
    template_name = "auth/password_reset_form.html"
    success_url = "/password-reset/done/"

    subject_template_name = "emails/password_reset_subject.txt"
    email_template_name = "emails/password_reset_email.txt"
    html_email_template_name = "emails/password_reset.html"

    def dispatch(self, request, *args, **kwargs):
        ip = get_client_ip(request) or "0.0.0.0"
        window = getattr(settings, "RESET_LIMIT_WINDOW", 15 * 60)
        limit_ip = getattr(settings, "RESET_LIMIT_PER_IP", 10)

        ip_key = f"pwreset:ip:{ip}"
        if cache.get(ip_key, 0) >= limit_ip:
            return HttpResponse("Слишком много попыток. Попробуйте позже.", status=429)

        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        request = self.request
        ip = get_client_ip(request) or "0.0.0.0"
        ua = (request.META.get("HTTP_USER_AGENT", "") or "")[:500]

        email = (form.cleaned_data.get("email", "") or "").strip().lower()
        window = getattr(settings, "RESET_LIMIT_WINDOW", 15 * 60)
        limit_email = getattr(settings, "RESET_LIMIT_PER_EMAIL", 3)

        email_key = f"pwreset:email:{email}"
        if cache.get(email_key, 0) >= limit_email:
            return HttpResponse("Слишком много попыток для этого email. Попробуйте позже.", status=429)

        # счётчики
        ip_key = f"pwreset:ip:{ip}"
        cache.set(ip_key, cache.get(ip_key, 0) + 1, timeout=window)
        cache.set(email_key, cache.get(email_key, 0) + 1, timeout=window)

        user = User.objects.filter(email__iexact=email).first()

        PasswordResetAttempt.objects.create(
            email=email,
            ip=ip,
            user_agent=ua,
            success=bool(user),
            user=user if user else None,
        )

        if not user:
            logger.warning(
                "Password reset: в Django нет пользователя с email=%r — "
                "письмо не отправлялось (форма всё равно ведёт на /password-reset/done/).",
                email,
            )
            return HttpResponse("", status=302, headers={"Location": self.success_url})

        domain = getattr(settings, "SITE_DOMAIN", "eccoprom.windexs.ru")
        use_https = getattr(settings, "SITE_PROTOCOL", "https").lower() == "https"

        try:
            form.save(
                domain_override=domain,
                use_https=use_https,
                request=None,  # чтобы не взял 192.168.*
                from_email=settings.DEFAULT_FROM_EMAIL,
                subject_template_name=self.subject_template_name,
                email_template_name=self.email_template_name,
                html_email_template_name=self.html_email_template_name,
                extra_email_context={
                    "site_domain": domain,
                    "year": timezone.now().year,
                },
            )
        except SMTPAuthenticationError as e:
            smtp_err = getattr(e, "smtp_error", b"") or b""
            if isinstance(smtp_err, bytes):
                smtp_err = smtp_err.decode("utf-8", errors="replace")
            logger.exception(
                "SMTP authentication failed: smtp_code=%s smtp_error=%r — "
                "отказ на стороне mailer-server (учётка ящика / AUTH / пароль в БД). "
                "На сервере почты: sudo journalctl -u mailer-server -n 120 --no-pager "
                "| grep mailer-smtp-auth",
                getattr(e, "smtp_code", None),
                smtp_err,
            )
            messages.error(
                request,
                "Почтовый сервер отклонил вход SMTP (код аутентификации). "
                "Проверьте EMAIL_HOST_USER и EMAIL_HOST_PASSWORD в .env (логин и пароль "
                "именно почтового ящика). Если они верные — на сервере почты выполните: "
                "sudo journalctl -u mailer-server -n 120 --no-pager | grep mailer-smtp-auth",
            )
            return redirect(reverse("password_reset"))
        except (SMTPException, OSError) as e:
            logger.exception("SMTP send failed: %s", e)
            messages.error(
                request,
                "Не удалось отправить письмо через SMTP. Проверьте хост, порт и сеть.",
            )
            return redirect(reverse("password_reset"))

        logger.info("Password reset: SMTP send OK for user id=%s email=%s", user.pk, email)
        return HttpResponse("", status=302, headers={"Location": self.success_url})
