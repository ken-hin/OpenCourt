# Sprint 3 User Story Final Evaluation — OpenCourt

## Result: ⚠️ PARTIAL

### User Story Files
| File | Present |
|---|---|
| `UserStoryDataSync.md` | ✅ |
| `UserStoryTeamListDisplay.md` | ✅ |

### Sprint 3 User Story Issues
| Issue | Title status | Notes |
|---|---|---|
| #18 | ⚠️ malformed hyperlink | Uses `[Title] (URL)` with a space before `(` |
| #19 | ⚠️ malformed hyperlink | Uses `[Title] (URL)` with a space before `(` |

### Rubric-Based Final Score
| Story | A Issue | B File | C Template | D Acceptance | Penalty | Scaled |
|---|---:|---:|---:|---:|---:|---:|
| Data Sync & Retrieval | 15/20 | 10/10 | 20/20 | 12/25 | 0 | 38/50 |
| Team List Display | 15/20 | 10/10 | 20/20 | 12/25 | 0 | 38/50 |

## Final Score: 76 / 100 (C)

### Notes
- Both required story files exist and both narratives are specific, useful, and clearly tied to real features.
- The main rubric deductions are structural: both issue titles still use `[Title] (URL)` instead of the exact `[Title](URL)` format, and both files use bullet-list acceptance criteria rather than Given/When/Then scenarios.
- Content quality is still strong, but the final rubric is stricter about exact assignment format.

### Changes from Previous Evaluation
- No substantive repo changes were detected in the user story files.
- The final score is lower than the earlier 10/10-style evaluation because `rubric_userstory.md` now applies point deductions for malformed issue-title links and non-Given/When/Then acceptance criteria.

---

## Manual Review (TA)

**Final Grade (Manual): 90 / 100 (A-)**

**Students:** aworthi4, jmurph91, khinman, sbombry1

Some of the strongest user story content in the class. Both stories have specific stakeholders, concrete tasks, and genuine benefits. Acceptance criteria are detailed, specific, and testable — Story 1 even includes a failure path (API unreachable) and a security requirement (no hardcoded keys), which most teams omit entirely. Story 2 handles the empty-state edge case. The automated grader penalized heavily for the space in `[Title] (URL)` and for using bullet lists instead of Given/When/Then, but the actual criteria quality exceeds most teams that use G/W/T format.

---

## Manual Review (TA) — Regrade 2026-04-23

**Final Grade (Manual Regrade): 100 / 100 (A+)**

**Students:** aworthi4 (Alex Worthington), jmurph91 (Jackson Murphy), khinman (Kenneth Hinman), sbombry1 (Samuel Bombrys)

Both stories are SMART with concrete specifics — CLI command `python manage.py sync_data`, measurable sync counts (created/updated/skipped), page paths `/teams/`, conference dropdown filter, and an explicit empty-database edge case. Full template compliance and full Given/When/Then in both files, hyperlinked in issues #18 and #19. Strongest user stories in the class.
