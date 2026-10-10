"""Bridge between the chainsim engine and the game frontend.

Holds one running simulation (a :class:`~chainsim.core.engine.SimulationEngine`
stepped one period at a time) and serializes its state into plain JSON-friendly
dicts. All simulation logic stays in chainsim; this module only wraps it.
"""

from __future__ import annotations

import math
from collections.abc import Callable
from typing import Any

import numpy as np

from chainsim.core.demand import DemandGenerator, SeasonalDemand, StationaryDemand, TrendDemand
from chainsim.core.disruptions import DemandShock
from chainsim.core.edges import TransportLink
from chainsim.core.engine import SimulationEngine
from chainsim.core.network import SupplyChainNetwork
from chainsim.core.nodes import DEFAULT_SKU, DistributionCenter, Node, Retailer, Supplier
from chainsim.core.policies import (
    BaseStockPolicy,
    OrderUpTo,
    ReplenishmentPolicy,
    RQPolicy,
    sSPolicy,
)
from chainsim.metrics.kpis import fill_rate, service_level, summarize
from chainsim.scenarios import (
    global_commodity_flow,
    manufacturing_jit,
    pharma_cold_chain,
    retail_replenishment,
)
from chainsim.scenarios._common import ScenarioConfig
import campaign as campaign_mod
from events import EventContext, EventDirector
from economy import PRESET_ECONOMY, CappedPolicy, EconomySpec, EconomyTracker
from network_spec import NetworkSpec, config_to_spec, spec_to_config, validate_spec
from scoring import COST_TARGET_FACTOR, ScoreKeeper, Targets

SCENARIOS: dict[str, Callable[[], ScenarioConfig]] = {
    "retail_replenishment": retail_replenishment.build_scenario,
    "pharma_cold_chain": pharma_cold_chain.build_scenario,
    "manufacturing_jit": manufacturing_jit.build_scenario,
    "global_commodity_flow": global_commodity_flow.build_scenario,
}

POLICY_TYPES = ("order_up_to", "s_S", "r_q", "base_stock")


class _TrackedEngine(SimulationEngine):
    """Engine subclass that also records each shipment currently in flight.

    The base engine schedules shipments as anonymous SimPy processes, so there
    is no per-edge view of what is in transit. This hooks the two internal
    methods involved (``_ship_downstream`` / ``_deliver``) purely to observe
    them; it does not change simulation behaviour.
    """

    def _init_run(self) -> None:
        super()._init_run()
        self.shipments: dict[int, dict[str, Any]] = {}
        self.next_shipment_id = 0
        self._shipper: str | None = None

    def _ship_downstream(self, node, successors, sku, issued, incoming_orders, t) -> None:
        self._shipper = node.id
        try:
            super()._ship_downstream(node, successors, sku, issued, incoming_orders, t)
        finally:
            self._shipper = None

    def _apply_disruptions(self, t: int) -> None:
        super()._apply_disruptions(t)
        # The base engine keeps one demand shock per node (the last listed). Decision
        # events add more, so combine every active shock on a node by multiplying.
        grouped: dict[str, float] = {}
        for event in self.disruptions:
            if isinstance(event, DemandShock) and event.applies_at(t):
                grouped[event.target_id] = grouped.get(event.target_id, 1.0) * event.multiplier
        self._active_demand_shocks = {
            target: DemandShock(target, t, 1, mult) for target, mult in grouped.items()
        }

    def _deliver(self, node, sku, qty, lead_time):
        if self._shipper is None:  # external replenishment of a root node
            return super()._deliver(node, sku, qty, lead_time)
        depart = int(self.env.now)
        shipment_id = self.next_shipment_id
        self.next_shipment_id += 1
        self.shipments[shipment_id] = {
            "id": shipment_id,
            "source": self._shipper,
            "target": node.id,
            "qty": qty,
            "depart": depart,
            # The engine delivers at the first step whose period >= depart + lead_time.
            "arrive": max(depart + 1, math.ceil(depart + lead_time)),
            # Fraction that actually arrives; a quality event can lower it in flight.
            "keep": 1.0,
        }
        return self._deliver_tracked(shipment_id, node, sku, qty, lead_time)

    def _deliver_tracked(self, shipment_id: int, node, sku, qty, lead_time):
        # Same behaviour as the base engine's _deliver, but honouring in-flight losses.
        yield self.env.timeout(lead_time)
        shipment = self.shipments.pop(shipment_id, None)
        keep = shipment["keep"] if shipment else 1.0
        node.receive(qty * keep, sku, period=int(self.env.now))


