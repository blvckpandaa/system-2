"""
Local development overrides.
Loaded only when DJANGO_DEV=1 in .env.
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

# Local email domain overrides (SMTP credentials still come from .env via settings.py)
SITE_DOMAIN = os.environ.get("SITE_DOMAIN", "eccoprom.windexs.ru")
SITE_PROTOCOL = os.environ.get("SITE_PROTOCOL", "https")
