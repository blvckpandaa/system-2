"""
Local development / current server overrides.
Always imported at the end of settings.py (as before).
Forces SQLite + DEBUG so the site runs without psycopg2.
"""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

DEBUG = True
ALLOWED_HOSTS = ["*"]

DATABASE_DIR = os.path.join(BASE_DIR, "db.sqlite3")
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": DATABASE_DIR,
    }
}

EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"


def _env_bool(name: str, default: bool = False) -> bool:
    raw = os.environ.get(name)
    if raw is None or str(raw).strip() == "":
        return default
    return str(raw).strip().lower() in ("1", "true", "yes", "on")


EMAIL_HOST = os.environ.get("EMAIL_HOST", "mail.windexs.ru")
EMAIL_PORT = int(os.environ.get("EMAIL_PORT", "13090"))
if _env_bool("EMAIL_USE_SSL", False):
    EMAIL_USE_SSL = True
    EMAIL_USE_TLS = False
else:
    EMAIL_USE_TLS = _env_bool("EMAIL_USE_TLS", False)
    EMAIL_USE_SSL = False

if _env_bool("EMAIL_SMTP_AUTH", True):
    EMAIL_HOST_USER = os.environ.get("EMAIL_HOST_USER", "eccoprom@windexs.ru").strip() or None
    EMAIL_HOST_PASSWORD = os.environ.get("EMAIL_HOST_PASSWORD", "").strip() or None
else:
    EMAIL_HOST_USER = None
    EMAIL_HOST_PASSWORD = None

DEFAULT_FROM_EMAIL = "Ecco Prom <eccoprom@windexs.ru>"
SERVER_EMAIL = DEFAULT_FROM_EMAIL

SITE_DOMAIN = os.environ.get("SITE_DOMAIN", "eccoprom.windexs.ru")
SITE_PROTOCOL = os.environ.get("SITE_PROTOCOL", "https")
