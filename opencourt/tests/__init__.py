# tests/ — Test package for the opencourt app.
#
# Organized by module:
#   test_stats.py      — stats.py helper functions (win_percentage, point_differential)
#   test_models.py     — Model logic (save overrides, properties, constraints, ordering)
#   test_views.py      — View responses (HTTP status, templates, context data, edge cases)
#   test_predictions.py — ML pipeline (feature engineering, prediction, model loading)
#   test_services.py   — Data pipeline (helpers, fetch mocking, sync/update idempotency)
#   test_urls.py       — URL routing (resolve, reverse, named routes)
#
# Run all tests:
#   uv run python manage.py test opencourt
#
# Run a single module:
#   uv run python manage.py test opencourt.tests.test_models
#
# Run a single class:
#   uv run python manage.py test opencourt.tests.test_models.TeamModelTest
#
# Run a single test:
#   uv run python manage.py test opencourt.tests.test_models.TeamModelTest.test_slug_auto_generated_on_first_save
