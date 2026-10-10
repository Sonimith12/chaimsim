"""The 10-level campaign: scenario, economy, events and objectives for each level.

A level is just a network spec plus rules layered on the same engine, economy and
event systems the sandbox uses. Objectives come in three tiers:

* ``required`` - meet all of them to pass the level (1 star)
* ``goal``     - meet these as well for 2 stars
* ``bonus``    - meet these too for 3 stars
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from economy import EconomySpec
from network_spec import DemandSpec, EdgeSpec, NetworkSpec, NodeSpec, PolicySpec

ACTS = {1: "Learning the Ropes", 2: "Managing Complexity", 3: "Expert Mode", 4: "The Final Challenge"}


def _demand(kind: str = "stationary", **kw: Any) -> DemandSpec:
    return DemandSpec(type=kind, **kw)  # type: ignore[arg-type]


def _node(
    id_: str,
    type_: str,
    *,
    inv: float,
    hold: float = 1.0,
    back: float = 0.0,
    cap: float | None = None,
    demand: DemandSpec | None = None,
    policy: PolicySpec | None = None,
    shelf: int | None = None,
    echelon: int = 0,
    slot: int = 0,
    size: int = 1,
    x: float | None = None,
    z: float | None = None,
    forecast: float | None = None,
) -> NodeSpec:
    return NodeSpec(
        id=id_, name=id_.replace("_", " "), type=type_,  # type: ignore[arg-type]
        initial_inventory=inv, holding_cost=hold, backlog_cost=back, capacity=cap,
        demand=demand, policy=policy, shelf_life=shelf, echelon=echelon, slot=slot,
        echelon_size=size, x=x, z=z, forecast=forecast,
    )


def _pol(kind: str, **params: float) -> PolicySpec:
    return PolicySpec(type=kind, params=params)  # type: ignore[arg-type]


def _edge(a: str, b: str, lt: float, mode: str = "truck") -> EdgeSpec:
    return EdgeSpec(source=a, target=b, lead_time=lt, mode=mode)


@dataclass
class Level:
    id: int
    act: int
    name: str
    blurb: str
    description: str
    difficulty: int  # 1..5
    n_periods: int
    seed: int
    objectives: list[dict[str, Any]]
    completion: str
    build: Callable[[Any], NetworkSpec]
    special_rules: list[str] = field(default_factory=list)
    hints: bool = False
    edit_mode: bool = False
    # Event configuration (see events.EventDirector).
    events: bool = True
    event_chance: tuple[float, float] | None = None
    event_script: dict[int, str] | None = None
    event_pool: list[str] | None = None
    # Level 10 only: multipliers applied to retailer demand when the run starts, so
    # the forecast the player planned against is only approximately right.
    hidden_demand: dict[str, float] = field(default_factory=dict)

    def meta(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "act": self.act,
            "act_name": ACTS[self.act],
            "name": self.name,
            "blurb": self.blurb,
            "description": self.description,
            "difficulty": self.difficulty,
            "n_periods": self.n_periods,
            "objectives": [{"label": o["label"], "tier": o["tier"]} for o in self.objectives],
            "special_rules": self.special_rules,
            "completion": self.completion,
            "edit_mode": self.edit_mode,
            "hints": self.hints,
        }


def _obj(kind: str, tier: str, label: str, **kw: Any) -> dict[str, Any]:
    return {"kind": kind, "tier": tier, "label": label, **kw}


# --- objective evaluation -------------------------------------------------------------


def _rel_status(actual: float, target: float, at_least: bool, margin: float) -> str:
    if at_least:
        if actual >= target:
            return "ok"
        return "borderline" if actual >= target - margin else "failing"
    if actual <= target:
        return "ok"
    return "borderline" if actual <= target + margin else "failing"


def evaluate_objectives(level: Level, c: dict[str, Any]) -> list[dict[str, Any]]:
    """Evaluate a level's objectives against live run numbers ``c``."""
    out: list[dict[str, Any]] = []
    for i, o in enumerate(level.objectives):
        kind = o["kind"]
        t = o.get("target", 0.0)
        unit, comparison, actual, target, status = "percent", "at_least", 0.0, t, "ok"
        if kind == "no_bankruptcy":
            unit, comparison, actual, target = "count", "at_most", float(c["bankrupt"]), 0.0
            met = not c["bankrupt"]
            status = "ok" if met else "failing"
        elif kind in ("fill", "service", "margin"):
            actual = {"fill": c["fill"], "service": c["service"], "margin": c["margin"]}[kind]
            met = actual >= t
            started = c["completed"] > 0 and (kind != "margin" or c["revenue"] > 0)
            status = _rel_status(actual, t, True, 0.05) if started else "ok"
        elif kind == "service_each":
            actual = min(c["sink_service"].values()) if c["sink_service"] else 1.0
            met = actual >= t
            status = _rel_status(actual, t, True, 0.05) if c["completed"] > 0 else "ok"
        elif kind in ("cash_positive", "cash_at_least"):
            unit, actual = "currency", c["cash"]
            target = 0.0 if kind == "cash_positive" else t
            met = actual > target if kind == "cash_positive" else actual >= target
            status = _rel_status(actual, target, True, max(500.0, abs(target) * 0.1))
        elif kind == "waste_under":
            unit, comparison, actual = "units", "at_most", c["waste"]
            target = max(25.0, c["max_waste"] * o.get("factor", 1.0))
            met = actual <= target
            status = _rel_status(actual, target, False, max(2.0, target * 0.15))
        elif kind == "stockouts_at_most":
            unit, comparison, actual = "count", "at_most", float(c["stockouts"])
            met = actual <= t
            status = _rel_status(actual, t, False, 1.0)
        elif kind == "no_stockouts_in":
            unit, comparison, target = "count", "at_most", 0.0
            actual = float(sum(1 for p in c["stockout_log"] if o["start"] <= p <= o["end"]))
            met = actual == 0
            status = "ok" if met else "failing"
        elif kind == "cost_under_baseline":
            unit, comparison = "currency", "at_most"
            target = round(c["baseline_cost"] * o["factor"])
            actual = c["total_cost"]
            met = actual <= target
            # Cost accrues over the run, so compare against the pro-rated budget.
            pace = target * (c["completed"] / c["n_periods"]) if c["n_periods"] else target
            status = _rel_status(actual, pace, False, pace * 0.1) if c["completed"] else "ok"
        elif kind == "score_ratio":
            actual = c["score"] / c["score_max"] if c["score_max"] else 0.0
            met = actual >= t
            status = "ok" if met or c["completed"] < c["n_periods"] * 0.5 else "borderline"
        else:  # pragma: no cover
            raise ValueError(f"unknown objective kind: {kind}")
        out.append(
            {
                "id": f"{o['tier'][:3]}{i}",
                "label": o["label"],
                "title_only": True,
                "tier": o["tier"],
                "unit": unit,
                "comparison": comparison,
                "target": target,
                "actual": actual,
                "met": bool(met),
                "status": status,
                "bonus": o["tier"] == "bonus",
            }
        )
    return out


