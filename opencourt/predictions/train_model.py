#!/usr/bin/env python
"""
train_model.py — Train the game outcome prediction model.

Standalone script. Run from the project root:
    python -m opencourt.predictions.train_model

Or directly (the Django setup block below handles the import path):
    python opencourt/predictions/train_model.py

What it does:
    1. Queries historical Game results from the database
    2. For each game, builds a feature vector from both teams'
       TeamSeasonStats for that season (via features.py)
    3. Trains a logistic regression (swap for RandomForest, XGBoost, etc.)
    4. Saves the trained model to predictions/trained_model.pkl
"""

# ── Django setup (required for standalone execution) ─────────────────────
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

import django
django.setup()

# ── Imports ──────────────────────────────────────────────────────────────
from pathlib import Path
import numpy as np
import joblib
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline

from opencourt.models import Game
from opencourt.predictions.features import build_matchup_features, get_feature_names

# Output path for the trained model
MODEL_PATH = Path(__file__).resolve().parent / 'trained_model.pkl'

# How many seasons back to use for training data
TRAINING_SEASONS_BACK = 5


def build_training_data():
    """
    Build X (features) and y (labels) arrays from historical games.

    For each completed game with a known winner, builds a feature vector
    from both teams' season stats and labels it:
        y = 1 if home team won, 0 if away team won.

    Returns:
        X — numpy array of shape (n_games, n_features)
        y — numpy array of shape (n_games,) with values 0 or 1
    """
    from datetime import date
    current_year = date.today().year
    start_season = current_year - TRAINING_SEASONS_BACK

    games = (
        Game.objects
        .filter(
            season__gte=start_season,
            season__lt=current_year,     # exclude current season (incomplete)
            home_winner__isnull=False,    # only completed games with a result
        )
        .select_related('home_team', 'away_team')
    )

    feature_names = get_feature_names()
    X_rows = []
    y_rows = []
    skipped = 0

    print(f"Building training data from {games.count()} games "
          f"(seasons {start_season}–{current_year - 1})...")

    for game in games.iterator():
        features = build_matchup_features(
            game.home_team, game.away_team, season=game.season
        )

        if features is None:
            skipped += 1
            continue

        row = [features.get(name, 0.0) for name in feature_names]
        X_rows.append(row)
        y_rows.append(1 if game.home_winner else 0)

    print(f"  Built {len(X_rows)} samples ({skipped} skipped — missing stats)")

    return np.array(X_rows), np.array(y_rows)


def train():
    """Train the model, print metrics, and save to disk."""
    X, y = build_training_data()

    if len(X) == 0:
        print("No training data available. Make sure games and season stats are synced.")
        return

    # Split into train/test sets
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    print(f"\n  Training set: {len(X_train)} games")
    print(f"  Test set:     {len(X_test)} games")

    # Build a pipeline: scale features → logistic regression
    # Samuel can swap LogisticRegression for RandomForestClassifier,
    # GradientBoostingClassifier, etc.
    pipeline = Pipeline([
        ('scaler', StandardScaler()),
        ('classifier', LogisticRegression(
            max_iter=1000,
            random_state=42,
            C=1.0,             # regularization strength (tune via CV)
        )),
    ])

    pipeline.fit(X_train, y_train)

    # Evaluate
    train_acc = pipeline.score(X_train, y_train)
    test_acc = pipeline.score(X_test, y_test)
    print(f"\n  Train accuracy: {train_acc:.4f}")
    print(f"  Test accuracy:  {test_acc:.4f}")

    # Baseline comparison: always predict home win
    home_win_rate = y.mean()
    print(f"  Baseline (always home): {home_win_rate:.4f}")

    # Save the trained model
    joblib.dump(pipeline, MODEL_PATH)
    print(f"\n  Model saved to {MODEL_PATH}")


if __name__ == '__main__':
    train()
