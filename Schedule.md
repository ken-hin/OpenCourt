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
| Proposal revision | ~Feb 24 ✓ |
| MVP + Status Report 1 | ~Mar 10 ✓ |
| Improve + Status Report 2 | ~Mar 24 ✓ |
| Testing + Status Report 3 | ~Apr 10 ✓ |
| Final project, report & presentation | **May 5** |

---

## Sprint Overview

```
Sprint 1 │ Feb 3  – Feb 18 │ Project Proposal                          ← Proposal due ~Feb 17 ✓
Sprint 2 │ Feb 18 – Mar 4  │ Proposal Revision + Foundation & Pipeline  ← Revision due ~Feb 24 ✓
Sprint 3 │ Mar 5  – Mar 17 │ Core Pages & MVP                          ← Status Report 1 ~Mar 10 ✓
Sprint 4 │ Mar 18 – Mar 31 │ Advanced Features & Analytics             ← Status Report 2 ~Mar 24 ✓
Sprint 5 │ Apr 1  – Apr 15 │ Deployment, Testing & Final Polish        ← Status Report 3 ~Apr 10 ✓
Sprint 6 │ Apr 16 – May 5  │ Production Launch, Report & Presentation  ← Final presentation May 5
```

---

## Sprint 1: Project Proposal (Feb 3 – Feb 18) ✓ COMPLETE

**Sprint Goal:** Submit a complete project proposal covering customer value, technology, team roles, and schedule.

**Sprint Deliverable:** Approved proposal.md submitted to the class.

| Person | Tasks |
|--------|-------|
| **Kenneth** | Project scaffolding, `config/` + `opencourt/` app setup, Tailwind v4 + DaisyUI v5 integration, base template, home page, README, .gitignore, .env.example ✓ |
| **All** | Collaborate on proposal sections; clone repo, run `uv sync`, `tailwind install`, confirm dev server works locally ✓ |

> **📋 Proposal due ~Feb 17** ✓

---

## Sprint 2: Proposal Revision + Foundation & Data Pipeline (Feb 18 – Mar 4) ✓ COMPLETE

**Sprint Goal:** Address all grader feedback on the proposal, get all teammates' environments working, and have the app connected to the CBBData API with core pages navigable.

**Sprint Deliverable:** Revised proposal.md submitted. `python manage.py sync_data` populates 50+ teams. Home → team list → team detail navigation works with real data.

---

### Week 1: Proposal Revision + Initial Setup (Feb 18 – Feb 24)

**Goals:** Address grader feedback, finalize schedule, resolve all dev environment issues across teammates' machines.

| Person | Tasks |
|--------|-------|
| **Kenneth** | Address grade.md feedback — customer persona, measures of success, block diagram, week-by-week schedule, expanded constraints; update Schedule.md with sprint structure ✓ |
| **Alex** | Resolve any local dev environment issues; review revised proposal ✓ |
| **Jackson** | Resolve npm/Node.js path issues (`NPM_BIN_PATH`); confirm `tailwind start` works on Windows machine ✓ |
| **Samuel** | Review revised proposal; confirm dev environment working locally ✓ |

**Milestone:** All teammates running the dev server. Revised proposal submitted. ✓

> **📋 Proposal Revision due ~Feb 24** ✓

---

### Week 2: Models, API Integration & Core Pages (Feb 24 – Mar 4)

**Goals:** Core database models defined, CBBData API connected, data syncing into the database, and core pages navigable with real data.

| Person | Tasks |
|--------|-------|
| **Kenneth** | Define `Team` and `Conference` models in `models.py`; run and commit initial migrations; build `HomeView`, `TeamListView`, `TeamDetailView`; URL routing for all core pages; pagination on team list ✓ |
| **Jackson** | Build out services layer — implement `fetch_teams()`, `fetch_conferences()`, `sync_teams()`, `sync_conferences()`; write `sync_data` management command; expand sync to game results; add error handling and logging ✓ |
| **Alex** | Build navigation component in `base.html`; `home.html` with conference cards/grid; `team_list.html` with search input and filter dropdowns (DaisyUI); `team_detail.html` page layout; responsive mobile navigation ✓ |
| **Samuel** | Research CBB API data fields; document fields needed for win %, point differential, and Four Factors; implement win %, point differential, and pace in `opencourt/stats.py`; write unit tests for each calculation ✓ |