def campaign_result(level: Level, objectives: list[dict[str, Any]], finished: bool, bankrupt: bool) -> dict[str, Any]:
    by_tier = {t: [o for o in objectives if o["tier"] == t] for t in ("required", "goal", "bonus")}
    met = {t: sum(o["met"] for o in v) for t, v in by_tier.items()}
    passed = finished and not bankrupt and met["required"] == len(by_tier["required"])
    stars = 0
    if passed:
        stars = 1
        if met["goal"] == len(by_tier["goal"]):
            stars = 2
            if met["bonus"] == len(by_tier["bonus"]):
                stars = 3
    return {
        "level": level.id,
        "passed": passed,
        "stars": stars,
        "required_met": met["required"],
        "required_total": len(by_tier["required"]),
        "goals_met": met["goal"],
        "goals_total": len(by_tier["goal"]),
        "bonus_met": met["bonus"],
        "bonus_total": len(by_tier["bonus"]),
    }


# --- level builders -------------------------------------------------------------------


def _preset(bridge: Any, name: str) -> NetworkSpec:
    return NetworkSpec(**bridge.preset_spec(name))


def _finish(spec: NetworkSpec, level: Level, economy: EconomySpec) -> NetworkSpec:
    spec.name = level.name
    spec.description = level.description
    spec.n_periods = level.n_periods
    spec.seed = level.seed
    spec.economy = economy
    spec.campaign_level = level.id
    spec.events_enabled = level.events
    spec.scenario_id = None
    # The level's own starting network is already built: it costs nothing to keep.
    spec.free_nodes = [n.id for n in spec.nodes]
    spec.free_edges = [(e.source, e.target) for e in spec.edges]
    return spec


