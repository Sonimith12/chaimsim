"""A plain-data description of a supply chain network, for the frontend's edit mode.

The editor works on a :class:`NetworkSpec`: presets are converted into one
(:func:`config_to_spec`), the player edits it, and it is validated
(:func:`validate_spec`) and turned back into a runnable chainsim scenario
(:func:`spec_to_config`). Everything the engine needs lives here or in chainsim;
the frontend only edits and displays the data.
"""

from __future__ import annotations

import math
from typing import Any, Literal

import networkx as nx
import numpy as np
from pydantic import BaseModel, Field

from chainsim.core.demand import DemandGenerator, SeasonalDemand, StationaryDemand, TrendDemand
from chainsim.core.disruptions import (
    CapacityReduction,
    DemandShock,
    DisruptionEvent,
    LeadTimeShock,
    NodeOutage,
)
from chainsim.core.edges import TransportLink
from chainsim.core.network import SupplyChainNetwork
from chainsim.core.nodes import (
    DEFAULT_SKU,
    DistributionCenter,
    Manufacturer,
    Node,
    Retailer,
    Supplier,
    constant_lead_time,
)
from chainsim.scenarios._common import ScenarioConfig
from economy import EconomySpec, infrastructure_cost

MAX_NODES = 10
NodeType = Literal["Supplier", "Manufacturer", "DistributionCenter", "Retailer"]
_NODE_CLASSES: dict[str, type[Node]] = {
    "Supplier": Supplier,
    "Manufacturer": Manufacturer,
    "DistributionCenter": DistributionCenter,
    "Retailer": Retailer,
}
# Types that can feed a network from outside it.
_SOURCE_TYPES = {"Supplier", "Manufacturer"}


class DemandSpec(BaseModel):
    type: Literal["stationary", "seasonal", "trend"] = "stationary"
    # stationary
    mean: float = 40.0
    std: float = 0.0
    distribution: Literal["poisson", "normal"] = "poisson"
    # seasonal / trend share `base` and `noise_std`
    base: float = 40.0
    amplitude: float = 10.0
    period_length: int = 13
    trend_per_period: float = 0.5
    noise_std: float = 0.0


class PolicySpec(BaseModel):
    type: Literal["order_up_to", "s_S", "r_q", "base_stock"]
    params: dict[str, float] = Field(default_factory=dict)


class NodeSpec(BaseModel):
    id: str
    name: str = ""
    type: NodeType
    x: float | None = None
    z: float | None = None
    # Layout hints for presets; ignored when building.
    echelon: int = 0
    slot: int = 0
    echelon_size: int = 1

    # Campaign: an approximate demand forecast shown instead of the real parameters.
    forecast: float | None = None
    initial_inventory: float = 0.0
    holding_cost: float = 1.0
    backlog_cost: float = 0.0
    capacity: float | None = None
    shelf_life: int | None = None
    external_lead_time: float = 1.0
    demand: DemandSpec | None = None
    policy: PolicySpec | None = None


class EdgeSpec(BaseModel):
    source: str
    target: str
    lead_time: float = 2.0
    capacity: float | None = None
    cost_per_unit: float = 0.0
    mode: str = "truck"


class DisruptionSpec(BaseModel):
    type: Literal["node_outage", "capacity_reduction", "lead_time_shock", "demand_shock"]
    target_id: str
    start: int
    duration: int
    value: float = 1.0  # factor (capacity_reduction) or multiplier (shocks)


class NetworkSpec(BaseModel):
    scenario_id: str | None = None
    name: str = "Custom Network"
    description: str = ""
    nodes: list[NodeSpec] = Field(default_factory=list)
    edges: list[EdgeSpec] = Field(default_factory=list)
    disruptions: list[DisruptionSpec] = Field(default_factory=list)
    n_periods: int = 52
    seed: int | None = 42
    inventory_scale: float = 20.0
    economy: EconomySpec = Field(default_factory=EconomySpec)
    events_enabled: bool = True
    # Campaign: which level this network is for, and nodes the player can't remove.
    campaign_level: int | None = None
    locked_nodes: list[str] = Field(default_factory=list)
    # Items that came with the preset: they cost nothing to keep.
    free_nodes: list[str] = Field(default_factory=list)
    free_edges: list[tuple[str, str]] = Field(default_factory=list)

    def infrastructure_cost(self) -> float:
        return infrastructure_cost(
            self.economy,
            [(n.id, n.type) for n in self.nodes],
            [(e.source, e.target, e.lead_time) for e in self.edges],
            set(self.free_nodes),
            {tuple(p) for p in self.free_edges},
        )


