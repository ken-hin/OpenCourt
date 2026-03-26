# predict.py — Public prediction interface.
#
# This is the module your Django views import. It ties together
# features.py (data extraction) and model.py (model loading) to
# produce a prediction result for a given matchup.
#
# Usage from a view:
#   from opencourt.predictions.predict import predict_matchup
#   result = predict_matchup(team1, team2)
#   # result = {
#   #     'home_team': <Team>,
#   #     'away_team': <Team>,
#   #     'home_win_prob': 0.63,
#   #     'away_win_prob': 0.37,
#   #     'predicted_winner': <Team>,
#   #     'confidence': 0.63,
#   # }

from datetime import date
from .features import build_matchup_features, get_feature_names
from .model import load_model


def predict_matchup(home_team, away_team, season=None):
    """
    Predict the outcome of a matchup between two teams.

    Args:
        home_team:  Team model instance (home side)
        away_team:  Team model instance (away side)
        season:     Season year (int). Defaults to the current year.

    Returns:
        dict with prediction results:
            home_team        — the home Team object
            away_team        — the away Team object
            home_win_prob    — float, probability that home team wins (0-1)
            away_win_prob    — float, probability that away team wins (0-1)
            predicted_winner — Team object of the predicted winner
            confidence       — float, the winning probability (0.5-1.0)

        Returns None if features can't be built (missing season stats)
        or if the model file hasn't been trained yet.
    """
    if season is None:
        season = date.today().year

    # Build the feature vector for this matchup
    features = build_matchup_features(home_team, away_team, season)
    if features is None:
        return None

    # Load the trained model (cached after first call)
    try:
        model = load_model()
    except FileNotFoundError:
        return None

    # Convert features dict to ordered list matching training column order
    feature_names = get_feature_names()
    feature_values = [features.get(name, 0.0) for name in feature_names]

    # predict_proba returns [[P(away_wins), P(home_wins)]]
    # Class ordering depends on how the model was trained.
    # Convention: class 0 = away win, class 1 = home win
    probabilities = model.predict_proba([feature_values])[0]
    home_win_prob = float(probabilities[1])
    away_win_prob = float(probabilities[0])

    predicted_winner = home_team if home_win_prob >= 0.5 else away_team
    confidence = max(home_win_prob, away_win_prob)

    return {
        'home_team': home_team,
        'away_team': away_team,
        'home_win_prob': round(home_win_prob, 4),
        'away_win_prob': round(away_win_prob, 4),
        'predicted_winner': predicted_winner,
        'confidence': round(confidence, 4),
    }
