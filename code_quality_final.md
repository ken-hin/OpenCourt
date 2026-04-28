# Code Quality Final — OpenCourt

**Evaluation Date:** 2026-04-12  
**Scope:** Code Quality & Maintainability only  
**Rubric:** `news/rubric_quality.md`

| Sub-criterion | Score | Notes |
|---|---:|---|
| 2a — Readability & Style | 20 / 25 | Naming and formatting are consistent, but `opencourt/views.py` (641 lines) and `opencourt/models.py` (575 lines) are oversized and `views.py` has duplicated imports. |
| 2b — Documentation | 23 / 25 | Best documentation in the class: `models.py`, `views.py`, and `services/sync.py` all have strong file headers and function/class docstrings. |
| 2c — Modularization | 22 / 30 | Django layering is strong (`models.py`, `views.py`, `services/`, `predictions/`, `management/commands/`), but the main view/model modules have grown into large multi-responsibility files. |
| 2d — Complexity | 15 / 20 | Most logic is readable, but the very large view/model modules make the code harder to navigate than the smaller service modules. |

## Final Score: 80 / 100 (B-)

### Key Findings
- This is still one of the most maintainable repos in the class because the code is heavily documented and follows recognizable Django patterns.
- The main maintainability penalty is size: `views.py`, `models.py`, and `services/sync.py` are now large enough that they should be split by feature/domain.
- The strongest parts of the repo are the service modules and the predictions package, which keep purpose and naming clear.

---

## Manual Review (TA)

**Final Grade (Manual): 93 / 100 (A)**

**Students:** aworthi4, jmurph91, khinman, sbombry1

Best documentation in the class — models, views, and service modules all have strong file headers and function/class docstrings. Django architecture is solid with proper layering (models, views, services, predictions, management/commands). The service modules and predictions package demonstrate good architectural thinking and separation of concerns. The main issue is that `views.py` and `models.py` have grown large and could benefit from being split by feature/domain, but this is a natural consequence of an active, feature-rich project.

---

## Manual Review (TA) — Regrade 2026-04-23

**Final Grade (Manual Regrade): 100 / 100 (A+)**

**Students:** aworthi4 (Alex Worthington), jmurph91 (Jackson Murphy), khinman (Kenneth Hinman), sbombry1 (Samuel Bombrys)

Best-documented codebase in the class — docstrings on every function and class explaining parameters, return values, and error conditions. Textbook Django architecture (6 models, 7 class-based views, service/prediction/management command layers cleanly separated). Added an XGBoost ML pipeline in Sprint 4 cleanly isolated from app logic. PEP 8 compliant throughout, environment-based config, no hardcoded secrets. Nothing substantive missing under the rubric.
