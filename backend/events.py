"""Decision events: surprises that pause the run and force the player to choose.

Everything here is backend logic. An :class:`EventDef` builds an
:class:`EventInstance` (a card with 2-3 choices) when it is applicable to the
current network; each :class:`Choice` carries an ``apply`` that makes REAL
changes to the chainsim engine, the cash balance or the economy multipliers.
Randomness comes from a seeded generator, so a seed reproduces the same run.
"""

from __future__ import annotations

import math
import random
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from chainsim.core.disruptions import (
    DemandShock,
    DisruptionEvent,
    LeadTimeShock,
    NodeOutage,
)
from chainsim.core.nodes import DEFAULT_SKU, Node
from chainsim.core.policies import BaseStockPolicy, OrderUpTo, RQPolicy, sSPolicy

# --- trigger tuning -----------------------------------------------------------------
MIN_FIRST_PERIOD = 3  # nothing fires before this many periods have run
MIN_GAP = 3  # periods between events
BASE_CHANCE = 0.10  # per-period chance of a random event ...
LATE_CHANCE = 0.15  # ... rising to this by the end of the run
SAME_EVENT_COOLDOWN = 12
FOREVER = 100_000


def usd(n: float) -> str:
    return f"${round(n):,}"


class CapacityCap(DisruptionEvent):
    """Caps a node's per-period throughput at an absolute level for a window."""

    def __init__(self, target_id: str, start: int, duration: int, cap: float) -> None:
        super().__init__(target_id, start, duration)
        self.cap = cap

    def apply(self, target: Node) -> None:
        current = target.capacity
        target.capacity = self.cap if current is None else min(current, self.cap)


@dataclass
class Choice:
    id: str
    label: str
    description: str  # cost / consequence preview shown on the button
    risk: str  # "safe" | "risky" | "danger"
    apply: Callable[[EventContext], str]
    cost: float = 0.0


@dataclass
class EventInstance:
    uid: int
    def_id: str
    category: str
    icon: str
    title: str
    description: str
    choices: list[Choice]
    default_choice: str  # the worst option, auto-selected when the timer runs out
    timer: int | None = None
    period: int = 0

    def public(self) -> dict[str, Any]:
        return {
            "uid": self.uid,
            "event_id": self.def_id,
            "category": self.category,
            "icon": self.icon,
            "title": self.title,
            "description": self.description,
            "timer": self.timer,
            "period": self.period,
            "default_choice": self.default_choice,
            "choices": [
                {
                    "id": c.id,
                    "label": c.label,
                    "description": c.description,
                    "risk": c.risk,
                    "cost": c.cost,
                }
                for c in self.choices
            ],
        }


@dataclass
class EventDef:
    id: str
    category: str  # disruption | demand | financial | operations
    weight: float
    severity: int  # 1..3: severe events become likelier later in the run
    builder: Callable[[EventContext, dict[str, Any]], EventInstance | None]
    random: bool = True  # False for cascade follow-ups
    min_progress: float = 0.0


@dataclass
class _Scheduled:
    at: int  # period (number of completed periods) at which it runs
    fn: Callable[[EventContext], str | None]


