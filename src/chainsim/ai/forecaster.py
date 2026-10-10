"""Forecaster protocol/ABC (fit, predict) with simple baseline implementations.

The `Forecaster` ABC exposes `.fit(history)` and `.predict(horizon) ->
np.ndarray`. Ships three trivial baselines with no hard dependency on
external ML libraries: `NaiveForecaster` (repeats the last observation),
`MovingAverageForecaster`, and `ExponentialSmoothingForecaster`. Wrapping
Prophet, LightGBM, or a foundation model (Chronos/TimesFM-style) behind
this interface is a natural extension, not a hard dependency — subclass
`Forecaster` and implement `fit`/`predict`.

Also provides basic forecast-accuracy metrics (`mae`, `rmse`, `mape`) and
`forecast_accuracy`, used by `examples/04_forecast_benchmark.ipynb`.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

import numpy as np


class Forecaster(ABC):
    """Abstract base class for a demand forecaster."""

    @abstractmethod
    def fit(self, history: np.ndarray) -> None:
        """Fit the forecaster on a 1-D array of historical demand observations."""
        raise NotImplementedError

    @abstractmethod
    def predict(self, horizon: int) -> np.ndarray:
        """Return a length-``horizon`` array of point forecasts. Requires ``fit`` first."""
        raise NotImplementedError


class NaiveForecaster(Forecaster):
    """Repeats the last observed value for the whole horizon — the simplest
    possible baseline; any useful forecaster should beat this.
    """

    def __init__(self) -> None:
        self._last: float | None = None

    def fit(self, history: np.ndarray) -> None:
        history = np.asarray(history, dtype=float)
        if history.size == 0:
            raise ValueError("history must be non-empty")
        self._last = float(history[-1])

    def predict(self, horizon: int) -> np.ndarray:
        if self._last is None:
            raise RuntimeError("call fit() before predict()")
        return np.full(horizon, self._last)


class MovingAverageForecaster(Forecaster):
    """Forecasts the mean of the last ``window`` observations, held flat over the horizon.

    Args:
        window: Number of trailing periods to average. If ``history`` is
            shorter than ``window`` at fit time, all of it is used.
    """

    def __init__(self, window: int = 7) -> None:
        if window <= 0:
            raise ValueError("window must be positive")
        self.window = window
        self._level: float | None = None

    def fit(self, history: np.ndarray) -> None:
        history = np.asarray(history, dtype=float)
        if history.size == 0:
            raise ValueError("history must be non-empty")
        self._level = float(history[-self.window :].mean())

    def predict(self, horizon: int) -> np.ndarray:
        if self._level is None:
            raise RuntimeError("call fit() before predict()")
        return np.full(horizon, self._level)


class ExponentialSmoothingForecaster(Forecaster):
    """Simple (single) exponential smoothing: ``level_t = alpha*x_t + (1-alpha)*level_{t-1}``,
    held flat over the forecast horizon.

    Args:
        alpha: Smoothing constant in (0, 1]; higher weights recent
            observations more heavily.
    """

    def __init__(self, alpha: float = 0.3) -> None:
        if not 0.0 < alpha <= 1.0:
            raise ValueError("alpha must be in (0, 1]")
        self.alpha = alpha
        self._level: float | None = None

    def fit(self, history: np.ndarray) -> None:
        history = np.asarray(history, dtype=float)
        if history.size == 0:
            raise ValueError("history must be non-empty")
        level = float(history[0])
        for value in history[1:]:
            level = self.alpha * float(value) + (1 - self.alpha) * level
        self._level = level

    def predict(self, horizon: int) -> np.ndarray:
        if self._level is None:
            raise RuntimeError("call fit() before predict()")
        return np.full(horizon, self._level)


def mae(actual: np.ndarray, predicted: np.ndarray) -> float:
    """Mean absolute error."""
    actual, predicted = np.asarray(actual, dtype=float), np.asarray(predicted, dtype=float)
    return float(np.mean(np.abs(actual - predicted)))


def rmse(actual: np.ndarray, predicted: np.ndarray) -> float:
    """Root mean squared error."""
    actual, predicted = np.asarray(actual, dtype=float), np.asarray(predicted, dtype=float)
    return float(np.sqrt(np.mean((actual - predicted) ** 2)))


def mape(actual: np.ndarray, predicted: np.ndarray) -> float:
    """Mean absolute percentage error (%). Periods with zero actual demand are
    excluded (undefined percentage error) rather than producing ``inf``/``nan``.
    """
    actual, predicted = np.asarray(actual, dtype=float), np.asarray(predicted, dtype=float)
    mask = actual != 0
    if not mask.any():
        return float("nan")
    return float(np.mean(np.abs((actual[mask] - predicted[mask]) / actual[mask])) * 100)


def forecast_accuracy(actual: np.ndarray, predicted: np.ndarray) -> dict[str, float]:
    """Bundle of forecast-accuracy metrics for one forecaster's predictions."""
    return {
        "mae": mae(actual, predicted),
        "rmse": rmse(actual, predicted),
        "mape": mape(actual, predicted),
    }
