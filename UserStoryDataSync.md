# User Story: Data Sync & Retrieval

**As a** site admin,
**I want** to run a single CLI command that fetches and syncs all team and conference data from the CBBData API into the database,
**so that** the site always serves up-to-date stats without requiring manual database edits.

(Issue #18)

## Acceptance Criteria

- `python manage.py sync_data` syncs both teams and conferences in one command
- New records are created and existing records are updated (no duplicates)
- A summary is printed on completion: created, updated, and skipped counts
- If the API is unreachable or returns an error, the command logs a warning and exits cleanly without crashing
- `CBB_API_KEY` is read from `.env` and is never hardcoded

## Notes

- `sync_teams()` is implemented in `opencourt/services.py`
- `sync_conferences()` is stubbed and ready to be implemented
- Intended to be run manually during development and on a cron schedule in production
