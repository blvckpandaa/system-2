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

EMAIL_HOST = os.environ.get("EMAIL_HOST", "mail.windexs.ru")
EMAIL_PORT = int(os.environ.get("EMAIL_PORT", "13091"))
EMAIL_USE_TLS = False
EMAIL_USE_SSL = True

EMAIL_HOST_USER = "eccoprom@windexs.ru"
EMAIL_HOST_PASSWORD = os.environ.get("EMAIL_HOST_PASSWORD", "")

DEFAULT_FROM_EMAIL = "Ecco Prom <eccoprom@windexs.ru>"
SERVER_EMAIL = DEFAULT_FROM_EMAIL

# для ссылок в письмах
SITE_DOMAIN = "eccoprom.windexs.ru"
SITE_PROTOCOL = "https"
