# apps.py — App configuration for the opencourt Django app.
#
# Django reads this file to register the app with the project.
# OpenCourtConfig is referenced in config/settings.py under INSTALLED_APPS.
# Add any app-level startup logic in the ready() method if needed.

from django.apps import AppConfig


class OpenCourtConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'opencourt'
    verbose_name = 'OpenCourt'
