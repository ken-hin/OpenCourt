# stats.py statistic calculation for django app

# Calculates win percentage using the wins and losses from the TeamSeasonUnitStats as documented in the api
# Percent is given as a whole number
# EDGE CASE: will raise ZeroDivisionError if both wins and losses are 0 (i.e. a team with no games played).
# This shouldn't occur with real API data mid-season, but should be handled before this function
# is called from a view or exposed to user input.
def win_percentage(wins, losses):
    total_games = wins + losses
    percent_wins = round((wins / total_games) * 100, 2) # Just decided to round 2 digits.
    return percent_wins

# Calculates the difference from points scored to points allowed in a single season
def point_differential(scored_points, allowed_points):
  return scored_points - allowed_points


# The api has the pace pre-computed in the TeamSeasonStats portion
# I'll leave this here unless we decide to still calculate our own
#def pace(possessions, total_Minutes):
# return possessions / total_minutes

# The four factors are the most "important" factors for a basketball teams success,
# with them being shooting(40%), turnovers(25%), rebounding(20%), and free throws(15%).
# Naming and source is: https://www.basketball-reference.com/about/factors.html
#   - Shooting is measured through eFG%(effective field goal percentage) = (FG + 0.5 *3P) / FGA
#   - Turnovers is TOV%(Turnover percentage) = TOV / (FGA + 0.44 * FTA + TOV)
#   - Rebounding is measured through ORB% and DRB%(offensive and defensive rebound percentage) = ORB / (ORB + Opp DRB) & DRB / (DRB + Opp DRB) for the defensive and offensive respectively
#   - Free throws are just FT / FTA.
