"""Pydantic models for the REST bodies and WebSocket messages exchanged with the frontend."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class LoadScenarioRequest(BaseModel):
    name: str


class CustomPolicy(BaseModel):
    type: Literal["order_up_to", "s_S", "r_q", "base_stock"] = "base_stock"
    params: dict[str, float] = Field(default_factory=dict)


class CustomDemand(BaseModel):
    type: Literal["stationary", "seasonal", "trend"] = "stationary"
    mean: float = 50.0
    std: float = 5.0
    # seasonal
    amplitude: float = 15.0
    period_length: int = 13
    # trend
    trend_per_period: float = 0.5


class CustomScenarioRequest(BaseModel):
    echelons: int = Field(3, ge=2, le=6)
    n_periods: int = Field(52, ge=1, le=520)
    lead_time: float = Field(2.0, gt=0)
    seed: int | None = 0
    demand: CustomDemand = Field(default_factory=CustomDemand)
    policy: CustomPolicy = Field(default_factory=CustomPolicy)


# --- WebSocket client -> server -------------------------------------------------


class StepCommand(BaseModel):
    type: Literal["step"]


class ResetCommand(BaseModel):
    type: Literal["reset"]


class PolicyChangeCommand(BaseModel):
    type: Literal["policy_change"]
    node_id: str
    policy_type: Literal["order_up_to", "s_S", "r_q", "base_stock"]
    params: dict[str, float] = Field(default_factory=dict)


# --- WebSocket server -> client -------------------------------------------------


class StateMessage(BaseModel):
    type: Literal["state"] = "state"
    state: dict[str, Any]
    # Set on the reply to a policy change so the client can confirm it applied.
    event: Literal["policy_changed"] | None = None
    node_id: str | None = None


class ErrorMessage(BaseModel):
    type: Literal["error"] = "error"
    message: str
