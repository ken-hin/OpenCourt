# services.py — External API and data-fetching logic for the opencourt app.
#
# This file is the single place for all CBB data API calls and any web scraping.
# Keeping this separate from views.py means views stay clean and focused on
# HTTP logic, while all the data-fetching details live here.
#
# Usage pattern — call these functions from views.py:
#   from opencourt.services import fetch_teams
#   teams = fetch_teams()
#
# The `requests` library is already listed in pyproject.toml and installed by `uv sync`.
# No additional install step is needed.
#
# The CBB_API_KEY is read from the .env file (never hardcode it here).
# See .env.example for setup instructions.
#
# This file will be built out in Week 2. Functions to implement:
#   - fetch_teams()       : pull all teams from the CBB API
#   - fetch_conferences() : pull all conferences
#   - sync_teams()        : fetch from API and save to the database
#   - sync_conferences()  : fetch from API and save to the database

import os

# CBB_API_KEY = os.environ.get('CBB_API_KEY')  # uncomment when ready

# --- Team Data ---

# def fetch_teams():
#     """Fetch all teams from the CBB API. Returns a list of team dicts."""
#     pass

# --- Conference Data ---

# def fetch_conferences():
#     """Fetch all conferences from the CBB API. Returns a list of conference dicts."""
#     pass

# --- Sync Functions ---
# These call the fetch functions above and save results to the database.

# def sync_teams():
#     """Fetch teams from the API and upsert them into the Team model."""
#     pass

# def sync_conferences():
#     """Fetch conferences from the API and upsert them into the Conference model."""
#     pass
