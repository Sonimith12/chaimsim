"""Forecaster protocol/ABC (fit, predict) with simple baseline implementations.

To be implemented in Phase 3. The `Forecaster` Protocol/ABC exposes
`.fit(history)` and `.predict(horizon) -> np.ndarray`. Ships two trivial
baselines (moving average, exponential smoothing) with no hard dependency
on external ML libraries. Wrapping Prophet, LightGBM, or a foundation
model (Chronos/TimesFM-style) behind this interface is documented as an
example, not a hard dependency.
"""
