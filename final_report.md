# OpenCourt Stats — Final Report

- **Title:** OpenCourt Stats
- **Team Name:** OpenCourt
- **Team Members:** Kenneth Hinman · Alex Worthington · Jackson Murphy · Samuel Bombrys
- **Live URL:** https://cs340-opencourt.up.railway.app/
- **Repository:** https://github.com/cs340-26/OpenCourt

---

## Section 1: Introduction

OpenCourt Stats is a free, open-source college basketball (CBB) analytics dashboard built in Django. It pulls team, game, season-stat, and poll data from the CBBData API, presents that data through interactive visualizations, and uses an XGBoost classifier to predict outcomes for upcoming games. The site is publicly deployed on Railway with a Supabase Postgres database and is kept current by a daily incremental sync.

The motivation was simple: the most analytically rigorous CBB sites (EvanMiya, CBB Analytics) hide their best content behind subscriptions, leaving casual fans with only surface-level metrics like points-per-game. We wanted to make advanced efficiency stats and forecasting freely available, with an interface fans can use without prior statistics training.

Our approach was to build a thin Django service over a Postgres mirror of the CBBData API: a sync layer pulls and normalizes data, six ORM models store it, seven class-based views render dashboards, and a separate predictions module loads a trained XGBoost model to forecast games. Tailwind v4 + DaisyUI v5 handle styling and ApexCharts handles visualizations.

The only meaningful change from the proposal was the prediction stack: the proposal listed scikit-learn or PyTorch as candidates, but we settled on XGBoost after early experiments because the differential-feature design fit a gradient-boosted classifier better than either alternative. Player-level stats — a "nice to have" in the proposal's descoping list — were not built. Everything in the "must have" and "should have" tiers shipped.

**Result:** the project was a success. All MVP goals were met, the stretch-goal prediction model shipped and is live in production, and the application has been deployed at https://cs340-opencourt.up.railway.app/ since Sprint 4.

---

## Section 2: Customer Value

Three changes from the proposal are worth recording.

**Change 1 — Prediction stack (2026-03-15).** The proposal proposed scikit-learn or PyTorch for the prediction model; we shipped an XGBoost classifier instead. *Motivation:* the differential-feature design (10-feature vector of paired stat deltas) is a natural fit for tree-based gradient boosting, and XGBoost gave better calibration than logistic regression in our early notebook trials with fewer hyperparameters to tune than a PyTorch network. *Implication:* the customer-facing functionality is unchanged — users still get a binary home/away prediction — but the model trains faster and is easier to retrain as the season progresses.

**Change 2 — Upcoming Games view (2026-03-22).** The proposal described predictions surfacing on a generic team page; the final product instead exposes them through a dedicated `/upcoming/` page that shows upcoming matchups *with* predictions and completed games *with* prediction accuracy alongside actual results. *Motivation:* user-testing inside the team showed that fans want a single page where they can scan predictions for the week, not hunt through team pages one at a time. *Implication:* the predictions feature feels first-class rather than buried, and post-hoc accuracy is now visible to users, which builds trust in the model.

**Change 3 — Player-level stats deferred.** The proposal listed player-level stats in the "nice to have" tier. They were not built. *Motivation:* the CBBData API endpoints for player data require separate sync logic and roughly double our database footprint, and time was better spent hardening the prediction model and finishing deployment. *Implication:* none for the MVP — the descoping plan explicitly anticipated this — but it is the most obvious next-iteration feature.

---

## Section 3: Technology

### Architecture

The system follows a standard layered Django architecture with a clearly separated data pipeline and prediction module:

```
Client (browser)
   │  Tailwind v4 + DaisyUI v5 + ApexCharts (CDN)
   ▼
Django App
   ├── Views (7 CBVs)  ──► Templates (Jinja2)
   ├── Models (6: Conference, Team, TeamSeasonStats, Game,
   │           GameTeamStats, Ranking)
   ├── Services layer (fetch.py / sync.py / update.py / helpers.py)
   ├── Predictions module (features.py / predict.py / model.py /
   │                       train_model.py / evaluate.py)
   └── Management commands (sync_data, update_data, sync_teams, …)
   ▼
External: CBBData API · Database: SQLite (dev) / Supabase Postgres (prod)
Hosting: Railway · Static files: WhiteNoise · WSGI: Gunicorn
```

