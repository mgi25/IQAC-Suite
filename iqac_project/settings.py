from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = 'django-insecure-…'  # rotate this before you go to production!
DEBUG = True

ALLOWED_HOSTS = [
    '127.0.0.1',
    'localhost',
    '192.168.0.104',
    '7c40-103-229-129-85.ngrok-free.app',
]

CSRF_TRUSTED_ORIGINS = [
    "https://7c40-103-229-129-85.ngrok-free.app",
]

# ──────────────────────────────────────────────────────────────────────────────
# INSTALLED APPS
# ──────────────────────────────────────────────────────────────────────────────
INSTALLED_APPS = [
    # Django core
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.sites',  # ← required by allauth

    # Allauth for Google login
    'allauth',
    'allauth.account',
    'allauth.socialaccount',
    'allauth.socialaccount.providers.google',

    # Your apps
    'core.apps.CoreConfig',
    'emt',
    'transcript',
]

# ──────────────────────────────────────────────────────────────────────────────
# MIDDLEWARE
# ──────────────────────────────────────────────────────────────────────────────
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'allauth.account.middleware.AccountMiddleware',  # ← allauth middleware
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

# ──────────────────────────────────────────────────────────────────────────────
# URLS / TEMPLATES / WSGI
# ──────────────────────────────────────────────────────────────────────────────
ROOT_URLCONF = 'iqac_project.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',  # ← required by allauth
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'iqac_project.wsgi.application'

# ──────────────────────────────────────────────────────────────────────────────
# DATABASE
# ──────────────────────────────────────────────────────────────────────────────
import os
from dotenv import load_dotenv
import dj_database_url

load_dotenv()  # 👈 This is critical

DATABASES = {
    'default': dj_database_url.parse(
        os.getenv('DATABASE_URL'),
        engine='django.db.backends.postgresql',
    )
}


# ──────────────────────────────────────────────────────────────────────────────
# AUTHENTICATION
# ──────────────────────────────────────────────────────────────────────────────
AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
    'allauth.account.auth_backends.AuthenticationBackend',
]

SITE_ID = 1 # Must match ID in django_site table


LOGIN_URL = '/accounts/login/'
LOGIN_REDIRECT_URL = 'dashboard'  # This should be a URL name, not a path
LOGOUT_REDIRECT_URL = '/accounts/login/'

# ──────────────────────────────────────────────────────────────────────────────
# ALLAUTH SETTINGS
# ──────────────────────────────────────────────────────────────────────────────
ACCOUNT_EMAIL_REQUIRED = True
ACCOUNT_USERNAME_REQUIRED = False
ACCOUNT_AUTHENTICATION_METHOD = 'email'
ACCOUNT_EMAIL_VERIFICATION = 'none'
ACCOUNT_UNIQUE_EMAIL = True
ACCOUNT_LOGOUT_REDIRECT_URL = '/accounts/login/'
ACCOUNT_LOGOUT_ON_GET = True

SOCIALACCOUNT_AUTO_SIGNUP = True
SOCIALACCOUNT_LOGIN_ON_GET = True
SOCIALACCOUNT_QUERY_EMAIL = True
SOCIALACCOUNT_EMAIL_REQUIRED = True

SOCIALACCOUNT_PROVIDERS = {
    'google': {
        'SCOPE': ['profile', 'email'],
        'AUTH_PARAMS': {'access_type': 'online'},
    }
}

# Use custom adapter to enforce domain restriction
SOCIALACCOUNT_ADAPTER = 'core.adapters.SchoolSocialAccountAdapter'

# ──────────────────────────────────────────────────────────────────────────────
# LOCALIZATION
# ──────────────────────────────────────────────────────────────────────────────
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# ──────────────────────────────────────────────────────────────────────────────
# STATIC FILES
# ──────────────────────────────────────────────────────────────────────────────
STATIC_URL = '/static/'
STATICFILES_DIRS = [
    BASE_DIR / 'static',
]

# settings.py

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'


DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
