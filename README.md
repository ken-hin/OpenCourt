# OpenCourt

A free, open-source college basketball (CBB) stats and analytics dashboard. OpenCourt pulls data from the [CBBData API](https://cbbdata.com), presents it through interactive visualizations, and uses an XGBoost prediction model to forecast game outcomes.

**Tech Stack:** Python 3.14 · Django 6 · Tailwind CSS v4 · DaisyUI v5 · ApexCharts · XGBoost · SQLite (dev) / PostgreSQL (prod) · Railway · Supabase

---

## Architecture

```
┌──────────────────────────────────────────────────────────────────────────┐
│  Client (Browser)                                                        │
│  ┌────────────┐  ┌──────────────┐  ┌──────────────┐                     │
│  │ Tailwind v4 │  │  DaisyUI v5  │  │  ApexCharts  │                     │
│  │ + DaisyUI   │  │  Components  │  │  (CDN)       │                     │
│  └────────────┘  └──────────────┘  └──────────────┘                     │
└──────────────────────────────┬───────────────────────────────────────────┘
                               │ HTTP
┌──────────────────────────────▼───────────────────────────────────────────┐
│  Django Application                                                      │
│                                                                          │
│  ┌─────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐  │
│  │  Views   │  │  Templates   │  │  Static      │  │  Admin Panel     │  │
│  │  (CBVs)  │──│  (Jinja2)    │  │  (WhiteNoise)│  │  /admin/         │  │
│  └────┬─────┘  └──────────────┘  └──────────────┘  └──────────────────┘  │
│       │                                                                  │
│  ┌────▼─────────────────┐  ┌───────────────────────────────────────┐     │
│  │  Models (ORM)        │  │  Predictions Module                   │     │
│  │  Team, Conference,   │  │  features.py → XGBoost classifier     │     │
│  │  Game, GameTeamStats,│  │  (10-feature differential model)      │     │
│  │  TeamSeasonStats,    │  │  Predicts: home win vs away win       │     │
│  │  Ranking             │  └───────────────────────────────────────┘     │
│  └────┬─────────────────┘                                                │
│       │                                                                  │
│  ┌────▼─────────────────────────────────────────────────────────────┐    │
│  │  Services Layer (opencourt/services/)                             │    │
│  │  fetch.py → sync.py (full backfill) / update.py (incremental)    │    │
│  └──────────────────────────┬────────────────────────────────────────┘    │
└─────────────────────────────┼────────────────────────────────────────────┘
                              │ HTTPS (CBBData API)
┌─────────────────────────────▼──────────────────────────────────────┐
│  External                                                          │
│  ┌───────────────┐         ┌────────────────────────────────────┐  │
│  │  CBBData API  │         │  Database                          │  │
│  │  (cbbdata.com)│         │  SQLite (dev) / Supabase PG (prod) │  │
│  └───────────────┘         └────────────────────────────────────┘  │
└────────────────────────────────────────────────────────────────────┘
```

### Data Pipeline

Data flows through the system in two modes:

**Full sync** (`python manage.py sync_data`) — pulls all historical data from the CBBData API. Used for initial database setup or backfills. Runs ~30+ API calls and takes several minutes. Sync order matters because of foreign key dependencies: Conferences → Teams → Season Stats → Games → Game Team Stats → Rankings.

**Incremental update** (`python manage.py update_data`) — pulls only the last 30 days of games and the current season's stats/rankings. About 5 API calls total. Designed for daily cron jobs to keep the database current without rate-limiting.

Both are idempotent — running them multiple times produces the same result via `update_or_create()`.

### Prediction Model

The prediction model uses an XGBoost classifier trained on historical game data. For each matchup, it builds a 10-feature vector based on the difference between the two teams' season stats: effective FG%, turnover rate, point differential, pace, free throw rate, offensive rating, blocks, offensive rebound %, assist-to-turnover ratio, and home advantage. The model outputs a binary prediction (home win or away win) and is displayed on the Upcoming Games page alongside actual results for completed games.

The trained model is stored as a pickle file in `models/final_model/` and loaded at prediction time.

---

## Pages & URL Routes

| URL | View | Description |
|-----|------|-------------|
| `/` | `HomeView` | Landing page with top 5 ranked teams, featured conferences, and platform-wide stats |
| `/about/` | `AboutView` | About the project and team |
| `/teams/` | `TeamListView` | All ~360 D1 teams with conference filtering and search |
| `/conferences/` | `ConferenceListView` | Two-panel layout: conference sidebar with team list and aggregate stats |
| `/rankings/` | `RankingsListView` | Side-by-side AP Top 25 and Coaches Poll with week-by-week navigation |
| `/upcoming/` | `UpcomingView` | Upcoming games with prediction model output, plus completed game results with prediction accuracy |
| `/<slug>/` | `TeamDetailView` | Individual team page with historical season stats, ApexCharts visualizations, and current season schedule with expandable box scores |
| `/admin/` | Django Admin | Database admin panel (superuser required) |

---

## Environment Setup

Follow these steps to get the project running on your machine from scratch. If you run into issues, message Kenneth before changing anything.

### 1. Check Your Python Version

Open a terminal and run:

```bash
python3 --version
```

You need **Python 3.14 or higher**. If your version is lower, or if the command isn't found, follow the install step below.

### 2. Install or Update Python

**macOS:**

The easiest way is to download the official installer from [python.org/downloads](https://www.python.org/downloads/). Download the latest 3.14.x macOS package and run it. Once installed, re-run `python3 --version` to confirm.

Alternatively, if you use Homebrew:
```bash
brew install python@3.14
```

**Windows:**

Download the official installer from [python.org/downloads](https://www.python.org/downloads/). When running the installer, **make sure to check "Add Python to PATH"** before clicking Install — this is easy to miss and causes problems later.

After installing, open a new Command Prompt and run:
```
python --version
```

### 3. Install Node.js

Node.js is required to compile Tailwind CSS. If you already have it, skip this step — confirm with `node --version` (you need v18 or higher).

**macOS:**

The easiest option is the official installer at [nodejs.org/en/download](https://nodejs.org/en/download/). Download the LTS macOS package and run it. Or with Homebrew:
```bash
brew install node
```

**Windows:**

Download the LTS installer from [nodejs.org/en/download](https://nodejs.org/en/download/) and run it. When prompted, leave "Automatically install necessary tools" checked. After installing, open a new terminal and confirm:
```
node --version
```

### 4. Install uv (Package Manager)

We use [uv](https://docs.astral.sh/uv/) to manage dependencies instead of pip. It's significantly faster and ensures everyone on the team installs the exact same package versions.

**macOS / Linux:**
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

**Windows (PowerShell):**
```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

After installing, close and reopen your terminal, then confirm it worked:
```bash
uv --version
```

### 5. Clone the Repository

If you haven't already, clone the repo and move into it:

```bash
git clone https://github.com/cs340-26/OpenCourt.git
cd OpenCourt
```

Then create your local environment file by copying the example:

```bash
cp .env.example .env
```

The `.env` file is listed in `.gitignore` and will never be committed. The defaults work fine for local development — you don't need to change anything yet. Add your `CBB_API_KEY` when you're ready to sync data from the API.

### 6. Install Project Dependencies

Run the following command from the project root. uv will create a virtual environment (`.venv/`) and install everything listed in `pyproject.toml` automatically:

```bash
uv sync
```

You should see it install Django and its dependencies. You only need to re-run this when new packages are added to the project.

### 7. Install Tailwind CSS (npm packages)

This is a one-time step that downloads the Tailwind CLI and DaisyUI into `theme/static_src/node_modules/`. You only need to run it once after cloning:

```bash
uv run python manage.py tailwind install
```

### 8. Apply Database Migrations

Set up your local SQLite database by running:

```bash
uv run python manage.py migrate
```

### 9. Sync Data from the API

Populate your local database with CBB data. Make sure your `CBB_API_KEY` is set in `.env` first:

```bash
uv run python manage.py sync_data
```

This takes a few minutes on the first run. After the initial sync, use `update_data` to pull recent changes:

```bash
uv run python manage.py update_data
```

### 10. Start the Development Server

Starting the dev server requires **two terminals** — one for Django and one for Tailwind CSS. Open two terminal tabs in the project root:

**Terminal 1 — Django:**
```bash
uv run python manage.py runserver
```

**Terminal 2 — Tailwind (auto-recompiles CSS on save):**
```bash
uv run python manage.py tailwind start
```

Open your browser and go to [http://127.0.0.1:8000](http://127.0.0.1:8000). The browser will automatically refresh whenever you save a template or CSS file.

The admin panel is available at [http://127.0.0.1:8000/admin](http://127.0.0.1:8000/admin) — create a superuser to log in:

```bash
uv run python manage.py createsuperuser
```

---

## Project Structure

```
OpenCourt/
├── config/                            # Django project configuration
│   ├── settings.py                    #   Settings (DB, apps, middleware, static files)
│   ├── urls.py                        #   Root URL routing
│   ├── wsgi.py                        #   WSGI entry point (Gunicorn uses this)
│   └── asgi.py                        #   ASGI entry point (not currently used)
├── opencourt/                         # Main Django application
│   ├── models.py                      #   Database models (Team, Conference, Game, etc.)
│   ├── views.py                       #   View classes (Home, Teams, Rankings, etc.)
│   ├── urls.py                        #   App-level URL routing
│   ├── admin.py                       #   Django admin configuration
│   ├── stats.py                       #   Helper functions (win %, point differential)
│   ├── tests.py                       #   Unit tests
│   ├── services/                      #   Data pipeline layer
│   │   ├── fetch.py                   #     HTTP calls to CBBData API
│   │   ├── sync.py                    #     Full sync (initial backfill)
│   │   ├── update.py                  #     Incremental update (daily cron)
│   │   └── helpers.py                 #     Shared utilities (lookups, builders)
│   ├── predictions/                   #   ML prediction module
│   │   ├── features.py                #     Feature engineering (10-feature vector)
│   │   ├── predict.py                 #     Load model and predict game outcomes
│   │   ├── train_model.py             #     Training script (offline)
│   │   ├── model.py                   #     Model architecture/definition
│   │   └── evaluate.py                #     Evaluation metrics
│   └── management/commands/           #   Django CLI commands
│       ├── sync_data.py               #     Full sync orchestrator
│       ├── sync_teams.py              #     Sync teams only
│       ├── sync_conferences.py        #     Sync conferences only
│       ├── sync_games.py              #     Sync games only
│       ├── sync_season_stats.py       #     Sync season stats only
│       ├── sync_rankings.py           #     Sync rankings only
│       └── update_data.py             #     Incremental update (cron target)
├── models/                            # Trained ML model files
│   └── final_model/                   #   Pickled XGBoost classifier
├── templates/                         # HTML templates
│   ├── base.html                      #   Master layout (nav, footer, ApexCharts CDN)
│   └── opencourt/                     #   Page templates
│       ├── home.html                  #     Landing page
│       ├── about.html                 #     About page
│       ├── teams.html                 #     Team list with filtering
│       ├── team_details.html          #     Team detail with charts and schedule
│       ├── conferences.html           #     Conference browser
│       ├── rankings.html              #     AP Top 25 + Coaches Poll
│       ├── head_head.html             #     Upcoming games + predictions
│       └── components/                #     Reusable template fragments
│           ├── team_card.html
│           ├── conference_card.html
│           └── conference_filter.html
├── theme/                             # Tailwind CSS app (django-tailwind)
│   ├── static_src/                    #   Source config — edit these
│   │   ├── src/styles.css             #     Tailwind entry point (@source, @plugin)
│   │   └── package.json               #     npm config (Tailwind CLI + DaisyUI)
│   └── static/css/dist/               #   Compiled output — do not edit by hand
│       └── styles.css                 #     Generated by tailwind start / tailwind build
├── static/                            # Custom static assets
│   ├── css/main.css                   #   Custom styles beyond Tailwind/DaisyUI
│   ├── js/main.js                     #   Global JS utilities
│   ├── js/card_contrast.js            #   Contrast color calculation for team cards
│   ├── js/conference_filter.js        #   Client-side conference filtering
│   └── img/                           #   Images
├── manage.py                          # Django management CLI
├── pyproject.toml                     # Project dependencies (managed by uv)
├── uv.lock                            # Pinned dependency versions (auto-generated)
├── Procfile                           # Railway start command (Gunicorn)
├── railway.json                       # Railway deploy config (collectstatic + migrate)
├── DEPLOY.md                          # Step-by-step deployment walkthrough
└── Schedule.md                        # Sprint schedule and team assignments
```

---

## Database Models

The database has six models organized around foreign key relationships. Sync order matters because of these dependencies.

```
Conference
  └── Team (FK: conference)
        ├── TeamSeasonStats (FK: team) — one per team per season
        ├── Game (FK: home_team, away_team) — also links to Conference
        │     └── GameTeamStats (FK: game, team) — per-team box score for each game
        └── Ranking (FK: team, conference) — per-week poll rankings
```

**Conference** — D1 basketball conferences (e.g., ACC, Big Ten). Fields: name, abbreviation, short name.

**Team** — D1 basketball teams (~360 total). Fields: school name, mascot, colors, venue, city/state. Auto-generates URL slug on save (e.g., "Duke Blue Devils" → `duke-blue-devils`).

**TeamSeasonStats** — Aggregate stats for one team in one season. Includes win/loss record, shooting percentages (FG, 2pt, 3pt, FT), Four Factors (eFG%, turnover ratio, ORB%, FT rate), offensive rating, pace, and full opponent/defensive mirrors of each stat.

**Game** — A single game between two teams. Includes final scores, period scores (JSON), Elo ratings, venue info, attendance, seedings, and an excitement index.

**GameTeamStats** — Per-team box score for a game. Full shooting splits, rebounds, assists, steals, blocks, turnovers, fouls, and advanced stats (true shooting, game score, offensive rating).

**Ranking** — Weekly poll rankings (AP Top 25 and Coaches Poll). Tracks rank, points, and first-place votes per team per week.

---

## Frontend Libraries

| Library | Version | How It's Loaded | Docs |
|---------|---------|-----------------|------|
| Tailwind CSS | v4 | Compiled locally (`tailwind start`) | [tailwindcss.com/docs](https://tailwindcss.com/docs/utility-first) |
| DaisyUI | v5 | Bundled with Tailwind at compile time | [daisyui.com/components](https://daisyui.com/components/) |
| ApexCharts | latest | CDN in `base.html` | [apexcharts.com/docs](https://apexcharts.com/docs/chart-types/) |

**How Tailwind + DaisyUI work in this project:**

Tailwind CSS and DaisyUI are compiled into a single CSS file at `theme/static/css/dist/styles.css`. The source config lives in `theme/static_src/src/styles.css`. When you run `python manage.py tailwind start`, the Tailwind CLI watches your templates for class names and regenerates the CSS file automatically on every save.

**For the UI/UX:** write all styling using DaisyUI component classes and Tailwind utility classes directly in HTML templates. Any custom styles that go beyond what the frameworks provide belong in `static/css/main.css`. Page-specific chart initialization scripts go in the `{% block extra_js %}` block of the relevant template — see `static/js/main.js` for an example.

**To change the DaisyUI theme:** open `theme/static_src/src/styles.css` and change `light` in the `@plugin "daisyui"` block to any theme name from [daisyui.com/docs/themes](https://daisyui.com/docs/themes/).

---

## Common Commands

| Task | Command |
|------|---------|
| Start Django dev server | `uv run python manage.py runserver` |
| Start Tailwind watcher (2nd terminal) | `uv run python manage.py tailwind start` |
| Build minified CSS for production | `uv run python manage.py tailwind build` |
| Full data sync (initial setup) | `uv run python manage.py sync_data` |
| Incremental data update (daily) | `uv run python manage.py update_data` |
| Add a Python dependency | `uv add <package>` |
| After pulling new changes | `uv sync` → `uv run python manage.py migrate` |
| Create a new migration | `uv run python manage.py makemigrations` |
| Apply migrations | `uv run python manage.py migrate` |
| Run tests | `uv run python manage.py test` |
| Collect static files (production) | `uv run python manage.py collectstatic --noinput` |

---

## Environment Variables

All configuration is managed through `.env` (local) or platform environment variables (production). See `.env.example` for the full list.

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `SECRET_KEY` | Yes | Insecure dev key | Django secret key. Generate one at [djecrety.ir](https://djecrety.ir/) for production. |
| `DEBUG` | No | `True` | Set to `False` in production. Controls debug pages, error detail, and browser reload. |
| `ALLOWED_HOSTS` | No | `localhost,127.0.0.1` | Comma-separated domains Django will serve. Set to `.up.railway.app` in production. |
| `CBB_API_KEY` | Yes (for data sync) | — | API key from [cbbdata.com](https://cbbdata.com). Required for `sync_data` and `update_data`. |
| `DATABASE_URL` | No | SQLite | PostgreSQL connection URI. Only set in production (Supabase). |
| `NPM_BIN_PATH` | No | `npm` | Path to npm executable. Only needed if `tailwind install` can't find npm. |

---

## Production & Deployment

OpenCourt is deployed on **Railway** (hosting) and **Supabase** (PostgreSQL database). For the full step-by-step setup guide, see [`DEPLOY.md`](DEPLOY.md). This section covers the how and why so the whole team is on the same page.

### How Dev vs Production Works

The same `settings.py` runs in both environments — it reads environment variables and falls back to local defaults:

| Setting | Local Dev (your machine) | Production (Railway) |
|---------|--------------------------|---------------------|
| `DEBUG` | `True` (from `.env`) | `False` (Railway env var) |
| Database | SQLite (`db.sqlite3`) | Supabase PostgreSQL (via `DATABASE_URL`) |
| Static files | Django dev server | WhiteNoise (serves from `staticfiles/`) |
| Web server | `manage.py runserver` | Gunicorn (production WSGI server) |

**Nothing changes for local development.** Your `.env` still has `DEBUG=True` and no `DATABASE_URL`, so you'll keep using SQLite exactly as before.

### After Pulling the Deployment Branch

The only thing you need to do:

```bash
uv sync
```

That installs the new production dependencies. Then confirm everything still works locally:

```bash
uv run python manage.py runserver
```

That's it. No new setup, no Docker, no PostgreSQL install needed on your machine.

### Keeping Production Data Current

The `update_data` management command runs on a daily cron job on Railway. It pulls the last 30 days of games, current season stats, and rankings from the CBB API — about 5 API calls total, much lighter than a full `sync_data`. The cron job connects to the same Supabase database the web app reads from.

The cron schedule is configured entirely on Railway's side (not in the Django codebase), so there's nothing in the code to maintain for this.

### Deploying UI or Model Changes

When your branch gets merged and Railway picks it up:

- **Database migrations** run automatically — `railway.json` runs `migrate` on every deploy.
- **Static files** are collected automatically — `railway.json` runs `collectstatic` on every deploy.
- **Tailwind CSS** must be compiled and committed before pushing. Railway doesn't run `tailwind build` during deploy — it uses whatever compiled CSS is in the repo. So if you change templates or Tailwind classes, run `uv run python manage.py tailwind build` and commit the updated `theme/static/css/dist/styles.css` before pushing.

### Why These Tools?

| Tool | What It Does | Why We Chose It |
|------|-------------|-----------------|
| **Railway** | Hosts the Django app and cron job | Free $5 trial, simple GitHub deploy, built-in cron jobs, no config files beyond what's in the repo |
| **Supabase** | Hosted PostgreSQL database | Free 500MB tier, managed backups, no Docker or local Postgres needed |
| **Gunicorn** | Production web server | The standard for Django in production — replaces `runserver` which isn't meant for real traffic |
| **WhiteNoise** | Serves static files (CSS, JS, images) | Lets Django serve its own static files without needing nginx or a CDN |
| **dj-database-url** | Parses `DATABASE_URL` into Django's database config | Industry standard for 12-factor apps — one env var switches between SQLite and PostgreSQL |

### FAQ

**Do I need to install PostgreSQL on my machine?**
No. Local dev uses SQLite. PostgreSQL only runs on Supabase's servers — your app connects to it over the internet via `DATABASE_URL`.

**Do I need Docker?**
No. Docker is sometimes used to run Supabase locally for development, but we don't need that. We connect directly to the hosted Supabase instance in production, and locally we just use SQLite.

**What if I add a new model or change a field?**
Run `uv run python manage.py makemigrations` and commit the migration file. When it gets deployed, Railway runs `migrate` automatically and applies it to the production database.

**What if I change templates or Tailwind classes?**
Run `uv run python manage.py tailwind build` and commit the updated CSS before pushing. Production uses the compiled CSS from the repo — it doesn't recompile during deploy.

**What's the production URL?**
Railway gives us a free subdomain like `opencourt-production.up.railway.app`. No custom domain or DNS setup needed.

**How much does this cost?**
$0. Railway's free trial gives $5 of credit (more than enough for our usage), and Supabase's free tier includes 500MB of database storage.

---

## Troubleshooting

**Page loads but looks completely unstyled (no colors, layout, or fonts)**

The compiled Tailwind CSS file is missing or empty. Run:
```bash
uv run python manage.py tailwind build
```
Then refresh the browser. If it still looks wrong, make sure `tailwind install` was run first.

---

**`tailwind start` or `tailwind build` fails with "command not found" or npm errors**

The npm packages haven't been installed yet. Run:
```bash
uv run python manage.py tailwind install
```
This only needs to be done once after cloning. If it still fails, confirm Node.js is installed (`node --version` should show v18+).

---

**`tailwind install` fails with "node.js and/or npm is not installed or cannot be found"**

Node.js is installed but npm isn't on the PATH that Django can see. First, find where npm actually lives:

```bash
# macOS / Linux
which npm

# Windows
where npm
```

Then add the result to your `.env` file (copy from `.env.example` if you haven't already):

```
NPM_BIN_PATH=/opt/homebrew/bin/npm
```

Common paths: `/usr/local/bin/npm` (macOS Intel) · `/opt/homebrew/bin/npm` (macOS Apple Silicon) · `C:\Program Files\nodejs\npm.cmd` (Windows)

After saving `.env`, retry `python manage.py tailwind install`.

---

**`uv run python manage.py ...` fails with "No module named django"**

The Python virtual environment needs to be set up. Run:
```bash
uv sync
```
Then retry the original command.

---

**Database errors or "table doesn't exist" messages**

Migrations haven't been applied yet. Run:
```bash
uv run python manage.py migrate
```

---

**New Tailwind classes I added aren't showing up**

Tailwind only includes classes it finds by scanning the template files listed in `@source` directives in `theme/static_src/src/styles.css`. Make sure `tailwind start` is running in a second terminal — it watches for new classes and recompiles automatically. If you just added the class, save the file and it should appear.

---

**Still stuck?** Message Kenneth before changing settings or deleting anything.

---

## Git Workflow

We use a **feature branch** workflow. Never commit directly to `main`.

### Branch Naming

Use the format `type/short-description`, for example:

- `feature/team-list-page`
- `feature/conference-model`
- `fix/navbar-mobile-layout`
- `data/cbb-api-sync`

### Day-to-Day Flow

```bash
# 1. Make sure your main is up to date before starting anything new
git checkout main
git pull

# 2. Create a new branch for your work
git checkout -b feature/your-feature-name

# 3. Do your work, then stage and commit
git add <specific-files>
git commit -m "short description of what you did"

# 4. Push your branch to GitHub
git push -u origin feature/your-feature-name

# 5. Open a Pull Request on GitHub — message Kenneth to review before merging 
```

### Rules

- **Never push directly to `main`** — all changes go through a Pull Request.
- **Keep branches focused** — one feature or fix per branch.
- **Pull before you start** — always `git pull` on `main` before branching to avoid conflicts.
- **After your PR is merged** — delete your branch on GitHub and pull `main` again locally before starting the next thing.

### Keeping Your Branch Up to Date

If `main` moves forward while you're working on a branch, sync it to avoid big merge conflicts later:

```bash
git checkout main
git pull
git checkout feature/your-feature-name
git merge main
```

---

## Team

| Name | Role | Responsibilities |
|------|------|-----------------|
| **Kenneth Hinman** | Project Manager / Backend Lead | Django, deployment, architecture, code review |
| **Alex Worthington** | UI/UX / Frontend Lead | Templates, Tailwind/DaisyUI, responsive design |
| **Jackson Murphy** | Data Pipeline / API Lead | CBBData API integration, sync/update pipeline |
| **Samuel Bombrys** | Analytics / ML Lead | Prediction model, stats calculations, data analysis |
