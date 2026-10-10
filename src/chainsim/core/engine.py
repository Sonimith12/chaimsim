"""SimulationEngine: SimPy-based runner tying together nodes, edges, policies, demand, disruptions.

Advances simulation time in discrete periods. Each period:

1. Every node/edge is reset to its baseline (pre-disruption) configuration,
   then any :class:`~chainsim.core.disruptions.DisruptionEvent` active at
   that period is applied.
2. Nodes are visited sink-first (customer-facing nodes before their
   suppliers) so that, by the time a node is processed, it already knows
   how much its downstream successors ordered from it this period.
3. Each node fulfills its period demand (external customer demand and/or
   downstream orders) from on-hand inventory, subject to its own and its
   outbound edges' capacity; unmet demand becomes backlog. Fulfilled
   quantity is shipped to successors as a delayed SimPy process keyed to
   the connecting edge's lead time (or, for a root node with no network
   predecessor, delayed by the node's own ``lead_time_distribution``,
   modeling replenishment from outside the modeled network).
4. Each node's :class:`~chainsim.core.policies.ReplenishmentPolicy` then
   decides how much to order, which is routed to its predecessor(s) (or
   scheduled as external replenishment for root nodes).
5. Holding/backlog cost and other period metrics are appended to a
   structured history log, returned as a ``pandas.DataFrame``.

:meth:`SimulationEngine.run` does all of the above for the whole horizon.
For callers that need to interleave an external decision each period (e.g.
:class:`chainsim.ai.gym_env.SupplyChainEnv` injecting an RL action),
:meth:`SimulationEngine.begin`/:meth:`step`/:meth:`finish` expose the same
logic one period at a time, with :meth:`step`'s ``overrides`` argument
forcing a specific node's order quantity for that period instead of
consulting its policy.

**Phase 1 scope:** single SKU per node (``chainsim.core.nodes.DEFAULT_SKU``
unless a node's first configured SKU says otherwise); a node with more than
one predecessor splits its order evenly across them, and a node with more
than one successor splits fulfilled quantity proportionally to each
successor's order share for the period. Both are exact and fully tested
for the common serial-chain/tree case (each node has at most one supplier);
general many-to-many networks use these as documented approximations.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd
import simpy

from chainsim.core.demand import DemandGenerator
from chainsim.core.disruptions import DemandShock, DisruptionEvent
from chainsim.core.edges import TransportLink
from chainsim.core.network import SupplyChainNetwork
from chainsim.core.nodes import DEFAULT_SKU, Node
from chainsim.core.policies import NodeState, ReplenishmentPolicy


@dataclass
class SimulationEngine:
    """Runs a period-by-period supply chain simulation over a network.

    Args:
        network: The topology to simulate.
        demand: Maps node id -> :class:`~chainsim.core.demand.DemandGenerator`
            for every customer-facing node that observes external demand.
        policies: Maps node id -> :class:`~chainsim.core.policies.ReplenishmentPolicy`.
            A node with no entry never places replenishment orders.
        disruptions: Disruption events to apply during the run.
        n_periods: Number of periods to simulate.
        seed: Seed for demand generation and stochastic lead times.
    """

    network: SupplyChainNetwork
    demand: dict[str, DemandGenerator] = field(default_factory=dict)
    policies: dict[str, ReplenishmentPolicy] = field(default_factory=dict)
    disruptions: list[DisruptionEvent] = field(default_factory=list)
    n_periods: int = 52
    seed: int | None = None

    def __post_init__(self) -> None:
        self.network.validate()
        self.history: pd.DataFrame | None = None

    # -- setup ----------------------------------------------------------

    def _sku_for(self, node: Node) -> str:
        return node.skus[0] if node.skus else DEFAULT_SKU

    def _resolve_target(self, target_id: str) -> Node | TransportLink:
        if target_id in self.network.graph.nodes:
            return self.network.get_node(target_id)
        if "->" in target_id:
            source, _, destination = target_id.partition("->")
            if self.network.graph.has_edge(source, destination):
                return self.network.get_edge(source, destination)
        raise KeyError(f"disruption target not found in network: {target_id!r}")

    def _init_run(self) -> None:
        self._rng = np.random.default_rng(self.seed)
        self.env = simpy.Environment()

        for node in self.network.nodes:
            node.reset()
        for edge in self.network.edges:
            edge.reset()
        for policy in self.policies.values():
            policy.reset()

        self._order = self.network.topological_order(downstream_first=True)
        self._pending_orders: dict[str, float] = {}
        self._order_shares: dict[tuple[str, str], float] = {}
        self._observed_demand: dict[str, list[float]] = {n.id: [] for n in self.network.nodes}
        self._rows: list[dict] = []

        self._demand_series: dict[str, np.ndarray] = {}
        for node_id, generator in self.demand.items():
            sub_seed = None if self.seed is None else self._rng.integers(0, 2**31 - 1)
            self._demand_series[node_id] = generator.generate(self.n_periods, seed=sub_seed)

    # -- running ----------------------------------------------------------

    def run(self) -> pd.DataFrame:
        """Run the full simulation and return the period-by-node history log."""
        self.begin()
        for t in range(self.n_periods):
            self.step(t)
        return self.finish()

    def begin(self) -> None:
        """Initialize a fresh run without executing any periods.

        For callers that need to step through periods one at a time —
        notably :class:`chainsim.ai.gym_env.SupplyChainEnv`, which injects an
        RL action for one node each period — instead of running the whole
        horizon at once via :meth:`run`. Call :meth:`step` for each period in
        order, then :meth:`finish` to collect the history DataFrame.
        """
        self._init_run()

    def step(self, t: int, overrides: dict[str, float] | None = None) -> list[dict]:
        """Process one period. Must be called with ``t`` in order, after :meth:`begin`.

        Args:
            t: The period to process (0-indexed).
            overrides: Maps node id -> order quantity to force for that node
                this period, bypassing its own :class:`~chainsim.core.policies.ReplenishmentPolicy`
                (or lack of one). Used by ``SupplyChainEnv`` to inject an
                external (e.g. RL) decision for the node(s) it controls;
                every other node still decides normally.

        Returns:
            The history rows appended during this period (one per node).
        """
        overrides = overrides or {}
        self._advance_to(t)
        self._apply_disruptions(t)
        self._order_shares = {}
        start = len(self._rows)
        for node in self._order:
            self._process_node(node, t, override=overrides.get(node.id))
        return self._rows[start:]

    def observed_demand(self, node_id: str) -> list[float]:
        """Period-by-period demand ``node_id`` has observed so far this run
        (external demand and/or downstream orders, whichever applies) — the
        same series :attr:`~chainsim.core.policies.NodeState.demand_history`
        is drawn from.
        """
        return self._observed_demand.get(node_id, [])

    def finish(self) -> pd.DataFrame:
        """Build the history DataFrame from whatever periods have been processed
        so far. Safe to call after :meth:`run`, or after a manual sequence of
        :meth:`step` calls (even a partial one).
        """
        self.history = pd.DataFrame(self._rows)
        return self.history

    def _advance_to(self, t: int) -> None:
        """Process all pending SimPy events with a scheduled time <= t, leaving
        ``env.now == t``. Plain ``env.run(until=t)`` alone would advance ``now``
        to ``t`` but stop just *before* running events scheduled at exactly
        ``t``, deferring deliveries by a full extra period — the loop below
        catches those too.
        """
        if t > self.env.now:
            self.env.run(until=t)
        while self.env.peek() <= self.env.now:
            self.env.step()

    def _apply_disruptions(self, t: int) -> None:
        for node in self.network.nodes:
            node.clear_disruptions()
        for edge in self.network.edges:
            edge.clear_disruptions()

        active = [e for e in self.disruptions if e.applies_at(t)]
        self._active_demand_shocks = {e.target_id: e for e in active if isinstance(e, DemandShock)}
        for event in active:
            if isinstance(event, DemandShock):
                continue
            event.apply(self._resolve_target(event.target_id))

    # -- per-node period logic --------------------------------------------

    def _process_node(self, node: Node, t: int, override: float | None = None) -> None:
        sku = self._sku_for(node)
        successors = self.network.successors(node.id)
        predecessors = self.network.predecessors(node.id)

        waste = node.expire(t, sku) if node.is_perishable else 0.0

        incoming_orders = self._pending_orders.pop(node.id, 0.0)
        external_demand = 0.0
        if node.id in self._demand_series:
            external_demand = float(self._demand_series[node.id][t])
            shock = self._active_demand_shocks.get(node.id)
            if shock is not None:
                external_demand = shock.apply(external_demand)

        period_demand = incoming_orders + external_demand
        self._observed_demand[node.id].append(period_demand)

        prior_backlog = node.backlog.get(sku, 0.0)
        total_owed = period_demand + prior_backlog

        node_cap = node.capacity if node.capacity is not None else float("inf")
        if successors:
            edge_cap_total = sum(
                (self.network.get_edge(node.id, s.id).capacity or float("inf")) for s in successors
            )
        else:
            edge_cap_total = float("inf")
        throughput_cap = min(node_cap, edge_cap_total)

        fulfillable = min(total_owed, throughput_cap) if node.active else 0.0
        issued = node.issue(fulfillable, sku, period=t)
        node.backlog[sku] = total_owed - issued

        self._ship_downstream(node, successors, sku, issued, incoming_orders, t)

        order_qty = (
            max(0.0, float(override)) if override is not None else self._decide_order(node, sku, t)
        )
        self._route_order(node, predecessors, sku, order_qty)

        self._rows.append(
            {
                "period": t,
                "node_id": node.id,
                "node_type": type(node).__name__,
                "active": node.active,
                "external_demand": external_demand,
                "incoming_orders": incoming_orders,
                "period_demand": period_demand,
                "fulfilled": issued,
                "on_hand": node.on_hand_qty(sku),
                "backlog": node.backlog.get(sku, 0.0),
                "pipeline": node.pipeline.get(sku, 0.0),
                "inventory_position": node.inventory_position(sku),
                "order_placed": order_qty,
                "waste": waste,
                "holding_cost": node.holding_cost * node.on_hand_qty(sku),
                "backlog_cost": node.backlog_cost * node.backlog.get(sku, 0.0),
            }
        )

    def _ship_downstream(
        self,
        node: Node,
        successors: list[Node],
        sku: str,
        issued: float,
        incoming_orders: float,
        t: int,
    ) -> None:
        if not successors or issued <= 0:
            return
        if len(successors) == 1:
            shares = {successors[0].id: 1.0}
        elif incoming_orders > 0:
            shares = {
                s.id: self._order_shares.get((node.id, s.id), 0.0) / incoming_orders
                for s in successors
            }
        else:
            shares = {s.id: 1.0 / len(successors) for s in successors}

        for successor in successors:
            ship_qty = issued * shares.get(successor.id, 0.0)
            if ship_qty <= 0:
                continue
            edge = self.network.get_edge(node.id, successor.id)
            lead_time = edge.sample_lead_time(self._rng)
            self.env.process(self._deliver(successor, sku, ship_qty, lead_time))

    def _deliver(self, node: Node, sku: str, qty: float, lead_time: float):
        yield self.env.timeout(lead_time)
        node.receive(qty, sku, period=int(self.env.now))

    def _decide_order(self, node: Node, sku: str, t: int) -> float:
        policy = self.policies.get(node.id)
        if policy is None:
            return 0.0
        state = NodeState(
            period=t,
            on_hand=node.on_hand_qty(sku),
            backlog=node.backlog.get(sku, 0.0),
            pipeline=node.pipeline.get(sku, 0.0),
            inventory_position=node.inventory_position(sku),
            demand_history=np.array(self._observed_demand[node.id][:-1]),
        )
        return max(0.0, policy.decide(state))

    def _route_order(
        self, node: Node, predecessors: list[Node], sku: str, order_qty: float
    ) -> None:
        if order_qty <= 0:
            return
        node.pipeline[sku] = node.pipeline.get(sku, 0.0) + order_qty

        if not predecessors:
            lead_time = node.lead_time_distribution(self._rng)
            self.env.process(self._deliver(node, sku, order_qty, lead_time))
            return

        share = order_qty / len(predecessors)
        for predecessor in predecessors:
            self._pending_orders[predecessor.id] = (
                self._pending_orders.get(predecessor.id, 0.0) + share
            )
            self._order_shares[(predecessor.id, node.id)] = share
