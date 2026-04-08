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
EMAIL_PORT = int(os.environ.get("EMAIL_PORT", "13091"))
# Порт 13091 у многих хостеров — STARTTLS (plain + starttls), не SMTPS как на 465.
# Если не коннектится: в .env попробуйте EMAIL_USE_SSL=1 и EMAIL_USE_TLS=0 (implicit SSL).
if _env_bool("EMAIL_USE_SSL", False):
    EMAIL_USE_SSL = True
    EMAIL_USE_TLS = False
else:
    EMAIL_USE_TLS = _env_bool("EMAIL_USE_TLS", True)
    EMAIL_USE_SSL = False

EMAIL_HOST_USER = "eccoprom@windexs.ru"
EMAIL_HOST_PASSWORD = os.environ.get("EMAIL_HOST_PASSWORD", "")

DEFAULT_FROM_EMAIL = "Ecco Prom <eccoprom@windexs.ru>"
SERVER_EMAIL = DEFAULT_FROM_EMAIL

# для ссылок в письмах
SITE_DOMAIN = "eccoprom.windexs.ru"
SITE_PROTOCOL = "https"
