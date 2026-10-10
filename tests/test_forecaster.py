"""Tests for chainsim.ai.forecaster."""

import numpy as np
import pytest

from chainsim.ai.forecaster import (
    ExponentialSmoothingForecaster,
    MovingAverageForecaster,
    NaiveForecaster,
    forecast_accuracy,
    mae,
    mape,
    rmse,
)


def test_naive_forecaster_repeats_last_value():
    f = NaiveForecaster()
    f.fit(np.array([10, 20, 30, 15]))
    assert np.array_equal(f.predict(4), np.full(4, 15.0))


def test_naive_forecaster_requires_fit():
    with pytest.raises(RuntimeError):
        NaiveForecaster().predict(3)


def test_moving_average_uses_trailing_window():
    f = MovingAverageForecaster(window=3)
    f.fit(np.array([10, 20, 30, 40, 50]))
    assert np.array_equal(f.predict(2), np.full(2, np.mean([30, 40, 50])))


def test_moving_average_uses_all_history_if_shorter_than_window():
    f = MovingAverageForecaster(window=10)
    f.fit(np.array([10, 20]))
    assert f.predict(1)[0] == pytest.approx(15.0)


def test_moving_average_rejects_nonpositive_window():
    with pytest.raises(ValueError):
        MovingAverageForecaster(window=0)


def test_exponential_smoothing_matches_hand_computed_level():
    history = np.array([10.0, 20.0, 30.0])
    alpha = 0.5
    level = 10.0
    for v in history[1:]:
        level = alpha * v + (1 - alpha) * level
    f = ExponentialSmoothingForecaster(alpha=alpha)
    f.fit(history)
    assert f.predict(3)[0] == pytest.approx(level)


def test_exponential_smoothing_rejects_bad_alpha():
    with pytest.raises(ValueError):
        ExponentialSmoothingForecaster(alpha=0.0)
    with pytest.raises(ValueError):
        ExponentialSmoothingForecaster(alpha=1.5)


def test_all_forecasters_reject_empty_history():
    for f in (NaiveForecaster(), MovingAverageForecaster(), ExponentialSmoothingForecaster()):
        with pytest.raises(ValueError):
            f.fit(np.array([]))


# -- accuracy metrics -----------------------------------------------------


def test_mae_zero_for_perfect_forecast():
    actual = np.array([1, 2, 3])
    assert mae(actual, actual) == 0.0


def test_mae_known_value():
    assert mae(np.array([10, 20]), np.array([12, 18])) == pytest.approx(2.0)


def test_rmse_known_value():
    assert rmse(np.array([0, 0]), np.array([3, 4])) == pytest.approx(np.sqrt((9 + 16) / 2))


def test_mape_known_value():
    assert mape(np.array([100, 200]), np.array([110, 180])) == pytest.approx(
        (0.10 + 0.10) / 2 * 100
    )


def test_mape_ignores_zero_actuals():
    assert mape(np.array([0, 100]), np.array([5, 90])) == pytest.approx(10.0)


def test_forecast_accuracy_bundle_has_all_metrics():
    result = forecast_accuracy(np.array([10, 20]), np.array([11, 19]))
    assert set(result) == {"mae", "rmse", "mape"}
