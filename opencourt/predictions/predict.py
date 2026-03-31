# predict.py — Create a dataframe using the teams classes
#
# Opens the model file and makes predictions based on the teams and parameters given,
# Makes a call to features build_features() function to get the features
# Predict is called through: from opencourt.predict import make_predictions
# Make predictions takes in two team classes and a path to the model file locations
# NOTE: home advantage has the following encoding depending on who has it.
# home_advantage = 1: Means team_a has advantage
# home_advantage = -1: Means team_b has advantage
# home_advantage = 0: Means no team has advantage


from .features import build_features
from ..models import TeamSeasonStats
import pickle
from xgboost import XGBClassifier

# Make the predictions with the model on file
def make_predictions(team_a, team_b, home_advantage, model_path='models/final_model'):

    # Build the feature data of what we are predicting
    matchup_data = build_features(team_a, team_b, home_advantage)

    # Error check
    try:
        with open(model_path, 'rb') as file:
            xg_model = pickle.load(file)

    except FileNotFoundError:
        return 1
    except Exception as e:
        return 1

    # Get the predictions and return
    pred = xg_model.predict(matchup_data)

    return pred
