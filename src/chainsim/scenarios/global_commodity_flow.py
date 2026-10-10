"""Large multi-modal global commodity network with geopolitical disruption events.

Two overseas Suppliers feed a single Global_Hub by ship (long lead times),
which redistributes to two Regional_DCs by rail/truck, each feeding a
regional Market. The Hub has two predecessors and two successors —
exercising the engine's documented approximations for nodes with more than
one supplier/customer (even order-split upstream, proportional shipment-
split downstream; see `chainsim.core.engine`). Three geopolitical-style
disruptions run over the year: a port congestion event
(`LeadTimeShock` on a shipping lane), a customs/labor dispute
(`CapacityReduction` at the Hub), and a sanctions-style total supplier
cutoff (`NodeOutage`).

Run standalone with ``python -m chainsim.scenarios.global_commodity_flow``.
"""

from __future__ import annotations

import pandas as pd

from chainsim.core.demand import StationaryDemand
from chainsim.core.disruptions import CapacityReduction, LeadTimeShock, NodeOutage
from chainsim.core.edges import TransportLink
from chainsim.core.engine import SimulationEngine
from chainsim.core.network import SupplyChainNetwork
from chainsim.core.nodes import DEFAULT_SKU, DistributionCenter, Retailer, Supplier
from chainsim.core.policies import BaseStockPolicy
from chainsim.scenarios._common import ScenarioConfig, print_scenario_report, run_scenario

N_PERIODS = 65  # weekly — long enough to run all three events plus recovery
SEED = 0
SERVICE_LEVEL = 0.95

# Ship capacity on the two international lanes: without a cap, a long-lead-time
# BaseStockPolicy reacting to a growing shortfall can order arbitrarily large
# catch-up quantities, which (combined with an already-long pipeline) produces
# an unbounded backlog spiral that never settles within the run — unrealistic,
# and it would smear every disruption's effect together. A real ship (or slot
# allocation) has a fixed capacity per sailing; modeling that also bounds and
# stabilizes the recovery dynamics.
INTL_LANE_CAPACITY = 500

# -- geopolitical disruption windows (weeks) --------------------------------
# Each node below carries several weeks of safety stock (see _POLICY_PARAMS /
# the steady-state initial_inventory), so these need real severity to bite
# rather than being fully absorbed by the buffer. With lead times this long,
# consequences lag well behind each event's own calendar window (see the
# note printed by _print_disruption_impact) — the three are spaced out below
# to keep them reasonably separable, but some smearing is expected and honest.
PORT_CONGESTION_START, PORT_CONGESTION_DURATION = 10, 6  # Asia -> Hub lane, lead time x2
PORT_CONGESTION_MULTIPLIER = 2.0
LABOR_DISPUTE_START, LABOR_DISPUTE_DURATION = 30, 4  # Hub throughput cut to 15%
LABOR_DISPUTE_FACTOR = 0.15
SANCTIONS_START, SANCTIONS_DURATION = 45, 8  # Europe supplier fully cut off


def _make_policy(mean_demand: float, std_demand: float, lead_time: float) -> BaseStockPolicy:
    return BaseStockPolicy(
        mean_demand=mean_demand,
        std_demand=std_demand,
        lead_time=lead_time,
        service_level=SERVICE_LEVEL,
    )


# Demand/lead-time assumptions behind each node's BaseStockPolicy, reused to also
# seed initial_inventory at each node's own steady-state S — with lead times this
# long (up to 21 days), starting from a small on-hand figure means a multi-week
# cold-start stockout before the first shipment ever lands, which would swamp the
# disruption effects this scenario is actually about. Starting at S instead means
# the reported KPIs reflect the disruptions, not simulation warm-up.
_POLICY_PARAMS = {
    "Market_NA": (150, 150**0.5, 2),
    "Market_EU": (120, 120**0.5, 2),
    "Regional_DC_NA": (150, 40, 5),
    "Regional_DC_EU": (120, 35, 3),
    "Global_Hub": (270, 60, 17),
}