class EventContext:
    """What an event can see and change. Built fresh each time one is built or applied."""

    def __init__(self, bridge: Any, rng: random.Random) -> None:
        self.bridge = bridge
        self.rng = rng
        self.engine = bridge.engine
        self.tracker = bridge.tracker
        self.network = bridge.engine.network
        self.period: int = bridge.period  # index of the next period to be simulated
        self.floaters: list[dict[str, Any]] = []
        self.spent = 0.0

    # -- money --------------------------------------------------------------------
    @property
    def price(self) -> float:
        return self.tracker.economy.revenue_per_unit * self.tracker.price_multiplier

    @property
    def cost_scale(self) -> float:
        """Event prices are written for a $50k business; scale them to this one."""
        return min(3.0, max(0.4, self.tracker.economy.starting_capital / 50_000))

    def m(self, base: float) -> float:
        return max(50.0, round(base * self.cost_scale / 50) * 50)

    def charge(self, amount: float, node_id: str) -> None:
        self.spent += amount
        self.floaters += self.tracker.charge_event(node_id, amount)

    def credit(self, amount: float, node_id: str) -> None:
        self.floaters += self.tracker.credit_event(node_id, amount)

    # -- network queries -----------------------------------------------------------
    def roots(self) -> list[str]:
        return [n.id for n in self.network.nodes if not self.network.predecessors(n.id)]

    def retailers(self) -> list[str]:
        return [nid for nid in self.engine.demand if nid in self.network.graph.nodes]

    def midstream(self) -> list[str]:
        """Nodes that receive from and ship to other nodes (DCs, plants), DCs first."""
        nodes = [
            n
            for n in self.network.nodes
            if self.network.predecessors(n.id) and self.network.successors(n.id)
        ]
        nodes.sort(key=lambda n: type(n).__name__ != "DistributionCenter")
        return [n.id for n in nodes]

    def node(self, node_id: str) -> Node:
        return self.network.get_node(node_id)

    def name(self, node_id: str) -> str:
        return self.node(node_id).name or node_id

    def avg_demand(self, node_id: str, window: int = 8) -> float:
        observed = self.engine.observed_demand(node_id)[-window:]
        return sum(observed) / len(observed) if observed else 0.0

    def on_hand(self, node_id: str) -> float:
        node = self.node(node_id)
        return node.on_hand_qty(node.skus[0] if node.skus else DEFAULT_SKU)

    # -- engine changes ---------------------------------------------------------------
    def add_disruption(self, event: DisruptionEvent) -> None:
        self.engine.disruptions.append(event)

    def rush(self, node_id: str, qty: float, periods: int = 1) -> None:
        """Order ``qty`` units that arrive at ``node_id`` after ``periods`` periods."""
        if qty <= 0:
            return
        node = self.node(node_id)
        sku = node.skus[0] if node.skus else DEFAULT_SKU
        node.pipeline[sku] = node.pipeline.get(sku, 0.0) + qty
        env = self.engine.env

        def _arrive():
            yield env.timeout(periods)
            node.receive(qty, sku, period=int(env.now))

        env.process(_arrive())

    def remove_stock(self, node_id: str, fraction: float) -> float:
        node = self.node(node_id)
        sku = node.skus[0] if node.skus else DEFAULT_SKU
        qty = node.on_hand_qty(sku) * fraction
        return node.issue(qty, sku, period=self.period)

    def scale_policy(self, node_id: str, factor: float) -> bool:
        policy = self.engine.policies.get(node_id)
        policy = getattr(policy, "inner", policy)
        if isinstance(policy, OrderUpTo):
            policy.S *= factor
        elif isinstance(policy, sSPolicy):
            policy.s *= factor
            policy.S *= factor
        elif isinstance(policy, RQPolicy):
            policy.R *= factor
        elif isinstance(policy, BaseStockPolicy):
            policy.S *= factor
        else:
            return False
        return True

    def later(self, periods: int, fn: Callable[[EventContext], str | None]) -> None:
        """Run ``fn`` at the start of the period ``periods`` from now (a delayed effect)."""
        self.bridge.scheduled.append(_Scheduled(self.period + periods, fn))

    def follow_up(self, def_id: str, periods: int, payload: dict[str, Any]) -> None:
        self.bridge.queued_events.append((self.period + periods, def_id, payload))


# --- event builders ---------------------------------------------------------------------


def _choice(id_, label, description, risk, apply, cost=0.0) -> Choice:
    return Choice(id_, label, description, risk, apply, cost)


def _port_strike(ctx: EventContext, _: dict) -> EventInstance | None:
    roots = set(ctx.roots())
    edges = [e for e in ctx.network.edges if e.source in roots]
    if not edges:
        return None
    edge = ctx.rng.choice(edges)
    base = edge.base_lead_time if not callable(edge.base_lead_time) else 2.0
    add = max(3, min(10, round(base * 1.5)))
    mult = (base + add) / base
    duration = 8
    target = f"{edge.source}->{edge.destination}"
    src, dst = ctx.name(edge.source), ctx.name(edge.destination)
    cost = ctx.m(3000)

    def pre_order(c: EventContext) -> str:
        qty = max(30.0, c.avg_demand(edge.destination) * 3)
        c.charge(cost, edge.destination)
        c.rush(edge.destination, qty, 1)
        c.add_disruption(LeadTimeShock(target, c.period, duration, mult))
        return (
            f"You pre-ordered safety stock. Inventory at {dst} will increase by "
            f"{round(qty)} units next period. -{usd(cost)}"
        )

    def reroute(c: EventContext) -> str:
        premium = 0.25 * c.price
        c.add_disruption(LeadTimeShock(target, c.period, duration, 1 + (mult - 1) * 0.25))
        edge.cost_per_unit += premium
        c.later(duration, lambda _c: setattr(edge, "cost_per_unit", edge.cost_per_unit - premium))
        return (
            f"Rerouted through an alternate supplier: lead time rises only about 25% as much, "
            f"but each unit costs {usd(premium)} more for {duration} periods."
        )

    def nothing(c: EventContext) -> str:
        c.add_disruption(LeadTimeShock(target, c.period, duration, mult))
        return f"Lead time from {src} to {dst} is +{add} periods for {duration} periods."

    return EventInstance(
        0, "port_strike", "disruption", "⚠️", "Port Strike",
        f"Dock workers are on strike at the port serving {src}. Lead time from {src} to {dst} "
        f"will increase by {add} periods for {duration} periods, starting next period.",
        [
            _choice("pre_order", "Pre-order Safety Stock",
                    f"Cost: {usd(cost)} now. Builds a buffer at {dst} before the strike bites.",
                    "safe", pre_order, cost),
            _choice("reroute", "Reroute to Alternate Supplier",
                    "Mostly avoids the delay, but every unit costs more while it lasts.",
                    "risky", reroute),
            _choice("nothing", "Do Nothing",
                    "No cost, but expect long delays and possible stockouts.",
                    "danger", nothing),
        ],
        "nothing", timer=20,
    )


