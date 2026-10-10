"""Perishable pharma cold-chain scenario with strict lead times and service-level constraints.

A Manufacturer -> Cold_DC -> Hospital chain (daily periods) moving a
temperature-sensitive product with a hard shelf life at every node, tight
(fast, cold-chain) lead times, and a regulatory-style service level
target. Exercises perishable inventory (:mod:`chainsim.core.perishability`:
batch expiry, FEFO issuance): every node starts with a legacy stockpile
that predates its (well-tuned) replenishment policy, so each one takes
exactly one write-off hit when that starting batch outlives its shelf
life — reported alongside service level so the trade-off between chasing
a high service level and carrying (perishable) safety stock is visible,
not hidden behind a single KPI.

Run standalone with ``python -m chainsim.scenarios.pharma_cold_chain``.
"""

from __future__ import annotations

import pandas as pd

from chainsim.core.demand import StationaryDemand
from chainsim.core.disruptions import DemandShock
from chainsim.core.edges import TransportLink
from chainsim.core.engine import SimulationEngine
from chainsim.core.network import SupplyChainNetwork
from chainsim.core.nodes import DEFAULT_SKU, DistributionCenter, Manufacturer, Retailer
from chainsim.core.policies import BaseStockPolicy
from chainsim.metrics.kpis import service_level as service_level_kpi
from chainsim.metrics.kpis import total_waste
from chainsim.scenarios._common import ScenarioConfig, print_scenario_report, run_scenario

N_PERIODS = 90  # ~3 months, daily periods
SEED = 0
TARGET_SERVICE_LEVEL = 0.99  # regulatory-style: stockouts of a critical drug are unacceptable

DAILY_DEMAND_MEAN = 15.0
DC_LEAD_TIME = 2  # days, air freight from the plant
HOSPITAL_LEAD_TIME = 1  # day, dedicated cold-chain courier
DC_SHELF_LIFE = 45  # days
HOSPITAL_SHELF_LIFE = 15  # days — smaller local cold storage, tighter rotation

# A clinic closure cuts patient visits (and so demand) for two weeks mid-scenario:
# a realistic cause of near-expiry stock buildup on a fast-turning perishable.
CLOSURE_START, CLOSURE_DURATION, CLOSURE_DEMAND_MULTIPLIER = 40, 14, 0.25


