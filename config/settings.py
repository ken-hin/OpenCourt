# settings.py — Central configuration for the OpenCourt Django project.
#
# This file controls everything: installed apps, database, templates, static
# files, middleware, and more. All teammates should be familiar with this file.
#
# HOW DEV vs PRODUCTION WORKS:
# - Locally: .env file sets DEBUG=True, no DATABASE_URL → uses SQLite
# - On Railway: env vars set DEBUG=False, DATABASE_URL → uses Supabase PostgreSQL
# - The same settings.py works in both environments, no code changes needed.

import os
from pathlib import Path

import dj_database_url
from dotenv import load_dotenv
load_dotenv()

# BASE_DIR points to the project root (the repo folder).
# Use it to build absolute paths, e.g. BASE_DIR / 'templates'.
BASE_DIR = Path(__file__).resolve().parent.parent


# --- Security ---
# In production, SECRET_KEY is set as an environment variable on Railway.
# Locally, it falls back to the insecure dev key (fine for local dev only).
SECRET_KEY = os.environ.get(
    'SECRET_KEY',
    'django-insecure-5c#88oge0lq-ezo1n3@-33ia-vv+a(a$q6&za53ht!=blqlh^g',
)

# DEBUG is False unless explicitly set to "True" in the environment.
# On Railway this will be unset or "False" → production mode.
# In your local .env it's "True" → dev mode with debug toolbar, etc.
DEBUG = os.environ.get('DEBUG', 'False').lower() in ('true', '1', 'yes')

# ALLOWED_HOSTS controls which domain names Django will serve.
# Railway gives you a *.up.railway.app subdomain automatically.
# Locally, your .env sets this to "localhost,127.0.0.1".
ALLOWED_HOSTS = os.environ.get('ALLOWED_HOSTS', 'localhost,127.0.0.1').split(',')


# --- Apps ---
# Add new Django apps to this list. Built-in Django apps come first,
# then any third-party packages, then our local apps at the bottom.
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # Third-party: Tailwind CSS + live browser reload
    'tailwind',        # django-tailwind: bridges Django and the Tailwind CLI
    'theme',           # our Tailwind theme app (CSS source + compiled output)
    'django_browser_reload',  # auto-refreshes the browser when CSS or templates change
    "django.contrib.humanize",
    # Local apps
    'opencourt',
]

# --- Tailwind ---
# Tells django-tailwind which app houses the CSS source and compiled output.
# Run `python manage.py tailwind install` once after cloning to install npm deps.
# Run `python manage.py tailwind start` in a second terminal while developing.
TAILWIND_APP_NAME = 'theme'

# Path to the npm executable on your machine. Defaults to 'npm', which works if
# npm is on your system PATH. If you get a "node.js and/or npm is not installed"
# error, find your npm path with `which npm` (Mac/Linux) or `where npm` (Windows)
# and set NPM_BIN_PATH in your local .env file. Never hardcode a path here since
# it differs per machine.
# Common macOS paths: /usr/local/bin/npm (Intel) or /opt/homebrew/bin/npm (Apple Silicon)
# Common Windows path: C:\Program Files\nodejs\npm.cmd
NPM_BIN_PATH = os.environ.get('NPM_BIN_PATH', 'npm')

# Required by django-browser-reload to inject the live-reload script only in
# local dev. INTERNAL_IPS limits this to requests from your own machine.
INTERNAL_IPS = ['127.0.0.1']

# --- Middleware ---
# Middleware runs on every request/response. Order matters — do not reorder
# unless you know what you're doing.
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    # WhiteNoise serves static files (CSS, JS, images) directly from Django
    # in production, so you don't need nginx or a separate CDN. It sits right
    # after SecurityMiddleware so it can intercept static file requests early.
    # In dev (DEBUG=True), Django's staticfiles app handles this instead.
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    # Injects a tiny script that polls for CSS/template changes and refreshes
    # the browser automatically. Only active when DEBUG=True + INTERNAL_IPS match.
    'django_browser_reload.middleware.BrowserReloadMiddleware',
]

# Points Django to the project-level URL file (config/urls.py)
ROOT_URLCONF = 'config.urls'

# --- Templates ---
# DIRS tells Django where to look for shared templates (e.g. base.html).
# APP_DIRS=True also allows templates inside each app's templates/ subfolder.
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

# Entry point for WSGI-compatible servers (used in production deployment)
WSGI_APPLICATION = 'config.wsgi.application'


# --- Database ---
# If DATABASE_URL is set (production), use Supabase PostgreSQL.
# If not set (local dev), fall back to SQLite — no setup needed.
# dj-database-url parses the URL string into Django's DATABASES format.
# https://docs.djangoproject.com/en/6.0/ref/settings/#databases
DATABASES = {
    'default': dj_database_url.config(
        default=f'sqlite:///{BASE_DIR / "db.sqlite3"}',
        conn_max_age=600,       # keep DB connections open for 10 min (reduces latency)
        conn_health_checks=True, # verify connections are alive before reusing
    )
}


# --- Password Validation ---
# These validators enforce password strength for user accounts.
# https://docs.djangoproject.com/en/6.0/ref/settings/#auth-password-validators
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


# --- Internationalization ---
# https://docs.djangoproject.com/en/6.0/topics/i18n/
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'America/New_York'
USE_I18N = True
USE_TZ = True


# --- Static Files (CSS, JavaScript, Images) ---
# STATIC_URL is the URL prefix for static files in the browser.
# STATICFILES_DIRS tells Django where to find *additional* static file directories
# during development. We only list static/ (our hand-written CSS, JS, images) here.
#
# theme/static/ (the compiled Tailwind output) does NOT need to be listed here —
# Django's staticfiles app automatically discovers the static/ folder inside every
# app in INSTALLED_APPS, so `{% static 'css/dist/styles.css' %}` resolves to
# theme/static/css/dist/styles.css without any extra configuration.
#
# https://docs.djangoproject.com/en/6.0/howto/static-files/
STATIC_URL = 'static/'
STATICFILES_DIRS = [BASE_DIR / 'static']

# STATIC_ROOT is where `collectstatic` gathers all static files into one folder.
# WhiteNoise then serves files from here in production.
# This folder is in .gitignore — it's generated at deploy time, not committed.
STATIC_ROOT = BASE_DIR / 'staticfiles'

# WhiteNoise storage backend — compresses and fingerprints static files for
# better caching and performance. Only takes effect when collectstatic runs.
STORAGES = {
    'staticfiles': {
        'BACKEND': 'whitenoise.storage.CompressedManifestStaticFilesStorage',
    },
}

MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

# --- Logging ---
# Outputs INFO and above from the opencourt app to the console so that
# sync summary lines (created/updated/skipped counts, warnings) are
# visible when running management commands like `python manage.py sync_data`.
#
# To silence a noisy logger temporarily, raise its level to WARNING or ERROR.
# In production, swap the console handler for a file or external log service.
LOGGING = {
  'version': 1,
  'disable_existing_loggers': False,
  'formatters': {
    # Simple format for dev: just the level and message, no timestamps.
    # Swap in 'verbose' for production to include timestamps and module paths.
    'simple': {
      'format': '[{levelname}] {message}',
      'style': '{',
    },
  },
  'handlers': {
    'console': {
      'class': 'logging.StreamHandler',
      'formatter': 'simple',
    },
  },
  'loggers': {
    # opencourt app — covers services.py, models.py, views.py, etc.
    'opencourt': {
      'handlers': ['console'],
      'level': 'INFO',
      'propagate': False,
    },
  },
}