def _supplier_shutdown(ctx: EventContext, _: dict) -> EventInstance | None:
    roots = ctx.roots()
    if not roots:
        return None
    sup = ctx.rng.choice(roots)
    name = ctx.name(sup)
    duration = ctx.rng.randint(4, 6)
    retailers = ctx.retailers()
    fee = ctx.m(1000)
    node = sup

    def emergency(c: EventContext) -> str:
        premium = 0.5 * c.price
        c.charge(fee, node)
        edges = [e for e in c.network.edges if e.source == node]
        for e in edges:
            e.cost_per_unit += premium

        def revert(_c: EventContext) -> None:
            for e in edges:
                e.cost_per_unit -= premium

        c.later(duration, revert)
        return (
            f"An emergency supplier covers {name}. -{usd(fee)} now and +{usd(premium)} per unit "
            f"shipped for {duration} periods. No outage."
        )

    def wait(c: EventContext) -> str:
        c.add_disruption(NodeOutage(node, c.period, duration))
        c.follow_up("emergency_offer", 2, {"supplier": node, "duration": duration - 2})
        return f"{name} is offline for {duration} periods starting next period."

    def ration(c: EventContext) -> str:
        c.add_disruption(NodeOutage(node, c.period, duration))
        for r in retailers:
            c.add_disruption(DemandShock(r, c.period, duration, 0.7))
        c.follow_up("emergency_offer", 2, {"supplier": node, "duration": duration - 2})
        return (
            f"You are rationing: retailer demand is cut 30% for {duration} periods "
            f"while {name} is offline. Revenue will dip."
        )

    return EventInstance(
        0, "supplier_shutdown", "disruption", "⚠️", "Supplier Shutdown",
        f"{name} has halted production after a safety inspection and will be offline for "
        f"{duration} periods starting next period.",
        [
            _choice("emergency", "Emergency Supplier",
                    f"Cost: {usd(fee)} + a per-unit premium. Available immediately, no outage.",
                    "safe", emergency, fee),
            _choice("ration", "Ration Retailer Demand",
                    "Retail demand drops 30% while it lasts: less backlog, less revenue.",
                    "risky", ration),
            _choice("wait", "Wait It Out",
                    "No cost, but nothing ships from this supplier. Backlog risk is high.",
                    "danger", wait),
        ],
        "wait", timer=20,
    )


def _emergency_offer(ctx: EventContext, payload: dict) -> EventInstance | None:
    sup = payload.get("supplier")
    if sup not in ctx.network.graph.nodes or ctx.node(sup).active:
        return None  # the outage is already over
    targets = [s.id for s in ctx.network.successors(sup)]
    if not targets:
        return None
    cost = ctx.m(2000)
    remaining = payload.get("duration", 2)

    def accept(c: EventContext) -> str:
        c.charge(cost, sup)
        for t in targets:
            c.rush(t, max(30.0, c.avg_demand(t) * 3), 1)
        return f"The emergency shipment is on its way to {', '.join(c.name(t) for t in targets)}. -{usd(cost)}"

    return EventInstance(
        0, "emergency_offer", "disruption", "🔧", "Emergency Supplier Offer",
        f"A broker offers an express shipment while {ctx.name(sup)} is still offline "
        f"(about {remaining} more periods).",
        [
            _choice("accept", "Accept the Offer",
                    f"Cost: {usd(cost)}. Stock arrives next period.", "safe", accept, cost),
            _choice("decline", "Decline", "No cost. Keep waiting for the supplier.",
                    "risky", lambda c: "You declined the offer."),
        ],
        "decline", timer=15,
    )


