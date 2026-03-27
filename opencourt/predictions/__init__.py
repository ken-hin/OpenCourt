# predictions/ — Game outcome prediction package.
#
# This package provides the pipeline for predicting college basketball
# game outcomes using TeamSeasonStats features from the Django ORM.
#
# Module overview:
#   features.py    — Extract and structure model features from TeamSeasonStats
#   model.py       — Load trained model from disk (singleton pattern)
#   predict.py     — Public interface: make_predictions(team_a, team_b, home_advantage, model_path='OpenCourt/models/final_model.pkl')
#   train_model.py — Standalone script to train the model on historical Game data
#   evaluate.py    — Standalone script to backtest model accuracy
#
# Usage from a Django view:
#   from opencourt.predictions.predict import make_predictions
#   result = make_predictions(team1, team2, home_advantage,)
