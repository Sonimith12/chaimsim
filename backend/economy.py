"""The money layer: cash balance, revenue, costs, crises and bankruptcy.

Layered on top of the chainsim engine without changing it. Each period the
engine's history rows (units fulfilled, holding/backlog cost, orders placed)
and the shipments that left are turned into cash flows per node; the tracker
keeps the balance and decides when the player is in a cash crisis or bankrupt.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel

from chainsim.core.policies import NodeState, ReplenishmentPolicy

BUCKETS = ("holding", "backlog", "transport", "ordering", "policy", "events")


class EconomySpec(BaseModel):
    """Economic parameters of a scenario (also the shape sent to / from the editor)."""

    starting_capital: float = 30_000.0
    revenue_per_unit: float = 10.0
    ordering_cost: float = 20.0  # fixed, per order placed
    transport_cost_per_lead_time: float = 10.0  # per shipment, per period of its lead time
    holding_multiplier: float = 1.0
    backlog_multiplier: float = 1.0
    policy_change_cost: float = 500.0
    overdraft_limit: float = 5_000.0
    bankruptcy_periods: int = 5  # consecutive periods with no cash
    build_cost_supplier: float = 5_000.0
    build_cost_dc: float = 3_000.0
    build_cost_retailer: float = 2_000.0
    build_cost_per_lead_time: float = 500.0

    def node_build_cost(self, node_type: str) -> float:
        if node_type in ("Supplier", "Manufacturer"):
            return self.build_cost_supplier
        if node_type == "DistributionCenter":
            return self.build_cost_dc
        return self.build_cost_retailer


# Balanced against each preset's baseline run: its default policies end around a
# 35-40% margin, while a careless one (never ordering) piles up backlog penalties
# many times its revenue and goes bankrupt.
PRESET_ECONOMY: dict[str, EconomySpec] = {
    "retail_replenishment": EconomySpec(starting_capital=50_000, revenue_per_unit=5),
    "pharma_cold_chain": EconomySpec(starting_capital=25_000, revenue_per_unit=40),
    "manufacturing_jit": EconomySpec(starting_capital=30_000, revenue_per_unit=20),
    "global_commodity_flow": EconomySpec(starting_capital=120_000, revenue_per_unit=8),
}


def infrastructure_cost(
    economy: EconomySpec,
    nodes: list[tuple[str, str]],
    edges: list[tuple[str, str, float]],
    free_nodes: set[str],
    free_edges: set[tuple[str, str]],
) -> float:
    """Build cost of everything not already part of the preset.

    ``nodes`` are (id, type); ``edges`` are (source, target, lead_time).
    """
    total = sum(economy.node_build_cost(t) for nid, t in nodes if nid not in free_nodes)
    total += sum(
        economy.build_cost_per_lead_time * lead
        for s, t, lead in edges
        if (s, t) not in free_edges
    )
    return total


class CappedPolicy(ReplenishmentPolicy):
    """Wraps a policy so that, during a cash crisis, orders can't exceed current demand."""

    def __init__(self, inner: ReplenishmentPolicy, node_id: str, bridge: Any) -> None:
        self.inner = inner
        self.node_id = node_id
        self._bridge = bridge

    def decide(self, state: NodeState) -> float:
        order = self.inner.decide(state)
        tracker = self._bridge.tracker
        if tracker is not None and tracker.crisis and self._bridge.engine is not None:
            observed = self._bridge.engine.observed_demand(self.node_id)
            if observed:
                return min(order, max(0.0, observed[-1]))
        return order

    def reset(self) -> None:
        self.inner.reset()