class NetworkSpecError(ValueError):
    """An edited network failed validation; ``errors`` holds the structured problems."""

    def __init__(self, errors: list[dict[str, Any]]) -> None:
        super().__init__(errors[0]["message"])
        self.errors = errors


def build_policy(policy_type: str, params: dict[str, float]) -> ReplenishmentPolicy:
    """Construct a chainsim policy from a type name and a flat param dict."""

    def need(*keys: str) -> list[float]:
        missing = [k for k in keys if k not in params]
        if missing:
            raise ValueError(f"policy {policy_type!r} requires params: {', '.join(missing)}")
        return [float(params[k]) for k in keys]

    if policy_type == "order_up_to":
        (S,) = need("S")
        return OrderUpTo(S=S)
    if policy_type == "s_S":
        s, S = need("s", "S")
        return sSPolicy(s=s, S=S)
    if policy_type == "r_q":
        R, Q = need("R", "Q")
        return RQPolicy(R=R, Q=Q)
    if policy_type == "base_stock" and "base_stock_level" in params:
        # An explicit base-stock level instead of one derived from demand statistics.
        level = float(params["base_stock_level"])
        if level < 0:
            raise ValueError("base_stock_level must be non-negative")
        policy = BaseStockPolicy(
            float(params.get("mean_demand", 0.0)),
            float(params.get("std_demand", 0.0)),
            float(params.get("lead_time", 0.0)),
            z=0.0,
        )
        policy.S = level
        return policy
    if policy_type == "base_stock":
        mean_demand, std_demand, lead_time = need("mean_demand", "std_demand", "lead_time")
        if "z" in params:
            return BaseStockPolicy(mean_demand, std_demand, lead_time, z=float(params["z"]))
        (service_level,) = need("service_level")
        return BaseStockPolicy(mean_demand, std_demand, lead_time, service_level=service_level)
    raise ValueError(f"unknown policy type: {policy_type!r}")


def describe_policy(policy: ReplenishmentPolicy | None) -> dict[str, Any] | None:
    if policy is None:
        return None
    policy = getattr(policy, "inner", policy)  # see through the cash-crisis cap
    if isinstance(policy, OrderUpTo):
        return {"type": "order_up_to", "params": {"S": policy.S}}
    if isinstance(policy, sSPolicy):
        return {"type": "s_S", "params": {"s": policy.s, "S": policy.S}}
    if isinstance(policy, RQPolicy):
        return {"type": "r_q", "params": {"R": policy.R, "Q": policy.Q}}
    if isinstance(policy, BaseStockPolicy):
        return {
            "type": "base_stock",
            "params": {
                "mean_demand": policy.mean_demand,
                "std_demand": policy.std_demand,
                "lead_time": policy.lead_time,
                "z": policy.z,
                "base_stock_level": policy.S,
            },
        }
    return {"type": "custom", "params": {}}


def _demand_generator(cfg: dict[str, Any]) -> DemandGenerator:
    kind = cfg.get("type", "stationary")
    if kind == "seasonal":
        return SeasonalDemand(
            base=cfg["mean"],
            amplitude=cfg["amplitude"],
            period_length=int(cfg["period_length"]),
            noise_std=cfg["std"],
        )
    if kind == "trend":
        return TrendDemand(
            base=cfg["mean"], trend_per_period=cfg["trend_per_period"], noise_std=cfg["std"]
        )
    if cfg["std"] > 0:
        return StationaryDemand(mean=cfg["mean"], std=cfg["std"], distribution="normal")
    return StationaryDemand(mean=cfg["mean"])


