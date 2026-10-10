"""Just-in-time manufacturing scenario with tight capacity constraints and supplier disruption.

A Supplier -> Plant -> Line chain (daily periods): the Line's replenishment
policy is a classic just-in-time (R, Q) reorder-point policy —
:class:`~chainsim.core.policies.RQPolicy` with a small fixed order quantity
placed frequently, instead of a big buffer — and the Plant's production
throughput is capacity-constrained. A scheduled Plant outage partway
through shows what JIT trades away for its low inventory cost: almost no
slack to absorb an upstream disruption. The same outage is re-run against a
buffered `OrderUpTo` policy so the fragility claim is measured, not assumed.

Run standalone with ``python -m chainsim.scenarios.manufacturing_jit``.
"""

from __future__ import annotations

import pandas as pd

from chainsim.core.demand import StationaryDemand
from chainsim.core.disruptions import NodeOutage
from chainsim.core.edges import TransportLink
from chainsim.core.engine import SimulationEngine
from chainsim.core.network import SupplyChainNetwork
from chainsim.core.nodes import DEFAULT_SKU, Manufacturer, Retailer, Supplier
from chainsim.core.policies import OrderUpTo, RQPolicy
from chainsim.scenarios._common import ScenarioConfig, print_scenario_report, run_scenario

N_PERIODS = 90  # ~3 months, daily periods
SEED = 0

DAILY_DEMAND_MEAN = 40.0
PLANT_CAPACITY = 55  # units/day the assembly line can consume from Plant
LINE_LEAD_TIME = 1  # day, JIT delivery from the Plant

OUTAGE_START, OUTAGE_DURATION = 45, 5  # a 5-day Plant outage (the Line's immediate supplier)

# JIT: reorder point covers the lead-time pipeline plus a thin safety margin
# (not zero — real JIT still has *some* cushion), replenished in small, frequent
# batches rather than a big one. Contrast: BUFFERED_S is ~10 days of demand, a
# conventional "hold weeks of stock just in case" policy.
JIT_R, JIT_Q = 90, 40
BUFFERED_S = 400


def _build_network() -> SupplyChainNetwork:
    net = SupplyChainNetwork()
    net.add_node(Supplier(id="Supplier", holding_cost=0.05, initial_inventory={DEFAULT_SKU: 5_000}))
    net.add_node(
        Manufacturer(
            id="Plant",
            holding_cost=0.3,
            capacity=PLANT_CAPACITY,
            initial_inventory={DEFAULT_SKU: 80},
        )
    )
    net.add_node(
        Retailer(
            id="Line",
            holding_cost=1.0,
            backlog_cost=15.0,  # a stalled assembly line is expensive
            initial_inventory={DEFAULT_SKU: JIT_R + 5},
        )
    )
    net.add_edge(TransportLink(source="Supplier", destination="Plant", lead_time=2, mode="truck"))
    net.add_edge(
        TransportLink(source="Plant", destination="Line", lead_time=LINE_LEAD_TIME, mode="truck")
    )
    return net


def build_scenario(seed: int = SEED, line_policy: str = "jit") -> ScenarioConfig:
    """Args:
    line_policy: ``"jit"`` (the default — a small, frequent ``RQPolicy``) or
        ``"buffered"`` (a large ``OrderUpTo`` policy), used to compare JIT's
        fragility to a disruption against a conventional buffered policy run
        through the exact same outage.
    """
    net = _build_network()
    demand = {"Line": StationaryDemand(mean=DAILY_DEMAND_MEAN, distribution="poisson")}

    if line_policy == "jit":
        line = RQPolicy(R=JIT_R, Q=JIT_Q)
        policy_label = "just-in-time (small, frequent orders)"
    elif line_policy == "buffered":
        line = OrderUpTo(S=BUFFERED_S)
        policy_label = "conventionally buffered"
    else:
        raise ValueError(f"unknown line_policy: {line_policy!r}")

    policies = {
        "Line": line,
        "Plant": OrderUpTo(S=PLANT_CAPACITY * 3),
    }
    disruptions = [NodeOutage(target_id="Plant", start=OUTAGE_START, duration=OUTAGE_DURATION)]

    return ScenarioConfig(
        name=f"Manufacturing JIT ({line_policy})",
        description=(
            "A Supplier -> Plant -> Line chain with a capacity-constrained Plant and a "
            f"{policy_label} Line policy, hit by a {OUTAGE_DURATION}-day Plant outage."
        ),
        network=net,
        demand=demand,
        policies=policies,
        disruptions=disruptions,
        n_periods=N_PERIODS,
        seed=seed,
    )


def _print_disruption_impact(history: pd.DataFrame) -> None:
    line = history[history.node_id == "Line"]
    window = range(OUTAGE_START, OUTAGE_START + OUTAGE_DURATION)
    during = line[line.period.isin(window)]
    before = line[line.period < OUTAGE_START]
    print(
        f"\nPlant outage: days {OUTAGE_START}-{OUTAGE_START + OUTAGE_DURATION - 1}. "
        f"Line avg backlog before: {before['backlog'].mean():.1f}, "
        f"during: {during['backlog'].mean():.1f}, "
        f"peak during: {during['backlog'].max():.1f}."
    )


def _compare_jit_vs_buffered() -> None:
    print("\n--- JIT vs. a buffered policy, same outage ---")
    for line_policy in ("jit", "buffered"):
        config = build_scenario(line_policy=line_policy)
        engine, history = run_scenario(config)
        line = history[history.node_id == "Line"]
        window = range(OUTAGE_START, OUTAGE_START + OUTAGE_DURATION)
        during = line[line.period.isin(window)]
        avg_on_hand = line["on_hand"].mean()
        peak_backlog = during["backlog"].max()
        total_backlog_cost = line["backlog_cost"].sum()
        print(
            f"  {line_policy:<9} avg on-hand {avg_on_hand:6.1f} | "
            f"peak backlog during outage {peak_backlog:6.1f} | "
            f"total backlog cost {total_backlog_cost:9.1f}"
        )
    print(
        "  JIT carries far less inventory day-to-day, but that's exactly what leaves it "
        "with less slack to absorb the Plant outage — the buffered policy pays more in "
        "holding cost all year to take a smaller hit when the disruption actually happens."
    )


def main() -> tuple[SimulationEngine, pd.DataFrame]:
    config = build_scenario()
    engine, history = run_scenario(config)
    print_scenario_report(config, engine, history)
    _print_disruption_impact(history)
    _compare_jit_vs_buffered()
    return engine, history


if __name__ == "__main__":
    main()
