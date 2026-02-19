#!/usr/bin/env python
# manage.py — Django's command-line utility for administrative tasks.
#
# Run all commands from the project root using `uv run python manage.py <command>`.
#
# --- Dev server ---
#   runserver                        — start the local dev server at http://127.0.0.1:8000
#
# --- Tailwind CSS (run in a second terminal alongside runserver) ---
#   tailwind install                 — download npm packages (Tailwind CLI + DaisyUI) — one-time after cloning
#   tailwind start                   — watch templates for class changes and recompile CSS automatically
#   tailwind build                   — compile and minify CSS for production
#
# --- Database ---
#   makemigrations                   — generate migration files after editing models.py
#   migrate                          — apply pending migrations to the local database
#
# --- Admin ---
#   createsuperuser                  — create an admin account for /admin/
#
# --- Testing ---
#   test                             — run the full test suite
#   test opencourt                   — run tests for the opencourt app only
#
# Do not modify this file. Django generates and manages it automatically.

import os
import sys


def main():
    """Run administrative tasks."""
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    main()
