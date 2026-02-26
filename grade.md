# OpenCourt Stats Proposal Grade

## Grade: A- (90/100)

---

## Section-by-Section Evaluation

### Heading (8/10)
- ✅ Descriptive title: "OpenCourt Stats"
- ✅ Team name: "OpenCourt"
- ✅ All four team members listed
- ❌ GitHub team name not included
- ⚠️ Heading section could be more visually distinct from the body

### Section 1: Introduction (19/20)
- ✅ Project described clearly (full-stack web app for free CBB analytics)
- ✅ Motivation grounded in personal experience (paywall frustration)
- ✅ Market context with named competitors (EvanMiya.com, CBB Analytics)
- ✅ Novelty addressed (free, open access as differentiator)
- ✅ All four team backgrounds described with specific projects
- ✅ Reader orientation included (self-explanatory UI goal)
- ⚠️ No description of whether anyone has built a similar full-stack data app before as a team

### Section 2: Customer Value (21/25)
- ✅ Target audience precisely defined (ages 18–35, bracket participants, advanced stat followers)
- ✅ Underlying problem stated (paywalled advanced stats, surface-level free alternatives)
- ✅ Proposed solution from customer POV
- ✅ Five quantitative success metrics (200 unique users, 30% return rate, 3 min session, ≥4/5 usefulness rating, accuracy vs. baseline)
- ❌ Idea has not been tested on anyone — no user validation mentioned
- ⚠️ No mention of how/when user surveys will be conducted

### Section 3: Technology (22/25)
- ✅ Minimal system explicitly described (team rankings, conference filtering, team detail pages, 3 visualizations)
- ✅ Detailed ASCII architecture diagram with all layers labeled
- ✅ Comprehensive tools table (versions, purposes)
- ✅ Priority order for features (must/should/nice-to-have) effectively serves as descoping
- ❌ No dedicated testing section — how will the system be tested? (unit tests, data validation, load testing?)
- ⚠️ Predictions listed as a "stretch goal" but no description of what model type, training data, or accuracy target is envisioned

### Section 4: Team (9/10)
- ✅ Individual skills table with relevant experience
- ✅ Tools familiarity addressed ("challenge is integrating them")
- ✅ Roles table with clear responsibilities per person
- ❌ Rotating vs. fixed roles not stated
- ⚠️ No mention of what happens if the ML lead (Samuel) or PM/Backend lead (Kenneth) is unavailable

### Section 5: Project Management (18/20)
- ✅ Week-by-week schedule with feature-level detail and per-person assignment reference to Schedule.md
- ✅ Milestone table with dates
- ✅ Ethical constraints (gambling disclaimer)
- ✅ Legal constraints (API ToS, scraping policy, attribution)
- ✅ Resources (CBBData API coverage noted)
- ✅ Descoping with explicit priority order (must/should/nice-to-have)
- ❌ Meeting schedule not stated — when and how often does the team meet?
- ⚠️ Schedule defers to a separate Schedule.md — week-by-week detail should be present in the proposal itself

---

## Summary of Strengths
1. **Best architecture diagram** among web app proposals — detailed, layered, professional
2. **Strongest success metrics** — five quantitative targets including model accuracy vs. baseline
3. **Excellent legal section** — CBBData ToS, scraping policy, and attribution all addressed
4. **Clear MVP** — dashboard is useful even without the prediction model
5. **Professional structure** — numbered sections match the outline exactly

## Suggestions for Improvement
1. **Add a testing section** — specify unit tests (Django views/models), data validation tests, and how the prediction model's accuracy will be measured
2. **State meeting schedule** — when and how often does the team meet? (required by the outline)
3. **State rotating vs fixed roles** explicitly
4. **Test the idea on users** — even informal feedback from basketball fans would strengthen the customer value section
5. **Include GitHub team name** in the heading
6. **Move schedule detail into the proposal** — don't rely solely on a separate Schedule.md file; the outline requires a week-by-week schedule in the proposal