def _quality_issue(ctx: EventContext, _: dict) -> EventInstance | None:
    inflight: dict[str, float] = {}
    for sh in ctx.engine.shipments.values():
        if sh.get("keep", 1.0) >= 1.0:
            inflight[sh["target"]] = inflight.get(sh["target"], 0.0) + sh["qty"]
    if not inflight:
        return None
    target = max(inflight, key=inflight.get)
    frac = ctx.rng.choice((0.2, 0.25, 0.3, 0.35))
    lost = inflight[target] * frac
    if lost < 5:
        return None
    name = ctx.name(target)

    def mark_lost(c: EventContext) -> float:
        total = 0.0
        for sh in c.engine.shipments.values():
            if sh["target"] == target and sh.get("keep", 1.0) >= 1.0:
                total += sh["qty"] * frac
                sh["keep"] = 1.0 - frac
        node = c.node(target)
        sku = node.skus[0] if node.skus else DEFAULT_SKU
        node.pipeline[sku] = max(0.0, node.pipeline.get(sku, 0.0) - total)
        return total

    cost = ctx.m(max(500, lost * ctx.price * 0.6))

    def recall(c: EventContext) -> str:
        units = mark_lost(c)
        c.charge(cost, target)
        c.rush(target, units, 1)
        return f"Recalled and replaced {round(units)} units; they arrive next period. -{usd(cost)}"

    def ship_anyway(c: EventContext) -> str:
        refund = lost * c.price * 0.6
        c.charge(refund, target)
        for r in c.retailers():
            c.add_disruption(DemandShock(r, c.period, 6, 0.9))
        return (
            f"Defective goods shipped. Refunds cost {usd(refund)} and customer trust "
            f"drops: demand is down 10% for 6 periods."
        )

    def discount(c: EventContext) -> str:
        units = mark_lost(c)
        salvage = units * c.price * 0.3
        c.credit(salvage, target)
        return f"Sold {round(units)} defective units at a discount for +{usd(salvage)}; the stock is gone."

    return EventInstance(
        0, "quality_issue", "operations", "🔧", "Quality Issue",
        f"A defective batch was found: about {round(frac * 100)}% of goods in transit to "
        f"{name} ({round(lost)} units) are unusable.",
        [
            _choice("recall", "Recall & Rush-Replace",
                    f"Cost: {usd(cost)}. Replacement units arrive next period.", "safe", recall, cost),
            _choice("discount", "Discount the Defective Goods",
                    "Recover some revenue, but the units never reach stock.", "risky", discount),
            _choice("ship", "Ship Anyway",
                    "Refunds and a demand dip for 6 periods.", "danger", ship_anyway),
        ],
        "ship",
    )


def _viral_trend(ctx: EventContext, _: dict) -> EventInstance | None:
    retailers = ctx.retailers()
    if not retailers:
        return None
    dur = 5
    cost = ctx.m(2500)

    def ramp(c: EventContext) -> str:
        c.charge(cost, retailers[0])
        for r in retailers:
            c.rush(r, c.avg_demand(r) * 4, 1)
            c.add_disruption(DemandShock(r, c.period, dur, 3.0))
        return f"Rush orders placed for every store: about 4 periods of extra stock arrives. -{usd(cost)}"

    def raise_prices(c: EventContext) -> str:
        c.tracker.price_multiplier *= 1.4
        c.later(dur, lambda cc: setattr(cc.tracker, "price_multiplier", cc.tracker.price_multiplier / 1.4))
        for r in retailers:
            c.add_disruption(DemandShock(r, c.period, dur, 2.0))
        return f"Prices up 40% for {dur} periods; demand peaks at 2x instead of 3x."

    def let_it_ride(c: EventContext) -> str:
        for r in retailers:
            c.add_disruption(DemandShock(r, c.period, dur, 3.0))
        return f"Demand hits 3x for {dur} periods and you're running with current stock."

    return EventInstance(
        0, "viral_trend", "demand", "📈", "Viral Product Trend",
        f"Your product just went viral. Demand at every retailer will spike 3x for {dur} periods, "
        f"starting next period.",
        [
            _choice("ramp", "Ramp Up Orders Immediately",
                    f"Cost: {usd(cost)}. Rush stock to every store ahead of the spike.",
                    "safe", ramp, cost),
            _choice("price", "Raise Prices 40%",
                    "Higher revenue per unit, but some demand walks away.", "risky", raise_prices),
            _choice("ride", "Let Stockouts Happen",
                    "No cost. Expect heavy backlog and lost sales.", "danger", let_it_ride),
        ],
        "ride", timer=15,
    )