The architecture did not change meaningfully from the proposal. The two additions are (a) a dedicated `predictions/` package separating ML code from app code, and (b) WhiteNoise + Gunicorn + Railway cron in the deployment layer, none of which were specified in the original proposal diagram.

### Design and Implementation

**Data pipeline.** `services/fetch.py` wraps the CBBData API with retry/backoff for 429 responses (honoring `Retry-After`). `services/sync.py` performs full backfills in foreign-key order (Conferences → Teams → Season Stats → Games → Game Team Stats → Rankings). `services/update.py` performs a daily 5-call incremental refresh of the most recent 30 days. Both are idempotent via `update_or_create()`, and both are exposed as Django management commands.

**Predictions.** `predictions/features.py` builds a 10-element differential feature vector for each matchup (effective FG%, turnover rate, point differential, pace, free-throw rate, offensive rating, blocks, offensive rebound %, assist-to-turnover ratio, home-court flag). `predictions/predict.py` loads a pickled XGBoost classifier from `models/final_model/` (cached as a module-level singleton) and returns a home-win probability. The training pipeline is offline (`train_model.py` / `evaluate.py`) so the production app never trains, only predicts.

**Views and templates.** Seven class-based views cover the Home, About, Team list, Team detail, Conference list, Rankings, and Upcoming Games pages. Templates use DaisyUI components, with reusable fragments (`team_card.html`, `conference_card.html`, `conference_filter.html`) factored into `templates/opencourt/components/`. Chart rendering is per-page in `extra_js` blocks.

### What works

- All MVP pages render against live Supabase data (`/`, `/teams/`, `/conferences/`, `/rankings/`, `/upcoming/`, `/<slug>/`, `/about/`).
- Daily incremental sync runs as a Railway cron job and keeps production data current.
- The prediction model is integrated end-to-end: features → model → page render. Predictions appear on `/upcoming/` for future games and prediction accuracy is shown alongside actual results for completed games.
- Conference filtering, team search, week-by-week ranking navigation, and per-game expandable box scores all function on production.

### What does not work / known limitations

- `build_features()` in `predictions/features.py` has a documented `ZeroDivisionError` risk when `off_possessions = 0`. This case has not been observed in production data and is flagged in the test suite as a known bug.
- Player-level stats are not implemented (deferred per Section 2 above).
- Mobile layout polish on the `/upcoming/` page lags the rest of the site at very narrow widths.

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

We replaced the original 4-test stub with a full test suite organized by module: `test_models.py`, `test_views.py`, `test_urls.py`, `test_stats.py`, `test_services.py`, and `test_predictions.py`. The suite uses `mock.patch` to fake CBBData API calls in service tests and `MagicMock` to stub the XGBoost model in prediction tests, so the entire suite runs without network access or the model pickle file.

| Test file | Approx. count | What it covers |
|---|---:|---|
| `test_stats.py` | 14 unit tests | `win_percentage()` and `point_differential()` including zero-games and float-input edges |
| `test_urls.py` | 7 routing tests | URL resolver for every public route + slug routing |
| `test_views.py` | 40+ integration tests | Every CBV: 200 responses, context keys, template choice, filter/search behavior |
| `test_models.py` | 30+ tests | Model `__str__`, slug auto-generation, FK constraints, default values |
| `test_services.py` | 20+ tests | `fetch.py` retry/backoff with mocked 429s, `sync.py` `update_or_create()` paths, `update.py` window selection |
| `test_predictions.py` | 16+ tests | `build_features()` differential math, model-load singleton, `make_predictions()` error paths |

**Results:** the full suite passes. The TA evaluation on 2026-04-23 graded the test suite 38/40 on Automated Testing and called it "the strongest functional correctness submission in the class." The one ZeroDivisionError noted above is the only known failing edge case, and it is documented in the test code rather than triggered in production.

---

## Section 4: Team

The four proposal roles stayed the same end-to-end. There was no rotation.

