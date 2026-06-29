import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

DEBUG = True

DATABASE_DIR = os.path.join(BASE_DIR, 'db.sqlite3')
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': DATABASE_DIR,
    }
}

EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"


def _env_bool(name: str, default: bool) -> bool:
    raw = os.environ.get(name)
    if raw is None or raw.strip() == "":
        return default
    return raw.strip().lower() in ("1", "true", "yes", "on")


EMAIL_HOST = os.environ.get("EMAIL_HOST", "mail.windexs.ru")
# На mail.windexs.ru обычно plain SMTP на 13090; 13091 у вас тоже без STARTTLS (см. EHLO).
EMAIL_PORT = int(os.environ.get("EMAIL_PORT", "13090"))
# Порт 13091 у многих хостеров — STARTTLS (plain + starttls), не SMTPS как на 465.
# Если не коннектится: в .env попробуйте EMAIL_USE_SSL=1 и EMAIL_USE_TLS=0 (implicit SSL).
if _env_bool("EMAIL_USE_SSL", False):
    EMAIL_USE_SSL = True
    EMAIL_USE_TLS = False
else:
    EMAIL_USE_TLS = _env_bool("EMAIL_USE_TLS", False)
    EMAIL_USE_SSL = False

# Django вызывает SMTP AUTH только если заданы и логин, и пароль (см. smtp backend).
# Если сервер не поддерживает AUTH — включите AUTH в mailer-server ИЛИ временно:
#   EMAIL_SMTP_AUTH=0  (только если релей с IP приложения разрешён без логина).
if _env_bool("EMAIL_SMTP_AUTH", True):
    EMAIL_HOST_USER = os.environ.get("EMAIL_HOST_USER", "eccoprom@windexs.ru").strip() or None
    EMAIL_HOST_PASSWORD = os.environ.get("EMAIL_HOST_PASSWORD", "").strip() or None
else:
    EMAIL_HOST_USER = None
    EMAIL_HOST_PASSWORD = None

DEFAULT_FROM_EMAIL = "Ecco Prom <eccoprom@windexs.ru>"
SERVER_EMAIL = DEFAULT_FROM_EMAIL

# для ссылок в письмах
SITE_DOMAIN = "eccoprom.windexs.ru"
SITE_PROTOCOL = "https"
