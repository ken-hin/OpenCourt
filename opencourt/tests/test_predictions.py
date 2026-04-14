# test_predictions.py — Unit tests for the opencourt/predictions/ module.
#
# Tests the ML prediction pipeline: feature engineering, model loading,
# and the predict function. The actual XGBoost model file is NOT used
# in tests — all model interactions are mocked to keep tests fast and
# environment-independent.
#
# Key areas tested:
#   - build_features(): Correct differential computation from TeamSeasonStats
#   - build_features(): Handling of None/zero fields (ZeroDivisionError risk)
#   - make_predictions(): Integration of features + model + error handling
#   - load_model(): Singleton caching and cache invalidation
#
# Run just these tests:
#   uv run python manage.py test opencourt.tests.test_predictions

from unittest.mock import patch, MagicMock, mock_open
from django.test import TestCase
import numpy as np
import pandas as pd

# =============================================================================
# Mock TeamSeasonStats
# =============================================================================
# We use a simple namespace class instead of real ORM objects so we don't
# need database setup. build_features() only reads attributes — it doesn't
# call any ORM methods.

class MockStats:
    """
    Lightweight stand-in for a TeamSeasonStats object.

    Accepts keyword arguments and sets them as attributes, mimicking the
    ORM model's attribute access pattern (e.g. stats.off_eff_fg_pct).
    """
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)

def _make_mock_stats(**overrides):
    """
    Create a MockStats instance with realistic default values.

    Defaults represent a competitive D1 team. Override any field by
    passing keyword arguments.
    """
    defaults = {
        'off_eff_fg_pct': 0.52,
        'off_turnovers': 350.0,
        'off_possessions': 2000.0,
        'off_points': 2400.0,
        'opp_points': 2100.0,
        'pace': 68.5,
        'off_ft_rate': 0.35,
        'off_rating': 112.5,
        'off_blocks': 120.0,
        'off_oreb_pct': 0.32,
        'off_assists': 450.0,
    }
    defaults.update(overrides)
    return MockStats(**defaults)

# =============================================================================
# build_features() Tests
# =============================================================================

class BuildFeaturesTest(TestCase):
    """
    Tests for predictions.features.build_features().

    build_features() takes two team stats objects and a home_advantage
    flag, computes 10 differential features, and returns a pandas
    DataFrame ready for model input.
    """

    def test_returns_dataframe(self):
        """build_features() should return a pandas DataFrame."""
        from opencourt.predictions.features import build_features

        team_a = _make_mock_stats()
        team_b = _make_mock_stats()
        result = build_features(team_a, team_b, home_advantage=1)
        self.assertIsInstance(result, pd.DataFrame)

    def test_dataframe_has_10_columns(self):
        """
        The returned DataFrame should have exactly 10 feature columns:
        the 9 stat differentials + home_advantage.
        """
        from opencourt.predictions.features import build_features

        team_a = _make_mock_stats()
        team_b = _make_mock_stats()
        result = build_features(team_a, team_b, home_advantage=1)
        self.assertEqual(len(result.columns), 10)

    def test_dataframe_has_one_row(self):
        """The DataFrame should contain exactly one row (one matchup)."""
        from opencourt.predictions.features import build_features

        team_a = _make_mock_stats()
        team_b = _make_mock_stats()
        result = build_features(team_a, team_b, home_advantage=0)
        self.assertEqual(len(result), 1)

    def test_identical_teams_produce_zero_differentials(self):
        """
        When both teams have identical stats, all differential features
        should be 0.0 (except home_advantage which is passed through).
        """
        from opencourt.predictions.features import build_features

        team_a = _make_mock_stats()
        team_b = _make_mock_stats()  # same defaults as team_a
        result = build_features(team_a, team_b, home_advantage=0)

        for col in result.columns:
            self.assertAlmostEqual(
                result[col].iloc[0], 0.0, places=5,
                msg=f"Feature '{col}' should be 0 for identical teams"
            )

    def test_efg_pct_differential(self):
        """
        diff_efg_pct should be team_a.off_eff_fg_pct - team_b.off_eff_fg_pct.
        """
        from opencourt.predictions.features import build_features

        team_a = _make_mock_stats(off_eff_fg_pct=0.55)
        team_b = _make_mock_stats(off_eff_fg_pct=0.50)
        result = build_features(team_a, team_b, home_advantage=0)
        self.assertAlmostEqual(result['diff_efg_pct'].iloc[0], 0.05, places=5)

    def test_home_advantage_passthrough(self):
        """
        home_advantage should be passed through directly to the DataFrame:
        1 (team_a home), -1 (team_b home), or 0 (neutral site).
        """
        from opencourt.predictions.features import build_features

        team_a = _make_mock_stats()
        team_b = _make_mock_stats()

        for adv in [1, -1, 0]:
            result = build_features(team_a, team_b, home_advantage=adv)
            self.assertEqual(
                result['home_advantage'].iloc[0], adv,
                msg=f"home_advantage should be {adv}"
            )

    def test_rating_differential(self):
        """
        diff_avg_rating should be team_a.off_rating - team_b.off_rating.
        """
        from opencourt.predictions.features import build_features

        team_a = _make_mock_stats(off_rating=115.0)
        team_b = _make_mock_stats(off_rating=100.0)
        result = build_features(team_a, team_b, home_advantage=0)
        self.assertAlmostEqual(result['diff_avg_rating'].iloc[0], 15.0, places=5)

    def test_pace_differential(self):
        """diff_pace should be team_a.pace - team_b.pace."""
        from opencourt.predictions.features import build_features

        team_a = _make_mock_stats(pace=72.0)
        team_b = _make_mock_stats(pace=65.0)
        result = build_features(team_a, team_b, home_advantage=0)
        self.assertAlmostEqual(result['diff_pace'].iloc[0], 7.0, places=5)

    def test_zero_possessions_raises_error(self):
        """
        If off_possessions is 0, the turnover rate calculation divides by
        zero. This documents the current behavior (ZeroDivisionError).

        NOTE: This is a known bug identified in the testing audit. Once
        build_features() is patched to handle this case, update this test
        to verify the fix (e.g. returns None or uses a default value).
        """
        from opencourt.predictions.features import build_features

        team_a = _make_mock_stats(off_possessions=0.0)
        team_b = _make_mock_stats()

        with self.assertRaises(ZeroDivisionError):
            build_features(team_a, team_b, home_advantage=0)

    def test_zero_turnovers_raises_error(self):
        """
        If off_turnovers is 0, the assist-to-turnover ratio calculation
        divides by zero. This documents the current behavior.

        NOTE: Known bug — see zero_possessions test above.
        """
        from opencourt.predictions.features import build_features

        team_a = _make_mock_stats(off_turnovers=0.0)
        team_b = _make_mock_stats()

        with self.assertRaises(ZeroDivisionError):
            build_features(team_a, team_b, home_advantage=0)

    def test_none_field_raises_type_error(self):
        """
        If a stat field is None, arithmetic operations will raise TypeError.
        This documents the current behavior.

        NOTE: Known bug — the view wraps calls in try/except, but the
        function itself should handle None gracefully.
        """
        from opencourt.predictions.features import build_features

        team_a = _make_mock_stats(off_eff_fg_pct=None)
        team_b = _make_mock_stats()

        with self.assertRaises(TypeError):
            build_features(team_a, team_b, home_advantage=0)

