# Code Quality Report — OpenCourt

## Overview
A Django web application for browsing college basketball (Division I) team statistics. It syncs team, conference, and season stats from the CBBData API and displays them with charts. The project follows Django conventions closely with separate models, views, services, management commands, and tests.

**Language:** Python (Django)  
**Source files:** 30  
**Lines of code:** ~750 (excluding migrations)

---

## Strengths

### Excellent documentation
Nearly every function and class has a comprehensive docstring explaining purpose, parameters, return values, error conditions, and links to related code. This is the best-documented codebase in the batch.

```python
def fetch_season_stats_bulk(season):
    """
    Fetch season stats for ALL teams in a single season from the CBBData API.
    One call returns every team's stats for that year — far more efficient
    than calling the API once per team (~362 calls)...
    """
```

### Clean separation of concerns
- `models.py` — data layer only  
- `views.py` — HTTP logic only  
- `services.py` — all external API calls  
- `stats.py` — pure calculation functions  
- `management/commands/` — CLI sync operations  

This follows Django best practices and makes each layer independently testable.

### Robust API error handling
`services.py` handles three distinct failure modes for every API call (HTTP errors, connection errors, configuration errors) and uses exponential backoff with `Retry-After` header support for rate limiting (HTTP 429):
```python
wait = retry_after if retry_after else RETRY_BASE_DELAY * (2 ** attempt)
```

### Structured logging
Module-level `logging.getLogger(__name__)` is used consistently. Log messages are tagged (`'opencourt.services'`), filterable, and descriptive. `tqdm` progress bars are redirected through the logging system with `logging_redirect_tqdm`.

### Tests exist
`tests.py` covers `win_percentage()` with normal, undefeated, and winless cases — a good start on a test suite.

### Auto-generated slugs
Both `Team` and `Conference` override `save()` to auto-generate URL slugs on first creation, which is the correct Django pattern.

---

## Issues

### `win_percentage` raises `ZeroDivisionError` on 0-0 record
```python
def win_percentage(wins, losses):
    total_games = wins + losses
    percent_wins = round((wins / total_games) * 100, 2)
```
The docstring acknowledges this edge case but leaves it unhandled. Passing `wins=0, losses=0` raises `ZeroDivisionError`. Since this is called from `TeamSeasonStats.save()`, any import of a team with no games will corrupt the sync. This should return `0.0` or `None` when `total_games == 0`.

### `Conference.save()` missing docstring
`Team.save()` has a detailed docstring; `Conference.save()` has none. Consistency matters in a well-documented codebase.

### Inconsistent indentation in `models.py`
`Team`'s methods use 2-space indentation while the surrounding class uses 2 spaces (matching Django's own convention), but `TeamSeasonStats.save()` and its `Meta` class use inconsistent spacing around `:` operators:
```python
class Meta :
    unique_together = ('team', 'season')
```
The space before `:` is not PEP 8 compliant.

### Context dict key starts with a digit
```python
context['3pt_pct'] = json.dumps(off_3pt_pct)
```
String keys beginning with digits are valid in Python dicts, but they cannot be accessed with dot notation in Django templates (e.g., `{{ 3pt_pct }}` is a syntax error). The template must use `{{ stat.3pt_pct }}` or the view must rename this to `three_pt_pct`.

### `TeamListView.get_queryset` is redundant
```python
def get_queryset(self):
    return Team.objects.all()
```
`ListView` returns `Model.objects.all()` by default when `model` is set. This override does nothing and can be removed.

### `sync_all_season_stats` builds team lookup by school name
```python
team_lookup = {t.school.lower(): t for t in Team.objects.all()}
```
The docstring explains this is necessary because the stats API's `teamId` differs from the teams API's `id`. This is a reasonable workaround, but it means any school name mismatch between the two API endpoints silently drops that team's stats (counted as `ignored_count`). A warning log for unexpectedly high ignored counts would help detect drift.

### No view tests
Only `stats.win_percentage` is tested. Views, models, and services have no test coverage. Adding tests for `TeamDetailView` context data and the sync functions (with mocked API responses) would significantly increase confidence.

---

## Summary

| Dimension            | Rating |
|----------------------|--------|
| Organization         | ★★★★★ |
| Readability          | ★★★★★ |
| Correctness          | ★★★★☆ |
| Error handling       | ★★★★★ |
| Security             | ★★★★☆ |
| Testing              | ★★☆☆☆ |
| **Overall**          | **★★★★☆** |

OpenCourt is the strongest codebase in this set. It follows Django conventions, documents its code thoroughly, handles API failures gracefully, and has a clean service/model/view separation. The main gaps are the unhandled division-by-zero in `win_percentage`, the digit-prefixed context key, and limited test coverage beyond the pure stats functions.