**Milestone:** `sync_data` populates 50+ teams. Full navigation working — home → conference → team list → team detail, all with real data. ✓

---

## Sprint 3: Core Features & MVP (Mar 5 – Mar 17) ✓ COMPLETE

**Sprint Goal:** A fully navigable app with charts, analytics, and conference pages — functional enough to demo end-to-end for Status Report 1.

**Sprint Deliverable:** Working app with real data, 3+ charts, and full navigation. Ready to demo.

---

### Week 1: Charts & Four Factors (Mar 5 – Mar 11)

**Goals:** ApexCharts integrated, key visualizations rendering, Four Factors analytics live.

| Person | Tasks |
|--------|-------|
| **Kenneth** | Conference detail page; search functionality (filter teams by name/conference); ensure all views pass correct context for charts ✓ |
| **Jackson** | Pull any additional data fields needed for charts (game-by-game logs, opponent stats); write a script to backfill historical data if needed ✓ |
| **Alex** | Integrate ApexCharts — win/loss donut chart on team detail, points-per-game line chart, conference standings table ✓ |
| **Samuel** | Four Factors calculations (eFG%, TOV%, ORB%, FT rate); team comparison utility; pass analytics data into view context for charts to consume ✓ |

**Milestone: MVP complete — full working demo with real data and charts.** ✓

> **📋 Status Report 1 + MVP demo due ~Mar 10** ✓

---

### Week 2: Polish & Conference Pages (Mar 12 – Mar 17)

**Goals:** Conference pages complete, UI polished, all MVP PRs reviewed and merged.

| Person | Tasks |
|--------|-------|
| **Kenneth** | Code review Sprint 2–3 PRs; fix any blocking bugs from Status Report 1 feedback; conference standings view ✓ |
| **Jackson** | Data validation pass — verify all teams have complete data; fix any sync edge cases ✓ |
| **Alex** | Overall UI polish pass — consistent spacing, typography, DaisyUI component cleanup ✓ |
| **Samuel** | Document all stats calculations; ensure all analytics are passing correct data to templates ✓ |

**Milestone:** Clean, polished MVP with all conference pages working and PRs merged. ✓

---

## Sprint 4: Advanced Features & Analytics (Mar 18 – Mar 31) ✓ COMPLETE

**Sprint Goal:** Add 2–3 features beyond MVP. Prediction model built and integrated. App is polished and close to production quality.

**Sprint Deliverable:** Advanced features live, UI polished, mobile responsive, prediction model visible in UI.

---

### Week 1: Advanced Features & Prediction Model (Mar 18 – Mar 24)

**Goals:** Head-to-head comparisons, custom rankings, and prediction model foundations.

| Person | Tasks |
|--------|-------|
| **Kenneth** | Head-to-head matchup view (compare two teams side-by-side); custom rankings page with sortable table; review and merge PRs ✓ |
| **Jackson** | Historical trends data pipeline (multi-season if available); data preparation for prediction model — clean features, export to training format ✓ |
| **Alex** | Head-to-head comparison UI; custom rankings page with sortable/filterable DaisyUI table; historical trends chart (multi-season line chart in ApexCharts) ✓ |
| **Samuel** | Build initial prediction model — feature engineering, train/test split, XGBoost model; evaluate accuracy; document approach ✓ |

**Milestone:** Head-to-head page live. Prediction model producing outputs. ✓

> **📋 Status Report 2 due ~Mar 24** ✓

---

### Week 2: Polish & Model Integration (Mar 25 – Mar 31)

**Goals:** Bug fixes, performance, mobile layout, prediction model integrated into UI.