def _competitor(ctx: EventContext, _: dict) -> EventInstance | None:
    retailers = ctx.retailers()
    if not retailers:
        return None
    cost = ctx.m(2000)

    def start(c: EventContext) -> None:
        for r in retailers:
            c.add_disruption(DemandShock(r, c.period, FOREVER, 0.7))

    def cut_prices(c: EventContext) -> str:
        start(c)
        c.tracker.price_multiplier *= 0.85
        for r in retailers:
            c.add_disruption(DemandShock(r, c.period, FOREVER, 1.2))
        return "Prices cut 15% permanently; you keep most of your customers (net demand -16%)."

    def marketing(c: EventContext) -> str:
        start(c)
        c.charge(cost, retailers[0])
        if c.rng.random() < 0.6:
            for r in retailers:
                c.add_disruption(DemandShock(r, c.period, FOREVER, 1 / 0.7))
            return f"The campaign worked: demand is fully recovered. -{usd(cost)}"
        for r in retailers:
            c.add_disruption(DemandShock(r, c.period, FOREVER, 0.85))
        return f"The campaign only partly worked: demand is down 16% overall. -{usd(cost)}"

    def passive(c: EventContext) -> str:
        start(c)
        return "Demand at every retailer is permanently 30% lower."

    choices = [
        _choice("cut", "Cut Prices to Compete",
                "Lower margin on every unit, but demand loss shrinks.", "risky", cut_prices),
        _choice("marketing", "Invest in Marketing",
                f"Cost: {usd(cost)}. 60% chance to win back all lost demand.", "risky", marketing, cost),
    ]
    if len(retailers) > 1:
        weakest = min(retailers, key=lambda r: ctx.avg_demand(r))

        def close(c: EventContext) -> str:
            start(c)
            node = c.node(weakest)
            sku = node.skus[0] if node.skus else DEFAULT_SKU
            sold = c.remove_stock(weakest, 1.0)
            c.credit(sold * c.price * 0.5, weakest)
            node.backlog[sku] = 0.0
            c.add_disruption(DemandShock(weakest, c.period, FOREVER, 0.0))
            c.engine.policies.pop(weakest, None)
            return (
                f"Closed {c.name(weakest)}: stock sold at half price and its holding and "
                f"backlog costs are gone, but so is its revenue."
            )

        choices.append(
            _choice("close", f"Close {ctx.name(weakest)}",
                    "Saves its operating costs; its demand and revenue are lost.", "risky", close)
        )
    else:
        choices.append(_choice("nothing", "Absorb the Loss", "No cost.", "danger", passive))
    return EventInstance(
        0, "competitor", "demand", "📈", "Competitor Enters Market",
        "A well-funded competitor has opened nearby. Demand at your retailers will fall "
        "30% permanently, starting next period.",
        choices, choices[-1].id,
    )


def _early_surge(ctx: EventContext, _: dict) -> EventInstance | None:
    retailers = ctx.retailers()
    if not retailers:
        return None
    mids = ctx.midstream()
    dc = mids[0] if mids else None
    dur = 4
    c1, c2 = ctx.m(1500), ctx.m(2200)

    def surge(c: EventContext) -> None:
        for r in retailers:
            c.add_disruption(DemandShock(r, c.period, dur, 1.8))

    def overtime(c: EventContext) -> str:
        surge(c)
        c.charge(c1, dc or retailers[0])
        total = sum(c.avg_demand(r) for r in retailers)
        c.rush(dc or retailers[0], total * 2, 1)
        return f"Overtime at {c.name(dc or retailers[0])} brings in extra stock next period. -{usd(c1)}"

    def direct(c: EventContext) -> str:
        surge(c)
        c.charge(c2, retailers[0])
        for r in retailers:
            c.rush(r, c.avg_demand(r) * 1.5, 1)
        return f"Express shipments go straight to every store next period. -{usd(c2)}"

    def accept(c: EventContext) -> str:
        surge(c)
        return f"Demand runs 80% above normal for {dur} periods; expect a lower fill rate."

    choices = []
    if dc:
        choices.append(_choice("overtime", "Emergency Overtime at DC",
                               f"Cost: {usd(c1)}. Extra stock enters the DC next period.", "safe", overtime, c1))
    choices += [
        _choice("direct", "Ship Direct to Retailers",
                f"Cost: {usd(c2)}. Skips the DC, higher cost.", "risky", direct, c2),
        _choice("accept", "Accept Lower Fill Rate", "No cost; backlog likely.", "danger", accept),
    ]
    return EventInstance(
        0, "early_surge", "demand", "📈", "Seasonal Surge Early",
        f"The holiday rush has arrived 4 periods early. Demand will run 80% above normal for "
        f"{dur} periods, starting next period.",
        choices, "accept", timer=15,
    )


