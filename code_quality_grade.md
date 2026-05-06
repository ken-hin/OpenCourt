# Code Quality Grade — OpenCourt

**Evaluation Date:** 2026-04-07  
**Framework:** Functional Correctness & Robustness · Code Quality & Maintainability · Collaboration & Version Control

**Type:** Django web app (college basketball statistics + ML game prediction)  
**Language:** Python · **LOC:** ~3,800 · **Source files:** 35+

---

## Scoring Key

| Stars | Meaning |
|-------|---------|
| ★★★★★ | Excellent — meets or exceeds professional standards |
| ★★★★☆ | Good — minor gaps only |
| ★★★☆☆ | Adequate — functional but notable weaknesses |
| ★★☆☆☆ | Developing — significant gaps |
| ★☆☆☆☆ | Insufficient — major deficiencies |

---

## 1. Functional Correctness & Robustness — ★★★★☆

- **Automated Testing:** `tests.py` covers `win_percentage()` with four cases (normal, undefeated, winless, 0–0 edge case). Test count has not grown since Sprint 3 — the new `predictions/` ML module (`model.py`, `train_model.py`, `evaluate.py`, `predict.py`) has zero tests. No view or service tests exist.
- **Edge Case Handling:** The `3pt_pct` template bug from Sprint 3 is **fixed** — the context key was renamed to `three_pt_pct`, a valid Python identifier used safely in templates with `|safe`. The zero-division guard in `win_percentage` remains correct. API sync `ignored_count` counter still has no warning log when unexpectedly high.
- **Security & Reliability:** API keys loaded from environment variables. Exponential backoff with `Retry-After` support handles rate limiting correctly. No hardcoded secrets. A revert pattern (`Revert "Update settings.py"` / `Revert "Extract card contrast logic"`) visible in Sprint 4 suggests some merge instability in the final sprint, but the final state is clean.

---

## 2. Code Quality & Maintainability — ★★★★★

- **Readability & Style:** PEP 8 compliant throughout. Consistent snake_case naming. No regressions in style.
- **Documentation:** Best-documented codebase in the class. Every function and class has comprehensive docstrings explaining purpose, parameters, return values, and error conditions. The predictions module maintains this standard.
- **Modularization:** Textbook Django separation — `models.py`, `views.py`, `services/`, `stats.py`, `management/commands/`, and now `predictions/`. Each layer is independently testable.
- **Complexity:** Logic remains straightforward. The predictions module cleanly separates training (`train_model.py`) from inference (`predict.py`) and evaluation (`evaluate.py`).

---

## 3. Collaboration & Version Control — ★★★★☆

- **Commit History:** 143 total commits. Kenneth Hinman (94), Jackson Murphy (28), Alex Worthington (8), Sbombr (7). Kenneth's share decreased slightly (from ~66% to 66%) but the distribution remains uneven. Commit messages are descriptive and issue-linked.
- **Branching Strategy:** 13+ remote branches with 27+ documented PR merges, including `fix/team-card-filtering` (#54), `final-prod-ui` (#52), `feature/integrate-model` (#51), `feature/update-data-functions` (#50). Strongest branching discipline in the class.
- **Integration:** Multiple production-ready merges with issue-linked PR numbers. Double-revert pattern in the final sprint (`Revert "Update settings.py"` then re-apply) indicates some merge instability in the production UI branch, but the final state is clean.

---

## Summary

| Dimension | Rating |
|-----------|--------|
| Functional Correctness & Robustness | ★★★★☆ |
| Code Quality & Maintainability | ★★★★★ |
| Collaboration & Version Control | ★★★★☆ |
| **Overall** | **★★★★☆ — A−** |

### Top Strengths
1. Best-documented codebase in the class — comprehensive docstrings on every function and class
2. Strongest branching strategy — 13 feature branches, 27+ PR merges, issue-linked commits
3. Clean Django architecture — service/model/view/stats separation, each layer independently testable
4. Sprint 4 added a full ML predictions module — technically the most ambitious addition in the class

### Recommendations for Improvement
1. **Expand test coverage** — add tests for the new `predictions/` module and at least one view test
2. **Add warning log** when `ignored_count` exceeds a threshold during API sync — silent drops are hard to detect
3. **Balance team contribution** — Kenneth's 66% share should decrease; other members should own more Sprint deliverables
4. **Review before reverting** — the double-revert pattern in Sprint 4 suggests insufficient pre-merge review

---

## Changes from Previous Evaluation (2026-03-29)

- Commit count grew from 106 → 143; 4 new PRs merged in Sprint 4
- The previously reported `3pt_pct` template `TemplateSyntaxError` bug **is fixed** (renamed to `three_pt_pct`)
- New `predictions/` ML module added (game outcome prediction) — technically impressive but untested
- Two reverts appeared in the `final-prod-ui` branch suggesting merge instability, now resolved
- Grade unchanged at **A−**; the project remains the strongest in the class