# --- chainsim -> spec -------------------------------------------------------------


def _demand_to_spec(gen: DemandGenerator) -> DemandSpec:
    if isinstance(gen, SeasonalDemand):
        return DemandSpec(
            type="seasonal",
            base=gen.base,
            amplitude=gen.amplitude,
            period_length=gen.period_length,
            noise_std=gen.noise_std,
        )
    if isinstance(gen, TrendDemand):
        return DemandSpec(
            type="trend",
            base=gen.base,
            trend_per_period=gen.trend_per_period,
            noise_std=gen.noise_std,
        )
    if isinstance(gen, StationaryDemand):
        return DemandSpec(
            type="stationary", mean=gen.mean, std=gen.std, distribution=gen.distribution
        )
    # Unsupported generator (e.g. empirical): approximate with its average.
    return DemandSpec(type="stationary", mean=float(np.mean(gen.generate(52, seed=0))))


def _disruption_to_spec(event: DisruptionEvent) -> DisruptionSpec:
    base = {"target_id": event.target_id, "start": event.start, "duration": event.duration}
    if isinstance(event, NodeOutage):
        return DisruptionSpec(type="node_outage", **base)
    if isinstance(event, CapacityReduction):
        return DisruptionSpec(type="capacity_reduction", value=event.factor, **base)
    if isinstance(event, LeadTimeShock):
        return DisruptionSpec(type="lead_time_shock", value=event.multiplier, **base)
    if isinstance(event, DemandShock):
        return DisruptionSpec(type="demand_shock", value=event.multiplier, **base)
    raise ValueError(f"unsupported disruption: {type(event).__name__}")


def config_to_spec(
    config: ScenarioConfig,
    *,
    scenario_id: str | None,
    describe_policy,
    edge_lead_time,
    inventory_scale: float,
    echelons: dict[str, tuple[int, int, int]],
    economy: EconomySpec,
) -> NetworkSpec:
    """Describe a runnable scenario as editable data (stochastic lead times become their mean)."""
    rng = np.random.default_rng(0)
    nodes = []
    for node in config.network.nodes:
        sku = node.skus[0] if node.skus else DEFAULT_SKU
        capacity = node.base_capacity
        policy = describe_policy(config.policies.get(node.id))
        echelon, slot, size = echelons[node.id]
        nodes.append(
            NodeSpec(
                id=node.id,
                name=node.name,
                type=type(node).__name__,  # type: ignore[arg-type]
                echelon=echelon,
                slot=slot,
                echelon_size=size,
                initial_inventory=float(node.initial_inventory.get(sku, 0.0)),
                holding_cost=node.holding_cost,
                backlog_cost=node.backlog_cost,
                capacity=None if capacity is None or math.isinf(capacity) else float(capacity),
                shelf_life=node.shelf_life,
                external_lead_time=float(node.lead_time_distribution(rng)),
                demand=(
                    _demand_to_spec(config.demand[node.id]) if node.id in config.demand else None
                ),
                policy=(
                    PolicySpec(type=policy["type"], params=policy["params"])
                    if policy and policy["type"] != "custom"
                    else None
                ),
            )
        )
    edges = [
        EdgeSpec(
            source=e.source,
            target=e.destination,
            lead_time=edge_lead_time(e),
            capacity=e.base_capacity,
            cost_per_unit=e.cost_per_unit,
            mode=e.mode,
        )
        for e in config.network.edges
    ]
    return NetworkSpec(
        scenario_id=scenario_id,
        name=config.name,
        description=config.description,
        nodes=nodes,
        edges=edges,
        disruptions=[_disruption_to_spec(d) for d in config.disruptions],
        n_periods=config.n_periods,
        seed=42,
        inventory_scale=inventory_scale,
        economy=economy,
        free_nodes=[n.id for n in nodes],
        free_edges=[(e.source, e.target) for e in edges],
    )