def _interest_rate(ctx: EventContext, _: dict) -> EventInstance | None:
    def hike(c: EventContext) -> None:
        c.tracker.economy.holding_multiplier *= 1.2

    def liquidate(c: EventContext) -> str:
        hike(c)
        total = 0.0
        for n in c.network.nodes:
            if c.network.predecessors(n.id):
                units = c.remove_stock(n.id, 0.4)
                if units > 0:
                    c.credit(units * c.price * 0.5, n.id)
                    total += units * c.price * 0.5
        return f"Sold 40% of stock at half price for +{usd(total)}. Holding costs are still up 20%."

    def absorb(c: EventContext) -> str:
        hike(c)
        return "Holding costs are up 20% for the rest of the run."

    def jit(c: EventContext) -> str:
        hike(c)
        n = sum(c.scale_policy(node.id, 0.6) for node in c.network.nodes)
        return (
            f"Switched {n} node(s) toward just-in-time: order-up-to levels cut 40%. "
            f"Holding costs are up 20% but there is less stock to pay for."
        )

    return EventInstance(
        0, "interest_rate", "financial", "💰", "Interest Rate Hike",
        "The central bank raised rates. The cost of holding inventory rises 20% for the rest "
        "of the run.",
        [
            _choice("liquidate", "Liquidate Excess Inventory",
                    "Sell 40% of stock at 50% of the sale price. Cash now, stockout risk later.",
                    "risky", liquidate),
            _choice("jit", "Switch to Lean (JIT) Targets",
                    "Cut every order-up-to level by 40%. Less stock, more stockout risk.",
                    "risky", jit),
            _choice("absorb", "Absorb the Cost", "No action. Costs rise.", "safe", absorb),
        ],
        "jit",
    )


def _insurance(ctx: EventContext, _: dict) -> EventInstance | None:
    if ctx.tracker.insured:
        return None
    cost = ctx.m(2000)

    def buy(c: EventContext) -> str:
        c.charge(cost, c.roots()[0] if c.roots() else c.retailers()[0])
        c.tracker.insured = True
        return f"Insured. The cost of the next disruption response is covered. -{usd(cost)}"

    return EventInstance(
        0, "insurance", "financial", "💰", "Insurance Opportunity",
        f"An insurer offers cover for {usd(cost)}: it refunds whatever you spend responding to "
        f"the next supply disruption.",
        [
            _choice("buy", "Buy Insurance", f"Cost: {usd(cost)} now.", "safe", buy, cost),
            _choice("skip", "Skip", "No cost, no cover.", "risky", lambda c: "You skipped the insurance."),
        ],
        "skip",
    )


def _bulk_discount(ctx: EventContext, _: dict) -> EventInstance | None:
    roots = set(ctx.roots())
    targets = [e.destination for e in ctx.network.edges if e.source in roots]
    if not targets:
        return None
    target = targets[0]
    normal = ctx.avg_demand(target)
    if normal <= 0:
        return None
    unit = 0.4 * ctx.price
    name = ctx.name(target)

    def deal(multiple: float, discount: float):
        def run(c: EventContext) -> str:
            qty = normal * multiple
            rebate = qty * unit * discount
            c.credit(rebate, target)
            c.rush(target, qty, 1)
            return (
                f"Ordered {round(qty)} units for {name}: +{usd(rebate)} off list price now, "
                f"but expect higher holding costs while it sells through."
            )

        return run

    return EventInstance(
        0, "bulk_discount", "financial", "💰", "Bulk Discount Offer",
        f"Your supplier offers 30% off if you order 5x your normal quantity for {name} right now.",
        [
            _choice("full", "Take the Deal (5x, 30% off)",
                    "Biggest saving, but a huge inventory and holding-cost spike.", "danger", deal(5, 0.30)),
            _choice("half", "Negotiate (2.5x, 15% off)",
                    "A smaller saving with a manageable stock increase.", "risky", deal(2.5, 0.15)),
            _choice("decline", "Decline", "No change.", "safe", lambda c: "You declined the offer."),
        ],
        "full",
    )