def _l1(bridge: Any) -> NetworkSpec:
    nodes = [
        _node("Supplier", "Supplier", inv=5000, hold=0, echelon=0),
        # Starts on an (R, Q) policy whose order quantity is far below demand.
        _node("Shop", "Retailer", inv=60, hold=1, back=1.5, echelon=1,
              demand=_demand("stationary", mean=30, std=0, distribution="normal"),
              policy=_pol("r_q", R=25, Q=12)),
    ]
    spec = NetworkSpec(nodes=nodes, edges=[_edge("Supplier", "Shop", 2)], inventory_scale=10)
    return _finish(spec, LEVELS[0], EconomySpec(
        starting_capital=15_000, revenue_per_unit=8, ordering_cost=10,
        transport_cost_per_lead_time=5, policy_change_cost=0))


def _l2(bridge: Any) -> NetworkSpec:
    d = lambda m: _demand("stationary", mean=m, std=6, distribution="normal")  # noqa: E731
    nodes = [
        _node("Supplier", "Supplier", inv=8000, hold=0, echelon=0),
        _node("DC", "DistributionCenter", inv=220, hold=0.5, echelon=1,
              policy=_pol("order_up_to", S=330)),
        _node("Store_A", "Retailer", inv=70, hold=1, back=6, echelon=2, slot=0, size=2,
              demand=d(30), policy=_pol("order_up_to", S=95)),
        _node("Store_B", "Retailer", inv=50, hold=1, back=6, echelon=2, slot=1, size=2,
              demand=d(22), policy=_pol("order_up_to", S=60)),
    ]
    edges = [_edge("Supplier", "DC", 2, "rail"), _edge("DC", "Store_A", 1), _edge("DC", "Store_B", 1)]
    return _finish(NetworkSpec(nodes=nodes, edges=edges, inventory_scale=15), LEVELS[1],
                   EconomySpec(starting_capital=22_000, revenue_per_unit=7, policy_change_cost=150))


def _l3(bridge: Any) -> NetworkSpec:
    sd = lambda base, amp: _demand("seasonal", base=base, amplitude=amp, period_length=13, noise_std=3)  # noqa: E731
    nodes = [
        _node("Supplier", "Supplier", inv=10000, hold=0, echelon=0),
        _node("DC", "DistributionCenter", inv=260, hold=0.5, echelon=1,
              policy=_pol("order_up_to", S=380)),
        _node("Store_A", "Retailer", inv=80, hold=1, back=6, echelon=2, slot=0, size=2,
              demand=sd(32, 12), policy=_pol("order_up_to", S=100)),
        _node("Store_B", "Retailer", inv=60, hold=1, back=6, echelon=2, slot=1, size=2,
              demand=sd(24, 9), policy=_pol("order_up_to", S=80)),
    ]
    edges = [_edge("Supplier", "DC", 2, "rail"), _edge("DC", "Store_A", 1), _edge("DC", "Store_B", 1)]
    return _finish(NetworkSpec(nodes=nodes, edges=edges, inventory_scale=15), LEVELS[2],
                   EconomySpec(starting_capital=20_000, revenue_per_unit=7, policy_change_cost=250))