| Person | Tasks |
|--------|-------|
| **Kenneth** | Cross-browser testing (Chrome, Firefox, Safari); fix any critical backend bugs; performance check on slow queries; update documentation and code comments ✓ |
| **Jackson** | Data validation pass — check for missing/null values, handle edge cases in sync; ensure sync command is reliable and idempotent ✓ |
| **Alex** | Full mobile responsive pass; accessibility improvements (alt text, focus states, color contrast); CSS cleanup; final UI polish ✓ |
| **Samuel** | Integrate prediction model output into a view and template; display predictions on team detail or dedicated predictions page; test for accuracy and document limitations ✓ |

**Milestone:** Stable, polished app with predictions visible in the UI. ✓

---

## Sprint 5: Deployment, Testing & Final Polish (Apr 1 – Apr 15) ⚠️ MOSTLY COMPLETE

**Sprint Goal:** App is live on a public URL with a real PostgreSQL database, fully tested, and presentation-ready.

**Sprint Deliverable:** Production URL shared with class. All features working in production. Presentation drafted.

**Carried into Sprint 6:** Production deployment go-live (infrastructure configured but not yet deployed), favicon, presentation slide deck.

---

### Week 1: Production Deployment (Apr 1 – Apr 7)

**Goals:** Production environment live, PostgreSQL on Supabase, all environment variables configured.

| Person | Tasks |
|--------|-------|
| **Kenneth** | Set up hosting (Railway or Render) ✓; provision Supabase PostgreSQL database ✓; configure `DATABASE_URL` and all production environment variables (infra ready, final go-live pending); add `whitenoise` for static file serving ✓; run `collectstatic` and `migrate` against production DB — **rolled to Sprint 6** |
| **Jackson** | Run `sync_data` management command against production database to populate real data; verify sync works in the production environment — **rolled to Sprint 6** (blocked on go-live) |
| **Alex** | Final production UI review — check for any layout issues ✓; meta description added ✓; **favicon still outstanding — rolled to Sprint 6** |
| **Samuel** | Deploy and test prediction model in production ✓ (model working locally; verify in prod once live); verify predictions are accurate and displaying correctly ✓; document model methodology for the report ✓ |

**Milestone: App is live at a public URL.** ⚠️ infrastructure ready; final go-live deferred to Sprint 6.

---

### Week 2: Final Polish & Testing (Apr 7 – Apr 15)

**Goals:** Status Report 3 submitted. Code quality & user stories reviewed. Test coverage expanded.