| Member | Role | Primary contributions |
|---|---|---|
| **Kenneth Hinman** | Project Manager / Backend Lead | Django architecture, models, all 7 views, deployment to Railway + Supabase, CI/PR review |
| **Alex Worthington** | UI/UX / Frontend Lead | All HTML templates, DaisyUI integration, responsive layout, component refactor |
| **Jackson Murphy** | Data Pipeline / API Lead | `services/fetch.py`, `services/sync.py`, `services/update.py`, all 7 management commands |
| **Samuel Bombrys** | Analytics / ML Lead | XGBoost model design and training, `predictions/` module, feature engineering, evaluation |

Contributions were roughly equal in time invested. Kenneth and Jackson carried more total commits because their work (architecture, sync pipeline, management commands) cut across more files; Alex and Samuel produced fewer commits but each owned a self-contained, high-value surface (the entire UI, the entire ML pipeline). The team met twice a week, with backend/data pairing as needed during sync-pipeline integration in Sprint 2 and again during the predictions wiring in Sprint 4.

---

## Section 5: Project Management

We hit every milestone from the proposal schedule on or near its date:

| Milestone | Planned | Actual | Status |
|---|---|---|---|
| Project scaffolding & base UI | ~Feb 18 | Feb 17 | On time |
| Models + CBBData API integration | ~Feb 25 | Feb 25 | On time |
| Team list, conference, team detail pages | ~Mar 4 | Mar 6 | +2 days |
| ApexCharts + Four Factors (MVP) | ~Mar 11 | Mar 11 | On time |
| Predictions foundation | ~Mar 18 | Mar 20 | +2 days |
| Predictions in UI | ~Mar 25 | Mar 24 | On time |
| Production deployment | ~Apr 1 | Mar 31 | On time |
| Final polish + presentation | ~Apr 9 | Apr 9 | On time |

Two items in the proposal were intentionally not built: player-level stats and historical-trend pages beyond the per-team chart. Both were "nice to have" tier in the proposal's descoping plan, and we descoped them in Sprint 4 to focus on test coverage and the production deploy — the right tradeoff in retrospect.

The only goal we did not fully meet was the customer-side success metric "≥200 unique users during the March Madness window." The site went live on Mar 31, after the tournament's first weekend, so the realistic March Madness window was compressed to about a week. We did not formally collect usage analytics, so we cannot report on this metric one way or the other. All other proposal goals (model accuracy vs. baseline, MVP feature scope, production deployment, free public access with no paywall) were met.

---

## Section 6: Reflection

### What went well

- **Architecture discipline.** Treating `services/`, `predictions/`, and `management/commands/` as separate layers from day one paid off — the predictions module was added in Sprint 4 with no churn elsewhere in the codebase. The TA review specifically called out the test suite and documentation as the strongest in the class.
- **Realistic descoping.** The proposal's must/should/nice-to-have tiers turned out to be a load-bearing decision. When testing and deployment ran tight in Sprint 4, we had a pre-agreed list of what to cut (player stats, historical trends) and lost no time debating it.
- **Production deployment.** Going live on Railway + Supabase before the final sprint meant we shook out the real-world bugs (static files, secret management, cron timing) in time to fix them, and demo'd against the live site rather than a localhost screenshot.

### What didn't go as well

- **Testing came late.** Sprint 1–3 left us with four unit tests for one helper file. The full test suite was written in Sprint 4, which is much later than it should have been. It worked out — the suite ended up strong — but the team accepted real risk for several weeks by relying on manual testing.
- **No formal user feedback.** The proposal listed a survey-rating success metric, but we never ran a survey. We collected anecdotal feedback from CBB-fan friends, which informed the `/upcoming/` page design, but nothing systematic.
- **Two-developer files.** `views.py` (1,379 lines) and `models.py` (710 lines) grew large enough that they should have been split by feature/domain. The early grading review flagged this and we did not refactor.

### Did the project succeed?

Yes. We shipped a free, publicly accessible CBB analytics dashboard with advanced efficiency stats, interactive visualizations, weekly poll views, and a working prediction model — all within an 8-week sprint plan, deployed to production, with comprehensive test coverage and clean documentation. The product fulfills the core value proposition stated in the proposal: advanced college basketball analytics, free, no subscription, no account required. Everything in the proposal's "must have" and "should have" tiers is live, the stretch-goal prediction model is integrated, and the codebase is in good enough shape to keep iterating after the semester ends.
