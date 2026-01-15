from datetime import timezone

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.views import PasswordResetView
from django.core.cache import cache
from django.core.mail import EmailMultiAlternatives
from django.http import HttpResponse
from django.template.loader import render_to_string
from urllib.parse import urljoin
from django.urls import reverse

from .models import PasswordResetAttempt

User = get_user_model()
RESET_BASE_URL = "https://eccoprom.windexs.ru"

def get_client_ip(request):
    xff = request.META.get("HTTP_X_FORWARDED_FOR")
    if xff:
        return xff.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


class BrandedPasswordResetView(PasswordResetView):
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

        return super().form_valid(form)

    def send_mail(self, subject_template_name, email_template_name, context, from_email, to_email, html_email_template_name=None):
        RESET_BASE_URL = "https://eccoprom.windexs.ru"

        path = reverse("password_reset_confirm", kwargs={"uidb64": context["uid"], "token": context["token"]})
        reset_url = urljoin(RESET_BASE_URL.rstrip("/") + "/", path.lstrip("/"))

        subject = render_to_string(subject_template_name, context).strip()

        # ВАЖНО: передаём reset_url в контекст писем
        mail_ctx = {**context, "reset_url": reset_url, "site_domain": "eccoprom.windexs.ru"}

        text_body = render_to_string(email_template_name, mail_ctx)
        html_body = render_to_string("emails/password_reset.html", {**mail_ctx, "year": timezone.now().year})

        from django.core.mail import EmailMultiAlternatives
        msg = EmailMultiAlternatives(subject, text_body, from_email, [to_email])
        msg.attach_alternative(html_body, "text/html")
        msg.send()
