"""DemandGenerator ABC and implementations: stationary, seasonal, trend, correlated-SKU, empirical.

The :class:`DemandGenerator` ABC exposes ``.generate(n_periods, seed) ->
np.ndarray``. Implementations: :class:`StationaryDemand` (Poisson/Normal),
:class:`SeasonalDemand`, :class:`TrendDemand`, :class:`CorrelatedSKUDemand`
(multi-product), and :class:`EmpiricalDemand` (loads from a CSV or an
in-memory series, e.g. M5- or WSTS-style data).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

import numpy as np


class DemandGenerator(ABC):
    """Abstract base class for a demand process faced by a customer-facing node."""

    @abstractmethod
    def generate(self, n_periods: int, seed: int | None = None) -> np.ndarray:
        """Generate a length-``n_periods`` array of non-negative demand quantities."""
        raise NotImplementedError


class StationaryDemand(DemandGenerator):
    """IID demand each period, drawn from a Poisson or Normal distribution.

    Args:
        mean: Mean demand per period.
        std: Standard deviation, only used for ``distribution="normal"``.
        distribution: ``"poisson"`` (default) or ``"normal"``. Normal draws
            are clipped at zero.
    """

    def __init__(self, mean: float, std: float = 0.0, distribution: str = "poisson") -> None:
        if distribution not in ("poisson", "normal"):
            raise ValueError(f"unknown distribution: {distribution!r}")
        self.mean = mean
        self.std = std
        self.distribution = distribution

    def generate(self, n_periods: int, seed: int | None = None) -> np.ndarray:
        rng = np.random.default_rng(seed)
        if self.distribution == "poisson":
            return rng.poisson(self.mean, size=n_periods).astype(float)
        draws = rng.normal(self.mean, self.std, size=n_periods)
        return np.clip(draws, 0.0, None)


class SeasonalDemand(DemandGenerator):
    """Sinusoidal seasonal pattern around a base level, with optional Gaussian noise.

    ``demand[t] = base + amplitude * sin(2*pi*t / period_length) + noise``,
    clipped at zero.
    """

    def __init__(
        self,
        base: float,
        amplitude: float,
        period_length: int,
        noise_std: float = 0.0,
    ) -> None:
        self.base = base
        self.amplitude = amplitude
        self.period_length = period_length
        self.noise_std = noise_std

    def generate(self, n_periods: int, seed: int | None = None) -> np.ndarray:
        rng = np.random.default_rng(seed)
        t = np.arange(n_periods)
        seasonal = self.base + self.amplitude * np.sin(2 * np.pi * t / self.period_length)
        noise = rng.normal(0.0, self.noise_std, size=n_periods) if self.noise_std else 0.0
        return np.clip(seasonal + noise, 0.0, None)


class TrendDemand(DemandGenerator):
    """Linearly trending demand: ``base + trend_per_period * t + noise``, clipped at zero."""

    def __init__(self, base: float, trend_per_period: float, noise_std: float = 0.0) -> None:
        self.base = base
        self.trend_per_period = trend_per_period
        self.noise_std = noise_std

    def generate(self, n_periods: int, seed: int | None = None) -> np.ndarray:
        rng = np.random.default_rng(seed)
        t = np.arange(n_periods)
        trend = self.base + self.trend_per_period * t
        noise = rng.normal(0.0, self.noise_std, size=n_periods) if self.noise_std else 0.0
        return np.clip(trend + noise, 0.0, None)


class CorrelatedSKUDemand:
    """Multivariate-normal-correlated demand across multiple SKUs, clipped at zero.

    Not a :class:`DemandGenerator` itself (that interface is single-series);
    use :meth:`generate` to get a ``(n_periods, len(skus))`` array, or
    :meth:`series_for` to wrap one SKU's column as a plain
    :class:`DemandGenerator`-compatible callable.
    """

    def __init__(self, skus: list[str], mean: np.ndarray, cov: np.ndarray) -> None:
        mean = np.asarray(mean, dtype=float)
        cov = np.asarray(cov, dtype=float)
        if mean.shape != (len(skus),):
            raise ValueError("mean must have shape (len(skus),)")
        if cov.shape != (len(skus), len(skus)):
            raise ValueError("cov must have shape (len(skus), len(skus))")
        self.skus = list(skus)
        self.mean = mean
        self.cov = cov

    def generate(self, n_periods: int, seed: int | None = None) -> np.ndarray:
        rng = np.random.default_rng(seed)
        draws = rng.multivariate_normal(self.mean, self.cov, size=n_periods)
        return np.clip(draws, 0.0, None)


class EmpiricalDemand(DemandGenerator):
    """Replays a historical demand series, looping if ``n_periods`` exceeds its length.

    Args:
        data: A 1-D array/sequence of historical demand values, or a path
            to a single-column CSV file of demand values.
        shuffle: If True, bootstraps by sampling with replacement from
            ``data`` instead of replaying it in order.
    """

    def __init__(self, data: np.ndarray | list[float] | str | Path, shuffle: bool = False) -> None:
        if isinstance(data, (str, Path)):
            data = np.loadtxt(data, delimiter=",")
        self.data = np.asarray(data, dtype=float).ravel()
        if self.data.size == 0:
            raise ValueError("empirical demand data must be non-empty")
        self.shuffle = shuffle

    def generate(self, n_periods: int, seed: int | None = None) -> np.ndarray:
        rng = np.random.default_rng(seed)
        if self.shuffle:
            return rng.choice(self.data, size=n_periods, replace=True)
        reps = int(np.ceil(n_periods / self.data.size))
        return np.tile(self.data, reps)[:n_periods]