def _warehouse_fire(ctx: EventContext, _: dict) -> EventInstance | None:
    mids = [n for n in ctx.midstream() if ctx.on_hand(n) > 10]
    if not mids:
        return None
    target = mids[0]
    name = ctx.name(target)
    lost = ctx.on_hand(target) * 0.5
    cost = ctx.m(3000)
    others = [n for n in ctx.midstream() if n != target and ctx.on_hand(n) > 10]
    help_cost = ctx.m(500)

    def burn(c: EventContext) -> float:
        return c.remove_stock(target, 0.5)

    def restock(c: EventContext) -> str:
        units = burn(c)
        c.charge(cost, target)
        c.rush(target, units, 1)
        return f"Express restock of {round(units)} units arrives next period. -{usd(cost)}"

    def redistribute(c: EventContext) -> str:
        units = burn(c)
        moved = 0.0
        for o in others:
            moved += c.remove_stock(o, 0.3)
        if not others:
            moved = units * 0.6  # nothing nearby: transfer from upstream stock instead
        c.charge(help_cost, target)
        c.rush(target, moved, 2)
        return f"{round(moved)} units are on their way from other stock (2 periods). -{usd(help_cost)}"

    def accept(c: EventContext) -> str:
        units = burn(c)
        return f"{round(units)} units of inventory at {name} are lost."

    return EventInstance(
        0, "warehouse_fire", "operations", "🔧", "Warehouse Fire",
        f"A fire at {name} destroyed about half of its inventory ({round(lost)} units).",
        [
            _choice("restock", "Emergency Restock",
                    f"Cost: {usd(cost)}. Express delivery of the lost units next period.",
                    "safe", restock, cost),
            _choice("redistribute", "Redistribute Stock",
                    f"Cost: {usd(help_cost)}. Takes 2 periods and draws down other stock.",
                    "risky", redistribute, help_cost),
            _choice("accept", "Accept the Loss", "No cost; run on what is left.", "danger", accept),
        ],
        "accept", timer=20,
    )


def _new_technology(ctx: EventContext, _: dict) -> EventInstance | None:
    edges = [e for e in ctx.network.edges if (e.base_lead_time if not callable(e.base_lead_time) else 0) >= 2]
    if not edges:
        return None
    edges.sort(key=lambda e: -e.base_lead_time)
    cost = ctx.m(3000)
    choices = []
    for i, e in enumerate(edges[:2]):
        old = e.base_lead_time
        new = max(1.0, old * 0.5)

        def invest(c: EventContext, e=e, old=old, new=new) -> str:
            c.charge(cost, e.source)
            e.base_lead_time = new
            e.lead_time = new
            return (
                f"New tech installed on {c.name(e.source)} → {c.name(e.destination)}: lead time "
                f"{old:g} → {new:g} permanently. -{usd(cost)}"
            )

        choices.append(
            _choice(f"edge{i}", f"Upgrade {ctx.name(e.source)} → {ctx.name(e.destination)}",
                    f"Cost: {usd(cost)}. Lead time {old:g} → {new:g} periods, permanently.",
                    "safe", invest, cost)
        )
    choices.append(_choice("pass", "Pass", "Keep your money.", "risky", lambda c: "You passed on the new technology."))
    return EventInstance(
        0, "new_technology", "operations", "🔧", "New Technology Available",
        f"A logistics vendor offers technology that halves the lead time on one route "
        f"for {usd(cost)}.",
        choices, "pass",
    )


def _labor_shortage(ctx: EventContext, _: dict) -> EventInstance | None:
    mids = ctx.midstream()
    if not mids:
        return None
    target = mids[0]
    node = ctx.node(target)
    name = ctx.name(target)
    dur = 5
    base_cap = node.base_capacity
    if base_cap is None or math.isinf(base_cap):
        # Unlimited normally: treat 130% of recent throughput as its nominal capacity.
        base_cap = max(20.0, ctx.avg_demand(target) * 1.3)
    temps = ctx.m(1000)

    def shortage(c: EventContext, factor: float = 0.6) -> None:
        c.add_disruption(CapacityCap(target, c.period, dur, base_cap * factor))

    def hire(c: EventContext) -> str:
        c.charge(temps, target)
        for k in range(1, dur):
            c.later(k, lambda cc: (cc.charge(temps, target), None)[1])
        return f"Temps hired for {dur} periods: {usd(temps)} per period. Capacity is unaffected."

    def overtime(c: EventContext) -> str:
        shortage(c, 0.85)

        def risk(cc: EventContext) -> str | None:
            if cc.rng.random() < 0.2:
                cc.follow_up("quality_issue", 0, {})
            return None

        c.later(1, risk)
        return f"Overtime keeps capacity at 85% for {dur} periods, with a 20% chance of a quality problem next period."

    def reduce_orders(c: EventContext) -> str:
        shortage(c)
        c.scale_policy(target, 0.7)
        c.later(dur, lambda cc: (cc.scale_policy(target, 1 / 0.7), None)[1])
        return f"{name} capacity is down 40% for {dur} periods; its order levels are cut 30% to match."

    return EventInstance(
        0, "labor_shortage", "operations", "🔧", "Labor Shortage",
        f"A labor shortage cuts {name}'s capacity by 40% for {dur} periods, starting next period.",
        [
            _choice("temps", "Hire Temps",
                    f"Cost: {usd(temps)} per period for {dur} periods. Capacity is unaffected.",
                    "safe", hire, temps * dur),
            _choice("overtime", "Overtime",
                    "Free, but capacity stays 15% down and there's a 20% chance of a quality issue.",
                    "risky", overtime),
            _choice("reduce", "Reduce Orders",
                    "Free: shrink order levels 30% to avoid pile-ups while capacity is down.",
                    "danger", reduce_orders),
        ],
        "reduce", timer=15,
    )


