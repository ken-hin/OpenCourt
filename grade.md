# Project Proposal Grade: OpenCourt Stats

## Grade: 76 / 100

| Section | Points Possible | Points Awarded | Notes |
|---|---|---|---|
| Heading | 10 | 9 | Title, team name, and members present; minor: backgrounds listed collectively, not per-person |
| Introduction | 15 | 12 | Covers all elements; individual backgrounds are vague (pooled list rather than attributed) |
| Customer Value | 20 | 13 | Need is thin ("free access"); measures of success are weak ("having useful tools for free?") |
| Technology | 25 | 19 | Good tools list; block diagram and minimal system not explicitly articulated |
| Team | 15 | 13 | Individual backgrounds are detailed; PM role fixed + others rotating ✓ |
| Project Management | 15 | 10 | Deadline schedule ✓; no week-by-week task breakdown; constraints and descoping are brief |
| **Total** | **100** | **76** | |

---

## Key Issues

1. **Customer Value is underdeveloped** — "Free access to sports analytics" is a feature, not a customer need. Who specifically is the customer? Casual fan? Fantasy sports player? Scout? Their underlying problem is not explored.
2. **Measures of success are weak** — "Having useful tools available for free for anyone to use?" is not a customer-centric metric. How would you know users actually benefited?
3. **No week-by-week task breakdown** — The schedule lists high-level deadlines from the syllabus but does not break down *which features* will be built each week.
4. **Block diagram is absent** — The technology section describes components but no architecture diagram (text or image) is included.
5. **Team backgrounds are pooled** — The introduction lists skills collectively ("web-development, machine learning, statistics") rather than attributing them to specific individuals. It's not clear who knows what.
6. **Constraints section is minimal** — "Legal: NO" is not an adequate answer. Data scraping has terms-of-service implications (CBBData, EvanMiya). "Ethical: people using our data for personal financial decisions" is noted but not analyzed.

---

## Suggestions for Improvement

### Customer Value
- Define a specific customer persona: e.g., "A college basketball fan who plays ESPN bracket challenges and wants free team efficiency metrics."
- Articulate the underlying problem more deeply: paywalls prevent casual fans from accessing data that informs their enjoyment and participation in bracket/fantasy contests.
- Define measurable success metrics: e.g., "X unique visitors per month", "users return for >3 sessions during March Madness", "user survey rates the predictions as useful ≥4/5."

### Technology
- Add a simple block diagram showing data flow: CBBData API → Django backend → SQLite → ApexCharts frontend.
- Explicitly state the minimal system: e.g., "A working dashboard displaying team rankings and season stats for all D1 teams, with no predictions."

### Project Management
- Expand the schedule to assign specific features to each week (not just deadline names).
- Address the legal/ToS implications of scraping CBBData or EvanMiya's data.
- Clarify descoping: if the predictive model is cut, does the site still have meaningful value? (Answer is yes — state it explicitly.)

### Introduction
- Assign backgrounds to specific people: "Kenneth: CFB dashboard in Django. Alex: professional web dev experience. Jackson: ML models and web scraping. Samuel: ML/deep learning, Chrome extension."
