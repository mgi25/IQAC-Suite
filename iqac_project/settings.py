# settings.py
from pathlib import Path
import os
import logging
import dj_database_url

# ──────────────────────────────────────────────────────────────────────────────
# BASE / .env loader (dotenv first, fallback to os.getenv)
# ──────────────────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent.parent

try:
    from dotenv import load_dotenv
    load_dotenv(dotenv_path=BASE_DIR / ".env")
except Exception:
    pass

try:
    import environ
    env = environ.Env()
    environ.Env.read_env(os.path.join(BASE_DIR, ".env"))
except Exception:
    env = None

def _env(key: str, default=None, cast=None):
    """Prefer django-environ, then os.getenv, else default."""
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

# ──────────────────────────────────────────────────────────────────────────────
# AI config (kept from your version)
# ──────────────────────────────────────────────────────────────────────────────
AI_BACKEND       = _env("AI_BACKEND", default="OLLAMA")
OLLAMA_BASE      = _env("OLLAMA_BASE", default="http://127.0.0.1:11434")
OLLAMA_MODEL     = _env("OLLAMA_MODEL", default="llama3")
AI_HTTP_TIMEOUT  = int(_env("AI_HTTP_TIMEOUT", default="120"))

OPENROUTER_API_KEY = _env("OPENROUTER_API_KEY", default="")
OPENROUTER_MODEL   = _env("OPENROUTER_MODEL", default="qwen/qwen3.5:free")
OLLAMA_GEN_MODEL    = _env("OLLAMA_GEN_MODEL", default=OLLAMA_MODEL)
OLLAMA_CRITIC_MODEL = _env("OLLAMA_CRITIC_MODEL", default=OLLAMA_MODEL)

# ──────────────────────────────────────────────────────────────────────────────
# Core Django
# ──────────────────────────────────────────────────────────────────────────────
SECRET_KEY = os.getenv("SECRET_KEY", "django-insecure-…")
DEBUG = _env("DEBUG", default="False").lower() in ("1", "true", "yes")

# Hosts / CSRF (Render-safe)
ALLOWED_HOSTS = ["127.0.0.1", "localhost"]
# Add your previous ngrok if you still use it locally:
# ALLOWED_HOSTS += ["7c40-103-229-129-85.ngrok-free.app"]

RENDER_EXTERNAL_HOSTNAME = os.getenv("RENDER_EXTERNAL_HOSTNAME")
if RENDER_EXTERNAL_HOSTNAME:
    # e.g. "iqac-suite.onrender.com"
    ALLOWED_HOSTS.append(RENDER_EXTERNAL_HOSTNAME)
    CSRF_TRUSTED_ORIGINS = [f"https://{RENDER_EXTERNAL_HOSTNAME}"]
else:
    # Hardcode fallback for Render if env var missing
    ALLOWED_HOSTS += ["iqac-suite.onrender.com"]
    CSRF_TRUSTED_ORIGINS = ["https://iqac-suite.onrender.com"]

# If you still need ngrok for dev CSRF:
# CSRF_TRUSTED_ORIGINS += ["https://7c40-103-229-129-85.ngrok-free.app"]

# Trust Render’s proxy for HTTPS
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG

# ──────────────────────────────────────────────────────────────────────────────
# Installed apps
# ──────────────────────────────────────────────────────────────────────────────
INSTALLED_APPS = [
    # Django core
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "whitenoise.runserver_nostatic",  # let Whitenoise handle static in dev too
    "django.contrib.staticfiles",
    "django.contrib.sites",           # required by allauth
    "django_extensions",

    # Allauth for Google login
    "allauth",
    "allauth.account",
    "allauth.socialaccount",
    "allauth.socialaccount.providers.google",

    # Your apps
    "core.apps.CoreConfig",
    "emt",
    "transcript",
]

SITE_ID = 2

# ──────────────────────────────────────────────────────────────────────────────
# Middleware (Whitenoise must be right after SecurityMiddleware)
# ──────────────────────────────────────────────────────────────────────────────
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",  # serves /static/ in prod
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "core.middleware.ImpersonationMiddleware",
    "allauth.account.middleware.AccountMiddleware",
    "core.middleware.ActivityLogMiddleware",
    "core.middleware.EnsureSiteMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

