import importlib.util
import os
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.environ.get("SECRET_KEY", "django-insecure-…")
DEBUG = True

# TOOLBAR: Required for Django Debug Toolbar to display
INTERNAL_IPS = [
    "127.0.0.1",
]

ALLOWED_HOSTS = [
    "127.0.0.1",
    "localhost",
    "192.168.0.104",
    "7c40-103-229-129-85.ngrok-free.app",
]

_LOCAL_CSRF_TRUSTED_ORIGINS = [
    "http://127.0.0.1:8000",
    "https://127.0.0.1:8000",
    "http://localhost:8000",
    "https://localhost:8000",
]
CSRF_TRUSTED_ORIGINS = list(_LOCAL_CSRF_TRUSTED_ORIGINS)

additional_csrf = os.getenv("ADDITIONAL_CSRF_TRUSTED_ORIGINS", "")
if additional_csrf:
    CSRF_TRUSTED_ORIGINS.extend(
        origin.strip() for origin in additional_csrf.split(",") if origin.strip()
    )

CSRF_TRUSTED_ORIGINS = list(dict.fromkeys(CSRF_TRUSTED_ORIGINS))

# ──────────────────────────────────────────────────────────────────────────────
# INSTALLED APPS
# ──────────────────────────────────────────────────────────────────────────────
INSTALLED_APPS = [
    # Django core
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.sites",  # ← required by allauth
    "django_extensions",

    # Third-party apps (debug_toolbar appended conditionally below)

    # Allauth for Google login
    "allauth",
    "allauth.account",
    "allauth.socialaccount",
    "allauth.socialaccount.providers.google",

    # Your apps
    "core.apps.CoreConfig",
    "emt",
    "transcript",
    "usermanagement.apps.UserManagementConfig",
]


ALLOWED_HOSTS = ["127.0.0.1", "localhost"]
# ──────────────────────────────────────────────────────────────────────────────
# MIDDLEWARE
# ──────────────────────────────────────────────────────────────────────────────
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "core.middleware.ImpersonationMiddleware",
    "allauth.account.middleware.AccountMiddleware",  # ← allauth middleware
    "core.middleware.ActivityLogMiddleware",
    "core.middleware.EnsureSiteMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

X_FRAME_OPTIONS = "SAMEORIGIN"

# ──────────────────────────────────────────────────────────────────────────────
# URLS / TEMPLATES / WSGI
# ──────────────────────────────────────────────────────────────────────────────
ROOT_URLCONF = "iqac_project.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": False,
        "OPTIONS": {
            "loaders": [
                "django.template.loaders.app_directories.Loader",
                "django.template.loaders.filesystem.Loader",
            ],
            "context_processors": [
                "django.template.context_processors.request",  # ← required by allauth
                "django.contrib.auth.context_processors.auth",
                "django.template.context_processors.csrf",
                "django.contrib.messages.context_processors.messages",
                "core.context_processors.notifications",
                "core.context_processors.active_academic_year",
                "core.context_processors.sidebar_permissions",
            ],
            "libraries": {
                "dict_filters": "core.templatetags.dict_filters",
                "group_filters": "core.templatetags.group_filters",
            },
        },
    },
]

WSGI_APPLICATION = "iqac_project.wsgi.application"

# ──────────────────────────────────────────────────────────────────────────────
# DATABASE
# ──────────────────────────────────────────────────────────────────────────────

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}


# ──────────────────────────────────────────────────────────────────────────────
# AUTHENTICATION
# ──────────────────────────────────────────────────────────────────────────────
AUTHENTICATION_BACKENDS = [
    "django.contrib.auth.backends.ModelBackend",  # ← REQUIRED for /admin
    "core.auth_backends.AllowInactiveFirstLoginBackend",
    "allauth.account.auth_backends.AuthenticationBackend",
]

SITE_ID = 1


LOGIN_URL = "/accounts/login/"
LOGIN_REDIRECT_URL = "dashboard"  # Default redirect after login
LOGOUT_REDIRECT_URL = "/accounts/login/"