def _default_policy_params(policy_type: str, mean: float, std: float, lead_time: float) -> dict:
    protection = lead_time + 1
    safety = 1.65 * max(std, 1.0) * math.sqrt(protection)
    top = mean * protection + safety
    if policy_type == "order_up_to":
        return {"S": top}
    if policy_type == "s_S":
        return {"s": top - mean, "S": top}
    if policy_type == "r_q":
        return {"R": mean * lead_time + safety, "Q": mean * 2}
    return {
        "mean_demand": mean,
        "std_demand": max(std, 1.0),
        "lead_time": lead_time,
        "service_level": 0.95,
    }


def build_custom_scenario(config: dict[str, Any]) -> ScenarioConfig:
    """Build a serial Supplier -> DC... -> Retailer chain from a custom config dict."""
    echelons = int(config["echelons"])
    lead_time = float(config["lead_time"])
    demand_cfg = config["demand"]
    policy_cfg = config["policy"]
    mean, std = float(demand_cfg["mean"]), float(demand_cfg["std"])

    net = SupplyChainNetwork()
    ids = ["Supplier"] + [f"DC_{i}" for i in range(1, echelons - 1)] + ["Retailer"]
    stock = mean * (lead_time + 1)
    for node_id in ids:
        if node_id == "Supplier":
            node: Node = Supplier(
                id=node_id, holding_cost=0.0, initial_inventory={DEFAULT_SKU: 100_000}
            )
        elif node_id == "Retailer":
            node = Retailer(
                id=node_id,
                holding_cost=1.0,
                backlog_cost=8.0,
                initial_inventory={DEFAULT_SKU: stock},
            )
        else:
            node = DistributionCenter(
                id=node_id, holding_cost=0.5, initial_inventory={DEFAULT_SKU: stock}
            )
        net.add_node(node)
    for source, destination in zip(ids, ids[1:], strict=False):
        net.add_edge(TransportLink(source=source, destination=destination, lead_time=lead_time))

    policy_type = policy_cfg["type"]
    params = {
        **_default_policy_params(policy_type, mean, std, lead_time),
        **policy_cfg.get("params", {}),
    }
    policies = {node_id: build_policy(policy_type, params) for node_id in ids[1:]}

    return ScenarioConfig(
        name="Custom Chain",
        description=f"A {echelons}-echelon serial chain with {demand_cfg['type']} demand.",
        network=net,
        demand={"Retailer": _demand_generator(demand_cfg)},
        policies=policies,
        n_periods=int(config["n_periods"]),
        seed=config.get("seed"),
    )


def _inventory_scale(history, network: SupplyChainNetwork) -> float:
    """Units per displayed crate, so a typical downstream node fills ~8 of the crate slots.

    Based on the peak on-hand of each node that has an upstream supplier (a root
    supplier's huge stock would otherwise flatten every other node), rounded to a
    "nice" number so the legend stays readable.
    """
    peaks = history.groupby("node_id")["on_hand"].max()
    downstream = [peaks[n.id] for n in network.nodes if network.predecessors(n.id) and n.id in peaks]
    if not downstream:
        downstream = list(peaks.values)
    raw = float(np.median(downstream)) / 8.0
    if raw <= 1:
        return 1.0
    magnitude = 10 ** math.floor(math.log10(raw))
    for step in (1, 2, 2.5, 5, 10):
        if raw <= step * magnitude:
            return float(step * magnitude)
    return float(10 * magnitude)


def _new_shipments(engine: "_TrackedEngine", before_id: int) -> list[dict[str, Any]]:
    """Shipments that left during the period just stepped, with their transport terms."""
    out = []
    for sid in range(before_id, engine.next_shipment_id):
        sh = engine.shipments.get(sid)
        if sh is None:  # already delivered within the same step (zero lead time)
            continue
        edge = engine.network.get_edge(sh["source"], sh["target"])
        out.append(
            {
                "source": sh["source"],
                "target": sh["target"],
                "qty": sh["qty"],
                "lead": sh["arrive"] - sh["depart"],
                "unit_cost": edge.cost_per_unit,
            }
        )
    return out


def _finite(value: float) -> float | None:
    return None if value is None or not math.isfinite(value) else float(value)