# ──────────────────────────────────────────────────────────────────────────────
# URLs / Templates / WSGI
# ──────────────────────────────────────────────────────────────────────────────
ROOT_URLCONF = "iqac_project.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",  # required by allauth
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
# Database (Render Postgres with SSL; SQLite fallback for local)
# ──────────────────────────────────────────────────────────────────────────────
DATABASES = {
    "default": dj_database_url.config(
        env="DATABASE_URL",
        default=f"sqlite:///{BASE_DIR / 'db.sqlite3'}",
        conn_max_age=600,
        ssl_require=True,  # important on Render
    )
}
if "railway.internal" in str(DATABASES["default"].get("HOST", "")):
    raise RuntimeError("Invalid DB host — still pointing to Railway.")

# ──────────────────────────────────────────────────────────────────────────────
# Auth / Allauth
# ──────────────────────────────────────────────────────────────────────────────
AUTHENTICATION_BACKENDS = [
    "django.contrib.auth.backends.ModelBackend",  # REQUIRED for /admin
    "core.auth_backends.AllowInactiveFirstLoginBackend",
    "allauth.account.auth_backends.AuthenticationBackend",
]

LOGIN_URL = "/accounts/login/"
LOGIN_REDIRECT_URL = "dashboard"
LOGOUT_REDIRECT_URL = "/accounts/login/"

ACCOUNT_EMAIL_REQUIRED = True
ACCOUNT_USERNAME_REQUIRED = False
ACCOUNT_AUTHENTICATION_METHOD = "email"
ACCOUNT_EMAIL_VERIFICATION = "none"
ACCOUNT_UNIQUE_EMAIL = True
ACCOUNT_LOGOUT_REDIRECT_URL = "/accounts/login/"
ACCOUNT_LOGOUT_ON_GET = True

ACCOUNT_ADAPTER = "core.adapters.RoleBasedAccountAdapter"
SOCIALACCOUNT_AUTO_SIGNUP = True
SOCIALACCOUNT_LOGIN_ON_GET = True
SOCIALACCOUNT_QUERY_EMAIL = True
SOCIALACCOUNT_EMAIL_REQUIRED = True
SOCIALACCOUNT_ADAPTER = "core.adapters.SchoolSocialAccountAdapter"

SOCIALACCOUNT_PROVIDERS = {
    "google": {
        "SCOPE": ["profile", "email"],
        "AUTH_PARAMS": {"access_type": "online"},
    }
}

# ──────────────────────────────────────────────────────────────────────────────
# i18n / tz
# ──────────────────────────────────────────────────────────────────────────────
LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

# ──────────────────────────────────────────────────────────────────────────────
# Static / Media (Whitenoise)
# ──────────────────────────────────────────────────────────────────────────────
STATIC_URL = "/static/"
STATICFILES_DIRS = [BASE_DIR / "static"]  # your existing /static for source files
STATIC_ROOT = BASE_DIR / "staticfiles"    # collectstatic target
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ──────────────────────────────────────────────────────────────────────────────
# Logging (kept from your version; note Render’s FS is ephemeral)
# ──────────────────────────────────────────────────────────────────────────────
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
        "console": {"class": "logging.StreamHandler", "formatter": "simple"},
        "activity_file": {
            "level": "INFO",
            "class": "logging.handlers.RotatingFileHandler",
            "filename": BASE_DIR / "activity.log",
            "maxBytes": 5 * 1024 * 1024,
            "backupCount": 5,
            "formatter": "verbose",
        },
        "error_file": {
            "level": "ERROR",
            "class": "logging.FileHandler",
            "filename": BASE_DIR / "error.log",
            "formatter": "verbose",
        },
    },
    "loggers": {
        "django": {"handlers": ["console"], "level": "INFO", "propagate": True},
        "django.request": {"handlers": ["error_file"], "level": "ERROR", "propagate": True},
        "core": {"handlers": ["console", "activity_file"], "level": "INFO", "propagate": False},
        "emt": {"handlers": ["console", "activity_file"], "level": "INFO", "propagate": False},
        "transcript": {"handlers": ["console", "activity_file"], "level": "INFO", "propagate": False},
    },
}
