# OpenCourt Deployment Guide

How to deploy OpenCourt to Railway (hosting) + Supabase (PostgreSQL database) for free.

## What You'll End Up With

- A public URL like `opencourt-production.up.railway.app` anyone can visit
- A Supabase PostgreSQL database with all your CBB data
- Static files (CSS, JS, images) served by WhiteNoise
- A cron job that runs `update_data` daily to keep stats current

Total cost: $0 (Railway gives a $5 free trial, Supabase free tier is 500MB).

---

## Step 1: Create a Supabase Project

1. Go to [supabase.com](https://supabase.com) and sign up (or log in).
2. Click **New Project**.
3. Name it `opencourt`, pick a strong database password, and choose the region closest to you (e.g., East US).
4. **Save the database password somewhere safe** — you'll need it in a minute.
5. Once the project is created, go to **Settings → Database** (in the left sidebar).
6. Under **Connection string**, select the **URI** tab. You'll see something like:

   ```
   postgresql://postgres.[project-ref]:[YOUR-PASSWORD]@aws-0-us-east-1.pooler.supabase.com:6543/postgres
   ```

7. Copy this URI. Replace `[YOUR-PASSWORD]` with the password you set in step 4.

This is your `DATABASE_URL`. Keep it handy for Step 2.

**Important:** On the same **Settings → Database** page, make sure the connection mode is set to **Transaction** (port 6543). This works best with Django's connection pooling.

---

## Step 2: Deploy to Railway

### 2a. Create a Railway Account

1. Go to [railway.com](https://railway.com) and sign up with GitHub.
2. This automatically links your GitHub repos.

### 2b. Create a New Project

1. Click **New Project → Deploy from GitHub repo**.
2. Select your `OpenCourt` repository.
3. Railway will detect it's a Python project and start building. **It may fail the first time** — that's fine, you need to add environment variables first.

### 2c. Set Environment Variables

1. Click on your deployed service (the purple box in the Railway dashboard).
2. Go to the **Variables** tab.
3. Add these variables one by one (click **New Variable** for each):

   | Variable | Value |
   |----------|-------|
   | `SECRET_KEY` | Generate one at [djecrety.ir](https://djecrety.ir/) — paste the result |
   | `DEBUG` | `False` |
   | `ALLOWED_HOSTS` | `.up.railway.app` |
   | `DATABASE_URL` | The Supabase URI from Step 1 |
   | `CBB_API_KEY` | Your existing API key (same one from your local `.env`) |
   | `PORT` | `8000` |

4. After adding all variables, Railway will automatically redeploy.

### 2d. Generate a Public URL

1. In your service settings, go to **Settings → Networking → Public Networking**.
2. Click **Generate Domain**. You'll get a URL like `opencourt-production.up.railway.app`.

### 2e. Update ALLOWED_HOSTS

Once you have your Railway domain, go back to **Variables** and update:

```
ALLOWED_HOSTS=.up.railway.app
```

(The leading dot means "any subdomain of up.railway.app", so your specific subdomain is covered.)

---

## Step 3: Run Migrations & Sync Data

Railway gives you a terminal to run one-off commands against your production app.

1. In your Railway service, click the **three dots (⋯)** menu → **Open Shell** (or use the Railway CLI).
2. Run these commands in order:

```bash
# Create all database tables in Supabase
python manage.py migrate

# Populate the database with CBB data (this takes a few minutes)
python manage.py sync_data
```

If `sync_data` succeeds, your production database now has all teams, conferences, games, stats, and rankings.

---

## Step 4: Set Up a Cron Job (Daily Data Updates)

This makes Railway run `python manage.py update_data` automatically every day so your stats stay current.

1. In your Railway project dashboard, click **New → Cron Job**.
2. Select the same GitHub repo.
3. Set the cron schedule: `0 6 * * *` (runs daily at 6 AM UTC).
4. Set the start command to:

   ```
   python manage.py update_data
   ```

5. Add the same environment variables as your main service (especially `DATABASE_URL` and `CBB_API_KEY`).

This cron service shares the same Supabase database, so it will update the same data your web app reads.

---

## Step 5: Verify Everything Works

1. Visit your Railway URL in a browser — you should see the OpenCourt homepage.
2. Navigate to a team page — if data loads, your Supabase database is connected.
3. Check Railway's deploy logs (click on the service → **Deployments** → latest) to make sure there are no errors.

---

## How It All Fits Together

```
┌─────────────────────────────────────────────────┐
│  Railway                                        │
│                                                 │
│  ┌─────────────────────┐  ┌──────────────────┐  │
│  │  Web Service         │  │  Cron Job        │  │
│  │  gunicorn + Django   │  │  update_data     │  │
│  │  (serves pages)      │  │  (daily at 6am)  │  │
│  └──────────┬──────────┘  └────────┬─────────┘  │
│             │                      │             │
└─────────────┼──────────────────────┼─────────────┘
              │                      │
              ▼                      ▼
       ┌──────────────────────────────────┐
       │  Supabase PostgreSQL             │
       │  (teams, games, stats, rankings) │
       └──────────────────────────────────┘
```

---

## Local Development (Nothing Changes)

Your local `.env` still has `DEBUG=True` and no `DATABASE_URL`, so locally you'll keep using SQLite as before. No changes needed for your teammates.

---

## Troubleshooting

**"DisallowedHost" error when visiting the site:**
→ Double-check `ALLOWED_HOSTS` includes your Railway domain. Use `.up.railway.app` (with the leading dot).

**Static files missing (no CSS/styling):**
→ Make sure `python manage.py collectstatic --noinput` ran during deploy. The `railway.json` in the repo handles this automatically.

**Database connection errors:**
→ Verify `DATABASE_URL` is correct in Railway variables. Make sure you replaced `[YOUR-PASSWORD]` with your actual Supabase password.

**`sync_data` fails with API errors:**
→ Check that `CBB_API_KEY` is set in Railway variables.

**Railway free tier ran out:**
→ Railway gives $5/month free. If it runs out, you can add a credit card for the hobby plan ($5/mo) or pause the cron job to save usage.