# =============================================================================
# make_predictions() Tests
# =============================================================================

class MakePredictionsTest(TestCase):
    """
    Tests for predictions.predict.make_predictions().

    make_predictions() loads the model, builds features, and returns
    the model's prediction. The model file is mocked in all tests.
    """

    @patch('opencourt.predictions.predict.build_features')
    @patch('builtins.open', new_callable=mock_open, read_data=b'')
    @patch('opencourt.predictions.predict.pickle.load')
    def test_successful_prediction(self, mock_pickle, mock_file, mock_build):
        """
        When the model file exists and features build successfully,
        make_predictions should return the model's prediction array.
        """
        from opencourt.predictions.predict import make_predictions

        # Mock the model to return a numpy array prediction
        mock_model = MagicMock()
        mock_model.predict.return_value = np.array([1])
        mock_pickle.return_value = mock_model

        # Mock build_features to return a valid DataFrame
        mock_build.return_value = pd.DataFrame({'feature': [1.0]})

        team_a = _make_mock_stats()
        team_b = _make_mock_stats()
        result = make_predictions(team_a, team_b, 1)

        self.assertIsInstance(result, np.ndarray)
        self.assertEqual(result[0], 1)

    def test_file_not_found_returns_int(self):
        """
        When the model file doesn't exist, make_predictions returns 1 (int).

        NOTE: This is a code smell identified in the audit — returning a
        bare int makes it hard for callers to distinguish success from
        failure. The view checks `type(pred) is np.ndarray` which is fragile.
        """
        from opencourt.predictions.predict import make_predictions

        team_a = _make_mock_stats()
        team_b = _make_mock_stats()
        # Use a path that definitely doesn't exist
        result = make_predictions(team_a, team_b, 1, model_path='/nonexistent/model')
        self.assertEqual(result, 1)
        self.assertIsInstance(result, int)

# =============================================================================
# load_model() Tests
# =============================================================================

class LoadModelTest(TestCase):
    """
    Tests for predictions.model.load_model() and clear_cache().

    load_model() uses a singleton pattern — the model is loaded once
    from disk and cached in a module-level variable. clear_cache()
    resets the cache.
    """

    def tearDown(self):
        """
        Always clear the model cache after each test to prevent
        cross-test contamination from the singleton.
        """
        from opencourt.predictions.model import clear_cache
        clear_cache()

    @patch('opencourt.predictions.model.joblib.load')
    @patch('opencourt.predictions.model.Path.exists', return_value=True)
    def test_model_loaded_once_then_cached(self, mock_exists, mock_load):
        """
        Calling load_model() twice should only trigger one disk read.
        The second call should return the cached object.
        """
        from opencourt.predictions.model import load_model, clear_cache

        clear_cache()  # ensure clean state
        mock_load.return_value = MagicMock(name='FakeModel')

        model1 = load_model(path='/fake/model.pkl')
        model2 = load_model(path='/fake/model.pkl')

        mock_load.assert_called_once()
        self.assertIs(model1, model2)

    @patch('opencourt.predictions.model.joblib.load')
    @patch('opencourt.predictions.model.Path.exists', return_value=True)
    def test_clear_cache_forces_reload(self, mock_exists, mock_load):
        """
        After clear_cache(), the next load_model() call should read from
        disk again (useful after retraining the model).
        """
        from opencourt.predictions.model import load_model, clear_cache

        clear_cache()
        mock_load.return_value = MagicMock(name='FakeModel')

        load_model(path='/fake/model.pkl')
        self.assertEqual(mock_load.call_count, 1)

        clear_cache()
        load_model(path='/fake/model.pkl')
        self.assertEqual(mock_load.call_count, 2)

    def test_file_not_found_raises_error(self):
        """
        load_model() should raise FileNotFoundError with a helpful message
        when the model file doesn't exist at the given path.
        """
        from opencourt.predictions.model import load_model, clear_cache

        clear_cache()
        with self.assertRaises(FileNotFoundError):
            load_model(path='/definitely/not/a/real/path.pkl')