def _l4(bridge: Any) -> NetworkSpec:
    d = lambda m: _demand("stationary", mean=m, std=5, distribution="normal")  # noqa: E731
    nodes = [
        _node("Supplier_Asia", "Supplier", inv=9000, hold=0, echelon=0, slot=0, size=2),
        _node("Supplier_Local", "Supplier", inv=6000, hold=0, echelon=0, slot=1, size=2),
        _node("DC", "DistributionCenter", inv=300, hold=0.5, echelon=1,
              policy=_pol("order_up_to", S=420)),
        _node("Store_1", "Retailer", inv=70, hold=1, back=6, echelon=2, slot=0, size=3,
              demand=d(28), policy=_pol("order_up_to", S=95)),
        _node("Store_2", "Retailer", inv=60, hold=1, back=6, echelon=2, slot=1, size=3,
              demand=d(24), policy=_pol("order_up_to", S=85)),
        _node("Store_3", "Retailer", inv=50, hold=1, back=6, echelon=2, slot=2, size=3,
              demand=d(18), policy=_pol("order_up_to", S=65)),
    ]
    edges = [
        _edge("Supplier_Asia", "DC", 4, "ship"), _edge("Supplier_Local", "DC", 2, "truck"),
        _edge("DC", "Store_1", 1), _edge("DC", "Store_2", 1), _edge("DC", "Store_3", 1),
    ]
    return _finish(NetworkSpec(nodes=nodes, edges=edges, inventory_scale=15), LEVELS[3],
                   EconomySpec(starting_capital=14_000, revenue_per_unit=6, policy_change_cost=300,
                               holding_multiplier=1.2))


def _l5(bridge: Any) -> NetworkSpec:
    spec = _preset(bridge, "retail_replenishment")
    return _finish(spec, LEVELS[4], EconomySpec(
        starting_capital=2_500, revenue_per_unit=5, holding_multiplier=1.6,
        backlog_multiplier=1.2, ordering_cost=30, policy_change_cost=300))


def _l6(bridge: Any) -> NetworkSpec:
    spec = _preset(bridge, "global_commodity_flow")
    return _finish(spec, LEVELS[5], EconomySpec(
        starting_capital=90_000, revenue_per_unit=8, policy_change_cost=800))


def _l7(bridge: Any) -> NetworkSpec:
    spec = _preset(bridge, "pharma_cold_chain")
    # Staggered opening stock, so the whole opening batch doesn't expire in one period.
    for n in spec.nodes:
        if n.id == "Hospital":
            n.initial_inventory = 200
    return _finish(spec, LEVELS[6], EconomySpec(
        starting_capital=9_000, revenue_per_unit=40, policy_change_cost=1_000))


def _l8(bridge: Any) -> NetworkSpec:
    sd = lambda b, a: _demand("seasonal", base=b, amplitude=a, period_length=12, noise_std=4)  # noqa: E731
    st = lambda m: _demand("stationary", mean=m, std=6, distribution="normal")  # noqa: E731
    nodes = [
        _node("Supplier_A", "Supplier", inv=20000, hold=0, echelon=0, slot=0, size=2),
        _node("Supplier_B", "Supplier", inv=20000, hold=0, echelon=0, slot=1, size=2),
        _node("Hub_North", "DistributionCenter", inv=420, hold=0.5, cap=300, echelon=1, slot=0, size=2,
              policy=_pol("order_up_to", S=620)),
        _node("Hub_South", "DistributionCenter", inv=420, hold=0.5, cap=300, echelon=1, slot=1, size=2,
              policy=_pol("order_up_to", S=620)),
        _node("Store_N1", "Retailer", inv=80, hold=1, back=7, echelon=2, slot=0, size=4,
              demand=sd(34, 10), policy=_pol("order_up_to", S=115)),
        _node("Store_N2", "Retailer", inv=60, hold=1, back=7, echelon=2, slot=1, size=4,
              demand=st(26), policy=_pol("order_up_to", S=90)),
        _node("Store_S1", "Retailer", inv=70, hold=1, back=7, echelon=2, slot=2, size=4,
              demand=sd(30, 9), policy=_pol("order_up_to", S=105)),
        _node("Store_S2", "Retailer", inv=55, hold=1, back=7, echelon=2, slot=3, size=4,
              demand=st(22), policy=_pol("order_up_to", S=80)),
    ]
    edges = [
        _edge("Supplier_A", "Hub_North", 3, "rail"), _edge("Supplier_A", "Hub_South", 4, "rail"),
        _edge("Supplier_B", "Hub_South", 3, "rail"), _edge("Supplier_B", "Hub_North", 5, "ship"),
        _edge("Hub_North", "Store_N1", 1), _edge("Hub_North", "Store_N2", 2),
        _edge("Hub_South", "Store_S1", 1), _edge("Hub_South", "Store_S2", 2),
    ]
    return _finish(NetworkSpec(nodes=nodes, edges=edges, inventory_scale=20), LEVELS[7],
                   EconomySpec(starting_capital=26_000, revenue_per_unit=7, policy_change_cost=600,
                               holding_multiplier=1.2))