# --- validation ---------------------------------------------------------------------


def _error(code: str, message: str, **extra: Any) -> dict[str, Any]:
    return {"code": code, "message": message, **extra}


def validate_spec(spec: NetworkSpec, build_policy) -> list[dict[str, Any]]:
    """Return a list of structured problems; an empty list means the network can run.

    Each error carries ``node_ids`` / ``edges`` the UI should highlight.
    """
    errors: list[dict[str, Any]] = []
    ids = [n.id for n in spec.nodes]
    by_id = {n.id: n for n in spec.nodes}
    label = lambda node_id: by_id[node_id].name or node_id  # noqa: E731

    if not spec.nodes:
        return [_error("empty", "The network has no nodes", node_ids=[], edges=[])]
    for locked in spec.locked_nodes:
        if locked not in by_id:
            errors.append(
                _error("locked_missing", f"{locked} is part of the contract and can't be removed",
                       node_ids=[], edges=[])
            )
    if len(spec.nodes) > MAX_NODES:
        errors.append(
            _error("too_many_nodes", f"Too many nodes (maximum {MAX_NODES})", node_ids=[], edges=[])
        )
    if len(set(ids)) != len(ids):
        errors.append(_error("duplicate_id", "Duplicate node ids", node_ids=[], edges=[]))
    if not 1 <= spec.n_periods <= 520:
        errors.append(
            _error("periods", "Number of periods must be between 1 and 520", node_ids=[], edges=[])
        )

    build = spec.infrastructure_cost()
    if build > spec.economy.starting_capital:
        errors.append(
            _error(
                "over_budget",
                f"Build costs ${build:,.0f} exceed the budget of ${spec.economy.starting_capital:,.0f}",
                node_ids=[],
                edges=[],
            )
        )

    if not any(n.type in _SOURCE_TYPES for n in spec.nodes):
        errors.append(_error("no_supplier", "No supplier in the network", node_ids=[], edges=[]))
    if not any(n.type == "Retailer" for n in spec.nodes):
        errors.append(_error("no_retailer", "No retailer in the network", node_ids=[], edges=[]))

    graph = nx.DiGraph()
    graph.add_nodes_from(by_id)
    seen: set[tuple[str, str]] = set()
    for e in spec.edges:
        key = [e.source, e.target]
        if e.source not in by_id or e.target not in by_id:
            errors.append(
                _error("bad_edge", f"Edge {e.source} → {e.target} references a missing node",
                       node_ids=[], edges=[key])
            )
            continue
        if e.source == e.target:
            errors.append(
                _error("self_loop", f"{label(e.source)} is connected to itself",
                       node_ids=[e.source], edges=[key])
            )
            continue
        if (e.source, e.target) in seen:
            errors.append(
                _error("duplicate_edge", f"Duplicate edge {label(e.source)} → {label(e.target)}",
                       node_ids=[], edges=[key])
            )
            continue
        if e.lead_time < 1:
            errors.append(
                _error("lead_time", f"Lead time on {label(e.source)} → {label(e.target)} must be at least 1",
                       node_ids=[], edges=[key])
            )
        seen.add((e.source, e.target))
        graph.add_edge(e.source, e.target)

    if len(spec.nodes) > 1:
        for node_id in nx.isolates(graph):
            errors.append(
                _error("disconnected", f"Disconnected node: {label(node_id)} has no edges",
                       node_ids=[node_id], edges=[])
            )

    if not nx.is_directed_acyclic_graph(graph):
        try:
            cycle = nx.find_cycle(graph)
            cycle_nodes = sorted({u for u, _ in cycle})
            cycle_edges = [[u, v] for u, v in cycle]
        except nx.NetworkXNoCycle:  # pragma: no cover - guarded by the check above
            cycle_nodes, cycle_edges = [], []
        errors.append(
            _error("cycle", "Cycle detected", node_ids=cycle_nodes, edges=cycle_edges)
        )
    else:
        sources = [n.id for n in spec.nodes if n.type in _SOURCE_TYPES]
        reachable: set[str] = set(sources)
        for s in sources:
            reachable |= nx.descendants(graph, s)
        for n in spec.nodes:
            if n.type == "Retailer" and n.id not in reachable and graph.degree(n.id) > 0:
                errors.append(
                    _error("unreachable", f"{label(n.id)} is not supplied by any supplier",
                           node_ids=[n.id], edges=[])
                )

    for n in spec.nodes:
        if n.type == "Retailer" and n.demand is None:
            errors.append(
                _error("no_demand", f"Retailer {label(n.id)} has no demand configured",
                       node_ids=[n.id], edges=[])
            )
        if n.policy is not None:
            try:
                build_policy(n.policy.type, n.policy.params)
            except (ValueError, KeyError) as exc:
                errors.append(
                    _error("bad_policy", f"Invalid policy for {label(n.id)}: {exc.args[0]}",
                           node_ids=[n.id], edges=[])
                )
        if n.initial_inventory < 0 or n.holding_cost < 0 or n.backlog_cost < 0:
            errors.append(
                _error("negative", f"{label(n.id)} has a negative value", node_ids=[n.id], edges=[])
            )
        if n.capacity is not None and n.capacity < 0:
            errors.append(
                _error("negative", f"{label(n.id)} has a negative capacity", node_ids=[n.id], edges=[])
            )
    return errors