| Person | Tasks |
|--------|-------|
| **Kenneth** | Fix remaining bugs ✓; review full codebase for cleanliness ✓; whitespace/style normalization across views.py ✓; Status Report 3 submitted ✓; code quality review (93/100) ✓ |
| **Alex** | UI polish — global margins, Four Factors radial chart stub, DaisyUI cleanup ✓; **presentation slide deck — rolled to Sprint 6** |
| **Jackson** | Final data sync and validation ✓; `update_data` management command reliability pass ✓; **talking points on data pipeline — rolled to Sprint 6** |
| **Samuel** | Prediction model documentation ✓; user stories final review (90/100) ✓; **walkthrough of analytics methodology for presentation — rolled to Sprint 6** |
| **All** | Tests package refactored (PR #62) ✓; full codebase review ✓ |

**Milestone:** Status Report 3 submitted; code quality + user stories graded (A/A-). ✓

> **📋 Status Report 3 due ~Apr 10** ✓

---

## Sprint 6: Production Launch, Report & Presentation (Apr 14 – May 5)

**Sprint Goal:** Take the app live in production, complete the final project report, polish the presentation, and deliver a flawless demo on May 5.

**Sprint Deliverable:** App live at a public URL. Final project report submitted. Presentation deck + backup demo recording ready. Presentation delivered May 5.

---

### Week 1: Production Go-Live & Outstanding Polish (Apr 14 – Apr 22)

**Goals:** App deployed to production with real data. Outstanding UI items (favicon, final polish) wrapped. Any lingering bugs squashed.

| Person | Tasks |
|--------|-------|
| **Kenneth** | Deploy app to Railway — run `collectstatic`, `migrate`, configure all env vars, confirm public URL is live; smoke-test every page in prod; fix any deploy-specific bugs (SSL, ALLOWED_HOSTS, static files); share production URL with the team |
| **Jackson** | Run `sync_data` against the Supabase production database; verify data integrity in prod; schedule `update_data` to refresh periodically; confirm prediction inputs are current |
| **Alex** | Add favicon and app icons to `/static/img/` and reference in `base.html`; final production UI review across mobile/desktop; take high-quality screenshots of every page for the slide deck |
| **Samuel** | Verify prediction model in production — sanity-check outputs, confirm accuracy metrics match dev; draft methodology section of the final report |

**Milestone:** App live at a public URL with real data. Favicon shipped. No open critical bugs.

---

### Week 2: Project Report & Slide Deck (Apr 23 – Apr 29)

**Goals:** Complete written project report. Build presentation slide deck. Record backup demo video.

| Person | Tasks |
|--------|-------|
| **Kenneth** | Lead final project report — architecture section, block diagram update, lessons learned, measures-of-success evaluation against proposal; coordinate content across teammates; record a polished backup demo video (screen recording with voiceover) of all key flows |
| **Alex** | Build presentation slide deck (title, problem/customer, demo flow, architecture, results, roadmap); ensure brand consistency with the app; add screenshots and short looping clips where helpful |
| **Jackson** | Write data pipeline section of the report — CBBData API, sync/update commands, data validation; prep 2–3 talking-point slides on data work |
| **Samuel** | Finalize prediction model writeup — features, training, evaluation, limitations; prep 2–3 slides on analytics methodology with evaluation metrics |
| **All** | First full dry run of presentation by end of week; each teammate owns their section |

**Milestone:** Draft slide deck and full report ready for rehearsal. Backup demo recording saved.

---

### Week 3: Rehearsal, Final Polish & Presentation (Apr 30 – May 5)

**Goals:** Presentation rehearsed multiple times. Every link and feature verified in production. Deliver on May 5.

| Person | Tasks |
|--------|-------|
| **Kenneth** | Final production smoke test morning of May 5; confirm backup demo video is ready if live demo fails; submit final project materials (report + repo link + production URL) |
| **Alex** | Slide deck polish — final typography, transitions, timing; ensure deck opens cleanly on presentation machine |
| **Jackson** | Final `update_data` run against prod the day before; confirm latest games are reflected in the UI |
| **Samuel** | Final rehearsal of analytics/predictions walkthrough; prep answers for likely Q&A on model methodology |
| **All** | Two full dress rehearsals (Apr 30 and May 3); run-of-show agreed; handoffs between speakers practiced; backup plan (video demo) ready |

**Milestone:** Presentation delivered May 5. Final submission complete.

> **🏁 Final submission + presentation: May 5**

---

## Key Milestones

| Milestone | Date |
|-----------|------|
| Proposal submitted | Feb 17 ✓ |
| Proposal revision submitted | Feb 24 ✓ |
| Real data syncing from CBB API | Feb 28 ✓ |
| Core pages complete (list, detail, navigation) | **Mar 4** ✓ |
| **MVP complete — ready to demo** | **Mar 10** ✓ |
| Advanced features + predictions live | Mar 24 ✓ |
| App fully polished and stable | Mar 31 ✓ |
| Status Report 3 + code quality review | Apr 10 ✓ |
| **Production deployment live** | **Apr 22** |
| Report + slide deck drafted | Apr 29 |
| Presentation rehearsed (dress runs) | Apr 30 / May 3 |
| **Final submission + presentation** | **May 5** |

---

## Contingency Plans

**If behind schedule:**
- Cut prediction model from Sprint 4 — defer to post-MVP stretch goal
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

*Last Updated: Apr 16, 2026*
