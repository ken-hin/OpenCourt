# OpenCourt Stats — Final Report

- **Title:** OpenCourt Stats
- **Team Name:** OpenCourt
- **Team Members:** Kenneth Hinman · Alex Worthington · Jackson Murphy · Samuel Bombrys
- **Repository:** https://github.com/cs340-26/OpenCourt

---

## Section 1: Introduction

OpenCourt Stats is a free, open-source college basketball (CBB) analytics dashboard built in Django. It pulls team, game, season-stat, and poll data from the CBBData API, presents that data through interactive visualizations, and uses an XGBoost classifier to predict outcomes for upcoming games.

The motivation: the most analytically rigorous CBB sites (EvanMiya, CBB Analytics) hide advanced content behind subscriptions, leaving casual viewers with only surface-level metrics like points-per-game. We wanted to make advanced efficiency stats and forecasting freely available, with an interface usable without a statistics background.

Our approach was a thin Django service over a Postgres mirror of the CBBData API: a sync layer pulls and normalizes data, six ORM models store it, seven class-based views render dashboards, and a separate predictions module loads a trained XGBoost model. Tailwind v4 + DaisyUI v5 handle styling and ApexCharts handles visualizations.

The only meaningful change from the proposal was the prediction stack: the proposal listed scikit-learn or PyTorch as candidates, but we shipped XGBoost because the differential-feature design fit a gradient-boosted classifier best. Player-level stats — a "nice to have" in the proposal's descoping list — were not built.

**Result:** all MVP goals were met and the stretch-goal prediction model shipped. The project was deployed to Railway + Supabase for the duration of the class. The Railway free trial has since ended, so the public site is no longer live, but the application runs identically from a local checkout and the deployment configuration is preserved in the repository.

---

## Section 2: Customer Value

Three changes from the proposal:

**Change 1 — Prediction stack (2026-03-15).** Proposal proposed scikit-learn or PyTorch; we shipped an XGBoost classifier instead. *Motivation:* the 10-feature differential vector fits tree-based gradient boosting well, with better calibration than logistic regression and fewer hyperparameters than a PyTorch network. *Implication:* user-facing functionality is unchanged — still a binary home/away prediction — but the model trains and retrains faster.

**Change 2 — Upcoming Games view (2026-03-22).** Proposal described predictions surfacing on a team page; we instead built a dedicated `/upcoming/` page that pairs predictions for upcoming games with prediction accuracy on completed games. *Motivation:* during internal team review, a single scannable page was clearly more useful than digging through individual team pages. *Implication:* predictions are first-class rather than buried, and accuracy is visible.

**Change 3 — Player-level stats deferred.** Listed as "nice to have" in the proposal and not built. *Motivation:* separate sync logic and roughly double the DB footprint; time was better spent on the model and the deployment. *Implication:* none for the MVP — descoping anticipated this — but it is the most obvious next-iteration feature.

---

## Section 3: Technology

### Architecture

Standard layered Django architecture with a separated data pipeline and prediction module:

```
Client (browser)
   │  Tailwind v4 + DaisyUI v5 + ApexCharts (CDN)
   ▼
Django App
   ├── Views (7 CBVs) ──► Templates (Jinja2)
   ├── Models (6: Conference, Team, TeamSeasonStats, Game,
   │           GameTeamStats, Ranking)
   ├── Services (fetch.py / sync.py / update.py / helpers.py)
   ├── Predictions (features.py / predict.py / model.py /
   │                train_model.py / evaluate.py)
   └── Management commands (sync_data, update_data, sync_teams, …)
   ▼
External: CBBData API · Database: SQLite (dev) / Supabase Postgres
Hosting: Railway (now retired) · Static: WhiteNoise · WSGI: Gunicorn
```

The architecture did not change meaningfully from the proposal. Additions were a dedicated `predictions/` package separating ML from app code, and a WhiteNoise + Gunicorn + Railway-cron deployment layer.

### Design and Implementation

**Data pipeline.** `services/fetch.py` wraps the CBBData API with retry/backoff for 429 responses. `services/sync.py` performs full backfills in foreign-key order. `services/update.py` performs a daily 5-call incremental refresh of the most recent 30 days. Both are idempotent via `update_or_create()` and exposed as Django management commands.

**Predictions.** `predictions/features.py` builds a 10-element differential feature vector per matchup (effective FG%, turnover rate, point differential, pace, FT rate, offensive rating, blocks, ORB%, A:TO, home-court flag). `predictions/predict.py` loads a pickled XGBoost classifier (cached as a module-level singleton). Training is offline so the app only predicts.

**Views and templates.** Seven CBVs cover Home, About, Team list, Team detail, Conference list, Rankings, and Upcoming Games. Reusable template fragments live in `templates/opencourt/components/`.

### What works

- All MVP pages render against the synced database (`/`, `/teams/`, `/conferences/`, `/rankings/`, `/upcoming/`, `/<slug>/`, `/about/`).
- Daily incremental sync runs cleanly via the `update_data` management command.
- The prediction model is integrated end-to-end and surfaces predictions on `/upcoming/` alongside prediction accuracy for completed games.
- Conference filtering, team search, week-by-week ranking navigation, and per-game expandable box scores all function correctly.

### What does not work