# --- spec -> chainsim ---------------------------------------------------------------


def _demand_from_spec(d: DemandSpec) -> DemandGenerator:
    if d.type == "seasonal":
        return SeasonalDemand(
            base=d.base, amplitude=d.amplitude, period_length=max(1, d.period_length),
            noise_std=d.noise_std,
        )
    if d.type == "trend":
        return TrendDemand(base=d.base, trend_per_period=d.trend_per_period, noise_std=d.noise_std)
    return StationaryDemand(mean=d.mean, std=d.std, distribution=d.distribution)


def _disruption_from_spec(d: DisruptionSpec) -> DisruptionEvent:
    if d.type == "node_outage":
        return NodeOutage(d.target_id, d.start, d.duration)
    if d.type == "capacity_reduction":
        return CapacityReduction(d.target_id, d.start, d.duration, d.value)
    if d.type == "lead_time_shock":
        return LeadTimeShock(d.target_id, d.start, d.duration, d.value)
    return DemandShock(d.target_id, d.start, d.duration, d.value)


def spec_to_config(spec: NetworkSpec, build_policy) -> ScenarioConfig:
    """Build a runnable scenario. Assumes :func:`validate_spec` returned no errors."""
    net = SupplyChainNetwork()
    demand: dict[str, DemandGenerator] = {}
    policies = {}
    for n in spec.nodes:
        node = _NODE_CLASSES[n.type](
            id=n.id,
            name=n.name or n.id,
            initial_inventory={DEFAULT_SKU: n.initial_inventory},
            capacity=n.capacity,
            holding_cost=n.holding_cost,
            backlog_cost=n.backlog_cost,
            lead_time_distribution=constant_lead_time(n.external_lead_time),
            shelf_life=n.shelf_life,
        )
        net.add_node(node)
        if n.demand is not None:
            demand[n.id] = _demand_from_spec(n.demand)
        if n.policy is not None:
            policies[n.id] = build_policy(n.policy.type, n.policy.params)
    for e in spec.edges:
        net.add_edge(
            TransportLink(
                source=e.source,
                destination=e.target,
                lead_time=e.lead_time,
                capacity=e.capacity,
                cost_per_unit=e.cost_per_unit,
                mode=e.mode,
            )
        )

    # Drop disruptions whose target was deleted in the editor.
    node_ids = set(net.graph.nodes)
    disruptions = []
    for d in spec.disruptions:
        target_ok = (
            all(part in node_ids for part in d.target_id.split("->"))
            if "->" in d.target_id
            else d.target_id in node_ids
        )
        if target_ok and ("->" not in d.target_id or net.graph.has_edge(*d.target_id.split("->"))):
            disruptions.append(_disruption_from_spec(d))

    return ScenarioConfig(
        name=spec.name,
        description=spec.description,
        network=net,
        demand=demand,
        policies=policies,
        disruptions=disruptions,
        n_periods=spec.n_periods,
        seed=spec.seed,
    )
