# model.py — Load and cache the trained prediction model.
#
# Uses a singleton pattern so the model is loaded from disk once on
# first use and reused for all subsequent predictions within the same
# Django process. This avoids the overhead of reading the .pkl file
# on every request.
#
# The model file path defaults to predictions/trained_model.pkl
# (relative to this file), but can be overridden via the
# PREDICTION_MODEL_PATH Django setting.

import os
import joblib
from pathlib import Path

# Default location: predictions/trained_model.pkl (next to this file)
DEFAULT_MODEL_PATH = Path(__file__).resolve().parent / 'trained_model.pkl'

# Module-level cache — populated on first call to load_model()
_model = None


def load_model(path=None):
    """
    Load the trained model from disk and cache it in memory.

    Args:
        path: Optional path to the model file. Defaults to
              settings.PREDICTION_MODEL_PATH if defined, otherwise
              predictions/trained_model.pkl.

    Returns:
        The deserialized sklearn model (or pipeline) object.

    Raises:
        FileNotFoundError: If the model file doesn't exist.
    """
    global _model

    if _model is not None:
        return _model

    if path is None:
      # Check Django settings for a custom path (NEED TO ADD IN SETTINGS.PY)
        try:
            from django.conf import settings
            path = getattr(settings, 'PREDICTION_MODEL_PATH', None)
        except Exception:
            pass

    if path is None:
        path = DEFAULT_MODEL_PATH

    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(
            f"Trained model not found at {path}. "
            f"Run train_model.py first to generate the model file."
        )

    _model = joblib.load(path)
    return _model


def clear_cache():
    """
    Clear the cached model so the next load_model() call reads from disk.
    Useful after retraining the model without restarting the server.
    """
    global _model
    _model = None
