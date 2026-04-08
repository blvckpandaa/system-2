from django.utils import timezone

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.views import PasswordResetView
from django.core.cache import cache
from django.http import HttpResponse

from .forms import BrandedPasswordResetForm
from .models import PasswordResetAttempt

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

        domain = "eccoprom.windexs.ru"

        form.save(
            domain_override=domain,
            use_https=True,
            request=None,  # чтобы не взял 192.168.*
            from_email=settings.DEFAULT_FROM_EMAIL,
            subject_template_name=self.subject_template_name,
            email_template_name=self.email_template_name,
            html_email_template_name=self.html_email_template_name,
            extra_email_context={"site_domain": domain, "year": timezone.now().year},
        )

        return HttpResponse("", status=302, headers={"Location": self.success_url})
