"""Tests for chainsim.core.demand."""

import numpy as np
import pytest

from chainsim.core.demand import (
    CorrelatedSKUDemand,
    EmpiricalDemand,
    SeasonalDemand,
    StationaryDemand,
    TrendDemand,
)


def test_stationary_poisson_reproducible_with_seed():
    gen = StationaryDemand(mean=10, distribution="poisson")
    a = gen.generate(100, seed=7)
    b = gen.generate(100, seed=7)
    assert np.array_equal(a, b)
    assert len(a) == 100
    assert (a >= 0).all()


def test_stationary_poisson_mean_converges():
    gen = StationaryDemand(mean=20, distribution="poisson")
    sample = gen.generate(20000, seed=1)
    assert abs(sample.mean() - 20) < 0.5


def test_stationary_normal_clipped_at_zero():
    gen = StationaryDemand(mean=1, std=10, distribution="normal")
    sample = gen.generate(5000, seed=1)
    assert (sample >= 0).all()


def test_stationary_rejects_unknown_distribution():
    with pytest.raises(ValueError):
        StationaryDemand(mean=1, distribution="bogus")


def test_seasonal_oscillates_around_base():
    gen = SeasonalDemand(base=100, amplitude=20, period_length=12)
    sample = gen.generate(12, seed=0)
    assert abs(sample.mean() - 100) < 5
    assert sample.max() > sample.min()


def test_trend_demand_increases_over_time():
    gen = TrendDemand(base=10, trend_per_period=2, noise_std=0.0)
    sample = gen.generate(10, seed=0)
    assert np.array_equal(sample, 10 + 2 * np.arange(10))


def test_correlated_sku_demand_shape_and_correlation():
    mean = np.array([50.0, 50.0])
    cov = np.array([[100.0, 90.0], [90.0, 100.0]])
    gen = CorrelatedSKUDemand(skus=["a", "b"], mean=mean, cov=cov)
    sample = gen.generate(5000, seed=0)
    assert sample.shape == (5000, 2)
    corr = np.corrcoef(sample[:, 0], sample[:, 1])[0, 1]
    assert corr > 0.7  # strongly positively correlated as configured


def test_correlated_sku_demand_rejects_mismatched_shapes():
    with pytest.raises(ValueError):
        CorrelatedSKUDemand(skus=["a", "b"], mean=np.array([1.0]), cov=np.eye(2))


def test_empirical_demand_replays_in_order():
    gen = EmpiricalDemand([1, 2, 3])
    sample = gen.generate(7)
    assert list(sample) == [1, 2, 3, 1, 2, 3, 1]


def test_empirical_demand_shuffle_draws_from_data():
    gen = EmpiricalDemand([5, 6, 7], shuffle=True)
    sample = gen.generate(100, seed=0)
    assert set(sample.tolist()).issubset({5, 6, 7})


def test_empirical_demand_rejects_empty_data():
    with pytest.raises(ValueError):
        EmpiricalDemand([])
