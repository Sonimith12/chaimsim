"""DemandGenerator ABC and implementations: stationary, seasonal, trend, correlated-SKU, empirical.

To be implemented in Phase 1. The `DemandGenerator` ABC exposes
`.generate(n_periods, seed) -> np.ndarray`. Implementations: StationaryDemand
(Poisson/Normal), SeasonalDemand, TrendDemand, CorrelatedSKUDemand (multi-
product), and EmpiricalDemand (loads from CSV, e.g. M5 or WSTS-style data).
"""
