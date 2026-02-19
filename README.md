# OpenCourt

## Project Topic

The goal of OpenCourt is to democratize college basketball (CBB) data. Existing websites provide in-depth analysis of CBB team and player statistics, but these are mostly locked behind paywalls. We want to create a free, full-stack web app that pulls data from the CBBData API, synthesizes useful data visualizations for analysis, and — time permitting — trains a predictive model to make team and player predictions for the ongoing season.

**Tech Stack:** Python 3.14 · Django 6 · SQLite (dev) / PostgreSQL (prod) · Tailwind CSS v4 · DaisyUI v5 · ApexCharts

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
git clone https://github.com/YOUR-ORG/OpenCourt.git
cd OpenCourt
```

Then create your local environment file by copying the example:

```bash
cp .env.example .env
```

The `.env` file is listed in `.gitignore` and will never be committed. The defaults work fine for local development — you don't need to change anything yet. When Week 2 API integration starts, you'll add your `CBB_API_KEY` here.

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

### 9. Start the Development Server

Starting the dev server now requires **two terminals** — one for Django and one for Tailwind CSS. Open two terminal tabs in the project root:

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
├── config/                        # Django project config (settings, urls, wsgi, asgi)
├── opencourt/                     # Main Django app (models, views, urls, admin)
├── theme/                         # Tailwind CSS app managed by django-tailwind
│   ├── static_src/                # Source files — edit these
│   │   ├── src/styles.css         # Tailwind entry point (add @source, @plugin here)
│   │   └── package.json           # npm config for Tailwind CLI + DaisyUI
│   └── static/css/dist/           # Compiled output — do not edit by hand
│       └── styles.css             # Generated by `tailwind start` / `tailwind build`
├── templates/                     # HTML templates (base.html and app-specific pages)
├── static/                        # Custom CSS, JavaScript, and images
│   ├── css/main.css               # Custom styles beyond Tailwind/DaisyUI
│   ├── js/main.js                 # Global JavaScript utilities
│   └── img/
├── manage.py                      # Django management commands
├── pyproject.toml                 # Project dependencies — add packages here with `uv add`
└── uv.lock                        # Auto-generated lockfile — do not edit by hand
```

---

## Frontend Libraries

| Library | Version | How it's loaded | Docs |
|---------|---------|----------------|------|
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
| Add a Python dependency | `uv add <package>` |
| After pulling new changes | `uv sync` → `uv run python manage.py migrate` → `uv run python manage.py tailwind build` |
| Create a new migration | `uv run python manage.py makemigrations` |
| Apply migrations | `uv run python manage.py migrate` |
| Run tests | `uv run python manage.py test` |

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
