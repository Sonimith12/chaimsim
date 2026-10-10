"""ReplenishmentPolicy ABC and implementations: OrderUpTo, sSPolicy, BaseStock, RQPolicy.

The :class:`ReplenishmentPolicy` ABC exposes ``.decide(state) ->
order_quantity`` and is designed to be easy for users to subclass with
their own ordering logic — ``decide`` is a pure function of a
:class:`NodeState` snapshot, so custom policies don't need to know
anything about the simulation engine.

Also exposes two classic inventory-theory formulas used to parameterize
policies from cost/service data: :func:`economic_order_quantity` (EOQ) and
the newsvendor critical ratio, via :meth:`BaseStockPolicy.from_costs`.
"""

from __future__ import annotations

import math
from abc import ABC, abstractmethod
from dataclasses import dataclass, field

import numpy as np


@dataclass
class NodeState:
    """Snapshot of a node's state, passed to a policy's ``decide`` each period.

    Attributes:
        period: Current simulation period.
        on_hand: Current on-hand inventory.
        backlog: Currently unmet demand/orders.
        pipeline: Quantity already on order but not yet received.
        inventory_position: ``on_hand + pipeline - backlog``.
        demand_history: Observed demand up to (not including) ``period``,
            available for policies that estimate their own parameters.
    """

    period: int
    on_hand: float
    backlog: float
    pipeline: float
    inventory_position: float
    demand_history: np.ndarray = field(default_factory=lambda: np.array([]))


class ReplenishmentPolicy(ABC):
    """Abstract base class for a replenishment/ordering policy."""

    @abstractmethod
    def decide(self, state: NodeState) -> float:
        """Return the order quantity to place this period, given ``state``."""
        raise NotImplementedError

    def reset(self) -> None:
        """Reset any internal policy state between simulation runs. No-op by default."""


class OrderUpTo(ReplenishmentPolicy):
    """Order-up-to-``S`` policy: order enough each period to bring inventory position to ``S``."""

    def __init__(self, S: float) -> None:
        self.S = S

    def decide(self, state: NodeState) -> float:
        return max(0.0, self.S - state.inventory_position)


class sSPolicy(ReplenishmentPolicy):
    """(s, S) policy: when inventory position falls to or below reorder point ``s``,
    order up to ``S``; otherwise order nothing.
    """

    def __init__(self, s: float, S: float) -> None:
        if s > S:
            raise ValueError("S must be >= s")
        self.s = s
        self.S = S

    def decide(self, state: NodeState) -> float:
        if state.inventory_position <= self.s:
            return max(0.0, self.S - state.inventory_position)
        return 0.0


class RQPolicy(ReplenishmentPolicy):
    """(R, Q) / continuous-review policy: when inventory position falls to or below
    reorder point ``R``, order a fixed quantity ``Q``; otherwise order nothing.
    """

    def __init__(self, R: float, Q: float) -> None:
        if Q <= 0:
            raise ValueError("Q must be positive")
        self.R = R
        self.Q = Q

    def decide(self, state: NodeState) -> float:
        return self.Q if state.inventory_position <= self.R else 0.0


