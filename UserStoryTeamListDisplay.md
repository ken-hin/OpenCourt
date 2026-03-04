# User Story: Team List Display

**As a** casual fan visiting OpenCourt,
**I want** to browse a list of all Division I teams organized by conference,
**so that** I can quickly find and navigate to my team's stats page.

## Acceptance Criteria

- `/teams/` renders a card for every team in the database
- Each card displays the team school name, mascot, and conference
- Teams can be filtered by conference using a dropdown
- The page handles an empty database gracefully (shows a message instead of a blank grid)
- Cards wrap responsively across screen sizes

## Notes

- `TeamListView` is implemented in `opencourt/views.py`
- Template lives at `templates/opencourt/teams.html`
- DaisyUI `card` component should be used for each team card
- Filtering can be done client-side with Alpine.js or server-side via query params
