from pathlib import Path
import os
from dotenv import load_dotenv
import dj_database_url

load_dotenv()
BASE_DIR = Path(__file__).resolve().parent.parent

# SECRET_KEY loaded from environment with a development fallback
SECRET_KEY = os.environ.get('SECRET_KEY', 'django-insecure-…')
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
    'django_extensions',

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
    'core.middleware.ImpersonationMiddleware',
    'allauth.account.middleware.AccountMiddleware',  # ← allauth middleware
    'core.middleware.RegistrationRequiredMiddleware',
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
                'django.template.context_processors.csrf',
                'django.contrib.messages.context_processors.messages',
                'core.context_processors.notifications',
            ],
            'libraries': {
                'dict_filters': 'core.templatetags.dict_filters',
                'group_filters': 'core.templatetags.group_filters',
            },
        },
    },
]

WSGI_APPLICATION = 'iqac_project.wsgi.application'

# ──────────────────────────────────────────────────────────────────────────────
# DATABASE
# ──────────────────────────────────────────────────────────────────────────────


DATABASES = {
    'default': dj_database_url.config(
        default=os.getenv('DATABASE_URL', 'sqlite:///db.sqlite3')
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
LOGIN_REDIRECT_URL = 'dashboard'  # Default redirect after login
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

ACCOUNT_ADAPTER = 'core.adapters.RoleBasedAccountAdapter'

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
STATIC_ROOT = BASE_DIR / 'staticfiles'

# settings.py

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'


DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# LOGGING CONFIGURATION
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
        'activity_file': { # Renamed from 'file' for clarity
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': BASE_DIR / 'activity.log',
            'maxBytes': 1024 * 1024 * 5,  # 5 MB
            'backupCount': 5,
            'formatter': 'verbose',
        },
        ## NEW: Handler for error logging ##
        'error_file': {
            'level': 'ERROR',
            'class': 'logging.FileHandler', # No rotation needed for less frequent errors
            'filename': BASE_DIR / 'error.log',
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': True,
        },
        ## NEW: Logger for Django's request errors ##
        'django.request': {
            'handlers': ['error_file'],
            'level': 'ERROR',
            'propagate': True,
        },
        'core': {
            'handlers': ['console', 'activity_file'],
            'level': 'INFO',
            'propagate': False,
        },
        'emt': {
            'handlers': ['console', 'activity_file'],
            'level': 'INFO',
            'propagate': False,
        },
        'transcript': {
            'handlers': ['console', 'activity_file'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}