# ──────────────────────────────────────────────────────────────────────────────
# ALLAUTH SETTINGS
# ──────────────────────────────────────────────────────────────────────────────
ACCOUNT_LOGIN_METHODS = {"email"}
ACCOUNT_SIGNUP_FIELDS = ["email*", "password1*", "password2*"]
ACCOUNT_EMAIL_VERIFICATION = "none"
ACCOUNT_UNIQUE_EMAIL = True
ACCOUNT_LOGOUT_REDIRECT_URL = "/accounts/login/"
ACCOUNT_LOGOUT_ON_GET = True

ACCOUNT_ADAPTER = "core.adapters.RoleBasedAccountAdapter"

SOCIALACCOUNT_AUTO_SIGNUP = True
SOCIALACCOUNT_LOGIN_ON_GET = True
SOCIALACCOUNT_QUERY_EMAIL = True
SOCIALACCOUNT_EMAIL_REQUIRED = True

SOCIALACCOUNT_PROVIDERS = {
    "google": {
        "SCOPE": ["profile", "email"],
        "AUTH_PARAMS": {"access_type": "online"},
    }
}

# Use custom adapter to enforce domain restriction
SOCIALACCOUNT_ADAPTER = "core.adapters.SchoolSocialAccountAdapter"

# ──────────────────────────────────────────────────────────────────────────────
# LOCALIZATION
# ──────────────────────────────────────────────────────────────────────────────
LANGUAGE_CODE = "en-us"
TIME_ZONE = "Asia/Kolkata"
USE_I18N = True
USE_TZ = True

# ──────────────────────────────────────────────────────────────────────────────
# STATIC FILES
# ──────────────────────────────────────────────────────────────────────────────
STATIC_URL = "/static/"
STATICFILES_DIRS = [
    BASE_DIR / "static",
]
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

# settings.py

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"


DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# LOGGING CONFIGURATION
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "{levelname} {asctime} {module} {process:d} {thread:d} {message}",
            "style": "{",
        },
        "simple": {
            "format": "{levelname} {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "simple",
        },
        "activity_file": {  # Renamed from 'file' for clarity
            "level": "INFO",
            "class": "logging.handlers.RotatingFileHandler",
            "filename": BASE_DIR / "activity.log",
            "maxBytes": 1024 * 1024 * 5,  # 5 MB
            "backupCount": 5,
            "formatter": "verbose",
        },
        # NEW: Handler for error logging ##
        "error_file": {
            "level": "ERROR",
            "class": "logging.FileHandler",  # No rotation needed for less frequent errors
            "filename": BASE_DIR / "error.log",
            "formatter": "verbose",
        },
    },
    "loggers": {
        "django": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": True,
        },
        # NEW: Logger for Django's request errors ##
        "django.request": {
            "handlers": ["error_file"],
            "level": "ERROR",
            "propagate": True,
        },
        "core": {
            "handlers": ["console", "activity_file"],
            "level": "INFO",
            "propagate": False,
        },
        "emt": {
            "handlers": ["console", "activity_file"],
            "level": "INFO",
            "propagate": False,
        },
        "transcript": {
            "handlers": ["console", "activity_file"],
            "level": "INFO",
            "propagate": False,
        },
    },
}
ALLOWED_HOSTS = ["iqac-suite.onrender.com", "localhost", "127.0.0.1"]

RENDER_EXTERNAL_HOSTNAME = os.getenv("RENDER_EXTERNAL_HOSTNAME")
if RENDER_EXTERNAL_HOSTNAME:
    # e.g. "iqac-suite.onrender.com"
    ALLOWED_HOSTS.append(RENDER_EXTERNAL_HOSTNAME)
    render_origin = f"https://{RENDER_EXTERNAL_HOSTNAME}"
    if render_origin not in CSRF_TRUSTED_ORIGINS:
        CSRF_TRUSTED_ORIGINS.append(render_origin)
else:
    # fallback for local/dev or if you want to be permissive temporarily
    # ALLOWED_HOSTS.append("iqac-suite.onrender.com")   # <-- you can hardcode your URL too
    pass

# ──────────────────────────────────────────────────────────────────────────────
# EMAIL (SMTP) CONFIGURATION
# ──────────────────────────────────────────────────────────────────────────────
# Email config
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = "EMAIL_ID"
EMAIL_HOST_PASSWORD = "EMAIL_HOST_PASSWORD"
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
