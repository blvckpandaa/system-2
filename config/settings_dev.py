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

EMAIL_HOST = "smtp.mail.ru"
EMAIL_PORT = 465
EMAIL_USE_SSL = True
EMAIL_USE_TLS = False

EMAIL_HOST_USER = "eccoprom@besttrafik.ru"
EMAIL_HOST_PASSWORD = "FC65e24q2kAFRXFfd8Q8"

DEFAULT_FROM_EMAIL = "Ecco Prom <eccoprom@besttrafik.ru>"
SERVER_EMAIL = DEFAULT_FROM_EMAIL

# для ссылок в письмах
SITE_DOMAIN = "eccoprom.windexs.ru"
SITE_PROTOCOL = "https"
