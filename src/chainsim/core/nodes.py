"""Node base class and concrete node types: Supplier, Manufacturer, DistributionCenter, Retailer.

The abstract :class:`Node` base class defines identity (``id``, ``name``),
per-SKU inventory state, capacity, cost coefficients, and an optional
``lead_time_distribution`` used when the node replenishes from *outside*
the modeled network (i.e. it has no upstream predecessor in the
:class:`~chainsim.core.network.SupplyChainNetwork`).

Subclasses add role-specific defaults: :class:`Supplier` (near-infinite
upstream capacity), :class:`Manufacturer` (production capacity + a simple
bill-of-materials), :class:`DistributionCenter`, and :class:`Retailer`
(faces external customer demand).

State (on-hand inventory, backlog, pipeline) is mutable and owned by the
node instance; :class:`~chainsim.core.engine.SimulationEngine` drives it
period by period. Perishable nodes (``shelf_life`` set) delegate to a
:class:`~chainsim.core.perishability.PerishableInventory` per SKU instead
of tracking a bare float.
"""

from __future__ import annotations

from abc import ABC
from collections.abc import Callable
from dataclasses import dataclass, field

import numpy as np

from chainsim.core.perishability import PerishableInventory

LeadTimeDistribution = Callable[[np.random.Generator], float]

DEFAULT_SKU = "default"


def constant_lead_time(value: float) -> LeadTimeDistribution:
    """Return a lead-time distribution that always samples ``value``."""

    def _sample(_rng: np.random.Generator) -> float:
        return value

    return _sample


@dataclass
class Node(ABC):
    """Abstract base class for a node in a supply chain network.

    Attributes:
        id: Unique identifier, used as the node key in the network graph.
        name: Human-readable label.
        initial_inventory: Starting on-hand inventory per SKU.
        capacity: Optional cap on outbound shipment/production quantity per
            period. ``None`` means unlimited.
        holding_cost: Cost charged per unit of on-hand inventory per period.
        backlog_cost: Cost charged per unit of unmet demand/orders per period.
        lead_time_distribution: Sampled to determine how long this node's
            *own* replenishment takes when it has no predecessor node in the
            network (e.g. a root :class:`Supplier` sourcing raw material from
            outside the modeled system). Ignored for nodes with predecessors,
            since those use the connecting :class:`~chainsim.core.edges.TransportLink`'s
            lead time instead.
        shelf_life: If set, inventory for this node is tracked in expiry-aware
            batches (see :mod:`chainsim.core.perishability`) with this many
            periods of shelf life. ``None`` means non-perishable.
        skus: SKUs this node handles. Defaults to a single generic SKU.
    """

    id: str
    name: str = ""
    initial_inventory: dict[str, float] = field(default_factory=dict)
    capacity: float | None = None
    holding_cost: float = 1.0
    backlog_cost: float = 0.0
    lead_time_distribution: LeadTimeDistribution = field(
        default_factory=lambda: constant_lead_time(1.0)
    )
    shelf_life: int | None = None
    skus: list[str] = field(default_factory=lambda: [DEFAULT_SKU])

    # --- mutable simulation state, populated by reset() ---
    on_hand: dict[str, float] = field(default_factory=dict, init=False, repr=False)
    backlog: dict[str, float] = field(default_factory=dict, init=False, repr=False)
    pipeline: dict[str, float] = field(default_factory=dict, init=False, repr=False)
    _perishable: dict[str, PerishableInventory] = field(
        default_factory=dict, init=False, repr=False
    )
    active: bool = field(default=True, init=False, repr=False)
    base_capacity: float | None = field(default=None, init=False, repr=False)

    def __post_init__(self) -> None:
        self.name = self.name or self.id
        self.base_capacity = self.capacity
        self.reset()

    def clear_disruptions(self) -> None:
        """Restore capacity/active flags to baseline; called by the engine every period
        before applying that period's active disruptions.
        """
        self.active = True
        self.capacity = self.base_capacity

    def reset(self) -> None:
        """Reset all mutable state to the configured initial conditions."""
        self.clear_disruptions()
        self.on_hand = {}
        self.backlog = dict.fromkeys(self.skus, 0.0)
        self.pipeline = dict.fromkeys(self.skus, 0.0)
        self._perishable = {}
        for sku in self.skus:
            qty = self.initial_inventory.get(sku, 0.0)
            if self.is_perishable:
                inv = PerishableInventory(shelf_life=self.shelf_life)  # type: ignore[arg-type]
                if qty:
                    inv.receive(qty, period=0)
                self._perishable[sku] = inv
            else:
                self.on_hand[sku] = qty

    @property
    def is_perishable(self) -> bool:
        return self.shelf_life is not None

    def on_hand_qty(self, sku: str = DEFAULT_SKU) -> float:
        """Current on-hand quantity for a SKU (non-expired, for perishables)."""
        if self.is_perishable:
            return self._perishable[sku].on_hand
        return self.on_hand.get(sku, 0.0)

    def inventory_position(self, sku: str = DEFAULT_SKU) -> float:
        """On-hand + pipeline (on order) - backlog, the quantity a policy reacts to."""
        return self.on_hand_qty(sku) + self.pipeline.get(sku, 0.0) - self.backlog.get(sku, 0.0)

    def receive(self, qty: float, sku: str = DEFAULT_SKU, period: int = 0) -> None:
        """Receive a completed shipment/production run into on-hand inventory."""
        if qty <= 0:
            return
        self.pipeline[sku] = max(0.0, self.pipeline.get(sku, 0.0) - qty)
        if self.is_perishable:
            self._perishable[sku].receive(qty, period=period)
        else:
            self.on_hand[sku] = self.on_hand.get(sku, 0.0) + qty

    def issue(self, qty: float, sku: str = DEFAULT_SKU, period: int = 0) -> float:
        """Issue up to ``qty`` units from on-hand inventory. Returns the amount issued."""
        if qty <= 0:
            return 0.0
        if self.is_perishable:
            return self._perishable[sku].issue(qty, period=period)
        available = self.on_hand.get(sku, 0.0)
        issued = min(available, qty)
        self.on_hand[sku] = available - issued
        return issued

    def expire(self, period: int, sku: str = DEFAULT_SKU) -> float:
        """Remove expired batches for ``sku`` and return the wasted quantity."""
        if not self.is_perishable:
            return 0.0
        return self._perishable[sku].expire(period)


@dataclass
class Supplier(Node):
    """Root/upstream node with near-infinite raw-material capacity by default."""

    def __post_init__(self) -> None:
        if self.capacity is None:
            self.capacity = float("inf")
        super().__post_init__()


@dataclass
class Manufacturer(Node):
    """Converts upstream inventory into finished goods, subject to production capacity.

    ``bill_of_materials`` maps an output SKU to the input SKUs/quantities
    consumed per unit produced. Phase 1 keeps this metadata-only; the engine
    treats a Manufacturer like any other intermediate node (single-SKU
    throughput) unless a BOM is supplied for future use by callers.
    """

    bill_of_materials: dict[str, dict[str, float]] = field(default_factory=dict)


@dataclass
class DistributionCenter(Node):
    """Intermediate storage/consolidation node between manufacturing and retail."""


@dataclass
class Retailer(Node):
    """Customer-facing node; the sink that observes external demand directly."""
