from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent



SECRET_KEY = 'django-insecure-…'  # rotate this before you go to production!
DEBUG      = True
ALLOWED_HOSTS = []


INSTALLED_APPS = [
    # Django core
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.sites',               # ← required by allauth

    # django-allauth
    'allauth',
    'allauth.account',
    'allauth.socialaccount',
    'allauth.socialaccount.providers.google',

    # your app
    'core',
    'emt',
    'transcript'
]



MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',

    # add allauth’s account middleware here:
    'allauth.account.middleware.AccountMiddleware',

    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]


ROOT_URLCONF = 'iqac_project.urls'


TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR /'templates'],  # points at core/templates/
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


DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}


AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',       # Django default
    'allauth.account.auth_backends.AuthenticationBackend',  # allauth
]

SITE_ID = 1  # must match a row in django_site


# Redirect URLs
LOGIN_URL = '/accounts/login/'
LOGIN_REDIRECT_URL = 'dashboard'  # or 'home' or your custom view name
LOGOUT_REDIRECT_URL = '/accounts/login/'



# ──────────────────────────────────────────────────────────────────────────────
# django-allauth CONFIGURATION
# ──────────────────────────────────────────────────────────────────────────────

ACCOUNT_EMAIL_REQUIRED            = True
ACCOUNT_USERNAME_REQUIRED         = False
ACCOUNT_AUTHENTICATION_METHOD     = 'email'
ACCOUNT_EMAIL_VERIFICATION        = 'none'    # in prod you might set 'optional' or 'mandatory'
ACCOUNT_UNIQUE_EMAIL              = True
SOCIALACCOUNT_AUTO_SIGNUP         = True
SOCIALACCOUNT_LOGIN_ON_GET = True
ACCOUNT_LOGOUT_REDIRECT_URL = '/accounts/login/'
ACCOUNT_LOGOUT_ON_GET = True


SOCIALACCOUNT_PROVIDERS = {
    'google': {
        'SCOPE': ['profile', 'email'],
        'AUTH_PARAMS': {'access_type': 'online'},
        'DOMAIN': ['christuniversity.in'],
    }
}

# point allauth to your custom adapter that checks the email domain
SOCIALACCOUNT_ADAPTER = 'core.adapters.SchoolSocialAccountAdapter'



# ──────────────────────────────────────────────────────────────────────────────
# INTERNATIONALIZATION
# ──────────────────────────────────────────────────────────────────────────────

LANGUAGE_CODE = 'en-us'
TIME_ZONE     = 'UTC'
USE_I18N      = True
USE_TZ        = True


# ──────────────────────────────────────────────────────────────────────────────
# STATIC FILES
# ──────────────────────────────────────────────────────────────────────────────

STATIC_URL = '/static/'
STATICFILES_DIRS = [
    BASE_DIR / 'static',
]

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

