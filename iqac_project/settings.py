# iqac_project/settings.py

from pathlib import Path
import os
from dotenv import load_dotenv
import dj_database_url

# Load environment variables from .env file at the very top
load_dotenv()

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# --- Security Settings (Loaded from Environment) ---

# SECRET_KEY is loaded from the .env file.
# A default is provided for safety in case the .env file is missing.
SECRET_KEY = os.getenv('SECRET_KEY', 'a-default-secret-key-for-development-only')

# DEBUG is True only if DEBUG=1 is in the .env file. It defaults to False for safety.
DEBUG = os.getenv('DEBUG') == '1'

# ALLOWED_HOSTS is a comma-separated string in the .env file.
# It defaults to localhost for local development.
ALLOWED_HOSTS = os.getenv('ALLOWED_HOSTS', '127.0.0.1,localhost').split(',')

# CSRF_TRUSTED_ORIGINS should include your production domain and ngrok for testing.
# This list is built dynamically from your ALLOWED_HOSTS.
CSRF_TRUSTED_ORIGINS = [f"https://{host}" for host in ALLOWED_HOSTS if host not in ['127.0.0.1', 'localhost']]
if '7c40-103-229-129-85.ngrok-free.app' in ALLOWED_HOSTS:
    CSRF_TRUSTED_ORIGINS.append("https://7c40-103-229-129-85.ngrok-free.app")


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
    # Whitenoise middleware for serving static files in production
    'whitenoise.middleware.WhiteNoiseMiddleware',
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
DATABASES = {
    # dj_database_url reads the DATABASE_URL from the .env file
    'default': dj_database_url.config(
        conn_max_age=600,
        ssl_require=True
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
# ALLAUTH SETTINGS (Updated to remove deprecated values)
# ──────────────────────────────────────────────────────────────────────────────
ACCOUNT_AUTHENTICATION_METHOD = 'email' # Users log in with email
ACCOUNT_EMAIL_VERIFICATION = 'none'     # Set to 'mandatory' in production if you want email verification
ACCOUNT_UNIQUE_EMAIL = True
ACCOUNT_LOGOUT_ON_GET = True

# New settings to replace deprecated ones
ACCOUNT_LOGIN_METHOD = 'email'
ACCOUNT_USERNAME_REQUIRED = False # Users don't need a username
ACCOUNT_SIGNUP_PASSWORD_ENTER_TWICE = True # Users must confirm password on signup

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
# STATIC FILES (Production Ready with Whitenoise)
# ──────────────────────────────────────────────────────────────────────────────
STATIC_URL = '/static/'

# Directory where Django will collect all static files for production
STATIC_ROOT = BASE_DIR / 'staticfiles'

# Extra directories to find static files
STATICFILES_DIRS = [
    BASE_DIR / 'static',
]

# Storage engine for static files, compressed manifest is recommended for production
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'


# ──────────────────────────────────────────────────────────────────────────────
# MEDIA FILES
# ──────────────────────────────────────────────────────────────────────────────
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'