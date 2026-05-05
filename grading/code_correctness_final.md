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

## Manual Review (TA) — 2026-04-23

**Final Grade (Manual): 96 / 100 (A)**

**Students:** aworthi4 (Alex Worthington), jmurph91 (Jackson Murphy), khinman (Kenneth Hinman), sbombry1 (Samuel Bombrys)

### Sub-criterion breakdown

| Sub-criterion | Score | Comments |
|---|---:|---|
| 1a Automated Testing | 38/40 | 5+ test files covering URLs, views (40+ integration tests), stats helpers (14 unit tests with edge cases like zero games and float inputs), models, services with mocked API responses, and the predictions ML module (16+ tests). Tests documented with per-class docstrings. Minor: new `predictions/` module has lighter coverage than the rest. |
| 1b Edge Case Handling | 34/35 | Sprint 3 `3pt_pct` template bug fixed. Zero-division guard in `win_percentage` remains correct. Documented `ZeroDivisionError` risk in `build_features()` when `off_possessions=0` has not yet been fixed — test comments flag it as a known bug. |
| 1c Security & Reliability | 24/25 | API keys loaded from environment variables. Exponential backoff with `Retry-After` support handles rate limiting. No hardcoded secrets. Railway + Supabase deployment with env-based config. |

### Summary

Strongest functional correctness submission in the class — real test discipline, known bugs explicitly documented in test code, and production deployment with proper secret management.
