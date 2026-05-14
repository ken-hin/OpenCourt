## #66 — Deploy App and General Refactoring

**State:** CLOSED | **Author:** ken-hin | **Created:** 2026-04-16T16:38:03Z

- Deploy app to Railway — run collectstatic, migrate, configure all env vars, confirm public URL is live
- Smoke-test every page in prod
- Fix any deploy-specific bugs (SSL, ALLOWED_HOSTS, static files)
- Share production URL with the team
- Refactor large files into smaller modules (views.py, models.py, etc.)
- Ensure consistent  code style across project

---

## #65 — Check Proper Data and Predictions Page Enhancements

**State:** CLOSED | **Author:** ken-hin | **Created:** 2026-04-16T16:35:35Z

- Ensure the data being displayed on all pages is accurate, compare against ESPN
- Fix Per Game Averages section on team_details.html
- Implement pagination/tabs on teams.html, have it display 25 teams per page/tab and the ability to click through each page/tab
- Update head_head.html and UpcomingView to display all predictions from the season
- Implement pagination/tabs on head_head.html, have it display some number of predictions per page/tab and the ability to click through each page/tab.


---

## #64 — Final UI/UX Polish and Enhance team_details.html

**State:** CLOSED | **Author:** ken-hin | **Created:** 2026-04-16T16:28:11Z

- Final production UI review across mobile/desktop
- Implement more historical data charts in team_details.html
- Improve Schedule section of team_details.html so the accordion dropdown isn't as tall
- Ensure all colors, text, charts, etc. are easy to read and there are no contrast issues
- Add site wide footer section

---

## #61 — Add test coverage across the app

**State:** CLOSED | **Author:** ken-hin | **Created:** 2026-04-14T16:14:30Z

- Models — save overrides, auto-slug generation, `win_pct` calculation, `current_season` property, unique constraints
- Views — all 7 views should be tested for status codes, templates, and context data
- Predictions — feature engineering, model loading, and predict function (with mocked model file)
- Services — API response builders, lookup helpers, date range generation, and fetch functions (with mocked API calls)
- URL routing — verify all named routes resolve to the right views

---

## #58 — Prepare for Deployment

**State:** CLOSED | **Author:** ken-hin | **Created:** 2026-04-07T15:50:22Z

- Begin setting up production DB and server
- Create cron functions to run on production server that update data daily
- Get project ready for production and deployment
- Refactor codebase to ensure consistent code style, comments, docstrings, etc.
- Check for edge cases, ensure proper data being served to views, implement any necessary testing

---

## #57 — Improve Prediction Model

**State:** CLOSED | **Author:** ken-hin | **Created:** 2026-04-07T15:46:34Z

- Make further improvements to current model
- Add more features to model, could include each teams performance in last 5 games and opponent elo and/or rankings.
- Update UpcomingView to pass added features to prediction model 
- Ensure predictions are rendering in head_head.html
- Create documentation for prediction model for walkthrough of analytics methodology in presentation

---

## #56 — Site Wide UI/UX Improvements

**State:** CLOSED | **Author:** ken-hin | **Created:** 2026-04-07T15:40:50Z

- Continue improving overall website UI/UX across all pages
- Add more graphs, data, and fields on team_details.html
- Implement conference record and overall record for teams to be used in the conference cards in conferences.html
- Add team logos to team pages
- General team page enhancements

---

## #55 — Predictions Page Enhancements

**State:** CLOSED | **Author:** ken-hin | **Created:** 2026-04-07T15:34:35Z

- Fix season stats issue (team records not displaying properly)
- Polish UI for predictions page, ensure responsive layout
- Ensure proper data being displayed
- Generally improve the predictions page before deployment

---

## #53 — Fix Team Filtering and Refactor Codebase

**State:** CLOSED | **Author:** ken-hin | **Created:** 2026-04-06T18:19:56Z

- Break up html/css/js in teams.html into small portable files within the static and components directories
- Fix team card filtering bug on teams.html 

---

## #49 — Refactor services.py into modular package and add incremental update pipeline

**State:** CLOSED | **Author:** ken-hin | **Created:** 2026-04-05T14:44:18Z

- Break up `services.py` into a `services/` package for better organization
- Add helper functions to reduce duplicated code across sync and update flows
- Add `update_data` management command for lightweight daily database refreshes
- Move `NPM_BIN_PATH` out of `settings.py` and into `.env`

---

## #48 — Integrate Model

**State:** CLOSED | **Author:** ken-hin | **Created:** 2026-03-31T16:05:19Z

- Integrate prediction model output into a view and template
- Display predictions on a page
- Test for accuracy and document limitations

---

## #47 — Final production UI review

**State:** CLOSED | **Author:** ken-hin | **Created:** 2026-03-31T15:37:19Z

- Check for any layout issues
- Add favicon and meta description
- Ensure readability on custom team cards
- Update Conferences page to include more conference data per conference card

---

## #43 — Sprint 4: Build out a Head to Head games view page

**State:** CLOSED | **Author:** Jackson-Murphy04 | **Created:** 2026-03-26T15:58:22Z

