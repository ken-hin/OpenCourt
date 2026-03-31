# settings.py — Central configuration for the OpenCourt Django project.
#
# This file controls everything: installed apps, database, templates, static
# files, middleware, and more. All teammates should be familiar with this file.
#
# IMPORTANT: Never commit SECRET_KEY or sensitive credentials to version control.
# Before deploying to production, move secrets to environment variables and
# set DEBUG = False. See: https://docs.djangoproject.com/en/6.0/howto/deployment/checklist/

import os
from pathlib import Path

# Load environment variables from .env file (if it exists).
# This lets us read SECRET_KEY, DEBUG, NPM_BIN_PATH, etc. from .env
# without hardcoding them here. Requires: uv add python-dotenv
# Copy .env.example to .env and fill in your values — see README for setup.
from dotenv import load_dotenv
load_dotenv()

# BASE_DIR points to the project root (the repo folder).
# Use it to build absolute paths, e.g. BASE_DIR / 'templates'.
BASE_DIR = Path(__file__).resolve().parent.parent


# --- Security ---
# WARNING: keep the secret key used in production secret!
SECRET_KEY = 'django-insecure-5c#88oge0lq-ezo1n3@-33ia-vv+a(a$q6&za53ht!=blqlh^g'

# WARNING: don't run with debug=True in production!
DEBUG = True

# Add your production domain here before deploying (e.g. ['opencourt.com'])
ALLOWED_HOSTS = []


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
# NPM_BIN_PATH = os.environ.get('NPM_BIN_PATH', 'npm')

# Required by django-browser-reload to inject the live-reload script only in
# local dev. INTERNAL_IPS limits this to requests from your own machine.
INTERNAL_IPS = ['127.0.0.1']

# --- Middleware ---
# Middleware runs on every request/response. Order matters — do not reorder
# unless you know what you're doing.
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
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
# Using SQLite for development. Switch to PostgreSQL before deploying to
# production (see Schedule.md Week 7 — Deployment).
# https://docs.djangoproject.com/en/6.0/ref/settings/#databases
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
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

# NPM_BIN_PATH = r"C:\Program Files\nodejs\npm.cmd"
