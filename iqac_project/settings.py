from pathlib import Path
import os, dj_database_url
try:
    from dotenv import load_dotenv
    BASE_DIR = Path(__file__).resolve().parent.parent
    load_dotenv(dotenv_path=BASE_DIR / ".env")
except Exception:
    pass
import logging

# ---- .env loader (django-environ if available, else os.getenv) ----

try:
    import environ
    env = environ.Env()
    environ.Env.read_env(os.path.join(BASE_DIR, ".env"))
except Exception:
    env = None

def _env(key: str, default=None, cast=None):
    """Unified env reader: prefer django-environ, fallback to os.getenv, then default."""
    if env:
        try:
            return env(key) if cast is None else cast(env(key))
        except Exception:
            pass
    val = os.getenv(key, default)
    if cast and isinstance(val, str):
        try:
            return cast(val)
        except Exception:
            return default
    return val

# ---- AI config with safe defaults ----
AI_BACKEND       = _env("AI_BACKEND", default="OLLAMA")  # OLLAMA | OPENROUTER
OLLAMA_BASE      = _env("OLLAMA_BASE", default="http://127.0.0.1:11434")
OLLAMA_MODEL     = _env("OLLAMA_MODEL", default="llama3")  # guarantees a default
AI_HTTP_TIMEOUT  = _env("AI_HTTP_TIMEOUT", default="120")
try:
    AI_HTTP_TIMEOUT = int(AI_HTTP_TIMEOUT)
except Exception:
    AI_HTTP_TIMEOUT = 120

# Optional: generator/critic models if used elsewhere in code
OLLAMA_GEN_MODEL    = _env("OLLAMA_GEN_MODEL", default=OLLAMA_MODEL)
OLLAMA_CRITIC_MODEL = _env("OLLAMA_CRITIC_MODEL", default=OLLAMA_MODEL)

# Optional cloud fallback (only used if key provided or AI_BACKEND='OPENROUTER')
OPENROUTER_API_KEY = _env("OPENROUTER_API_KEY", default="")
OPENROUTER_MODEL   = _env("OPENROUTER_MODEL", default="qwen/qwen3.5:free")

# SECRET_KEY loaded from environment with a development fallback
SECRET_KEY = os.environ.get('SECRET_KEY', 'django-insecure-…')
DEBUG = True

ALLOWED_HOSTS = ["localhost", "127.0.0.1"]
RENDER_EXTERNAL_HOSTNAME = os.getenv("RENDER_EXTERNAL_HOSTNAME")
if RENDER_EXTERNAL_HOSTNAME:
    ALLOWED_HOSTS.append(RENDER_EXTERNAL_HOSTNAME)
    CSRF_TRUSTED_ORIGINS = [f"https://{RENDER_EXTERNAL_HOSTNAME}"]
else:
    ALLOWED_HOSTS += ["iqac-suite.onrender.com"]
    CSRF_TRUSTED_ORIGINS = ["https://iqac-suite.onrender.com"]

DATABASE_URL = os.getenv("DATABASE_URL")
if DATABASE_URL:
    DATABASES = {"default": dj_database_url.config(default=DATABASE_URL, conn_max_age=600, ssl_require=True)}
else:
    DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": BASE_DIR / "db.sqlite3"}}

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
    'core.middleware.ActivityLogMiddleware',
    'core.middleware.EnsureSiteMiddleware',
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
                'core.context_processors.active_academic_year',
                'core.context_processors.sidebar_permissions',
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
# AUTHENTICATION
# ──────────────────────────────────────────────────────────────────────────────
AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',           # ← REQUIRED for /admin
    'core.auth_backends.AllowInactiveFirstLoginBackend',
    'allauth.account.auth_backends.AuthenticationBackend',
]

SITE_ID = 2


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
