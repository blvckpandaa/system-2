import logging
import random

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils import timezone
from datetime import timedelta

from .models import EmailVerification

logger = logging.getLogger(__name__)

VERIFICATION_CODE_LENGTH = 6
VERIFICATION_CODE_TTL_MINUTES = 15


def generate_verification_code(length=VERIFICATION_CODE_LENGTH):
    return "".join(str(random.randint(0, 9)) for _ in range(length))


def send_verification_code_email(user, code):
    """Отправляет 6-значный код на email пользователя."""
    subject = render_to_string(
        "emails/verification_code_subject.txt",
        {"site_domain": getattr(settings, "SITE_DOMAIN", "eccoprom.windexs.ru")},
    ).strip()
    context = {
        "username": user.username,
        "code": code,
        "site_domain": getattr(settings, "SITE_DOMAIN", "eccoprom.windexs.ru"),
        "year": timezone.now().year,
        "ttl_minutes": VERIFICATION_CODE_TTL_MINUTES,
    }
    text_body = render_to_string("emails/verification_code_email.txt", context)
    html_body = render_to_string("emails/verification_code.html", context)

    msg = EmailMultiAlternatives(
        subject,
        text_body,
        settings.DEFAULT_FROM_EMAIL,
        [user.email],
    )
    msg.attach_alternative(html_body, "text/html")
    msg.send()
    logger.info("Verification code sent to user id=%s email=%s", user.pk, user.email)


def issue_verification_code(user):
    code = generate_verification_code()
    EmailVerification.objects.update_or_create(
        user=user,
        defaults={
            "code": code,
            "expires_at": timezone.now() + timedelta(minutes=VERIFICATION_CODE_TTL_MINUTES),
            "attempts": 0,
        },
    )
    send_verification_code_email(user, code)
    return code