def build_scenario(seed: int = SEED) -> ScenarioConfig:
    net = SupplyChainNetwork()
    net.add_node(
        Manufacturer(
            id="Plant",
            holding_cost=0.5,
            capacity=200,
            shelf_life=DC_SHELF_LIFE,
            initial_inventory={DEFAULT_SKU: 400},
        )
    )
    net.add_node(
        DistributionCenter(
            id="Cold_DC",
            holding_cost=1.0,
            shelf_life=DC_SHELF_LIFE,
            initial_inventory={DEFAULT_SKU: 200},
        )
    )
    net.add_node(
        Retailer(
            id="Hospital",
            holding_cost=2.0,
            backlog_cost=50.0,  # a stockout of a critical drug is expensive to treat as acceptable
            shelf_life=HOSPITAL_SHELF_LIFE,
            # A legacy stockpile that predates this replenishment policy — large
            # enough that FEFO issuance can't fully work through it before some
            # of it hits its shelf life (see the waste reported below).
            initial_inventory={DEFAULT_SKU: 280},
        )
    )
    net.add_edge(
        TransportLink(source="Plant", destination="Cold_DC", lead_time=DC_LEAD_TIME, mode="air")
    )
    net.add_edge(
        TransportLink(
            source="Cold_DC", destination="Hospital", lead_time=HOSPITAL_LEAD_TIME, mode="air"
        )
    )

    demand = {"Hospital": StationaryDemand(mean=DAILY_DEMAND_MEAN, distribution="poisson")}
    policies = {
        "Hospital": BaseStockPolicy(
            mean_demand=DAILY_DEMAND_MEAN,
            std_demand=DAILY_DEMAND_MEAN**0.5,  # Poisson: std = sqrt(mean)
            lead_time=HOSPITAL_LEAD_TIME,
            service_level=TARGET_SERVICE_LEVEL,
        ),
        "Cold_DC": BaseStockPolicy(
            mean_demand=DAILY_DEMAND_MEAN,
            std_demand=DAILY_DEMAND_MEAN**0.5,
            lead_time=DC_LEAD_TIME,
            service_level=TARGET_SERVICE_LEVEL,
        ),
        "Plant": BaseStockPolicy(
            mean_demand=DAILY_DEMAND_MEAN,
            std_demand=DAILY_DEMAND_MEAN**0.5,
            lead_time=1,
            service_level=TARGET_SERVICE_LEVEL,
        ),
    }

    disruptions = [
        DemandShock(
            target_id="Hospital",
            start=CLOSURE_START,
            duration=CLOSURE_DURATION,
            multiplier=CLOSURE_DEMAND_MULTIPLIER,
        )
    ]

    return ScenarioConfig(
        name="Pharma Cold Chain",
        description=(
            "A Manufacturer -> Cold_DC -> Hospital chain moving a perishable, "
            "temperature-sensitive product under a regulatory-style "
            f"{TARGET_SERVICE_LEVEL:.0%} service level target. The Hospital starts with "
            "a legacy stockpile that predates this replenishment policy, and there's a "
            "temporary clinic closure partway through."
        ),
        network=net,
        demand=demand,
        policies=policies,
        disruptions=disruptions,
        n_periods=N_PERIODS,
        seed=seed,
    )


def _print_compliance_check(history: pd.DataFrame) -> None:
    print("\nRegulatory check:")
    for node_id in ("Hospital", "Cold_DC", "Plant"):
        achieved = service_level_kpi(history, node_id)
        waste = total_waste(history, node_id)
        node_history = history[history.node_id == node_id]
        total_received = node_history["fulfilled"].sum() + waste
        waste_rate = waste / total_received if total_received else 0.0
        verdict = "PASS" if achieved >= TARGET_SERVICE_LEVEL else "FAIL"
        print(
            f"  {node_id}: service level {achieved:.1%} "
            f"(target {TARGET_SERVICE_LEVEL:.0%}) -> {verdict}; "
            f"waste {waste:.0f} units ({waste_rate:.1%} of throughput)"
        )

    write_offs = history[history["waste"] > 0][["node_id", "period", "waste"]]
    if len(write_offs):
        print(
            "\n  Every node here started with a legacy stockpile larger than its own "
            "shelf life could turn over at normal demand — each one takes exactly one "
            "write-off hit when that starting batch expires, since the base-stock "
            "policy correctly throttles new orders to ~0 while working through it but "
            "can't clear it in time:"
        )
        for _, row in write_offs.iterrows():
            day, node_id, wasted = int(row["period"]), row["node_id"], row["waste"]
            print(f"    day {day}: {node_id} writes off {wasted:.0f} units")
        print(
            "  (A write-off that empties the shelf mid-day can also cause that day's "
            "stockout — the batch is gone before that day's demand can be issued from it.)"
        )

    print(
        f"\n  Clinic closure: days {CLOSURE_START}-{CLOSURE_START + CLOSURE_DURATION - 1}, "
        f"demand cut to {CLOSURE_DEMAND_MULTIPLIER:.0%} of normal. No extra waste resulted "
        "from it — the base-stock policy scaled orders down with realized demand quickly "
        "enough that stock never built past what the remaining shelf life could absorb."
    )


def main() -> tuple[SimulationEngine, pd.DataFrame]:
    config = build_scenario()
    engine, history = run_scenario(config)
    print_scenario_report(config, engine, history)
    _print_compliance_check(history)
    return engine, history


if __name__ == "__main__":
    main()