class EconomyTracker:
    def __init__(
        self, economy: EconomySpec, revenue_nodes: set[str], infrastructure: float = 0.0
    ) -> None:
        # Own copy: events change multipliers mid-run and a reset must start clean.
        self.economy = economy.model_copy()
        self.revenue_nodes = revenue_nodes
        self.price_multiplier = 1.0
        self.insured = False
        self.infrastructure = infrastructure
        self.initial_cash = economy.starting_capital - infrastructure
        self.cash = self.initial_cash

        self.revenue = 0.0
        self.costs = dict.fromkeys(BUCKETS, 0.0)
        self.per_node: dict[str, dict[str, float]] = {}
        self.last_period: dict[str, dict[str, float]] = {}
        self.last_totals = self._empty_totals()

        self.crisis = False
        self.crisis_periods = 0
        self.zero_streak = 0
        self.bankrupt = False
        self.bankrupt_reason: str | None = None

    # -- helpers ---------------------------------------------------------------

    @staticmethod
    def _empty_totals() -> dict[str, float]:
        return {"revenue": 0.0, **dict.fromkeys(BUCKETS, 0.0), "net": 0.0}

    def _node(self, node_id: str) -> dict[str, float]:
        if node_id not in self.per_node:
            self.per_node[node_id] = {"revenue": 0.0, **dict.fromkeys(BUCKETS, 0.0)}
        return self.per_node[node_id]

    @property
    def total_costs(self) -> float:
        return sum(self.costs.values()) + self.infrastructure

    @property
    def net_profit(self) -> float:
        return self.revenue - self.total_costs

    @property
    def margin(self) -> float:
        return self.net_profit / self.revenue if self.revenue > 0 else 0.0

    @property
    def min_display(self) -> float:
        """Smallest flow worth drawing as a floating number."""
        return max(5.0, self.economy.starting_capital * 0.001)

    # -- per period ----------------------------------------------------------------

    def update(self, rows: list[dict], shipments: list[dict]) -> list[dict[str, Any]]:
        """Apply one period's cash flows; return events for the UI."""
        e = self.economy
        flows: dict[str, dict[str, float]] = {}

        def add(node_id: str, bucket: str, amount: float) -> None:
            flows.setdefault(node_id, {"revenue": 0.0, **dict.fromkeys(BUCKETS, 0.0)})
            flows[node_id][bucket] += amount

        for r in rows:
            nid = r["node_id"]
            if nid in self.revenue_nodes:
                add(nid, "revenue", r["fulfilled"] * e.revenue_per_unit * self.price_multiplier)
            add(nid, "holding", r["holding_cost"] * e.holding_multiplier)
            add(nid, "backlog", r["backlog_cost"] * e.backlog_multiplier)
            if r["order_placed"] > 0:
                add(nid, "ordering", e.ordering_cost)
        for s in shipments:
            add(
                s["source"],
                "transport",
                e.transport_cost_per_lead_time * s["lead"] + s["unit_cost"] * s["qty"],
            )

        totals = self._empty_totals()
        events: list[dict[str, Any]] = []
        for nid, f in flows.items():
            node = self._node(nid)
            for key, amount in f.items():
                node[key] += amount
                totals[key] += amount
            if f["revenue"] >= self.min_display:
                events.append({"type": "cost", "kind": "revenue", "node_id": nid, "amount": f["revenue"]})
            if f["holding"] >= self.min_display:
                events.append({"type": "cost", "kind": "holding", "node_id": nid, "amount": f["holding"]})
            if f["backlog"] >= self.min_display:
                events.append({"type": "cost", "kind": "backlog", "node_id": nid, "amount": f["backlog"]})
        self.last_period = flows
        outgoing = sum(totals[b] for b in BUCKETS)
        totals["net"] = totals["revenue"] - outgoing
        self.last_totals = totals

        self.revenue += totals["revenue"]
        for b in BUCKETS:
            self.costs[b] += totals[b]
        self.cash += totals["net"]
        events += self._assess()
        return events

    def charge_policy_change(self, node_id: str) -> list[dict[str, Any]]:
        cost = self.economy.policy_change_cost
        self._node(node_id)["policy"] += cost
        self.costs["policy"] += cost
        self.cash -= cost
        events: list[dict[str, Any]] = [
            {"type": "cost", "kind": "policy", "node_id": node_id, "amount": cost}
        ]
        return events + self._assess()

    def charge_event(self, node_id: str, amount: float) -> list[dict[str, Any]]:
        """Money paid because of a decision event."""
        self._node(node_id)["events"] += amount
        self.costs["events"] += amount
        self.cash -= amount
        out: list[dict[str, Any]] = []
        if amount >= self.min_display:
            out.append({"type": "cost", "kind": "event", "node_id": node_id, "amount": amount})
        return out

    def credit_event(self, node_id: str, amount: float) -> list[dict[str, Any]]:
        """Money received because of a decision event (liquidation, rebates, salvage)."""
        self._node(node_id)["revenue"] += amount
        self.revenue += amount
        self.cash += amount
        out: list[dict[str, Any]] = []
        if amount >= self.min_display:
            out.append({"type": "cost", "kind": "revenue", "node_id": node_id, "amount": amount})
        return out

    def refund_event(self, amount: float) -> None:
        """Insurance paying back what an event response cost."""
        self.costs["events"] -= amount
        self.cash += amount

    def reassess(self) -> list[dict[str, Any]]:
        """Re-evaluate crisis / bankruptcy after cash changed outside a period update."""
        return self._assess()

    def can_afford_policy_change(self) -> bool:
        return self.cash - self.economy.policy_change_cost >= -self.economy.overdraft_limit

    def _assess(self) -> list[dict[str, Any]]:
        """Update crisis / bankruptcy state from the current balance."""
        events: list[dict[str, Any]] = []
        was_crisis = self.crisis
        self.crisis = self.cash <= 0
        if self.crisis:
            self.crisis_periods += 1
            if not was_crisis:
                events.append({"type": "cash_crisis"})
        self.zero_streak = self.zero_streak + 1 if self.crisis else 0

        if not self.bankrupt:
            if self.cash < -self.economy.overdraft_limit:
                self.bankrupt, self.bankrupt_reason = True, "overdraft"
            elif self.zero_streak >= self.economy.bankruptcy_periods:
                self.bankrupt, self.bankrupt_reason = True, "insolvent"
            if self.bankrupt:
                events.append({"type": "bankrupt", "reason": self.bankrupt_reason})
        return events

    # -- reporting -------------------------------------------------------------------

    @property
    def multiplier(self) -> float:
        return 0.5 if self.crisis else 1.0

    def node_financials(self, node_id: str) -> dict[str, Any]:
        def pack(d: dict[str, float]) -> dict[str, float]:
            out = {k: d.get(k, 0.0) for k in ("revenue", *BUCKETS)}
            out["net"] = out["revenue"] - sum(out[b] for b in BUCKETS)
            return out

        return {
            "period": pack(self.last_period.get(node_id, {})),
            "cumulative": pack(self.per_node.get(node_id, {})),
        }

    def summary(self) -> dict[str, Any]:
        cash_ratio = self.cash / self.initial_cash if self.initial_cash > 0 else 0.0
        status = "red" if cash_ratio < 0.2 else "yellow" if cash_ratio <= 0.5 else "green"
        return {
            "cash": self.cash,
            "starting_capital": self.economy.starting_capital,
            "initial_cash": self.initial_cash,
            "cash_status": "red" if self.crisis else status,
            "crisis": self.crisis,
            "crisis_periods": self.crisis_periods,
            "zero_streak": self.zero_streak,
            "bankrupt": self.bankrupt,
            "bankrupt_reason": self.bankrupt_reason,
            "bankruptcy_periods": self.economy.bankruptcy_periods,
            "overdraft_limit": self.economy.overdraft_limit,
            "policy_change_cost": self.economy.policy_change_cost,
            "revenue": self.revenue,
            "costs": {**self.costs, "infrastructure": self.infrastructure, "total": self.total_costs},
            "net_profit": self.net_profit,
            "margin": self.margin,
            "last_period": self.last_totals,
            "insured": self.insured,
            "price_multiplier": self.price_multiplier,
            "holding_multiplier": self.economy.holding_multiplier,
        }
