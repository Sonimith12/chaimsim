"""TransportLink: a transportation edge connecting two nodes (lead time, capacity, cost, mode).

Carries origin, destination, lead time (deterministic or stochastic
distribution), capacity, cost per unit, and transportation mode
(truck/rail/ship/air) as metadata. Edges point in the direction of
material flow (origin ships to destination); orders/replenishment
requests flow in the opposite direction and are handled by
:mod:`chainsim.core.engine`.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

import numpy as np

LeadTimeDistribution = Callable[[np.random.Generator], float]


def constant_lead_time(value: float) -> LeadTimeDistribution:
    """Return a lead-time distribution that always samples ``value``."""

    def _sample(_rng: np.random.Generator) -> float:
        return value

    return _sample


def poisson_lead_time(mean: float) -> LeadTimeDistribution:
    """Return a lead-time distribution sampling ``Poisson(mean)`` periods (min 1)."""

    def _sample(rng: np.random.Generator) -> float:
        return max(1.0, float(rng.poisson(mean)))

    return _sample


def uniform_lead_time(low: float, high: float) -> LeadTimeDistribution:
    """Return a lead-time distribution sampling uniformly in ``[low, high]``."""

    def _sample(rng: np.random.Generator) -> float:
        return float(rng.uniform(low, high))

    return _sample


@dataclass
class TransportLink:
    """A directed transportation edge from ``source`` to ``destination``.

    Attributes:
        source: Upstream node id.
        destination: Downstream node id.
        lead_time: Deterministic value or a distribution callable
            ``(rng) -> float`` sampled once per shipment.
        capacity: Maximum quantity shippable per period. ``None`` = unlimited.
        cost_per_unit: Transportation cost charged per unit shipped.
        mode: Free-form transportation mode label (e.g. ``"truck"``).
    """

    source: str
    destination: str
    lead_time: float | LeadTimeDistribution = 1.0
    capacity: float | None = None
    cost_per_unit: float = 0.0
    mode: str = "truck"

    base_capacity: float | None = field(default=None, init=False, repr=False)
    base_lead_time: float | LeadTimeDistribution = field(default=1.0, init=False, repr=False)

    def __post_init__(self) -> None:
        self.base_capacity = self.capacity
        self.base_lead_time = self.lead_time

    def clear_disruptions(self) -> None:
        """Restore capacity/lead time to baseline; called by the engine every period
        before applying that period's active disruptions.
        """
        self.capacity = self.base_capacity
        self.lead_time = self.base_lead_time

    def reset(self) -> None:
        """Reset any disruption-modified state back to configured values."""
        self.clear_disruptions()

    def sample_lead_time(self, rng: np.random.Generator) -> float:
        """Sample a lead time for one shipment on this link."""
        if callable(self.lead_time):
            return self.lead_time(rng)
        return float(self.lead_time)

    @property
    def id(self) -> str:
        return f"{self.source}->{self.destination}"