def build_scenario(seed: int = SEED) -> ScenarioConfig:
    net = SupplyChainNetwork()
    policies = {node_id: _make_policy(*params) for node_id, params in _POLICY_PARAMS.items()}

    net.add_node(
        Supplier(id="Supplier_Asia", holding_cost=0.0, initial_inventory={DEFAULT_SKU: 50_000})
    )
    net.add_node(
        Supplier(id="Supplier_Europe", holding_cost=0.0, initial_inventory={DEFAULT_SKU: 50_000})
    )
    net.add_node(
        DistributionCenter(
            id="Global_Hub",
            holding_cost=0.3,
            capacity=2000,
            initial_inventory={DEFAULT_SKU: policies["Global_Hub"].S},
        )
    )
    net.add_node(
        DistributionCenter(
            id="Regional_DC_NA",
            holding_cost=0.6,
            initial_inventory={DEFAULT_SKU: policies["Regional_DC_NA"].S},
        )
    )
    net.add_node(
        DistributionCenter(
            id="Regional_DC_EU",
            holding_cost=0.6,
            initial_inventory={DEFAULT_SKU: policies["Regional_DC_EU"].S},
        )
    )
    net.add_node(
        Retailer(
            id="Market_NA",
            holding_cost=1.0,
            backlog_cost=6.0,
            initial_inventory={DEFAULT_SKU: policies["Market_NA"].S},
        )
    )
    net.add_node(
        Retailer(
            id="Market_EU",
            holding_cost=1.0,
            backlog_cost=6.0,
            initial_inventory={DEFAULT_SKU: policies["Market_EU"].S},
        )
    )

    net.add_edge(
        TransportLink(
            source="Supplier_Asia",
            destination="Global_Hub",
            lead_time=21,
            mode="ship",
            capacity=INTL_LANE_CAPACITY,
        )
    )
    net.add_edge(
        TransportLink(
            source="Supplier_Europe",
            destination="Global_Hub",
            lead_time=14,
            mode="ship",
            capacity=INTL_LANE_CAPACITY,
        )
    )
    net.add_edge(
        TransportLink(source="Global_Hub", destination="Regional_DC_NA", lead_time=5, mode="rail")
    )
    net.add_edge(
        TransportLink(source="Global_Hub", destination="Regional_DC_EU", lead_time=3, mode="truck")
    )
    net.add_edge(
        TransportLink(source="Regional_DC_NA", destination="Market_NA", lead_time=2, mode="truck")
    )
    net.add_edge(
        TransportLink(source="Regional_DC_EU", destination="Market_EU", lead_time=2, mode="truck")
    )

    demand = {
        "Market_NA": StationaryDemand(mean=150, distribution="poisson"),
        "Market_EU": StationaryDemand(mean=120, distribution="poisson"),
    }

    disruptions = [
        LeadTimeShock(
            target_id="Supplier_Asia->Global_Hub",
            start=PORT_CONGESTION_START,
            duration=PORT_CONGESTION_DURATION,
            multiplier=PORT_CONGESTION_MULTIPLIER,
        ),
        CapacityReduction(
            target_id="Global_Hub",
            start=LABOR_DISPUTE_START,
            duration=LABOR_DISPUTE_DURATION,
            factor=LABOR_DISPUTE_FACTOR,
        ),
        NodeOutage(target_id="Supplier_Europe", start=SANCTIONS_START, duration=SANCTIONS_DURATION),
    ]

    return ScenarioConfig(
        name="Global Commodity Flow",
        description=(
            "Two overseas Suppliers feeding one Global_Hub (a multi-predecessor node) that "
            "redistributes to two Regional_DC -> Market chains (a multi-successor node), hit "
            "by port congestion, a labor dispute, and a supplier sanctions event over the year."
        ),
        network=net,
        demand=demand,
        policies=policies,
        disruptions=disruptions,
        n_periods=N_PERIODS,
        seed=seed,
    )


def _print_disruption_impact(history: pd.DataFrame) -> None:
    print(
        f"\nDisruption timeline: port congestion weeks {PORT_CONGESTION_START}-"
        f"{PORT_CONGESTION_START + PORT_CONGESTION_DURATION - 1} (Asia lane lead time x"
        f"{PORT_CONGESTION_MULTIPLIER:g}), labor dispute weeks {LABOR_DISPUTE_START}-"
        f"{LABOR_DISPUTE_START + LABOR_DISPUTE_DURATION - 1} (Hub capacity cut to "
        f"{LABOR_DISPUTE_FACTOR:.0%}), sanctions weeks {SANCTIONS_START}-"
        f"{SANCTIONS_START + SANCTIONS_DURATION - 1} (Europe supplier cut off)."
    )

    for node_id in ("Global_Hub", "Regional_DC_NA", "Regional_DC_EU", "Market_NA", "Market_EU"):
        node_history = history[history.node_id == node_id]
        affected = node_history[node_history["backlog"] > 0]
        if len(affected):
            print(
                f"  {node_id}: backlog appears weeks {affected['period'].min():.0f}-"
                f"{affected['period'].max():.0f}, peaking at {affected['backlog'].max():.0f}"
            )
        else:
            print(f"  {node_id}: never backlogged")

    print(
        f"\n  With lead times this long (up to 21 days, x{PORT_CONGESTION_MULTIPLIER:g} during "
        "the port congestion), a disruption's consequence lags well behind its own calendar "
        "window and the three events' effects overlap rather than resolving cleanly "
        "between each one — visible above as one sustained elevated-backlog stretch "
        "at Global_Hub rather than three separable spikes. But it's the Hub that "
        "absorbs all of it: none of the downstream Regional_DCs or Markets ever "
        "backlog, since the Hub's own safety stock is what's built to take the hit."
    )
    print(
        "\n  Note on the sanctions event: chainsim's engine splits a multi-predecessor "
        "node's order evenly across all its predecessors regardless of their status "
        "(a documented Phase 1 approximation — see chainsim.core.engine), so Global_Hub "
        "keeps sending half its order to the disrupted Supplier_Europe rather than "
        "automatically rerouting that volume through Supplier_Asia. The effective supply "
        "cut is therefore deeper than 'lose one of two suppliers' would suggest — a real "
        "company could reroute; this model, as built, can't yet."
    )


def main() -> tuple[SimulationEngine, pd.DataFrame]:
    config = build_scenario()
    engine, history = run_scenario(config)
    print_scenario_report(config, engine, history)
    _print_disruption_impact(history)
    return engine, history


if __name__ == "__main__":
    main()
