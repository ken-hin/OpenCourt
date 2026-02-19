# OpenCourt — Project Schedule

## Team

| Name | Role | Strengths |
|------|------|-----------|
| **Kenneth Hinman** | Project Manager / Backend Lead | Django, Python, full-stack architecture, prior CFB dashboard |
| **Alex Worthington** | UI/UX / Frontend Lead | HTML, CSS, Bootstrap/Tailwind, professional web dev experience |
| **Jackson Murphy** | Data Pipeline / API Lead | Web scraping, Python data work, API integration, some ML |
| **Samuel Bombrys** | Analytics / ML Lead | Python ML & deep learning, statistics, data modeling |

---

## Class Deadlines

| Deadline | Date |
|----------|------|
| Proposal due | ~Feb 17 ✓ |
| Proposal revision | ~Feb 24 |
| MVP + Status Report 1 | ~Mar 10 |
| Improve + Status Report 2 | ~Mar 24 |
| Testing + Status Report 3 | ~Apr 10 |
| Complete project, report & presentation | **Apr 14** |

---

## Sprint Overview

```
Sprint 1 │ Feb 12 – Feb 25 │ Weeks 1-2 │ Foundation & Data Pipeline
Sprint 2 │ Feb 26 – Mar 11 │ Weeks 3-4 │ Core Pages & MVP          ← Status Report 1
Sprint 3 │ Mar 12 – Mar 25 │ Weeks 5-6 │ Advanced Features & Polish ← Status Report 2
Sprint 4 │ Mar 26 – Apr 9  │ Weeks 7-8 │ Deployment & Final Polish  ← Status Report 3
Final    │ Apr 10 – Apr 14 │           │ Presentation & Submission
```

---

## Sprint 1: Foundation & Data Pipeline (Feb 12 – Feb 25)

**Sprint Goal:** Project is scaffolded, running locally for all teammates, and pulling real CBB data into the database.

**Sprint Deliverable:** Live dev server showing team list page populated with real API data.

---

### Week 1: Setup & Scaffolding (Feb 12–18) ✓ COMPLETE

**Goals:** Django project structure, Tailwind/DaisyUI integration, git workflow established.

| Person | Tasks |
|--------|-------|
| **Kenneth** | Django project scaffolding, `config/` + `opencourt/` app setup, Tailwind v4 + DaisyUI v5 integration, base template, home page, README, .gitignore, .env.example |
| **All** | Clone repo, run `uv sync`, `tailwind install`, confirm dev server works locally |

**Milestone:** Everyone can run the dev server and see the home page. ✓

---

### Week 2: Models & Data Pipeline (Feb 19–25)

**Goals:** Core database models defined, CBB API connected, real team data syncing into the database.

| Person | Tasks |
|--------|-------|
| **Kenneth** | Define `Team` and `Conference` models in `models.py`; run and commit initial migrations; scaffold basic `TeamListView` and `ConferenceListView` |
| **Jackson** | Build out `services.py` — implement `fetch_teams()`, `fetch_conferences()`, `sync_teams()`, `sync_conferences()`; write a management command (`sync_data`) to trigger syncing from the terminal |
| **Alex** | Build navigation component in `base.html`; create `team_list.html` template with DaisyUI card or table layout; team card component |
| **Samuel** | Research all available CBB API data fields; document which fields are needed for win %, point differential, and Four Factors; verify data quality and note any gaps |

**Milestone:** `python manage.py sync_data` populates 50+ teams in the database. Team list page renders real data.

> **📋 Proposal Revision due ~Feb 24**

---

## Sprint 2: Core Pages & MVP (Feb 26 – Mar 11)

**Sprint Goal:** A fully navigable app with team list, team detail, and conference pages — functional enough to demo end-to-end.

**Sprint Deliverable:** Working app with real data, 3+ charts, and full navigation. Ready to demo.

---

### Week 3: Core Pages (Feb 26 – Mar 4)

**Goals:** Home page with conference overview, team list with filtering, team detail page.

| Person | Tasks |
|--------|-------|
| **Kenneth** | `HomeView` passing conference data to template; `TeamDetailView` with full stats context; URL routing for all core pages; pagination on team list |
| **Jackson** | Expand data sync to include game results if available from API; add error handling and logging to `services.py`; populate any missing fields identified by Samuel |
| **Alex** | `home.html` with conference cards/grid; `team_list.html` with search input and filter dropdowns (DaisyUI); `team_detail.html` page layout; responsive mobile navigation |
| **Samuel** | Implement win %, point differential, and pace as model properties or utility functions in a new `opencourt/stats.py`; write unit tests for each calculation |

**Milestone:** Full navigation working — home → conference → team list → team detail.

---

### Week 4: Charts & Analytics (Mar 5–11)

**Goals:** ApexCharts integrated, key visualizations rendering, MVP complete and demo-ready.

| Person | Tasks |
|--------|-------|
| **Kenneth** | Conference detail page; search functionality (filter teams by name/conference); ensure all views pass correct context for charts; code review Sprint 1–2 PRs |
| **Jackson** | Pull any additional data fields needed for charts (game-by-game logs, opponent stats); write a script to backfill historical data if needed |
| **Alex** | Integrate ApexCharts — win/loss donut chart on team detail, points-per-game line chart, conference standings table; overall UI polish pass before demo |
| **Samuel** | Four Factors calculations (eFG%, TOV%, ORB%, FT rate); team comparison utility; pass analytics data into view context for charts to consume |

**Milestone: MVP complete — full working demo with real data and charts.**

