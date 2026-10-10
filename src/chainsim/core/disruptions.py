"""DisruptionEvent ABC and implementations: outages, capacity reduction, lead-time/demand shocks.

The :class:`DisruptionEvent` ABC exposes ``applies_at(t) -> bool`` and
``apply(target)``. Implementations: :class:`NodeOutage`,
:class:`CapacityReduction`, :class:`LeadTimeShock`, :class:`DemandShock`.
Events are schedulable at specific times (``start``/``duration``) or
triggered probabilistically each period.

Each period, :class:`~chainsim.core.engine.SimulationEngine` first resets
every node/edge to its baseline configuration, then calls ``apply`` for
every event whose ``applies_at(t)`` is true — so effects only last for the
event's active window and never compound across periods.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

import numpy as np

from chainsim.core.edges import TransportLink
from chainsim.core.nodes import Node

Target = Node | TransportLink


class DisruptionEvent(ABC):
    """Abstract base class for a disruption applied to a node or edge during a time window."""

    def __init__(self, target_id: str, start: int, duration: int = 1) -> None:
        if duration <= 0:
            raise ValueError("duration must be positive")
        self.target_id = target_id
        self.start = start
        self.duration = duration

    @property
    def end(self) -> int:
        """First period at which the event is no longer active (exclusive)."""
        return self.start + self.duration

    def applies_at(self, t: int) -> bool:
        """Whether this event is active during period ``t``."""
        return self.start <= t < self.end

    @abstractmethod
    def apply(self, target: Any) -> None:
        """Mutate ``target``'s current-period effective attributes."""
        raise NotImplementedError


class NodeOutage(DisruptionEvent):
    """Takes a node fully offline: zero shipping/production capacity for the duration."""

    def apply(self, target: Node) -> None:
        target.active = False
        target.capacity = 0.0


class CapacityReduction(DisruptionEvent):
    """Scales a node's or edge's capacity by ``factor`` (e.g. 0.5 = halved) for the duration.

    Applies to nodes with finite capacity or edges; a target with unlimited
    (``None``/``inf``) base capacity is left unaffected since there is
    nothing to scale.
    """

    def __init__(self, target_id: str, start: int, duration: int, factor: float) -> None:
        super().__init__(target_id, start, duration)
        if not 0.0 <= factor <= 1.0:
            raise ValueError("factor must be in [0, 1]")
        self.factor = factor

    def apply(self, target: Node | TransportLink) -> None:
        base = target.base_capacity
        if base is None or base == float("inf"):
            return
        target.capacity = base * self.factor


class LeadTimeShock(DisruptionEvent):
    """Inflates a :class:`~chainsim.core.edges.TransportLink`'s lead time by ``multiplier``
    for the duration (e.g. a port closure slowing transit).
    """

    def __init__(self, target_id: str, start: int, duration: int, multiplier: float) -> None:
        super().__init__(target_id, start, duration)
        if multiplier < 0:
            raise ValueError("multiplier must be non-negative")
        self.multiplier = multiplier

    def apply(self, target: TransportLink) -> None:
        # Always derive from base_lead_time (not the possibly-already-shocked
        # current value) so repeated calls across periods don't compound.
        base_lead_time = target.base_lead_time
        multiplier = self.multiplier

        if callable(base_lead_time):
            base_sampler = base_lead_time

            def _shocked(rng: np.random.Generator, _base=base_sampler, _mult=multiplier) -> float:
                return _base(rng) * _mult

            target.lead_time = _shocked
        else:
            target.lead_time = base_lead_time * multiplier


class DemandShock(DisruptionEvent):
    """Scales the external demand a node observes by ``multiplier`` for the duration
    (e.g. a panic-buying spike or a demand collapse). Applied by the engine directly
    to the sampled demand value rather than to the node/generator itself.
    """

    def __init__(self, target_id: str, start: int, duration: int, multiplier: float) -> None:
        super().__init__(target_id, start, duration)
        if multiplier < 0:
            raise ValueError("multiplier must be non-negative")
        self.multiplier = multiplier

    def apply(self, target: float) -> float:
        """Given a baseline demand value, return the shocked value."""
        return target * self.multiplier