Shows upcoming Games each game can be clicked to reveal stats and predictions about the upcoming matchup should probably be sorted by highest ranked matchups
Features ideas:
Offensive — PPG, RPG, APG, FG%, 3P%
Advanced — Def Rtg, Off Rtg, Net Rtg, Pace, L5 Form (last 5 games)
betting lines and our game predictions should also be shown

---

## #40 — Sprint 4: Make code revisions based on code_quality.md

**State:** CLOSED | **Author:** asworthington | **Created:** 2026-03-24T14:53:52Z

https://github.com/cs340-26/OpenCourt/blob/main/code_quality.md

---

## #35 — Sprint 4: Add New Views and Update Models

**State:** CLOSED | **Author:** ken-hin | **Created:** 2026-03-18T19:45:44Z

- Head-to-head matchup view (compare two teams side-by-side)
- Conference detail page
- Pull any additional data fields needed for charts and prediction model (game-by-game logs, opponent stats)
- Update models

---

## #34 — Sprint 4: Begin Building Model

**State:** CLOSED | **Author:** ken-hin | **Created:** 2026-03-18T19:41:23Z

- Build initial prediction model — feature engineering 
- Train/test split, baseline model (logistic regression or random forest)
- Evaluate accuracy
- Document approach

---

## #33 — Sprint 4: Data Preperation

**State:** CLOSED | **Author:** ken-hin | **Created:** 2026-03-18T19:39:03Z

- Determine best way to pull data from DB/Team Model to feed to model
- Historical trends (TeamSeasonStats) data pipeline
- Data preparation for prediction model
- Export to training format
- Data validation pass — check for missing/null values
- Handle edge cases in sync
- Ensure sync command is reliable and idempotent

---

## #32 — Sprint 4 (Week 1): Rankings Page

**State:** CLOSED | **Author:** ken-hin | **Created:** 2026-03-17T17:05:38Z

### Rankings Page ###
- Display all teams sorted by ranking
- Implement other sorting options based on stats besides ranking
- custom rankings page with sortable/filterable DaisyUI table

---

## #29 — Teams page UI, conference filtering, team detail view, and model relationships

**State:** CLOSED | **Author:** ken-hin | **Created:** 2026-03-09T19:57:48Z

## Overview
Build out the core teams browsing experience — a filterable teams page with
animated card interactions, individual team detail pages, and the underlying
model changes that tie teams to their conferences.
### Data model
- Add a ForeignKey from `Team` to `Conference`. Rename the existing `conference_id` integer to
  `api_conference_id` to avoid a Django column collision with the FK.
### Teams page
- Clean up teams.html 
- Add conference toggle filter buttons (ACC, Big 10, Big 12, Big East, SEC)
  with a reset button.
- Implement `conference_filter.js` with two animation layers: grow/shrink
  (opacity + scale) on cards entering or leaving, and a FLIP slide on cards
  that stay visible but shift position to fill empty space.
### Team detail page
- Add `TeamDetailView` and register the `<slug:slug>/` URL route.
- Add `team_details.html` template stub for the detail page.


---

## #23 — User Stories NEEDED

**State:** CLOSED | **Author:** Jackson-Murphy04 | **Created:** 2026-03-03T16:54:26Z

We need 2 user stories connected to issues in sprint 3 

For Sprint 3, there should be at least two user story issues per project. Issue title should start with "User Story XXX."


User Stories
‒ In their words, what the system needs to do for customers

User Story Template
‒ Feature: [Name]
As a [kind of stakeholder]
I want to [do some task],
so that [I can achieve some benefit]

---

## #22 — Begin Implementing Stat Calculation Functionality

**State:** CLOSED | **Author:** ken-hin | **Created:** 2026-02-28T01:05:51Z

- Research CBB API data fields; document fields needed to calculate win %, point differential, and Four Factors
- Implement win %, point differential, and pace in opencourt/stats.py 
- Write unit tests for each calculation

---

## #19 — [User Story Navbar and Team List] (https://github.com/cs340-26/OpenCourt/blob/main/UserStoryTeamListDisplay.md)

**State:** CLOSED | **Author:** ken-hin | **Created:** 2026-02-24T16:39:10Z

## [User Story Navbar and Team List] (https://github.com/cs340-26/OpenCourt/blob/main/UserStoryTeamListDisplay.md) ##  
 - Build navigation component in base.html 
 - Create team_list.html template with DaisyUI card or table layout 
 - Create team card component 


---

## #18 — [User Story Data Retrieval and Sync] (https://github.com/cs340-26/OpenCourt/blob/main/UserStoryDataSync.md)

**State:** CLOSED | **Author:** ken-hin | **Created:** 2026-02-24T16:35:59Z

## [User Story Data Retrieval and Sync] https://github.com/cs340-26/OpenCourt/blob/main/UserStoryDataSync.md ##
| Build out services.py |
| ---------------------- |
| - fetch_conferences() |
| - sync_conferences() |
### Write a management command (sync_data) to trigger syncing from the terminal ###


---

