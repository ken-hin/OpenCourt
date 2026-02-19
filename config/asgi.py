# asgi.py — ASGI entry point for async-capable production deployment.
#
# ASGI (Asynchronous Server Gateway Interface) is the async successor to WSGI.
# Required if the project ever adds WebSockets or async views (e.g. for
# real-time score updates). Most deployments start with WSGI and upgrade later.
# You generally do not need to modify this file.

import os

from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

application = get_asgi_application()
