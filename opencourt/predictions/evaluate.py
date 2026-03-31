#!/usr/bin/env python
"""
evaluate.py — Backtest the trained prediction model.

Standalone script. Run from the project root:
    python -m opencourt.predictions.evaluate

Evaluates the model against the current season's completed games
(data the model was NOT trained on) and prints accuracy metrics,
a classification report, and a confidence calibration summary.
"""

# ── Django setup (required for standalone execution) ─────────────────────
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

import django
django.setup()

# ── Imports ──────────────────────────────────────────────────────────────
from datetime import date
import numpy as np
from sklearn.metrics import accuracy_score, classification_report

from opencourt.models import Game
from opencourt.predictions.features import build_matchup_features, get_feature_names
from opencourt.predictions.model import load_model


def evaluate():
    """Run the model against current season games and print results."""
    current_year = date.today().year

    try:
        model = load_model()
    except FileNotFoundError as e:
        print(f"Error: {e}")
        return

    # Get completed games from the current season (hold-out set)
    games = (
        Game.objects
        .filter(season=current_year, home_winner__isnull=False)
        .select_related('home_team', 'away_team')
    )

    feature_names = get_feature_names()
    y_true = []
    y_pred = []
    y_prob = []
    skipped = 0

    print(f"Evaluating on {games.count()} current season games...")

    for game in games.iterator():
        features = build_matchup_features(
            game.home_team, game.away_team, season=game.season
        )
        if features is None:
            skipped += 1
            continue

        row = [features.get(name, 0.0) for name in feature_names]
        true_label = 1 if game.home_winner else 0
        pred_prob = model.predict_proba([row])[0]
        pred_label = 1 if pred_prob[1] >= 0.5 else 0

        y_true.append(true_label)
        y_pred.append(pred_label)
        y_prob.append(pred_prob[1])

    if not y_true:
        print("No evaluable games found (all skipped due to missing stats).")
        return

    print(f"  Evaluated {len(y_true)} games ({skipped} skipped)\n")

    # ── Overall accuracy ─────────────────────────────────────────────────
    accuracy = accuracy_score(y_true, y_pred)
    baseline = np.mean(y_true)  # home win rate
    print(f"  Model accuracy:         {accuracy:.4f}")
    print(f"  Baseline (always home): {baseline:.4f}")
    print(f"  Improvement over base:  {accuracy - baseline:+.4f}")

    # ── Classification report ────────────────────────────────────────────
    print(f"\n{classification_report(y_true, y_pred, target_names=['Away Win', 'Home Win'])}")

    # ── Confidence calibration ───────────────────────────────────────────
    # Group predictions by confidence bucket and show actual win rate
    print("  Confidence calibration:")
    print(f"  {'Bucket':>12s}  {'Count':>6s}  {'Predicted':>10s}  {'Actual':>8s}")
    print(f"  {'-'*12}  {'-'*6}  {'-'*10}  {'-'*8}")

    buckets = [(0.5, 0.6), (0.6, 0.7), (0.7, 0.8), (0.8, 0.9), (0.9, 1.01)]
    for lo, hi in buckets:
        mask = [(lo <= p < hi) for p in y_prob]
        if not any(mask):
            continue
        bucket_true = [y_true[i] for i, m in enumerate(mask) if m]
        bucket_prob = [y_prob[i] for i, m in enumerate(mask) if m]
        actual_rate = np.mean(bucket_true)
        avg_conf = np.mean(bucket_prob)
        print(f"  {lo:.1f}–{hi:.1f}       {sum(mask):>6d}  {avg_conf:>10.3f}  {actual_rate:>8.3f}")


if __name__ == '__main__':
    evaluate()