## #17 — Initial Models and Views

**State:** CLOSED | **Author:** ken-hin | **Created:** 2026-02-24T16:32:19Z

## Initial Models and Views ##
-  Define Team and Conference models in models.py
- run and commit initial migrations
- scaffold basic TeamListView and ConferenceListView

---

## #12 — Basic Navbar and About page setup

**State:** CLOSED | **Author:** Jackson-Murphy04 | **Created:** 2026-02-20T16:04:25Z

Try to learn how everything is setup by doing something. So add another template page (about) and edit base to add navbar to make sure I understand how everything is working together in the project. 

---

## #10 — Initial Project Scaffoliding

**State:** CLOSED | **Author:** ken-hin | **Created:** 2026-02-19T17:17:56Z

Django project scaffolding, config/ + opencourt/ app setup, Tailwind v4 + DaisyUI v5 integration, base template, home page, README, .gitignore, .env.example

---

## #8 — Final Review check all suggested changes have been made

**State:** CLOSED | **Author:** Jackson-Murphy04 | **Created:** 2026-02-19T16:49:42Z

go over the grad document to check that the updated proposoal implements the suggested changes

No week-by-week task breakdown — The schedule lists high-level deadlines from the syllabus but does not break down which features will be built each week.

Technology
Add a simple block diagram showing data flow: CBBData API → Django backend → SQLite → ApexCharts frontend.
Explicitly state the minimal system: e.g., "A working dashboard displaying team rankings and season stats for all D1 teams, with no predictions."

---

## #7 — Revise team and Project Management sections

**State:** CLOSED | **Author:** Jackson-Murphy04 | **Created:** 2026-02-19T16:48:19Z

Revise based on comments below:

Team: Individual backgrounds are detailed; PM role fixed + others rotating ✓
Management: Deadline schedule ✓; no week-by-week task breakdown; constraints and descoping are brief.

Constraints section is minimal — "Legal: NO" is not an adequate answer. Data scraping has terms-of-service implications (CBBData, EvanMiya). "Ethical: people using our data for personal financial decisions" is noted but not analyzed.

Expand the schedule to assign specific features to each week (not just deadline names).
Address the legal/ToS implications of scraping CBBData or EvanMiya's data.
Clarify descoping: if the predictive model is cut, does the site still have meaningful value? (Answer is yes — state it explicitly.)

---

## #6 — Revise Customer Value and Technology Sections

**State:** CLOSED | **Author:** Jackson-Murphy04 | **Created:** 2026-02-19T16:45:38Z

Revise based on comments below:

Customer Value: Need is thin ("free access"); measures of success are weak ("having useful tools for free?")
Tech: Good tools list; block diagram and minimal system not explicitly articulated

Customer Value is underdeveloped — "Free access to sports analytics" is a feature, not a customer need. Who specifically is the customer? Casual fan? Fantasy sports player? Scout? Their underlying problem is not explored.

Measures of success are weak — "Having useful tools available for free for anyone to use?" is not a customer-centric metric. How would you know users actually benefited?

Block diagram is absent — The technology section describes components but no architecture diagram (text or image) is included.

Customer Value
Define a specific customer persona: e.g., "A college basketball fan who plays ESPN bracket challenges and wants free team efficiency metrics."
Articulate the underlying problem more deeply: paywalls prevent casual fans from accessing data that informs their enjoyment and participation in bracket/fantasy contests.
Define measurable success metrics: e.g., "X unique visitors per month", "users return for >3 sessions during March Madness", "user survey rates the predictions as useful ≥4/5."


---

## #5 — Revise Heading and Introduction

**State:** CLOSED | **Author:** Jackson-Murphy04 | **Created:** 2026-02-19T16:43:01Z

Revise based on Comments below:
Heading: Title, team name, and members present; minor: backgrounds listed collectively, not per-person
Intro: Covers all elements; individual backgrounds are vague (pooled list rather than attributed)

Assign backgrounds to specific people: "Kenneth: CFB dashboard in Django. Alex: professional web dev experience. Jackson: ML models and web scraping. Samuel: ML/deep learning, Chrome extension."

Team backgrounds are pooled — The introduction lists skills collectively ("web-development, machine learning, statistics") rather than attributing them to specific individuals. It's not clear who knows what.

---

## #4 — Section 5 and final review

**State:** CLOSED | **Author:** Jackson-Murphy04 | **Created:** 2026-02-19T16:36:58Z

do section 5 project management and look over whole proposal for completeness 

---

## #3 — section 3 and 4

**State:** CLOSED | **Author:** Jackson-Murphy04 | **Created:** 2026-02-19T16:35:31Z

Section 3: Proposed Solution & Technology and Section 4: Team

---

## #2 — Customer Value

**State:** CLOSED | **Author:** Jackson-Murphy04 | **Created:** 2026-02-19T16:34:22Z

do section 2 of the proposal customer value

---

## #1 — Intro

**State:** CLOSED | **Author:** Jackson-Murphy04 | **Created:** 2026-02-19T16:33:15Z

write intro section of proposal

---

