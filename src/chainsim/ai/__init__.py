"""AI/ML interface layer: Gymnasium environment, forecaster protocol, and baseline agents.

Layer 4. Wraps `chainsim.core` and `chainsim.metrics` in interfaces that
plug directly into RL and forecasting workflows.
"""

from chainsim.ai.baselines import Agent, OrderUpToAgent, RandomAgent, evaluate_agent
from chainsim.ai.forecaster import (
    ExponentialSmoothingForecaster,
    Forecaster,
    MovingAverageForecaster,
    NaiveForecaster,
    forecast_accuracy,
    mae,
    mape,
    rmse,
)
from chainsim.ai.gym_env import SupplyChainEnv

__all__ = [
    "Agent",
    "ExponentialSmoothingForecaster",
    "Forecaster",
    "MovingAverageForecaster",
    "NaiveForecaster",
    "OrderUpToAgent",
    "RandomAgent",
    "SupplyChainEnv",
    "evaluate_agent",
    "forecast_accuracy",
    "mae",
    "mape",
    "rmse",
]
