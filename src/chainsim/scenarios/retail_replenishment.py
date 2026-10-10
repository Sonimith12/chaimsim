"""Multi-echelon retail network (DC -> stores) with seasonal demand and promo shocks.

A distribution-center-to-stores network: one regional DC replenished from a
Supplier, feeding three stores of different size, each facing seasonal
weekly demand. Two promotional demand shocks (a spring and a holiday
promo) are scheduled partway through the year, exercising
:class:`~chainsim.core.disruptions.DemandShock` and the DC's proportional
shipment split across multiple downstream stores (multiple successors).

Run standalone with ``python -m chainsim.scenarios.retail_replenishment``.
"""

from __future__ import annotations

import pandas as pd

from chainsim.core.demand import SeasonalDemand
from chainsim.core.disruptions import DemandShock
from chainsim.core.edges import TransportLink
from chainsim.core.engine import SimulationEngine
from chainsim.core.network import SupplyChainNetwork
from chainsim.core.nodes import DEFAULT_SKU, DistributionCenter, Retailer, Supplier
from chainsim.core.policies import BaseStockPolicy
from chainsim.scenarios._common import ScenarioConfig, print_scenario_report, run_scenario

N_PERIODS = 52
SEED = 0
SERVICE_LEVEL = 0.95

STORES = {
    # store_id: (base weekly demand, seasonal amplitude, lead time from DC)
    "Store_Flagship": (60.0, 20.0, 1),
    "Store_Suburban": (35.0, 10.0, 2),
    "Store_Outlet": (18.0, 6.0, 2),
}
SEASON_LENGTH = 13  # a quarterly-ish cycle
DEMAND_NOISE = 3.0

# (start_week, duration_weeks, multiplier, [store ids affected])
PROMOS = [
    (10, 2, 2.5, ["Store_Flagship", "Store_Suburban"]),  # spring promo
    (47, 2, 3.0, list(STORES)),  # holiday promo, storewide
]


def build_scenario(seed: int = SEED) -> ScenarioConfig:
    net = SupplyChainNetwork()
    # Ample, cost-free upstream source: this scenario is about DC/store
    # replenishment, not Supplier-side warehousing economics.
    net.add_node(Supplier(id="Supplier", holding_cost=0.0, initial_inventory={DEFAULT_SKU: 15_000}))
    net.add_node(
        DistributionCenter(
            id="DC", holding_cost=0.4, capacity=400, initial_inventory={DEFAULT_SKU: 300}
        )
    )
    net.add_edge(TransportLink(source="Supplier", destination="DC", lead_time=3, mode="rail"))

    demand = {}
    policies = {
        "DC": BaseStockPolicy(
            mean_demand=113, std_demand=25, lead_time=3, service_level=SERVICE_LEVEL
        )
    }
    for store_id, (base, amplitude, lead_time) in STORES.items():
        net.add_node(
            Retailer(
                id=store_id,
                holding_cost=1.2,
                backlog_cost=8.0,
                initial_inventory={DEFAULT_SKU: base * 2},
            )
        )
        net.add_edge(
            TransportLink(source="DC", destination=store_id, lead_time=lead_time, mode="truck")
        )
        demand[store_id] = SeasonalDemand(
            base=base, amplitude=amplitude, period_length=SEASON_LENGTH, noise_std=DEMAND_NOISE
        )
        # Store-level safety stock, tuned from the same demand stats driving
        # the generator above (see chainsim.core.policies.BaseStockPolicy).
        policies[store_id] = BaseStockPolicy(
            mean_demand=base,
            std_demand=max(amplitude / 2, DEMAND_NOISE),
            lead_time=lead_time,
            service_level=SERVICE_LEVEL,
        )

    disruptions = [
        DemandShock(target_id=store_id, start=start, duration=duration, multiplier=multiplier)
        for start, duration, multiplier, store_ids in PROMOS
        for store_id in store_ids
    ]

    return ScenarioConfig(
        name="Retail Replenishment",
        description=(
            "A regional DC replenishing three stores of different size, facing seasonal "
            "weekly demand plus two scheduled promotional demand shocks."
        ),
        network=net,
        demand=demand,
        policies=policies,
        disruptions=disruptions,
        n_periods=N_PERIODS,
        seed=seed,
    )


def _print_promo_impact(history: pd.DataFrame) -> None:
    print("\nPromo impact:")
    for start, duration, multiplier, store_ids in PROMOS:
        window = range(start, start + duration)
        print(f"  weeks {start}-{start + duration - 1} (x{multiplier} demand): {store_ids}")
        for store_id in store_ids:
            store_history = history[history.node_id == store_id]
            promo_rows = store_history[store_history.period.isin(window)]
            baseline_rows = store_history[~store_history.period.isin(window)]
            promo_service = (promo_rows["backlog"] <= 0).mean()
            baseline_service = (baseline_rows["backlog"] <= 0).mean()
            print(
                f"    {store_id}: demand {promo_rows['external_demand'].mean():.1f} "
                f"(vs {baseline_rows['external_demand'].mean():.1f} baseline avg), "
                f"service level during promo {promo_service:.1%} "
                f"(vs {baseline_service:.1%} rest of year)"
            )


def main() -> tuple[SimulationEngine, pd.DataFrame]:
    config = build_scenario()
    engine, history = run_scenario(config)
    print_scenario_report(config, engine, history)
    _print_promo_impact(history)
    return engine, history


if __name__ == "__main__":
    main()