- `build_features()` has a documented `ZeroDivisionError` risk when `off_possessions = 0`; not observed in real data and flagged in the test suite.
- Player-level stats are not implemented (deferred per Section 2).
- Mobile layout on `/upcoming/` is rougher than the rest of the site at very narrow widths.
- The site is no longer publicly accessible since the Railway free trial expired at the end of the class.

### Example: running the daily sync from the command line

```
$ uv run python manage.py update_data
[update] Fetching last 30 days of games...
[update] Synced 47 games, 14 created, 33 updated.
[update] Refreshing TeamSeasonStats for 2025-26 season... done (358 teams).
[update] Refreshing rankings (AP + Coaches, week 14)... done.
[update] Complete in 11.3s.
```

### Tests

We replaced the original 4-test stub with a full test suite organized by module. The suite mocks CBBData API calls and the XGBoost model, so it runs without network access or the model pickle file.

| Test file | Approx. count | What it covers |
|---|---:|---|
| `test_stats.py` | 14 unit tests | `win_percentage()`, `point_differential()`, zero-games and float-input edges |
| `test_urls.py` | 7 routing tests | URL resolution for every public route + slug routing |
| `test_views.py` | 40+ integration tests | Every CBV: 200 responses, context keys, template choice, filter/search |
| `test_models.py` | 30+ tests | `__str__`, slug auto-generation, FK constraints, defaults |
| `test_services.py` | 20+ tests | `fetch.py` retry/backoff, `sync.py` upsert paths, `update.py` window selection |
| `test_predictions.py` | 16+ tests | `build_features()` math, model-load singleton, `make_predictions()` errors |

**Results:** the full suite passes. The only known failing edge case is the `ZeroDivisionError` noted above, which is documented in the test code rather than triggered in production.

---

## Section 4: Team

The four proposal roles stayed the same end-to-end. No rotation.

| Member | Role | Primary contributions |
|---|---|---|
| **Kenneth Hinman** | Project Manager / Backend Lead | Django architecture, models, all 7 views, deployment, PR review |
| **Alex Worthington** | UI/UX / Frontend Lead | All HTML templates, DaisyUI integration, responsive layout |
| **Jackson Murphy** | Data Pipeline / API Lead | `services/` modules and all management commands |
| **Samuel Bombrys** | Analytics / ML Lead | XGBoost model, `predictions/` module, feature engineering, evaluation |

Contributions were roughly equal in time invested. Kenneth and Jackson carried more total commits because their work cut across more files; Alex and Samuel produced fewer commits but each owned a self-contained, high-value surface (the UI and the ML pipeline).

---

## Section 5: Project Management

We hit every milestone on or near its scheduled date:

| Milestone | Planned | Actual | Status |
|---|---|---|---|
| Project scaffolding & base UI | ~Feb 18 | Feb 17 | On time |
| Models + CBBData API integration | ~Feb 25 | Feb 25 | On time |
| Team / conference / detail pages | ~Mar 4 | Mar 6 | +2 days |
| ApexCharts + Four Factors (MVP) | ~Mar 11 | Mar 11 | On time |
| Predictions foundation | ~Mar 18 | Mar 20 | +2 days |
| Predictions in UI | ~Mar 25 | Mar 24 | On time |
| Production deployment | ~Apr 1 | Mar 31 | On time |
| Final polish + presentation | ~Apr 9 | Apr 9 | On time |

Player-level stats and historical-trend pages beyond the per-team chart were intentionally not built. Both were "nice to have" tier and descoped in Sprint 4 to make room for test coverage and deployment.

The one goal we did not formally meet was the customer-side metric "≥200 unique users during the March Madness window." The site went live on Mar 31, after the first weekend of the tournament, and we did not instrument usage analytics. All other proposal goals (model accuracy vs. baseline, MVP feature scope, production deployment, free public access) were met.

---

## Section 6: Reflection

### What went well

- **Architecture discipline.** Treating `services/`, `predictions/`, and `management/commands/` as separate layers from day one paid off — the predictions module was added in Sprint 4 with no churn elsewhere in the codebase.
- **Realistic descoping.** The proposal's must/should/nice-to-have tiers turned out to be load-bearing. When time ran tight in Sprint 4, we already had a pre-agreed list of what to cut and lost no time debating it.
- **Production deployment.** Going live before the final sprint meant we shook out real-world bugs (static files, secret management, cron timing) in time to fix them and demo against the live site rather than a localhost screenshot.

### What didn't go well

- **Testing came late.** Sprints 1–3 left us with four unit tests for one helper file. The full suite was written in Sprint 4 — much later than it should have been. The result worked out, but the team accepted real risk for several weeks by leaning on manual testing.
- **No external user feedback.** The proposal listed a survey-rating success metric, but we only validated decisions internally within the team. No outside users were surveyed.
- **Oversized files.** `views.py` (~1,379 lines) and `models.py` (~710 lines) grew large enough that they should have been split by feature/domain. We did not refactor.

### Did the project succeed?

Yes. We shipped a free CBB analytics dashboard with advanced efficiency stats, interactive visualizations, weekly poll views, and a working prediction model within an 8-week plan, deployed to production for the duration of the class, with comprehensive test coverage and clean documentation. Everything in the proposal's "must have" and "should have" tiers is present, the stretch-goal prediction model is integrated, and the codebase is in good shape to keep iterating after the semester ends.