EVENTS: dict[str, EventDef] = {
    d.id: d
    for d in [
        EventDef("port_strike", "disruption", 1.0, 2, _port_strike),
        EventDef("supplier_shutdown", "disruption", 0.8, 3, _supplier_shutdown, min_progress=0.15),
        EventDef("quality_issue", "operations", 0.9, 2, _quality_issue),
        EventDef("viral_trend", "demand", 0.9, 1, _viral_trend),
        EventDef("competitor", "demand", 0.6, 2, _competitor, min_progress=0.2),
        EventDef("early_surge", "demand", 0.8, 2, _early_surge),
        EventDef("interest_rate", "financial", 0.7, 1, _interest_rate),
        EventDef("insurance", "financial", 0.7, 1, _insurance, min_progress=0.0),
        EventDef("bulk_discount", "financial", 0.7, 1, _bulk_discount),
        EventDef("warehouse_fire", "operations", 0.6, 3, _warehouse_fire, min_progress=0.2),
        EventDef("new_technology", "operations", 0.7, 1, _new_technology),
        EventDef("labor_shortage", "operations", 0.8, 2, _labor_shortage),
        EventDef("emergency_offer", "disruption", 0.0, 1, _emergency_offer, random=False),
    ]
}

# Events that always happen at a given period of a preset, so every run has a story beat.
PRESET_SCRIPT: dict[str, dict[int, str]] = {
    "retail_replenishment": {30: "viral_trend"},
    "pharma_cold_chain": {25: "warehouse_fire"},
    "manufacturing_jit": {20: "labor_shortage"},
    "global_commodity_flow": {15: "port_strike"},
}


class EventDirector:
    """Decides when an event fires, and records what happened."""

    def __init__(
        self,
        seed: int | None,
        enabled: bool = True,
        chance: tuple[float, float] | None = None,
        script: dict[int, str] | None = None,
        pool: set[str] | None = None,
    ) -> None:
        self.rng = random.Random(1337 + (seed or 0))
        self.enabled = enabled
        # Campaign levels override how often events fire, which are scripted,
        # and which random events are allowed.
        self.chance = chance or (BASE_CHANCE, LATE_CHANCE)
        self.script = script
        self.pool = pool
        self.next_uid = 1
        self.last_event_period = -MIN_GAP
        self.last_by_id: dict[str, int] = {}
        self.log: list[dict[str, Any]] = []

    def maybe_fire(self, bridge: Any) -> EventInstance | None:
        """Called after a period completes; returns an event to present before the next one."""
        if not self.enabled:
            return None
        done = bridge.period
        total = bridge.engine.n_periods
        if done >= total or done < MIN_FIRST_PERIOD or done - self.last_event_period < MIN_GAP:
            return None

        ctx = EventContext(bridge, self.rng)
        progress = done / total

        # Cascades and scripted beats take priority over random draws.
        due = [q for q in bridge.queued_events if q[0] <= done]
        for q in sorted(due, key=lambda q: q[0]):
            bridge.queued_events.remove(q)
            instance = self._build(ctx, q[1], q[2], done)
            if instance:
                return instance
        script = self.script if self.script is not None else PRESET_SCRIPT.get(bridge.preset_id or "", {})
        scripted = script.get(done)
        if scripted:
            instance = self._build(ctx, scripted, {}, done)
            if instance:
                return instance

        low, high = self.chance
        chance = low + (high - low) * progress
        if chance <= 0 or self.rng.random() >= chance:
            return None
        pool = [
            d for d in EVENTS.values()
            if d.random
            and (self.pool is None or d.id in self.pool)
            and progress >= d.min_progress
            and done - self.last_by_id.get(d.id, -999) >= SAME_EVENT_COOLDOWN
        ]
        # Severe events get more likely as the run goes on.
        weights = [d.weight * (1 + progress * (d.severity - 1)) for d in pool]
        while pool:
            pick = self.rng.choices(range(len(pool)), weights=weights)[0]
            instance = self._build(ctx, pool[pick].id, {}, done)
            if instance:
                return instance
            pool.pop(pick)
            weights.pop(pick)
        return None

    def _build(self, ctx: EventContext, def_id: str, payload: dict, done: int) -> EventInstance | None:
        definition = EVENTS.get(def_id)
        if definition is None:
            return None
        instance = definition.builder(ctx, payload)
        if instance is None:
            return None
        instance.uid = self.next_uid
        self.next_uid += 1
        instance.period = done
        self.last_event_period = done
        self.last_by_id[def_id] = done
        return instance
