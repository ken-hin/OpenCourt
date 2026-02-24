# OpenCourt Stats — Project Proposal

- **Title:** OpenCourt Stats
- **Team Name:** OpenCourt
- **Team Members:** Kenneth Hinman | Alex Worthington | Jackson Murphy | Samuel Bombrys

---

## Section 1: Introduction

### What is the project?

We want to create a full-stack web app that pulls data from the CBBData API and other similar sources. With the data, we hope to synthesize useful data visualizations for analysis and — time permitting — train a predictive model to make team and player predictions for the ongoing season.

### What is the motivation?

We enjoy watching and analyzing college basketball and have repeatedly encountered paywalls on the sites that offer the most meaningful analysis. We want to make the kind of data that informs real understanding of the game freely available to anyone.

### Market context

There are similar products in the market, but the most analytically rigorous ones operate on subscription models that block casual users from accessing advanced efficiency statistics and predictive tools. Sites like EvanMiya.com and CBB Analytics offer excellent data, but require paid accounts for full access.

### Is the project idea novel?

The idea is not novel — advanced CBB analytics sites exist. What we are doing differently is offering that level of analysis for free, with a clean and approachable interface designed for fans who are not statisticians.

### What existing software does it resemble?

- [EvanMiya.com](http://EvanMiya.com)
- CBB Analytics

### How is it different?

We will not lock anything behind a paywall. Our analysis, visualizations, and predictions will be fully public so that any fan can use them without a subscription.

### Team member backgrounds

- **Kenneth Hinman** — Built an early-stage CFB dashboard in Django. Has the most full-stack experience on the team and is serving as Project Manager.
- **Alex Worthington** — Professional web development experience. Proficient in HTML, CSS, and Bootstrap with a working knowledge of PHP and JavaScript.
- **Jackson Murphy** — Built a web scraper for extracting and analyzing stock market sentiment using Python and AI. Has experience building machine learning models and basic web development experience.
- **Samuel Bombrys** — Experience with machine learning and deep learning models in Python. Built a Chrome extension to analyze website safety.

### Orienting the reader

The site should guide users naturally without requiring a tutorial. The interface will be self-explanatory, with an optional onboarding flow if time allows.

---

## Section 2: Customer Value

### Customer Need

Our target audience is a college basketball fan (ages 18–35) who participates in bracket contests such as March Madness, follows advanced statistical discussions online, and wants deeper insight into team quality without paying for a subscription. Casual and semi-serious fans currently have no free access to advanced efficiency statistics and forecasting tools — the best tools are paywalled, forcing them to rely on surface-level stats like points per game and win percentage that do not accurately reflect how good a team actually is.

### Proposed Solution

OpenCourt Stats will offer free access to advanced team efficiency metrics, interactive data visualizations, and a transparent predictive model for college basketball games. The platform will focus on ease of use, enabling users to compare teams, examine trends over a season, and view game outcome predictions — all without a subscription or account.

### Measures of Success

- At least 200 unique users during the March Madness window
- At least 30% of users return for 3 or more sessions
- Average session duration of 3 minutes or more
- User survey rating of prediction usefulness ≥ 4 out of 5
- Prediction model accuracy exceeding a simple win-percentage baseline

---

## Section 3: Proposed Solution & Technology

### Minimal System

A working dashboard displaying team rankings and season statistics for all Division I teams, with conference filtering, team detail pages, and at least three data visualizations (win/loss chart, efficiency rating, points per game trend). Predictions are a stretch goal — the site has meaningful value without them.

### System Architecture

```
+------------------+
|  CBBData API     |   External data source
+--------+---------+
         |
         | HTTP requests
         v
+--------+---------+
|  services.py     |   Fetch and sync team, game, player data
+--------+---------+
         |
         v
+--------+---------+
|  models.py       |   Django ORM — Team, Conference, Game
+--------+---------+
         |
         v
+--------+------------------+
|  SQLite (dev)             |
|  PostgreSQL (prod)        |
+--------+------------------+
         |
    +----+----+
    |         |
    v         v
+---+----+ +--+------+
|stats.py| |views.py |
|        | |         |
|Win %   | |URL route|
|4Factor +>|Context  |
|Effic.  | |assembly |
+---+----+ +--+------+
    |         |
    v         |
+---+----+   |
|Predict.|   |
|Model   +--->
|sklearn |   |
+--------+   |
             |
             v
   +---------+--------+
   |  Django Templates |
   | HTML + Tailwind   |
   |   + DaisyUI       |
   +---------+--------+
             |
             v
   +---------+--------+
   |    ApexCharts    |
   |  Visualizations  |
   +---------+--------+
             |
             v
   +---------+--------+
   |  User / Browser  |
   +------------------+
```

### Tools & Technologies

| Tool | Version | Purpose |
|------|---------|---------|
| Python | 3.14 | Primary language |
| Django | 6.x | Web framework — views, ORM, URL routing, admin |
| Tailwind CSS | v4 | Utility-first styling |
| DaisyUI | v5 | Pre-built UI component library |
| ApexCharts | latest | Interactive data visualizations |
| CBBData API (`cbbd`) | latest | Primary data source for team/game stats |
| requests | latest | HTTP library for API calls |
| scikit-learn / PyTorch | latest | Prediction model (Week 5 stretch goal) |
| SQLite | built-in | Local development database |
| PostgreSQL (Supabase) | latest | Production database |
| uv | latest | Python package manager |
| Git / GitHub | — | Version control and collaboration |

---

## Section 4: Team

### Individual Skills

| Name | Relevant Experience |
|------|-------------------|
| **Kenneth Hinman** | Built a CFB dashboard in Django; most experienced with full-stack Django development and project architecture |
| **Alex Worthington** | Professional web development experience; proficient in HTML/CSS/Bootstrap; working knowledge of PHP and JavaScript |
| **Jackson Murphy** | Built a Python web scraper with AI-driven analysis; machine learning model experience; basic web development background |
| **Samuel Bombrys** | Machine learning and deep learning models in Python; built a Chrome extension; strong statistics background |

### Are the tools known or new?

At least one team member has individual experience with each tool. The challenge is integrating them into a single cohesive project — none of us have built a full-stack data application of this scope as a team before.

### Roles

| Name | Primary Role | Responsibilities |
|------|-------------|-----------------|
| **Kenneth Hinman** | Project Manager / Backend Lead | Architecture decisions, Django views, models, deployment, code review |
| **Alex Worthington** | UI/UX / Frontend Lead | Templates, DaisyUI components, Tailwind styling, responsive design |
| **Jackson Murphy** | Data Pipeline / API Lead | services.py, data sync, API integration, management commands |
| **Samuel Bombrys** | Analytics / ML Lead | Stats calculations, Four Factors, prediction model |

---

## Section 5: Project Management

### Schedule

The full week-by-week task breakdown with per-person assignments is maintained in `Schedule.md`. Summary of key deadlines:

| Milestone | Date |
|-----------|------|
| Proposal due | ~Feb 17 ✓ |
| Proposal revision | ~Feb 24 |
| Basic UI + data integration (MVP) | ~Mar 10 |
| Statistical analytics + ML model | ~Mar 24 |
| Testing + final clean-up | ~Apr 10 |
| Complete project, report & presentation | ~Apr 14 |

### Week-by-Week Feature Breakdown

| Week | Dates | Features Being Built |
|------|-------|----------------------|
| 1 | Feb 12–18 | Project scaffolding, Django setup, Tailwind/DaisyUI integration, base templates, home page |
| 2 | Feb 19–25 | Team and Conference models, CBBData API integration, data sync management command |
| 3 | Feb 26–Mar 4 | Home page with conference overview, team list with filtering, team detail page, navigation |
| 4 | Mar 5–11 | ApexCharts visualizations, Four Factors analytics, conference pages, search — **MVP complete** |
| 5 | Mar 12–18 | Head-to-head comparisons, custom rankings, historical trends, prediction model foundations |
| 6 | Mar 19–25 | Bug fixes, mobile responsive polish, prediction model integrated into UI |
| 7 | Mar 26–Apr 1 | Production deployment (Railway/Render + Supabase PostgreSQL) — **app goes live** |
| 8 | Apr 2–9 | Final polish, presentation slides, demo rehearsal |

### Constraints

**Ethical:**
Statistics and predictions displayed by the application may influence users to make decisions in bracket contests, fantasy sports, or sports betting. We will include a clear disclaimer that all predictions are probabilistic and for entertainment purposes only. We will not market the tool toward sports gambling use cases.

**Legal:**
- **CBBData API:** We will use the official `cbbd` Python client and comply fully with the CBBData API terms of service. We will not redistribute raw API data or exceed rate limits.
- **Web scraping:** If we supplement the CBBData API with scraped data from sites like EvanMiya, we will review each site's `robots.txt` and terms of service before scraping. Sites that explicitly prohibit scraping will not be targeted.
- **Data attribution:** Any data source used will be credited in the application's UI.

### Resources

The CBBData API provides comprehensive team, game, and player data for all Division I programs. This covers our core data needs. Scraping will only be considered if the API does not provide a specific metric we require.

### Descoping

If we cannot reach all goals, priority order is:

1. **Must have:** Team list, team detail pages, conference breakdown, basic stats (win %, PPG, opponent PPG)
2. **Should have:** Four Factors efficiency metrics, ApexCharts visualizations, team comparison
3. **Nice to have:** Predictive model, historical trends, player-level stats

A polished dashboard showing team efficiency data with clean visualizations — even without predictions — fulfills the core value proposition of democratizing advanced CBB stats. The site has meaningful value at every level of the above list.
