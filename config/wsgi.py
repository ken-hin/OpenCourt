# wsgi.py — WSGI entry point for production deployment.
#
# WSGI (Web Server Gateway Interface) is the standard way to serve Django
# apps in production using servers like Gunicorn or uWSGI.
# This file is used by platforms like Railway and Render when deploying.
# You generally do not need to modify this file.

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

application = get_wsgi_application()
