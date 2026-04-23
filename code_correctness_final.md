# Code Correctness Final — OpenCourt

**Evaluation Date:** 2026-04-23  
**Scope:** Functional Correctness & Robustness only  
**Rubric:** `news/rubric_correctness.md`

| Sub-criterion | Score | Notes |
|---|---:|---|
| 1a — Automated Testing | 20 / 40 | `opencourt/tests.py` has four real tests for `win_percentage()`, including the 0–0 edge case, but there are no tests for views, services, or the newer `predictions/` module. |
| 1b — Edge Case Handling | 28 / 35 | The code handles several important cases well: `win_percentage()` guards zero games, `views.py` catches `TypeError`/`ZeroDivisionError`, and `services/fetch.py` implements retry/backoff for 429 responses with `Retry-After`. |
| 1c — Security & Reliability | 17 / 25 | API keys are loaded from environment variables and `DEBUG` defaults to false, but `config/settings.py` still falls back to a committed Django `SECRET_KEY`, which keeps this below the top tier. |

## Final Score: 65 / 100 (D)

### Key Findings
- This repo is stronger on edge-case handling than on testing.
- The main correctness gap is missing test coverage for the large sync/view/prediction surface area.
- The main security deduction is the insecure `SECRET_KEY` fallback in `config/settings.py`.
