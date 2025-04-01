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

# Boshqa sozlamalar (EMAIL, TOKEN, va hokazo) ham shu faylda turishi mumkin
SMS_CODE_ACTIVE = False
ESKIZ_TOKEN = ''
MAPS_API_KEY = ''

EMAIL_HOST = 'smtp.sendgrid.net'
EMAIL_PORT = 587
EMAIL_HOST_USER = 'apikey'
EMAIL_HOST_PASSWORD = ''
SERVER_EMAIL = EMAIL_HOST_USER
DEFAULT_FROM_EMAIL = ''