def _l9(bridge: Any) -> NetworkSpec:
    spec = _preset(bridge, "manufacturing_jit")
    return _finish(spec, LEVELS[8], EconomySpec(
        starting_capital=9_000, revenue_per_unit=20, policy_change_cost=400, holding_multiplier=1.3))


# Level 10 market forecasts (what the player sees) and the hidden actual deviation.
_L10_MARKETS = [
    ("Market_W1", -16, -4, 38, 1.18),
    ("Market_W2", -16, 4, 30, 0.88),
    ("Market_E1", 16, -4, 44, 1.10),
    ("Market_E2", 16, 4, 34, 1.22),
]


def _l10(bridge: Any) -> NetworkSpec:
    nodes = [
        _node(name, "Retailer", inv=120, hold=1, back=8, x=x, z=z, forecast=fc,
              demand=_demand("stationary", mean=fc, std=7, distribution="normal"),
              policy=_pol("order_up_to", S=fc * 3.2))
        for name, x, z, fc, _ in _L10_MARKETS
    ]
    spec = NetworkSpec(nodes=nodes, edges=[], inventory_scale=20)
    spec = _finish(spec, LEVELS[9], EconomySpec(
        starting_capital=70_000, revenue_per_unit=6, policy_change_cost=700,
        build_cost_supplier=6_000, build_cost_dc=3_500, build_cost_retailer=2_000))
    spec.free_nodes = [n.id for n in nodes]
    spec.locked_nodes = [n.id for n in nodes]
    return spec


def _obj_set(*items: dict[str, Any]) -> list[dict[str, Any]]:
    return list(items)


