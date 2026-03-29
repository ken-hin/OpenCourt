# Code Quality Grade — OpenCourt

**Evaluation Date:** 2026-03-29  
**Framework:** Functional Correctness & Robustness · Code Quality & Maintainability · Collaboration & Version Control

**Type:** Django web app (college basketball statistics)  
**Language:** Python · **LOC:** ~750 · **Source files:** 30

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

- **Automated Testing:** `tests.py` covers `win_percentage()` with four cases: normal, undefeated, winless, and the zero-game edge case (0–0 → 0.0%). This is the only project in the class with intentional tests tied to an explicit edge case. No view, model, or service tests exist yet.
- **Edge Case Handling:** The zero-division bug in `win_percentage` (originally unhandled) was addressed in Sprint 4. The API sync functions handle missing team-name matches with a silent `ignored_count` counter — a warning log for unexpectedly high ignored counts is still missing.
- **Security & Reliability:** API keys are loaded from environment variables. Exponential backoff with `Retry-After` support handles rate limiting correctly. No hardcoded secrets found. The `3pt_pct` dict key (digit-prefixed) is invalid in Django templates and will cause a `TemplateSyntaxError` at runtime.

---

## 2. Code Quality & Maintainability — ★★★★★

- **Readability & Style:** PEP 8 compliant throughout, with one minor exception: `class Meta :` has a space before the colon in `models.py`. Naming is consistent (snake_case throughout).
- **Documentation:** Best-documented codebase in the class. Every function and class has a comprehensive docstring explaining purpose, parameters, return values, error conditions, and links to related code.
- **Modularization:** Textbook Django separation — `models.py` (data), `views.py` (HTTP), `services.py` (API calls), `stats.py` (pure functions), `management/commands/` (CLI). Each layer is independently testable.
- **Complexity:** Logic is straightforward. The only unnecessary complexity is the redundant `get_queryset` override in `TeamListView` (returns `Team.objects.all()`, which is the default behavior).

---

## 3. Collaboration & Version Control — ★★★★☆

- **Commit History:** 106 total commits. Kenneth Hinman (70), Jackson Murphy (25), Alex Worthington (4), Samuel Bom (2). Commit messages are descriptive and specific. The work distribution is uneven — Kenneth carries a disproportionate share of implementation.
- **Branching Strategy:** 11 remote feature branches (`feature/rankings-page`, `feature/head-to-head-matchups`, `feature/conference-view`, etc.) with 24 PR merges. This is the strongest branching discipline in the class.
- **Integration:** No evidence of unresolved merge conflicts. Sprint 4 includes a dedicated issue (#40) for code revisions based on the code quality report, showing responsiveness to feedback.

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
2. Strongest branching strategy — 11 feature branches, 24 PR merges, code reviews before integration
3. Clean Django architecture — textbook service/model/view separation, each layer independently testable
4. Robust API error handling — exponential backoff, rate-limit awareness, three distinct failure modes handled

### Recommendations for Improvement
1. **Expand test coverage** — add tests for views (`TeamDetailView` context data) and services (with mocked API responses)
2. **Rename `3pt_pct` context key** to `three_pt_pct` — a digit-prefixed key is a `TemplateSyntaxError` in Django templates
3. **Add warning log** when `ignored_count` is unexpectedly high during stats sync (silent drops are hard to detect)
4. **Balance team contribution** — the other three members should take ownership of more implementation tasks
