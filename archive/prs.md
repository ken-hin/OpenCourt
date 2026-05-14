## #75 — Add final report (DOCX and Markdown)

**State:** MERGED | **Author:** ken-hin | **documentation/final-report → main** | **Created:** 2026-05-13T14:00:48Z

- Add final_report.md and final_report.docx containing the project's final report for the OpenCourt Stats application.
- The markdown includes the introduction, customer-value changes, architecture and implementation details, prediction pipeline, tests, team roles, project timeline, known limitations, and reflections; it also links to the live site and repository.
- This provides the deliverable documentation for the project.

---

## #74 — Update dependencies and regenerate lockfile

**State:** MERGED | **Author:** ken-hin | **update/update-deps → main** | **Created:** 2026-05-08T02:16:09Z

- Bump several Python dependencies and update uv.lock to lock the new versions.

Notable changes:
- django >=6.0.5
- cbbd ==1.27.3
- psycopg[binary] ==3.3.4
- gunicorn ==26.0.0
- matplotlib >=3.10.9.

These updates apply minor/patch fixes and pin specific packages for reproducible installs.

---

## #73 — Move files into docs/ and grading/ directories

**State:** MERGED | **Author:** ken-hin | **refactor/grading-docs → main** | **Created:** 2026-05-08T02:09:55Z

- Organize repository by moving documentation and grading files into subfolders.
- FinalPresentation.pdf and user story markdowns were moved to docs/, and all grading-related markdowns were moved to grading/ (moves preserved file content).
- This cleans up the repo root and groups related resources.

---

## #72 — Documentation/head head

**State:** MERGED | **Author:** ken-hin | **documentation/head-head → main** | **Created:** 2026-05-06T13:06:20Z



---

## #71 — Enhance/predictions calendar

**State:** MERGED | **Author:** ken-hin | **enhance/predictions-calendar → main** | **Created:** 2026-05-06T03:32:13Z



---

## #70 — Add cache warmer and batch prediction [closes #66]

**State:** MERGED | **Author:** ken-hin | **fix/general-refactoring → main** | **Created:** 2026-05-05T03:55:01Z

- Add a CacheWarmerMiddleware and background warmer to precompute season-wide model accuracy (opencourt/middleware.py).
- Introduce a process-cached prediction model loader and helpers (_get_predict_model, _predict_home_win) and a batched season accuracy computation using pandas/NumPy to avoid per-game model loads (opencourt/views.py).
- Update UpcomingView to use the cached model and cached accuracy, falling back to synchronous warm when needed.
- Increase Gunicorn timeout to 120s in Procfile and railway.json to avoid worker timeouts during cold starts.
- Misc: defensive logging, DB connection cleanup in warmer thread, and cache TTLs for warm results.

---

## #69 — Enhance/model [closes #57]

**State:** MERGED | **Author:** ken-hin | **enhance/model → main** | **Created:** 2026-04-30T17:25:58Z



---

## #68 — Bug/data fix [closes #65]

**State:** MERGED | **Author:** Jackson-Murphy04 | **bug/dataFix → main** | **Created:** 2026-04-28T17:57:27Z

closes #65 

---

## #67 — Refactor team details layout and mobile nav [closes #64]

**State:** MERGED | **Author:** asworthington | **UI-and-team_detail-changes → main** | **Created:** 2026-04-23T14:45:45Z

