# features.py — Extract prediction features from TeamSeasonStats.
#
# This module converts Django ORM objects into flat feature dicts that
# the trained model can consume. It is the bridge between the database
# and the ML pipeline.
#
# Used by:
#   - predict.py  (at request time, called from views — Django already running)
#   - train_model.py (standalone — calls django.setup() before importing this)
#
# When running this file directly (for testing), Django is initialized
# below before any model imports.

import os, sys

# ── Django setup (must happen BEFORE importing any Django models) ────────
# When imported from a Django view, Django is already configured and this
# is a no-op. When run standalone, this bootstraps the ORM.
if not os.environ.get('DJANGO_SETTINGS_MODULE'):
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
    import django
    django.setup()

from datetime import date
from opencourt.models import TeamSeasonStats, Team

# ── Feature definition ───────────────────────────────────────────────────
# These field names must exactly match columns on TeamSeasonStats.
# The order matters when converting to an array for sklearn models.
#
# Grouped by category:
#   Four Factors (offense)  — the strongest predictors of team success
#   Four Factors (defense)  — opponent-side mirrors
#   Efficiency ratings      — tempo-independent scoring metrics
#   Tempo                   — affects game totals but not efficiency
#   Shooting                — granular shot-type breakdowns
#   Record                  — win percentage as a summary feature

FEATURE_FIELDS = [
    # Four Factors (offense)
    'off_eff_fg_pct',       # effective FG% — shooting efficiency
    'off_turnover_ratio',   # turnovers per 100 possessions
    'off_oreb_pct',         # offensive rebound %
    'off_ft_rate',          # FTA / FGA — free throw rate

    # Four Factors (defense / opponent)
    'opp_eff_fg_pct',       # opponent effective FG%
    'opp_turnover_ratio',   # opponent turnover ratio

    # Efficiency ratings
    'off_rating',           # points per 100 possessions (offense)
    'opp_rating',           # points allowed per 100 possessions (defense)

    # Tempo
    'pace',                 # possessions per 40 minutes

    # Shooting splits
    'off_3pt_pct',          # 3-point shooting %
    'off_ft_pct',           # free throw shooting %

    # Record
    'win_pct',              # season win percentage (0-100)
]


def get_team_features(team, season=None):
    """
    Pull a flat dict of prediction features for a single team.

    Args:
        team:   Team model instance or team primary key (int)
        season: Season year (int). Defaults to the current year.

    Returns:
        dict mapping feature names to float values, or None if no
        stats exist for the given team/season.
    """
    if season is None:
        season = date.today().year

    stats = TeamSeasonStats.objects.filter(team=team, season=season).first()
    if not stats:
        return None

    return {field: getattr(stats, field) or 0.0 for field in FEATURE_FIELDS}


def build_matchup_features(team1, team2, season=None):
    """
    Build the full feature vector for a matchup between two teams.

    Each team's stats are prefixed with home_ and away_ so the model
    can distinguish sides. Additional derived features (diffs) are
    appended to capture the relative strength between the two teams.

    Args:
        team1:  Team instance (home side)
        team2:  Team instance (away side)
        season: Season year (int). Defaults to the current year.

    Returns:
        dict of feature_name → float, or None if either team is missing stats.
    """
    home = get_team_features(team1, season)
    away = get_team_features(team2, season)

    if not home or not away:
        return None

    features = {}

    # Per-team features with home/away prefix
    for field in FEATURE_FIELDS:
        features[f'home_{field}'] = home[field]
        features[f'away_{field}'] = away[field]

    # Derived matchup features — differences that capture relative strength
    features['rating_diff']     = home['off_rating'] - away['off_rating']
    features['def_rating_diff'] = away['opp_rating'] - home['opp_rating']
    features['efg_diff']        = home['off_eff_fg_pct'] - away['off_eff_fg_pct']
    features['pace_diff']       = home['pace'] - away['pace']
    features['win_pct_diff']    = home['win_pct'] - away['win_pct']

    return features


def get_feature_names():
    """Return the ordered list of feature names the model expects."""
    names = []
    for field in FEATURE_FIELDS:
        names.append(f'home_{field}')
        names.append(f'away_{field}')
    names += ['rating_diff', 'def_rating_diff', 'efg_diff', 'pace_diff', 'win_pct_diff']
    return names


# ── Standalone testing ───────────────────────────────────────────────────
if __name__ == '__main__':
    # Django is already set up at the top of this file.
    # Quick smoke test: pick two teams and print their features
    team1 = Team.objects.filter(school__icontains='Duke').first()
    team2 = Team.objects.filter(school__icontains='North Carolina').first()

    if team1 and team2:
        features = build_matchup_features(team1, team2)
        if features:
            print(f"\n{team1.school} vs {team2.school}")
            print("-" * 50)
            for k, v in features.items():
                print(f"  {k:30s} = {v:.3f}")
        else:
            print("Missing season stats for one or both teams.")
    else:
        print("Could not find test teams in the database.")
