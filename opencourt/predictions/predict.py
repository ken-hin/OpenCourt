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
import joblib
import logging
from xgboost import XGBClassifier

logger = logging.getLogger(__name__)

# Available trained models — swap DEFAULT_MODEL to compare predictions.
# joblib.load can open both sklearn (RandomForest) and XGBoost classifiers,
# so the loader code below doesn't need to branch on the file type.
RF_MODEL_PATH = 'models/RandomForest_model'
XGB_MODEL_PATH = 'models/XGBoost_model'
INIT_MODEL_PATH = 'models/init_model'
DEFAULT_MODEL = RF_MODEL_PATH

# Make the predictions with the model on file
def make_predictions(team_a, team_b, home_advantage, model_path=DEFAULT_MODEL):

    # Build the feature data of what we are predicting
    matchup_data = build_features(team_a, team_b, home_advantage)

    # Load the trained model. Use joblib.load so we can read both pickle-saved
    # and joblib-saved files — joblib uses custom numpy wrappers that bare
    # pickle.load can't reconstruct
    try:
        pred_model = joblib.load(model_path)
    except FileNotFoundError:
        logger.error("Prediction model not found at %s", model_path)
        return 1
    except Exception:
        logger.exception("Failed to load prediction model from %s", model_path)
        return 1

    # Get the predictions and return
    pred = pred_model.predict(matchup_data)

    return pred