Added site-wide footer. Tweaked mobile-responsiveness (mobile now has dropdown menu for navbar. Fixed per-game averages and turnover ratio in team_details (wrong stats were showing). Also added Four Factors to historical data in teams_details. Issue #64 

---

## #63 — UI improvements

**State:** MERGED | **Author:** asworthington | **ui-improvements → main** | **Created:** 2026-04-16T15:44:36Z

Issue #56 

Let me know if you have any questions

---

## #62 — Refactor tests into package and add modules [closes #61]

**State:** MERGED | **Author:** ken-hin | **enhance/add-tests → main** | **Created:** 2026-04-14T16:15:27Z

- Remove the single monolithic opencourt/tests.py and introduce a tests package (opencourt/tests/) with __init__.py and multiple focused test modules.
- Adds comprehensive unit tests covering models, predictions, services, stats, URLs, and views (e.g. test_models.py, test_predictions.py, test_services.py, test_stats.py, test_urls.py, test_views.py).
- Tests include: factory helpers, model behavior, feature-building and model loading mocks, service/API mapping, date/season helpers, and routing/view checks to improve organization and coverage.

---

## #60 — Redesign UI and fix year stats across the site closes #55

**State:** MERGED | **Author:** Jackson-Murphy04 | **enhance/predictions → main** | **Created:** 2026-04-14T15:20:42Z

site wide UI improvements, added about page and home page, fixed small issue on upcoming page showing wrong year record

---

## #59 — Add Railway & Supabase deployment config [closes #58]

**State:** MERGED | **Author:** ken-hin | **feature/chron-functions → main** | **Created:** 2026-04-10T13:03:38Z

- Prepare project for production deployment on Railway + Supabase
- Add a detailed DEPLOY.md guide, Procfile, and railway.json (collectstatic → migrate → gunicorn start).
- Update config/settings.py to load env vars, use dj-database-url for DATABASE_URL, enable WhiteNoise and STATIC_ROOT for static file serving, and make DEBUG/ALLOWED_HOSTS env-driven.
- Add production dependencies to pyproject.toml (whitenoise, dj-database-url, psycopg, gunicorn)
- Register additional models in opencourt/admin.py.
- README.md updated to document architecture, data sync/deploy workflow, and developer instructions.

---

## #54 — Refactor team card contrast, fix team filtering, and add filter component [closes #53]

**State:** MERGED | **Author:** ken-hin | **fix/team-card-filtering → main** | **Created:** 2026-04-06T18:24:33Z

## Fix conference filtering and prediction display on team cards
 
- Fix conference filter not hiding/showing team cards by renaming the inner card component's class from `team-card` to `team-card-inner`, preventing `querySelectorAll('.team-card')` from matching both the filterable wrapper and the styled inner div
- Extract js from 'main.js' to `card_contrast.js` 
- Update 'card_contrast.js' and contrast-related CSS rules to target `.team-card-inner` so text color logic still applies correctly.
- Extract conference filter markup into a reusable `conference_filter.html` component

---

## #52 — Final prod UI [closes #47]

**State:** MERGED | **Author:** asworthington | **final-prod-ui → main** | **Created:** 2026-04-06T16:11:59Z

Issue #47 


---

## #51 — Integrate XGBoost prediction model into matchups page [closes #48]

**State:** MERGED | **Author:** ken-hin | **feature/integrate-model → main** | **Created:** 2026-04-05T17:02:24Z

## Summary

- Embed the XGBoost model into the Upcoming matchups view so each game card shows a win/loss prediction based on both teams' season stats
- Add a results mode (`?mode=results`) that displays completed games alongside their predictions, showing whether the model was correct with an overall accuracy banner
- Fix a numpy comparison bug where home-win predictions were silently dropped due to element-wise array evaluation in the prediction guard check
- Fix season year calculation so the correct stats (2025, not 2026) are loaded during the spring semester of a basketball season
- Fix naive datetime warnings by using timezone-aware comparisons for DateTimeField queries
- Add `.ipynb_checkpoints/` to `.gitignore` and remove hardcoded `NPM_BIN_PATH` from `settings.py`

## Changed files

- **`opencourt/views.py`** — Rewrote `UpcomingView` to support dual modes (upcoming predictions and completed results), added `enrich()` pipeline that runs `predict_game` per matchup, fixed season year logic and timezone handling
- **`templates/opencourt/head_head.html`** — Added mode toggle, accuracy banner, final score display with prediction correctness indicators, and date tab navigation for both modes
- **`opencourt/predictions/predict.py`** — Updated model file path
- **`config/settings.py`** — Removed hardcoded `NPM_BIN_PATH` override
- **`.gitignore`** — Added Jupyter notebook checkpoints
- **`pyproject.toml` / `uv.lock`** — Added `xgboost`, `numpy`, and `joblib` dependencies

## Test plan

- [ ] Load `/matchups` and verify every game card shows a prediction (home and away wins both appear)
- [ ] Load `/matchups?mode=results` and verify completed games show final scores with correct/incorrect indicators
- [ ] Verify accuracy banner displays at the top of results mode
- [ ] Confirm no console warnings about naive datetimes
- [ ] Run `python manage.py tailwind start` without a hardcoded `NPM_BIN_PATH` (ensure `.env` has it if npm isn't on PATH)

---

## #50 — Refactor services into package, add updater [closes #49]

**State:** MERGED | **Author:** ken-hin | **feature/update-data-functions → main** | **Created:** 2026-04-05T14:45:06Z

# PR: Refactor Services Module & Add Incremental Updates
 
## Summary
 
This refactor improves modularity, testability, and maintainability of the data layer while keeping all existing imports working. It also adds a new management command for lightweight daily updates and fixes an environment-specific config issue.
 
---
 
## Changes
 
### 1. Split `services.py` into a `services/` package
 
The monolithic `opencourt/services.py` (~1,500 lines) has been replaced with a structured package under `opencourt/services/`:
 
| File | Purpose |
|------|---------|
| `helpers.py` | Shared constants (API endpoints, season years, retry config), the API client factory, lookup builders for teams/conferences, and all `_build_*_defaults()` functions used by both sync and update flows. |
| `fetch.py` | Every `fetch_*` function that talks to the CBBData API, including retry logic with exponential backoff for rate-limited (HTTP 429) responses. |
| `sync.py` | Full-season `sync_*` functions for bulk-loading the database from scratch (teams, conferences, season stats, rankings, games, game-team stats). Use these when initializing or rebuilding the entire DB. |
| `update.py` | Incremental `update_*` functions that only pull data for the current season and the last 30 days of games. These are meant for routine daily refreshes where a full sync would be wasteful. |
| `__init__.py` | Re-exports every public function from the submodules so that existing imports like `from opencourt.services import sync_games` continue to work with zero changes elsewhere in the codebase. |
 
No changes are needed in views, management commands, or any other file that previously imported from `opencourt.services`.
 
### 2. Add `update_data` management command
 
A new Django management command (`python manage.py update_data`) runs all five incremental update functions in dependency order:
 
1. `update_teams` — refreshes the teams table
2. `update_season_stats` — pulls current-season stats only
3. `update_games` — fetches games from the last 30 days instead of the full Nov–May window
4. `update_game_team_stats` — fetches box-score stats for the same 30-day window
5. `update_rankings` — pulls current-season rankings
 
This drastically reduces the number of API calls compared to a full `sync_*` run, making it suitable for a daily cron job or manual refresh during the season.
 
### 3. Remove hardcoded `NPM_BIN_PATH` from `settings.py`
 
The commented-out line `NPM_BIN_PATH = r"C:\Program Files\nodejs\npm.cmd"` has been removed from `config/settings.py`. The setting is already read from your `.env` file via `os.environ.get('NPM_BIN_PATH', 'npm')` on line 67, which falls back to `'npm'` if unset (works when npm is on your system PATH).
 
**Action required:** If `tailwind start` fails with a "node.js and/or npm is not installed" error, add your local npm path to your `.env` file:
 
```bash
# macOS (Apple Silicon)
NPM_BIN_PATH=/opt/homebrew/bin/npm
 
# macOS (Intel)
NPM_BIN_PATH=/usr/local/bin/npm
 
# Windows
NPM_BIN_PATH=C:\Program Files\nodejs\npm.cmd
```
 
Since `.env` is gitignored, this keeps machine-specific paths out of the shared codebase.

---

## #46 — Feature/head to head view closes #43

**State:** MERGED | **Author:** Jackson-Murphy04 | **feature/headToHeadView → main** | **Created:** 2026-03-31T00:46:22Z

head to view page done still likely needs some visual updates here and there but features all in place for now 

*** not sure what to do when no futrue games are scheduled in a week or so might have to add some fake games to database to show how this page works and for testing***

---

## #45 — Feature/initial model

**State:** MERGED | **Author:** Sbombr | **feature/Initial_model → main** | **Created:** 2026-03-27T15:23:43Z

Added the prediction function accessible through predict.py make_predictions function. It takes in two TeamSeasonClassifiers: team_a and team_b, home_advantage where 1 = team_a, -1 = team_b, and 0 = neither. There is a last optional parameter for the path location of the model file.

---

## #44 — Implement rankings view and dual-poll template

**State:** MERGED | **Author:** ken-hin | **alex → main** | **Created:** 2026-03-26T17:11:26Z

Add RankingsListView to render AP Top 25 and Coaches Poll side-by-side with week selector and server-driven ranking queries. Import Ranking model and use subqueries to annotate each ranking entry with latest TeamSeasonStats (wins, losses, offensive/defensive points, point margin). Provide context variables (ap_rankings, coaches_rankings, poll dates, available_weeks, selected_week, conference_list). Update templates/opencourt/rankings.html to a two-column layout, add week dropdown, and remove the previous single list + client-side search/sort scripts. Also fix the TeamSeasonStats subquery filter to reference team__pk and order rankings by ranking.

---

## #42 — sync data command now pulls week by week top 25 rankings for coach an…

**State:** MERGED | **Author:** Jackson-Murphy04 | **feature/ranking-data-Jackson → main** | **Created:** 2026-03-24T16:37:20Z

sync data runs sync rankings
add sync rankings
models.py now has sync_all_rankings

---

## #41 — Update/teams list page

**State:** MERGED | **Author:** ken-hin | **update/teams-list-page → main** | **Created:** 2026-03-24T16:30:17Z



---

## #39 — Revisions based on code_quality.md

**State:** MERGED | **Author:** asworthington | **alex → main** | **Created:** 2026-03-24T14:52:41Z

Fixed the issues brought up in code_quality.md and changed the team_details game history chart to show the newest game at the top.

Issue #40 

---

## #38 — Feature/rankings page [closes #32]

**State:** MERGED | **Author:** asworthington | **feature/rankings-page → main** | **Created:** 2026-03-20T20:44:57Z

Corresponds to Issue #32 

---

## #37 — Add Game and GameTeamStats models with sync functionality and UI updates [closes #35]

**State:** MERGED | **Author:** ken-hin | **feature/head-to-head-matchups → main** | **Created:** 2026-03-20T15:43:26Z

## Summary

- Add `Game` and `GameTeamStats` models to store per-game results and box scores
- Add `sync_games` management command and service functions to pull game data from the CBBData API
- Work around the API's 3,000-row cap by splitting fetches into monthly date-range windows (Nov–May)
- Include postseason games (conference tournaments, NCAA, NIT)
- Display a scrollable schedule table on the team detail page with clickable rows that expand to show a 3-column box score comparison with color-coded progress bars
- Rearrange team detail layout: schedule table (right-aligned, scrollable) above a full-width Historical Data charts section

## Changes

- **`opencourt/models.py`** — New `Game` and `GameTeamStats` models with FK relationships to `Team`
- **`opencourt/services.py`** — `fetch_games_bulk()`, `fetch_game_team_stats_bulk()`, `sync_games()`, `sync_game_team_stats()` with monthly date-range windowing
- **`opencourt/management/commands/sync_games.py`** — Management command running game + box score sync
- **`opencourt/management/commands/sync_data.py`** — Added `sync_games` to the pipeline
- **`opencourt/views.py`** — `TeamDetailView` now queries games with prefetched `GameTeamStats` and builds a schedule context
- **`templates/opencourt/team_details.html`** — Schedule table with accordion box scores (progress bars colored by team `primary_color`), two-column layout with placeholder section, historical charts below
- **`migrations/0005_game_gameteamstats_and_more.py`** — Schema migration

## Test Plan

- [ ] Run `python manage.py migrate` and `python manage.py sync_games` — verify no errors and all months fetch data
- [ ] Open a team detail page and confirm the full season schedule appears (Nov through current date)
- [ ] Click a game row — verify the box score accordion expands with filled progress bars
- [ ] Confirm percentage stats (FG%, 3PT%, FT%, eFG%) cap at 100 and counting stats scale to the max of the two teams
- [ ] Verify postseason games appear in the schedule
- [ ] Check layout: schedule on the right, empty placeholder on the left, charts below under "Historical Data"

---

## #36 — Enhance team and conference management with new features and refactoring

**State:** MERGED | **Author:** ken-hin | **feature/conference-view → main** | **Created:** 2026-03-19T16:36:36Z

# Add conferences page with two-panel detail view

## Summary

- Add a conferences page with a two-panel layout: scrollable left sidebar of conference buttons (1/4 width) and a fixed right panel (3/4 width) that displays the selected conference's teams and current season stats
- Add `Team.current_season` property for clean template access to the latest season's stats, backed by `Prefetch` with `to_attr` to avoid N+1 queries
- Add comprehensive documentation across models.py, services.py, and views.py covering relationships, data flow, API field mapping, Four Factors glossary, and sync architecture
- Reduce stats sync window from 20 years to 9 years to cut sync time and storage
- Update team detail URL pattern to `<team-slug>/details`

## Changes

- `templates/opencourt/conferences.html` — new two-panel layout with JS toggle for conference selection
- `templates/opencourt/components/conference_card.html` — reusable detail card component with team list and current season records
- `templates/base.html` — add Conferences link to navbar
- `opencourt/models.py` — add `Team.current_season` property, expand docstrings with relationship diagram and stats glossary
- `opencourt/views.py` — add `ConferenceListView` with `Prefetch` optimization, document all views and context variables
- `opencourt/services.py` — document architecture, sync order, API field mapping, and retry behavior
- `opencourt/urls.py` — update team detail URL pattern

## Test plan

- [ ] Verify conferences page loads and shows only conferences with teams
- [ ] Click each conference button and confirm the right panel populates with team names and current season records
- [ ] Confirm `team.current_season.wins` renders correctly (not None/blank) for teams with stats
- [ ] Run `python manage.py sync_season_stats` and verify only the last 10 seasons are fetched
- [ ] Verify team detail page charts still render correctly after view/URL changes

---

## #31 — Feature/team season stats

**State:** MERGED | **Author:** ken-hin | **feature/team-season-stats → main** | **Created:** 2026-03-17T01:33:56Z

Prepare chart-ready team season data and add interactive charts to the team detail page; redesign team cards and team list UI; minor backend/statistics tweaks.

Summary of changes:
- views.py: Build JSON-serializable series and labels in TeamDetailView (wins, losses, win_pct, ratings, four-factors, points per game, etc.), fetch team by slug, and expose context used by client-side charts.
- team_details.html: New layout and ApexCharts initialization for line, radial, bar, and area charts using injected context variables.
- base.html: Wrap global chart/script includes in the extra_js block so pages can extend and append scripts.
- teams.html & components/team_card.html: Rework team card markup, add hover/link behavior, update filter UI to a dropdown, and simplify card grid/layout.
- stats.py: Add point_differential(scored_points, allowed_points) helper.
- services.py: Change STATS_START_YEAR from 25 to 20 (reduce seasons to sync).


New Managemnet Commands and Update Dependencies
Management commands:
- Split sync_data into three focused commands: sync_conferences,
  sync_teams, sync_season_stats — each runnable independently
- sync_data retained as an orchestrator via call_command()
- Dependency order documented in sync_data.py header comment

Dependencies:
- Added tqdm>=4.67.3 to pyproject.toml

These changes implement the frontend charts for team statistics, supply the necessary data from the view, and refresh the teams listing/cards and filter UI for navigation and presentation.

---

## #30 — Teams page UI, conference filtering, and model relationships — Closes #29

**State:** MERGED | **Author:** ken-hin | **feature/team-list-filter → main** | **Created:** 2026-03-09T20:04:45Z

## Summary
- Builds out the teams browsing experience with a filterable, animated
  card grid and individual team detail pages
- Introduces a proper `Conference` ForeignKey on `Team`
- Refactors the base template layout and extracts a reusable team card
  component
## Changes

### Models & data
- Replace the raw `conference` string field on `Team` with a `ForeignKey`
  to `Conference`; rename `conference_id` → `api_conference_id` to avoid
  a Django column collision with the FK

### Teams page
- Extract card markup into a reusable `team_card.html` component
- Add conference toggle filter buttons and a search bar
- Implement `conference_filter.js` with two animation layers.

### Team detail page
- Add `TeamDetailView`, register the `<slug:slug>/` URL route, and add
  the `team_details.html` template

### Base template & nav
- Add `{% block extra_js %}` for page-level script injection
- Remove the redundant Home nav link
- Simplify the `<main>` wrapper and clean up layout

---

## #28 — Implement fetch_conferences() sync_conferences() and sync data commands closes #18

**State:** MERGED | **Author:** Jackson-Murphy04 | **feature/data-sync → main** | **Created:** 2026-03-05T14:35:22Z

Implement fetch_conferences and sync_conferences

- Add fetch_conferences() to pull conference data from CBBData API
- Add sync_conferences() to upsert conferences into the database
- Update sync_data management command to sync conferences before teams
- Add Conference model import to services.py
- made my own api key added to .env 
- tested and ran sync 
- teams and confrences synced to data base

---

## #27 — Navbar and Team Page closes #19

**State:** MERGED | **Author:** asworthington | **alex-branch → main** | **Created:** 2026-03-04T14:51:49Z

Added teams.html to navbar. Built a rough draft of the teams.html page for the top 5 D1 conferences. Each team has their primary color as the background color for their card

(Issue #19)

---

## #26 — feature/conference model

**State:** MERGED | **Author:** ken-hin | **feature/conference-model → main** | **Created:** 2026-03-03T23:53:15Z

## Summary
- Add `Conference` model with auto-slug generation and admin registration
- Add `ConferenceListView` at `/conferences/` with URL routing
- Add `sync_data` management command (`python manage.py sync_data`) with full file header and styled terminal output
- Update `services.py` with structured error handling, per-record logging, and sync summary counters

Closes #17 

## Test plan
- [ ] Run `python manage.py migrate` — Conference migration applies cleanly
- [ ] Run `python manage.py sync_data` — syncs teams, prints styled success output
- [ ] Visit `/conferences/` — conference list page renders
- [ ] Visit `/admin/` — Conference model is browsable alongside Team
- [ ] Unset `CBB_API_KEY` and confirm `sync_data` logs a warning instead of crashing

---

## #25 — Sprint 3 stats addition

**State:** MERGED | **Author:** Sbombr | **sam-branch → main** | **Created:** 2026-03-03T20:03:15Z

Win percentage added in stats.py. Pace is already present in the api so I have it commented just in case. Points against is not given in the CBB data api so we may need to look into that.

---

## #24 — create user story for data synchronization feature #23 #18

**State:** MERGED | **Author:** Jackson-Murphy04 | **documentation/user-story-data-sync → main** | **Created:** 2026-03-03T17:13:29Z

Made a user story for one of my features and linked it to the issue also changed the issue name to ref user story

---

## #21 — Add Team model, CBBData API integration, and team list view

**State:** MERGED | **Author:** ken-hin | **feature/team-model → main** | **Created:** 2026-02-28T00:57:57Z

Implements the Team model with auto-slug generation, builds out services.py with fetch_teams/sync_teams to provide examples and structured error handling, adds TeamListView with teams.html template, registers Team in admin, and includes the initial migration.


---

## #20 — Update Schedule.md

**State:** MERGED | **Author:** ken-hin | **update/schedule-update → main** | **Created:** 2026-02-24T22:32:05Z

Updates to schedule to align with sprint structure for class

---

## #16 — Update proposal.md

**State:** MERGED | **Author:** ken-hin | **fix/update-proposal → main** | **Created:** 2026-02-24T16:07:47Z



---

## #15 — Proposal Revision

**State:** MERGED | **Author:** Sbombr | **sam-branch → main** | **Created:** 2026-02-23T20:08:27Z

Expanded schedule to be more specific, addressed legal and ethical concerns in more detail, and added a little more detail onto the descoping portion.

---

## #14 — Revise proposal introduction

**State:** MERGED | **Author:** asworthington | **alex-branch → main** | **Created:** 2026-02-23T16:48:38Z

Added specific backgrounds to each team member.

---

## #13 — Feature/learning by adding basic navbar and about page Closes #12

**State:** MERGED | **Author:** Jackson-Murphy04 | **feature/learning-by-adding-basic-navbar → main** | **Created:** 2026-02-20T16:50:55Z

added a nav bar and about page
dosent really matter if merge or not just trying to go through the motions and get an understanding of how everything works together in the project and the flow of using github

---

## #11 — Fix Build Issues

**State:** MERGED | **Author:** ken-hin | **fix-build-issues → main** | **Created:** 2026-02-19T18:21:15Z

Update .env file and settings.py to help with build issues related to node and npm. Update README.md to address these issues.

---

## #9 — Initial project scaffolding and environment setup

**State:** MERGED | **Author:** ken-hin | **setup → main** | **Created:** 2026-02-19T17:01:29Z

Sets up the full project foundation for OpenCourt. This PR establishes the Django project structure, frontend tooling, and all configuration needed for teammates to clone and run the app locally.

---