LEVELS: list[Level] = [
    Level(
        1, 1, "First Day on the Job",
        "Your uncle's corner shop keeps running out of stock, and he's handed you the order book. "
        "One supplier, one shop, steady customers. How hard can it be?",
        "One supplier feeding one shop. The shop's ordering rule is badly tuned.",
        1, 20, 101,
        _obj_set(
            _obj("no_bankruptcy", "required", "Don't go bankrupt"),
            _obj("fill", "required", "Achieve an 80% fill rate", target=0.80),
            _obj("margin", "goal", "Achieve a 20% profit margin", target=0.20),
            _obj("fill", "bonus", "Achieve a 95% fill rate", target=0.95),
        ),
        "The shop hasn't run dry in weeks. Your uncle is beaming - and he's already mentioned a second location.",
        _l1, ["Policy changes are free in this level."], hints=True, events=False,
    ),
    Level(
        2, 1, "Growing Pains",
        "The second shop opened. Now there's a distribution centre in the middle and two stores "
        "competing for the same stock.",
        "One supplier, one DC and two stores with variable demand. Balance stock between them.",
        1, 26, 202,
        _obj_set(
            _obj("service", "required", "Keep an 85% service level", target=0.85),
            _obj("cash_positive", "required", "End with positive cash"),
            _obj("margin", "goal", "Achieve a 15% profit margin", target=0.15),
            _obj("service", "bonus", "Keep a 95% service level", target=0.95),
        ),
        "Two stores humming along. Word is spreading - and holiday season is around the corner.",
        _l2, [], hints=True, events=False,
    ),
    Level(
        3, 1, "Seasonal Swings",
        "Demand rises and falls with the seasons, and the head office just warned that an early "
        "holiday surge is coming. Timing is everything.",
        "Seasonal demand with one scripted demand spike. Prepare before it lands.",
        2, 39, 303,
        _obj_set(
            _obj("fill", "required", "Achieve a 90% fill rate", target=0.90),
            _obj("no_stockouts_in", "required", "No stockouts during the demand spike", start=20, end=26),
            _obj("margin", "goal", "Achieve a 15% profit margin", target=0.15),
            _obj("stockouts_at_most", "bonus", "Zero stockouts all season", target=0),
        ),
        "You rode out the surge. The board asks if you're ready for 'real' supply chains next.",
        _l3, ["One scripted demand surge hits mid-season."], hints=False,
        events=True, event_chance=(0.0, 0.0), event_script={20: "early_surge"},
    ),
    Level(
        4, 2, "Supply Shock",
        "Your cheap overseas supplier is the backbone of your margins, until the port strike. "
        "A local supplier exists, at a price.",
        "Two suppliers (one slow and cheap, one local) feed a DC and three stores. A port strike is coming.",
        3, 30, 404,
        _obj_set(
            _obj("no_bankruptcy", "required", "Survive the disruption without going bankrupt"),
            _obj("service", "required", "Keep an 85% service level", target=0.85),
            _obj("margin", "goal", "Achieve a 10% profit margin", target=0.10),
            _obj("stockouts_at_most", "bonus", "At most 3 stockouts", target=3),
        ),
        "You diversified just in time. The stores noticed the empty trucks, but never the empty shelves.",
        _l4, ["Margins are tighter than before.", "A port strike is scripted for period 12."],
        events=True, event_chance=(0.0, 0.0), event_script={12: "port_strike"},
    ),
    Level(
        5, 2, "The Budget Squeeze",
        "Finance froze the budget. Holding costs are up, backlog penalties sting, and "
        "you have almost no cash cushion. Every dollar must earn its place.",
        "The retail network on a shoestring: tight starting cash, higher costs, random events.",
        3, 40, 505,
        _obj_set(
            _obj("cash_at_least", "required", "End with $5,000 or more in cash", target=5000),
            _obj("fill", "required", "Achieve an 85% fill rate", target=0.85),
            _obj("margin", "goal", "Achieve a 15% profit margin", target=0.15),
            _obj("service", "bonus", "Keep a 90% service level", target=0.90),
        ),
        "Lean and profitable. The CFO sent a thank-you card; it's the first one in company history.",
        _l5, ["Starting cash is very low.", "Holding costs are 60% higher.", "Random events are on."],
        events=True, event_chance=(0.14, 0.2),
        event_pool=["quality_issue", "viral_trend", "interest_rate", "bulk_discount", "early_surge", "insurance"],
    ),
    Level(
        6, 2, "Going Global",
        "Two continents, two suppliers, three-week ocean lead times. Disruptions elsewhere in "
        "the world are now your problem.",
        "The global commodity network: long lead times, multiple built-in disruptions.",
        4, 50, 606,
        _obj_set(
            _obj("service_each", "required", "Keep every market above 80% service level", target=0.80),
            _obj("margin", "required", "Achieve a positive profit margin", target=0.0),
            _obj("margin", "goal", "Achieve a 20% profit margin", target=0.20),
            _obj("service_each", "bonus", "Keep every market above 95% service level", target=0.95),
        ),
        "From a corner shop to a continental network. The old man asks, quietly, whether you remember the first shop.",
        _l6, ["Lead times are 2-3 weeks on the ocean legs.", "Several disruptions are built in."],
        events=True, event_chance=(0.06, 0.1),
        event_pool=["port_strike", "supplier_shutdown", "quality_issue", "interest_rate", "bulk_discount"],
    ),
    Level(
        7, 3, "Cold Chain Crisis",
        "Vaccines don't wait. Regulators demand 99% availability, product spoils on the shelf, "
        "and the company can afford exactly one mistake.",
        "A perishable pharma cold chain with a regulatory service level and almost no cash buffer.",
        4, 60, 707,
        _obj_set(
            _obj("service", "required", "Keep a 99% service level (regulatory)", target=0.99),
            _obj("waste_under", "required", "Keep spoilage under the allowed threshold", factor=2.0),
            _obj("margin", "goal", "Achieve a 25% profit margin", target=0.25),
            _obj("stockouts_at_most", "bonus", "Zero stockouts", target=0),
        ),
        "No missed deliveries, no spoilage scandals. The regulator wants to use your chain as a case study.",
        _l7, ["Service level is regulated at 99%.", "Cash buffer is thin: you can afford one mistake.",
              "A warehouse fire is scripted for period 30."],
        events=True, event_chance=(0.0, 0.0), event_script={30: "warehouse_fire"},
    ),
    Level(
        8, 3, "The Perfect Storm",
        "A supplier shutdown, a port strike, a fire and a labour shortage - and they all land "
        "in the same quarter. Nobody could plan for this. You'll have to improvise.",
        "A two-supplier, two-hub, four-store network under a scripted chain of crises.",
        5, 50, 808,
        _obj_set(
            _obj("no_bankruptcy", "required", "Don't go bankrupt"),
            _obj("service", "required", "Keep any positive service level", target=0.01),
            _obj("service", "goal", "Keep an 80% service level", target=0.80),
            _obj("margin", "bonus", "Achieve a 10% profit margin", target=0.10),
        ),
        "Standing, battered, still in business. The industry magazine called it 'the best crisis response of the decade'.",
        _l8, ["At least four events are guaranteed.", "Some events cascade into follow-ups."],
        events=True, event_chance=(0.06, 0.12),
        event_script={10: "supplier_shutdown", 22: "port_strike", 32: "warehouse_fire", 42: "labor_shortage"},
    ),
    Level(
        9, 3, "Lean Machine",
        "The new CEO wants 'zero waste, zero buffer, zero excuses'. A just-in-time plant has very "
        "little slack, and events will test whether your buffers are right.",
        "A just-in-time manufacturing line on a minimal budget. Efficiency counts.",
        5, 60, 909,
        _obj_set(
            _obj("service", "required", "Keep a 95% service level", target=0.95),
            _obj("cost_under_baseline", "goal", "Keep total cost within 5% of the benchmark", factor=1.05),
            _obj("cost_under_baseline", "bonus", "Beat the benchmark cost by 10%", factor=0.90),
        ),
        "Not a pallet to spare and not a customer disappointed. Lean isn't about having less - it's about knowing what you need.",
        _l9, ["Minimal cash.", "Graded on efficiency: lower cost scores higher.", "Random events test your buffer."],
        events=True, event_chance=(0.08, 0.14),
    ),
    Level(
        10, 4, "Supply Chain Master",
        "Four markets, two regions, and a blank map. You choose the suppliers, the hubs, the routes. "
        "The forecasts are your best guess; reality will disagree. Show what you've learned.",
        "Build your own network to serve four markets. Forecasts are only approximate.",
        5, 52, 1010,
        _obj_set(
            _obj("no_bankruptcy", "required", "Don't go bankrupt"),
            _obj("fill", "required", "Achieve an 85% fill rate", target=0.85),
            _obj("service", "goal", "Keep a 90% service level", target=0.90),
            _obj("margin", "goal", "Efficiency: achieve a 10% profit margin", target=0.10),
            _obj("stockouts_at_most", "goal", "Resilience: at most 8 stockouts despite events", target=8),
            _obj("score_ratio", "bonus", "Score at least 90% of the maximum", target=0.90),
        ),
        "You built a network that bends without breaking. They'll teach it in business schools - "
        "and they'll still get the details wrong.",
        _l10, ["You must build the network yourself within a build budget.",
               "Demand forecasts are approximate.", "Events are frequent."],
        hints=False, edit_mode=True, events=True, event_chance=(0.20, 0.30),
        hidden_demand={name: factor for name, *_, factor in _L10_MARKETS},
    ),
]


def get_level(level_id: int) -> Level:
    for level in LEVELS:
        if level.id == level_id:
            return level
    raise KeyError(f"unknown level: {level_id}")


def apply_hidden_demand(level: Level, spec: NetworkSpec) -> None:
    """Make the actual demand deviate from the published forecast (level 10)."""
    for node in spec.nodes:
        factor = level.hidden_demand.get(node.id)
        if factor and node.demand is not None:
            node.demand = node.demand.model_copy(
                update={"mean": node.demand.mean * factor, "base": node.demand.base * factor}
            )
