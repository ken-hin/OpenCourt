# Collaboration & Version Control — OpenCourt

**Evaluation Date:** 2026-05-11
**Rubric:** `news/rubric_collaboration.md` (3a /35 + 3b /35 + 3c /30 = 100)

---

## 3a. Commit History — 29/35

- 212 total commits between 2026-02-05 and 2026-05-07 — the most commits of any team in the class.
- Author distribution (student commits): Kenneth Hinman 143 (72%), Jackson Murphy 37 (19%), Alex Worthington 11 (6%), Sbombr/Samuel Bombrys 9 (5%). Alex and Samuel are below the 15% benchmark by commit count.
- **By lines, the distribution is far better than commit counts suggest:** Kenneth 21,637 ins (dominant), Jackson 8,278 ins, Alex 4,922 ins, Samuel 1,123 ins. All four members wrote substantial code.
- **Best commit-message quality in the class.** Examples: `Refactor UpcomingView with batched predictions`, `Add daily cron schedule to deploy`, `Clarify season field semantics in models`, `Add calendar view and game-card partial`, `Document and tidy Upcoming/Calendar templates`, `Prefix cron startCommand with 'uv run'`. Every message reads like a senior engineer wrote it.

## 3b. Branching Strategy — 34/35

- 30+ feature branches with **textbook conventional naming** — `feature/integrate-model`, `feature/headToHeadView`, `feature/ranking-data-Jackson`, `feature/chron-functions`, `fix/team-card-filtering`, `fix/general-refactoring`, `enhance/add-tests`, `enhance/model`, `enhance/predictions`, `enhance/predictions-calendar`, `refactor/grading-docs`, `update/update-deps`, `update/teams-list-page`, `documentation/head-head`, `bug/dataFix`, `final-prod-ui`, `ui-improvements`. **All `feature/`, `fix/`, `enhance/`, `refactor/`, `update/`, `chore/`, `docs/` prefix conventions used correctly.**
- 30+ PR merges with many `closes #N` references in the descriptions — issue-driven development.
- Merged branches are deleted (only `main` remains) — perfect post-merge hygiene.

## 3c. Integration — 30/30

- Live production deployment on Railway with a daily cron job; the integrated product is observable on the public internet, not just in the repo.
- End-to-end integration: data ingestion → prediction model → frontend templates with calendar/upcoming/head-to-head views — all wired together via the documented Railway deploy.
- Cron-based daily data update merged in late April shows the team is still hardening the integrated system in the final week.

---

## Summary

| Sub-Criterion | Score |
|---|---|
| 3a — Commit History | 29/35 |
| 3b — Branching Strategy | 34/35 |
| 3c — Integration | 30/30 |
| **Raw Total** | **93/100** |

---

## Manual Review (TA)

**Final Grade: 97/100 (A+)**

**Students:**
- sbombry1 — Samuel Bombrys
- khinman — Kenneth Hinman
- jmurph91 — Jackson Murphy
- aworthi4 — Alex Worthington

**Comment:** Exemplary git discipline — best commit messages in the class, textbook conventional branch naming (`feature/`, `fix/`, `enhance/`, `refactor/`, `chore/`, `docs/`), issue-driven PRs with `closes #N`, post-merge branch cleanup, and a live production deployment. By commit count Kenneth dominates, but by lines all four members ship substantial code. This is the model for the class.
