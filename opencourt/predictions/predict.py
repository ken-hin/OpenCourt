from .features import build_features
from ..models import TeamSeasonStats
import pickle
from xgboost import XGBClassifier

# Make the predictions with the model on file
def make_predictions(team_a, team_b, home_advantage, model_path='OpenCourt/models/final_model.pkl'):

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
