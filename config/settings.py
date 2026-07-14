"""
Django settings for config project.
"""

from pathlib import Path
import os

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(BASE_DIR / ".env")


def _env_bool(name: str, default: bool = False) -> bool:
    raw = os.environ.get(name)
    if raw is None or str(raw).strip() == "":
        return default
    return str(raw).strip().lower() in ("1", "true", "yes", "on")


# Quick-start development settings - unsuitable for production
SECRET_KEY = os.environ.get(
    "SECRET_KEY",
    "django-insecure-change-me-in-production",
).strip()

DEBUG = _env_bool("DEBUG", False)

CSRF_TRUSTED_ORIGINS = [
    origin.strip()
    for origin in os.environ.get(
        "CSRF_TRUSTED_ORIGINS",
        "https://eccoprom.windexs.ru,https://eccoprom.windexs.ru:1021,https://windexs.ru",
    ).split(",")
    if origin.strip()
]
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

_allowed = os.environ.get("ALLOWED_HOSTS", "eccoprom.windexs.ru,windexs.ru,localhost,127.0.0.1").strip()
ALLOWED_HOSTS = [h.strip() for h in _allowed.split(",") if h.strip()]


# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.humanize',
    'mptt',
    'blog',
    'templatetags',
    'dal',
    'dal_select2',
]
FKKO_API_URL = 'https://rpn.gov.ru/fkko/'

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'blog.middleware.RequireVerifiedEmailMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

AUTH_USER_MODEL = 'blog.User'

YOOKASSA_SHOP_ID = os.environ.get("YOOKASSA_SHOP_ID", "").strip()
YOOKASSA_SECRET_KEY = os.environ.get("YOOKASSA_SECRET_KEY", "").strip()

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'unique-cache-name',
    }
}

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'templates')],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'blog.views.pending_announcements_processor',
                'blog.views.unread_notifications_processor',
            ],
        },
    },
]


WSGI_APPLICATION = 'config.wsgi.application'


# SQLite: USE_SQLITE=1 (как раньше через settings_dev). Иначе PostgreSQL + psycopg2.
if _env_bool("USE_SQLITE", False):
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": os.environ.get("POSTGRES_DB", "postgres"),
            "USER": os.environ.get("POSTGRES_USER", "postgres"),
            "PASSWORD": os.environ.get("POSTGRES_PASSWORD", ""),
            "HOST": os.environ.get("POSTGRES_HOST", "localhost"),
            "PORT": os.environ.get("POSTGRES_PORT", "5432"),
        }
    }


AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


LANGUAGE_CODE = 'ru'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True


STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

SITE_DOMAIN = os.environ.get("SITE_DOMAIN", "eccoprom.windexs.ru")
SITE_PROTOCOL = os.environ.get("SITE_PROTOCOL", "https")
PASSWORD_RESET_TIMEOUT = 30 * 60  # 30 минут

# лимиты
RESET_LIMIT_PER_IP = 5
RESET_LIMIT_PER_EMAIL = 3
RESET_LIMIT_WINDOW = 15 * 60

# Email / SMTP (production + local)
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
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

DEFAULT_FROM_EMAIL = os.environ.get(
    "DEFAULT_FROM_EMAIL",
    "Ecco Prom <eccoprom@windexs.ru>",
)
SERVER_EMAIL = DEFAULT_FROM_EMAIL

# DeepSeek AI chat
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "").strip()
DEEPSEEK_API_URL = os.environ.get(
    "DEEPSEEK_API_URL",
    "https://api.deepseek.com/chat/completions",
).strip()
DEEPSEEK_MODEL = os.environ.get("DEEPSEEK_MODEL", "deepseek-chat").strip()
AI_CHAT_RATE_LIMIT = int(os.environ.get("AI_CHAT_RATE_LIMIT", "30"))
AI_CHAT_RATE_WINDOW = int(os.environ.get("AI_CHAT_RATE_WINDOW", str(60 * 60)))

# Local overrides only when DJANGO_DEV=1 (SQLite, DEBUG=True, etc.)
if _env_bool("DJANGO_DEV", False):
    try:
        from .settings_dev import *  # noqa: F401,F403
    except ImportError:
        pass