class SimBridge:
    """Owns the active simulation and exposes load / step / state / policy-change."""

    def __init__(self) -> None:
        self._builder: Callable[[], ScenarioConfig] | None = None
        self.config: ScenarioConfig | None = None
        self.engine: _TrackedEngine | None = None
        self.scenario_id: str | None = None
        self.period = 0
        self._last_rows: dict[str, dict] = {}
        self.keeper: ScoreKeeper | None = None
        self.run_id = 0
        self.inventory_scale = 1.0
        self.tracker: EconomyTracker | None = None
        self.economy = EconomySpec()
        self.infrastructure = 0.0
        # Node positions chosen in the editor; None for untouched presets.
        self.positions: dict[str, tuple[float, float]] | None = None
        # Decision events (see events.py).
        self.preset_id: str | None = None
        self.events_enabled = True
        self.director = EventDirector(None, enabled=False)
        self.pending_event: Any = None
        self.scheduled: list[Any] = []
        self.queued_events: list[tuple[int, str, dict[str, Any]]] = []
        self.event_log: list[dict[str, Any]] = []
        # Campaign: the level being played (None in sandbox) and the run's baseline targets.
        self.level: campaign_mod.Level | None = None
        self.targets: Targets | None = None

    # -- lifecycle ------------------------------------------------------------

    @property
    def loaded(self) -> bool:
        return self.engine is not None

    def list_scenarios(self) -> list[dict[str, Any]]:
        out = []
        for scenario_id, build in SCENARIOS.items():
            config = build()
            out.append(
                {
                    "id": scenario_id,
                    "name": config.name,
                    "description": config.description,
                    "n_periods": config.n_periods,
                }
            )
        return out

    def load_scenario(self, name: str) -> dict[str, Any]:
        if name not in SCENARIOS:
            raise KeyError(f"unknown scenario: {name!r}")
        self.scenario_id = name
        self.preset_id = name
        self.level = None
        self.events_enabled = True
        self.positions = None
        return self._load(SCENARIOS[name], PRESET_ECONOMY.get(name, EconomySpec()))

    def preset_spec(self, name: str) -> dict[str, Any]:
        """A preset described as an editable network spec (for edit mode)."""
        if name not in SCENARIOS:
            raise KeyError(f"unknown scenario: {name!r}")
        config = SCENARIOS[name]()
        economy = PRESET_ECONOMY.get(name, EconomySpec())
        _, scale = self._run_baseline(SCENARIOS[name], economy)
        network = config.network
        depth: dict[str, int] = {}
        for node in network.topological_order():
            preds = network.predecessors(node.id)
            depth[node.id] = 1 + max(depth[p.id] for p in preds) if preds else 0
        counts: dict[int, int] = {}
        for node in network.nodes:
            counts[depth[node.id]] = counts.get(depth[node.id], 0) + 1
        seen: dict[int, int] = {}
        echelons: dict[str, tuple[int, int, int]] = {}
        for node in network.nodes:
            d = depth[node.id]
            echelons[node.id] = (d, seen.get(d, 0), counts[d])
            seen[d] = seen.get(d, 0) + 1
        spec = config_to_spec(
            config,
            scenario_id=name,
            describe_policy=describe_policy,
            edge_lead_time=self._edge_lead_time,
            inventory_scale=scale,
            echelons=echelons,
            economy=economy,
        )
        return spec.model_dump()

    @staticmethod
    def validate_network(spec: NetworkSpec) -> list[dict[str, Any]]:
        return validate_spec(spec, build_policy)

    def load_spec(self, spec: NetworkSpec) -> dict[str, Any]:
        """Validate and load an edited network; raises ValueError with the problem list."""
        level = campaign_mod.get_level(spec.campaign_level) if spec.campaign_level else None
        if level is not None:
            # A campaign run is fixed by the level; the client only supplies the network.
            spec = spec.model_copy(deep=True)
            spec.n_periods, spec.seed, spec.events_enabled = level.n_periods, level.seed, level.events
            spec.name = level.name
            campaign_mod.apply_hidden_demand(level, spec)
        errors = self.validate_network(spec)
        if errors:
            raise NetworkSpecError(errors)
        self.level = level
        self.scenario_id = f"campaign:{level.id}" if level else f"net:{spec.name}"
        self.preset_id = None if level else spec.scenario_id
        self.events_enabled = spec.events_enabled
        self._load(
            lambda: spec_to_config(spec, build_policy),
            spec.economy,
            infrastructure=spec.infrastructure_cost(),
        )
        self.positions = {
            n.id: (n.x, n.z) for n in spec.nodes if n.x is not None and n.z is not None
        } or None
        return self.get_state()

    def level_spec(self, level_id: int) -> NetworkSpec:
        return campaign_mod.get_level(level_id).build(self)

    def start_level(self, level_id: int) -> dict[str, Any]:
        """Load a fixed campaign level straight into play (levels you don't build yourself)."""
        level = campaign_mod.get_level(level_id)
        if level.edit_mode:
            raise ValueError("This level starts in the network editor")
        return self.load_spec(level.build(self))

    def load_custom(self, config: dict[str, Any]) -> dict[str, Any]:
        self.scenario_id = "custom"
        self.preset_id = None
        self.level = None
        self.events_enabled = True
        self.positions = None
        return self._load(lambda: build_custom_scenario(config), EconomySpec())

    def reset(self) -> dict[str, Any]:
        if self._builder is None:
            raise RuntimeError("no scenario loaded")
        return self._load(self._builder, self.economy, self.infrastructure)

    def _load(
        self,
        builder: Callable[[], ScenarioConfig],
        economy: EconomySpec,
        infrastructure: float = 0.0,
    ) -> dict[str, Any]:
        # Build a fresh config so policy changes from a previous run don't leak in.
        config = builder()
        engine = _TrackedEngine(
            network=config.network,
            demand=config.demand,
            policies=config.policies,
            disruptions=config.disruptions,
            n_periods=config.n_periods,
            seed=config.seed,
        )
        engine.begin()
        self._builder, self.config, self.engine = builder, config, engine
        self.economy, self.infrastructure = economy, infrastructure
        self.period = 0
        self._last_rows = {}
        self.run_id += 1
        level = self.level
        self.director = EventDirector(
            config.seed,
            enabled=self.events_enabled,
            chance=level.event_chance if level else None,
            script=level.event_script if level else None,
            pool=set(level.event_pool) if level and level.event_pool else None,
        )
        self.pending_event = None
        self.scheduled, self.queued_events, self.event_log = [], [], []
        self.tracker = EconomyTracker(economy, set(config.demand), infrastructure)
        # In a cash crisis every node's orders are capped at its current demand.
        engine.policies = {
            node_id: CappedPolicy(policy, node_id, self)
            for node_id, policy in engine.policies.items()
        }
        targets, self.inventory_scale = self._run_baseline(builder, economy)
        self.targets = targets
        self.keeper = ScoreKeeper(
            n_periods=config.n_periods,
            sink_ids={n.id for n in engine.network.sinks()},
            targets=targets,
        )

        return self.get_state()

    @staticmethod
    def _run_baseline(
        builder: Callable[[], ScenarioConfig], economy: EconomySpec
    ) -> tuple[Targets, float]:
        """Run the scenario once, untouched, and derive objective targets and the
        inventory display scale from that baseline.
        """
        config = builder()
        engine = _TrackedEngine(
            network=config.network,
            demand=config.demand,
            policies=config.policies,
            disruptions=config.disruptions,
            n_periods=config.n_periods,
            seed=config.seed,
        )
        engine.begin()
        tracker = EconomyTracker(economy, set(config.demand))
        for t in range(config.n_periods):
            before = engine.next_shipment_id
            rows = engine.step(t)
            tracker.update(rows, _new_shipments(engine, before))
        history = engine.finish()
        summary = summarize(history, engine.network)
        perishable = any(n.is_perishable for n in engine.network.nodes)
        targets = Targets(
            # Total cost is the full cash outlay: holding, backlog, transport, orders.
            total_cost=tracker.total_costs * COST_TARGET_FACTOR,
            bonus="waste" if perishable else "stockouts",
            max_waste=max(1.0, math.ceil(summary["total_waste"] * COST_TARGET_FACTOR)),
        )
        return targets, _inventory_scale(history, engine.network)

    # -- stepping -------------------------------------------------------------

    @property
    def finished(self) -> bool:
        if self.engine is None:
            return False
        bankrupt = self.tracker is not None and self.tracker.bankrupt
        return bankrupt or self.period >= self.engine.n_periods

    def step(self) -> dict[str, Any]:
        engine = self._require_engine()
        events: list[dict[str, Any]] = []
        if self.pending_event is not None:
            raise ValueError("Choose an option for the pending event first")
        if not self.finished:
            events += self._run_scheduled()
            before = engine.next_shipment_id
            rows = engine.step(self.period)
            self._last_rows = {row["node_id"]: row for row in rows}
            self.period += 1
            assert self.keeper is not None and self.tracker is not None
            multiplier = self.tracker.multiplier  # a cash crisis halves point gains
            events = self.keeper.update(rows, multiplier)
            events += self.tracker.update(rows, _new_shipments(engine, before))
            if not self.finished:
                self.pending_event = self.director.maybe_fire(self)
        return self.get_state(events)

    # -- decision events ----------------------------------------------------------

    def _run_scheduled(self) -> list[dict[str, Any]]:
        """Delayed effects of earlier events that fall due at the start of this period."""
        due = [s for s in self.scheduled if s.at <= self.period]
        if not due:
            return []
        self.scheduled = [s for s in self.scheduled if s.at > self.period]
        ctx = EventContext(self, self.director.rng)
        for item in due:
            item.fn(ctx)
        assert self.tracker is not None
        return ctx.floaters + self.tracker.reassess()

    def resolve_event(
        self, uid: int, choice_id: str, auto: bool = False
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        """Apply the player's choice for the pending event and return (state, outcome)."""
        event = self.pending_event
        if event is None or event.uid != uid:
            raise ValueError("That event is no longer pending")
        choice = next((c for c in event.choices if c.id == choice_id), None)
        if choice is None:
            raise ValueError(f"unknown choice: {choice_id!r}")
        assert self.tracker is not None

        ctx = EventContext(self, self.director.rng)
        cash_before = self.tracker.cash
        message = choice.apply(ctx)
        if self.tracker.insured and event.category == "disruption" and ctx.spent > 0:
            self.tracker.refund_event(ctx.spent)
            self.tracker.insured = False
            message += " Insurance covered the cost."
        events = ctx.floaters + self.tracker.reassess()
        delta = self.tracker.cash - cash_before

        outcome = {
            "message": message,
            "cash_delta": delta,
            "title": event.title,
            "choice": choice.label,
            "auto": auto,
        }
        self.event_log.append(
            {
                "uid": event.uid,
                "period": event.period,
                "event_id": event.def_id,
                "title": event.title,
                "icon": event.icon,
                "category": event.category,
                "choice_id": choice.id,
                "choice": choice.label,
                "outcome": message,
                "cash_delta": delta,
                "auto": auto,
            }
        )
        self.pending_event = None
        return self.get_state(events), outcome

    def change_policy(
        self, node_id: str, policy_type: str, params: dict[str, float]
    ) -> dict[str, Any]:
        engine = self._require_engine()
        if node_id not in engine.network.graph.nodes:
            raise KeyError(f"unknown node: {node_id!r}")
        if self.finished:
            raise ValueError("the run is finished; reset to play again")
        policy = build_policy(policy_type, params)  # validates before any money moves
        assert self.keeper is not None and self.tracker is not None
        if not self.tracker.can_afford_policy_change():
            raise ValueError(
                f"Not enough cash to change a policy (costs ${self.economy.policy_change_cost:,.0f})"
            )
        events = self.tracker.charge_policy_change(node_id)
        engine.policies[node_id] = CappedPolicy(policy, node_id, self)
        self.keeper.note_policy_change(node_id)
        return self.get_state(events)

    # -- state ----------------------------------------------------------------

    def get_state(self, events: list[dict[str, Any]] | None = None) -> dict[str, Any]:
        engine = self._require_engine()
        assert self.config is not None
        network = engine.network

        depth: dict[str, int] = {}
        for node in network.topological_order():
            preds = network.predecessors(node.id)
            depth[node.id] = 1 + max(depth[p.id] for p in preds) if preds else 0
        slot_counter: dict[int, int] = {}
        slots: dict[str, int] = {}
        for node in network.nodes:
            slots[node.id] = slot_counter.get(depth[node.id], 0)
            slot_counter[depth[node.id]] = slots[node.id] + 1

        history = engine.finish() if engine._rows else None
        nodes = []
        for node in network.nodes:
            sku = node.skus[0] if node.skus else DEFAULT_SKU
            row = self._last_rows.get(node.id, {})
            observed = engine.observed_demand(node.id)
            # Demand shocks active in the most recently processed period, if any.
            shock = getattr(engine, "_active_demand_shocks", {}).get(node.id)
            nodes.append(
                {
                    "id": node.id,
                    "name": node.name,
                    "type": type(node).__name__,
                    "x": self.positions[node.id][0] if self.positions and node.id in self.positions else None,
                    "z": self.positions[node.id][1] if self.positions and node.id in self.positions else None,
                    "echelon": depth[node.id],
                    "slot": slots[node.id],
                    "echelon_size": slot_counter[depth[node.id]],
                    "on_hand": node.on_hand_qty(sku),
                    "backlog": node.backlog.get(sku, 0.0),
                    "pipeline": node.pipeline.get(sku, 0.0),
                    "last_order": row.get("order_placed", 0.0),
                    "last_demand": row.get("period_demand", 0.0),
                    "last_fulfilled": row.get("fulfilled", 0.0),
                    "fill_rate": (
                        _finite(fill_rate(history, node.id)) if history is not None else None
                    ),
                    "service_level": (
                        _finite(service_level(history, node.id)) if history is not None else None
                    ),
                    "financials": self.tracker.node_financials(node.id) if self.tracker else None,
                    "avg_demand": float(np.mean(observed)) if observed else 0.0,
                    # Below one period of typical demand on hand (drives the tutorial hint).
                    "low_stock": bool(
                        len(observed) >= 2
                        and node.id in engine.policies
                        and node.on_hand_qty(sku) < float(np.mean(observed))
                    ),
                    "forecast": self._forecast(node.id),
                    "demand_shock": shock.multiplier if shock is not None else None,
                    "active": bool(row.get("active", True)),
                    "policy": describe_policy(engine.policies.get(node.id)),
                }
            )

        shipments = sorted(engine.shipments.values(), key=lambda sh: sh["id"])
        in_transit: dict[tuple[str, str], float] = {}
        for sh in shipments:
            key = (sh["source"], sh["target"])
            in_transit[key] = in_transit.get(key, 0.0) + sh["qty"]

        edges = [
            {
                "source": e.source,
                "target": e.destination,
                "lead_time": self._edge_lead_time(e),
                "in_transit": in_transit.get((e.source, e.destination), 0.0),
                "mode": e.mode,
            }
            for e in network.edges
        ]

        metrics = self._metrics(history)
        assert self.tracker is not None
        metrics["total_cost"] = self.tracker.total_costs
        sink_service = (
            {
                n.id: _finite(service_level(history, n.id)) or 0.0
                for n in network.sinks()
            }
            if history is not None
            else {}
        )
        game = self._game_state(metrics, sink_service)
        return {
            "run_id": self.run_id,
            "pending_event": self.pending_event.public() if self.pending_event else None,
            "event_log": self.event_log,
            "inventory_scale": self.inventory_scale,
            "events": events or [],
            "scenario_id": self.scenario_id,
            "scenario_name": self.config.name,
            "description": self.config.description,
            "period": self.period,
            "n_periods": engine.n_periods,
            "finished": self.finished,
            "nodes": nodes,
            "edges": edges,
            "shipments": shipments,
            "metrics": metrics,
            **game,
        }

    def _forecast(self, node_id: str, horizon: int = 5) -> list[float] | None:
        """Expected demand for the next few periods (noise and shocks excluded)."""
        engine = self._require_engine()
        gen = engine.demand.get(node_id)
        if gen is None:
            return None
        out = []
        for t in range(self.period, self.period + horizon):
            if isinstance(gen, SeasonalDemand):
                v = gen.base + gen.amplitude * math.sin(2 * math.pi * t / gen.period_length)
            elif isinstance(gen, TrendDemand):
                v = gen.base + gen.trend_per_period * t
            elif isinstance(gen, StationaryDemand):
                v = gen.mean
            else:
                return None
            out.append(max(0.0, round(v, 1)))
        return out

    def _game_state(
        self, metrics: dict[str, float | None], sink_service: dict[str, float]
    ) -> dict[str, Any]:
        keeper, tracker = self.keeper, self.tracker
        assert keeper is not None and tracker is not None
        total_cost = metrics["total_cost"] or 0.0
        waste = metrics["waste"] or 0.0
        service = metrics["service_level"] if metrics["service_level"] is not None else 0.0
        fill = metrics["fill_rate"] if metrics["fill_rate"] is not None else 0.0

        score = keeper.score(total_cost, waste)
        level = self.level
        if level is not None:
            assert self.targets is not None
            objectives = campaign_mod.evaluate_objectives(
                level,
                {
                    "bankrupt": tracker.bankrupt, "fill": fill, "service": service,
                    "margin": tracker.margin, "revenue": tracker.revenue, "cash": tracker.cash,
                    "waste": waste, "max_waste": self.targets.max_waste,
                    "stockouts": keeper.stockouts, "stockout_log": keeper.stockout_log,
                    "baseline_cost": self.targets.total_cost / COST_TARGET_FACTOR,
                    "total_cost": total_cost, "completed": self.period,
                    "n_periods": keeper.n_periods, "score": score["total"],
                    "score_max": keeper.max_score(), "sink_service": sink_service,
                },
            )
        else:
            objectives = keeper.objectives(
                total_cost, service, fill, waste, tracker.margin, tracker.revenue
            )
        out: dict[str, Any] = {
            "score": {
                **score,
                "max": keeper.max_score(),
                "status": "red"
                if tracker.crisis
                else keeper.overall_status(
                    [o for o in objectives if o.get("tier", "required") == "required"]
                    if level
                    else objectives
                ),
                "multiplier": tracker.multiplier,
                "stockouts": keeper.stockouts,
                "policy_changes": keeper.policy_changes,
            },
            "level": {"id": level.id, "name": level.name, "n_periods": level.n_periods}
            if level
            else None,
            "economy": tracker.summary(),
            "objectives": objectives,
            "result": None,
        }
        if self.finished:
            met = sum(1 for o in objectives if o["met"])
            out["result"] = {
                "grade": "F" if tracker.bankrupt else keeper.grade(score["total"]),
                "stars": 1 if tracker.bankrupt else max(1, met),
                "objectives_met": met,
                "objectives_total": len(objectives),
                "bankrupt": tracker.bankrupt,
                "bankrupt_reason": tracker.bankrupt_reason,
                "periods_completed": self.period,
                "stats": {
                    "total_cost": total_cost,
                    "fill_rate": fill,
                    "service_level": service,
                    "waste": waste,
                    "stockouts": keeper.stockouts,
                    "policy_changes": keeper.policy_changes,
                    "revenue": tracker.revenue,
                    "costs": {
                        **tracker.costs,
                        "infrastructure": tracker.infrastructure,
                        "total": tracker.total_costs,
                    },
                    "cash": tracker.cash,
                    "net_profit": tracker.net_profit,
                    "margin": tracker.margin,
                },
            }
            if level is not None:
                out["result"]["campaign"] = campaign_mod.campaign_result(
                    level, objectives, True, tracker.bankrupt
                )
        return out

    def _metrics(self, history) -> dict[str, float | None]:
        engine = self._require_engine()
        if history is None:
            return {"total_cost": 0.0, "fill_rate": 1.0, "service_level": 1.0, "waste": 0.0}
        summary = summarize(history, engine.network)
        return {
            "total_cost": _finite(summary["total_cost"]),
            "fill_rate": _finite(summary["fill_rate"]),
            "service_level": _finite(summary["service_level"]),
            "waste": _finite(summary["total_waste"]),
        }

    @staticmethod
    def _edge_lead_time(edge: TransportLink) -> float:
        base = edge.base_lead_time
        if callable(base):
            rng = np.random.default_rng(0)
            return round(float(np.mean([base(rng) for _ in range(50)])), 1)
        return float(base)

    def _require_engine(self) -> _TrackedEngine:
        if self.engine is None:
            raise RuntimeError("no scenario loaded")
        return self.engine