class BaseStockPolicy(ReplenishmentPolicy):
    """Order-up-to policy whose level ``S`` is derived from demand statistics via the
    periodic-review newsvendor formula: ``S = mu*(L+1) + z*sigma*sqrt(L+1)``, where
    ``mu``/``sigma`` are per-period demand mean/std, ``L`` is the replenishment lead
    time (in periods), and ``z`` is the standard-normal quantile for the target
    cycle service level (or, via :meth:`from_costs`, the newsvendor critical ratio).

    Args:
        mean_demand: Mean demand per period.
        std_demand: Standard deviation of demand per period.
        lead_time: Replenishment lead time, in periods.
        service_level: Target cycle service level in (0, 1) — probability of
            not stocking out during a replenishment cycle. Mutually
            exclusive with ``z``.
        z: Standard-normal safety-factor to use directly instead of deriving
            it from ``service_level``.
    """

    def __init__(
        self,
        mean_demand: float,
        std_demand: float,
        lead_time: float,
        service_level: float | None = None,
        z: float | None = None,
    ) -> None:
        if (service_level is None) == (z is None):
            raise ValueError("pass exactly one of service_level or z")
        self.mean_demand = mean_demand
        self.std_demand = std_demand
        self.lead_time = lead_time
        self.z = z if z is not None else norm_ppf(service_level)  # type: ignore[arg-type]
        protection_periods = lead_time + 1
        self.S = mean_demand * protection_periods + self.z * std_demand * math.sqrt(
            protection_periods
        )

    @classmethod
    def from_costs(
        cls,
        mean_demand: float,
        std_demand: float,
        lead_time: float,
        holding_cost: float,
        backlog_cost: float,
    ) -> BaseStockPolicy:
        """Build a :class:`BaseStockPolicy` from the newsvendor critical ratio
        ``backlog_cost / (backlog_cost + holding_cost)`` instead of a stated
        service level directly.
        """
        if holding_cost < 0 or backlog_cost < 0:
            raise ValueError("costs must be non-negative")
        if holding_cost + backlog_cost <= 0:
            raise ValueError("holding_cost + backlog_cost must be positive")
        critical_ratio = backlog_cost / (backlog_cost + holding_cost)
        return cls(mean_demand, std_demand, lead_time, service_level=critical_ratio)

    def decide(self, state: NodeState) -> float:
        return max(0.0, self.S - state.inventory_position)


def economic_order_quantity(demand_rate: float, order_cost: float, holding_cost: float) -> float:
    """Classic EOQ formula: ``Q* = sqrt(2 * demand_rate * order_cost / holding_cost)``.

    Args:
        demand_rate: Demand per unit time (e.g. per period or per year —
            must match the time basis of ``holding_cost``).
        order_cost: Fixed cost incurred per order placed, independent of quantity.
        holding_cost: Cost to hold one unit for one unit of time.
    """
    if demand_rate < 0 or order_cost < 0 or holding_cost <= 0:
        raise ValueError("demand_rate, order_cost must be >= 0 and holding_cost > 0")
    return math.sqrt(2 * demand_rate * order_cost / holding_cost)


def norm_ppf(p: float) -> float:
    """Inverse CDF (quantile function) of the standard normal distribution.

    Implemented via Peter Acklam's rational approximation (no ``scipy``
    dependency), accurate to within about ``1.15e-9`` absolute error.
    """
    if not 0.0 < p < 1.0:
        raise ValueError("p must be in the open interval (0, 1)")

    a = [
        -3.969683028665376e01,
        2.209460984245205e02,
        -2.759285104469687e02,
        1.383577518672690e02,
        -3.066479806614716e01,
        2.506628277459239e00,
    ]
    b = [
        -5.447609879822406e01,
        1.615858368580409e02,
        -1.556989798598866e02,
        6.680131188771972e01,
        -1.328068155288572e01,
    ]
    c = [
        -7.784894002430293e-03,
        -3.223964580411365e-01,
        -2.400758277161838e00,
        -2.549732539343734e00,
        4.374664141464968e00,
        2.938163982698783e00,
    ]
    d = [
        7.784695709041462e-03,
        3.224671290700398e-01,
        2.445134137142996e00,
        3.754408661907416e00,
    ]
    p_low = 0.02425
    p_high = 1 - p_low

    if p < p_low:
        q = math.sqrt(-2 * math.log(p))
        return (((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]) / (
            (((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1
        )
    if p <= p_high:
        q = p - 0.5
        r = q * q
        return ((((((a[0] * r + a[1]) * r + a[2]) * r + a[3]) * r + a[4]) * r + a[5]) * q) / (
            ((((b[0] * r + b[1]) * r + b[2]) * r + b[3]) * r + b[4]) * r + 1
        )
    q = math.sqrt(-2 * math.log(1 - p))
    return -(((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]) / (
        (((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1
    )