> **📋 Status Report 1 + MVP demo due ~Mar 10**

---

## Sprint 3: Advanced Features & Polish (Mar 12 – Mar 25)

**Sprint Goal:** Add 2–3 "wow" features beyond the MVP. App is polished, stable, and close to production quality.

**Sprint Deliverable:** Advanced features live, UI polished, mobile responsive, code cleaned up.

---

### Week 5: Advanced Features (Mar 12–18)

**Goals:** Head-to-head comparisons, custom rankings, and prediction model foundations.

| Person | Tasks |
|--------|-------|
| **Kenneth** | Head-to-head matchup view (compare two teams side-by-side); custom rankings page with sortable table; review and merge PRs |
| **Jackson** | Historical trends data pipeline (multi-season if available); data preparation for Samuel's prediction model — clean features, export to format suitable for training |
| **Alex** | Head-to-head comparison UI; custom rankings page with sortable/filterable DaisyUI table; historical trends chart (multi-season line chart in ApexCharts) |
| **Samuel** | Build initial prediction model — feature engineering, train/test split, baseline model (logistic regression or random forest); evaluate accuracy; document approach |

**Milestone:** Head-to-head page live. Prediction model producing outputs.

---

### Week 6: Polish & Testing (Mar 19–25)

**Goals:** Bug fixes, performance, mobile layout, prediction model integrated.

| Person | Tasks |
|--------|-------|
| **Kenneth** | Cross-browser testing (Chrome, Firefox, Safari); fix any critical backend bugs; performance check on slow queries; update documentation and code comments |
| **Jackson** | Data validation pass — check for missing/null values, handle edge cases in sync; ensure sync command is reliable and idempotent |
| **Alex** | Full mobile responsive pass; accessibility improvements (alt text, focus states, color contrast); CSS cleanup; final UI polish |
| **Samuel** | Integrate prediction model output into a view and template; display predictions on team detail or dedicated predictions page; test for accuracy and document limitations |

**Milestone:** Stable, polished app with predictions visible in the UI.

> **📋 Status Report 2 due ~Mar 24**

---

## Sprint 4: Deployment & Final Polish (Mar 26 – Apr 9)

**Sprint Goal:** App is live on a public URL with a real PostgreSQL database.

**Sprint Deliverable:** Production URL shared with class. All features working in production.

---

### Week 7: Deployment (Mar 26 – Apr 1)

**Goals:** Production environment live, PostgreSQL on Supabase, all environment variables configured.

| Person | Tasks |
|--------|-------|
| **Kenneth** | Set up hosting (Railway or Render); provision Supabase PostgreSQL database; configure `DATABASE_URL` and all production environment variables; add `whitenoise` for static file serving; run `collectstatic` and `migrate` against production DB; go live |
| **Jackson** | Run `sync_data` management command against production database to populate real data; verify sync works in the production environment |
| **Alex** | Final production UI review — check for any layout issues; add favicon and meta description; test all pages on production URL |
| **Samuel** | Deploy and test prediction model in production; verify predictions are accurate and displaying correctly; document model methodology for the report |

**Milestone: App is live at a public URL.**

---

### Week 8: Final Polish & Presentation Prep (Apr 2–9)

**Goals:** No open bugs. Presentation ready. Demo rehearsed.

| Person | Tasks |
|--------|-------|
| **Kenneth** | Final production data check; fix any remaining bugs; review full codebase for cleanliness; finalize project report |
| **Alex** | Build presentation slide deck; ensure UI looks its best for the demo; create any screenshots or screen recordings needed |
| **Jackson** | Final data sync and validation in production; prepare talking points on the data pipeline for the presentation |
| **Samuel** | Finalize prediction model documentation; prepare walkthrough of analytics methodology for the presentation |
| **All** | Practice presentation; full demo run-through; agree on who covers each section |

**Milestone: Presentation rehearsed and ready.**

> **📋 Status Report 3 due ~Apr 10**

---

## Final Week (Apr 10–14)

| Task | Owner |
|------|-------|
| Final production check — all features working | Kenneth |
| Submit project materials | All |
| Deliver presentation | All |
| Live app demo | Kenneth (driver) |

> **🏁 Final submission + presentation: ~Apr 14**

---

## Key Milestones

| Milestone | Date |
|-----------|------|
| All teammates running dev server locally | Feb 25 |
| Real data syncing from CBB API | Feb 25 |
| Core pages complete (list, detail, navigation) | Mar 4 |
| **MVP complete — ready to demo** | **Mar 10** |
| Advanced features + predictions live | Mar 18 |
| App fully polished and stable | Mar 25 |
| **Production deployment live** | **Apr 1** |
| Presentation rehearsed | Apr 9 |
| **Final submission** | **Apr 14** |

---

## Contingency Plans

**If behind schedule:**
- Cut prediction model from Week 5 — defer to post-MVP stretch goal
- Simplify charts to 2 core visualizations (win/loss donut + standings table)
- Use static fixture data instead of live sync if API issues arise
- Focus on a polished, stable app over feature count

**If ahead of schedule:**
- More prediction model features (player-level predictions, confidence intervals)
- Additional chart types (shot charts, efficiency scatter plots)
- User accounts with saved favorite teams
- Improved UI animations and transitions

---

## Definition of Done

A task is only complete when:
- [ ] Code is on a feature branch and PR is open
- [ ] PR has been reviewed by at least one teammate
- [ ] Branch is merged to `main`
- [ ] Feature works locally on all teammates' machines

---

*Last Updated: Feb 19, 2026*
