"""Quickstart: build a 4-echelon serial chain, run 100 periods, plot inventory levels.

The Phase 1 deliverable: proves the simulation core (nodes, edges, network,
demand, policies, engine) works end to end, with no RL and no benchmarking
layer yet. Runnable as a plain script — no Streamlit dependency.

    Supplier -> Plant (Manufacturer) -> DC (DistributionCenter) -> Store (Retailer)

Each node runs a simple order-up-to policy; the retailer faces stochastic
(Poisson) customer demand. Run with:

    python examples/01_quickstart.py

Requires the `examples` extra for plotting: `pip install -e ".[examples]"`.
"""

from __future__ import annotations

import matplotlib.pyplot as plt

from chainsim.core import (
    DEFAULT_SKU,
    DistributionCenter,
    Manufacturer,
    OrderUpTo,
    Retailer,
    SimulationEngine,
    StationaryDemand,
    Supplier,
    SupplyChainNetwork,
    TransportLink,
)

N_PERIODS = 100
SEED = 7


def build_network() -> SupplyChainNetwork:
    """A 4-echelon serial chain: Supplier -> Plant -> DC -> Store."""
    net = SupplyChainNetwork()
    net.add_node(Supplier(id="Supplier", name="Raw Material Supplier", holding_cost=0.2))
    net.add_node(
        Manufacturer(
            id="Plant",
            name="Manufacturing Plant",
            holding_cost=0.5,
            capacity=150,
            initial_inventory={DEFAULT_SKU: 100},
        )
    )
    net.add_node(
        DistributionCenter(
            id="DC",
            name="Regional DC",
            holding_cost=0.8,
            initial_inventory={DEFAULT_SKU: 100},
        )
    )
    net.add_node(
        Retailer(
            id="Store",
            name="Retail Store",
            holding_cost=1.5,
            backlog_cost=10.0,
            initial_inventory={DEFAULT_SKU: 60},
        )
    )

    net.add_edge(TransportLink(source="Supplier", destination="Plant", lead_time=2, mode="rail"))
    net.add_edge(TransportLink(source="Plant", destination="DC", lead_time=2, mode="truck"))
    net.add_edge(TransportLink(source="DC", destination="Store", lead_time=1, mode="truck"))

    net.validate()
    return net


def main() -> None:
    network = build_network()

    engine = SimulationEngine(
        network=network,
        demand={"Store": StationaryDemand(mean=20, distribution="poisson")},
        policies={
            "Store": OrderUpTo(S=80),
            "DC": OrderUpTo(S=120),
            "Plant": OrderUpTo(S=140),
            "Supplier": OrderUpTo(S=160),
        },
        n_periods=N_PERIODS,
        seed=SEED,
    )
    history = engine.run()

    # -- console summary ---------------------------------------------------
    node_order = ["Supplier", "Plant", "DC", "Store"]
    print(f"Ran {N_PERIODS} periods over a 4-echelon serial chain (seed={SEED}).\n")
    summary = (
        history.groupby("node_id")
        .agg(
            avg_on_hand=("on_hand", "mean"),
            avg_backlog=("backlog", "mean"),
            total_holding_cost=("holding_cost", "sum"),
            total_backlog_cost=("backlog_cost", "sum"),
            total_waste=("waste", "sum"),
            periods_with_stockout=("backlog", lambda s: int((s > 0).sum())),
        )
        .loc[node_order]
    )
    summary["total_cost"] = summary["total_holding_cost"] + summary["total_backlog_cost"]
    print(summary.round(2).to_string())

    store = history[history.node_id == "Store"]
    fill_rate = 1 - store["backlog"].gt(0).mean()
    print(f"\nStore fill rate (periods without stockout): {fill_rate:.1%}")
    print(f"Total network cost: {summary['total_cost'].sum():.2f}")

    # -- plot ---------------------------------------------------------------
    fig, axes = plt.subplots(4, 1, figsize=(10, 10), sharex=True)
    for ax, node_id in zip(axes, node_order, strict=True):
        node_history = history[history.node_id == node_id]
        ax.plot(node_history["period"], node_history["on_hand"], label="on-hand", color="#2a6f97")
        ax.fill_between(
            node_history["period"],
            0,
            node_history["backlog"],
            label="backlog",
            color="#d62828",
            alpha=0.4,
            step="mid",
        )
        ax.set_ylabel(node_id)
        ax.legend(loc="upper right", fontsize=8)
        ax.grid(alpha=0.3)
    axes[-1].set_xlabel("period")
    fig.suptitle("chainsim quickstart: 4-echelon serial chain — inventory & backlog", y=0.995)
    fig.tight_layout()

    out_path = "examples/01_quickstart_output.png"
    fig.savefig(out_path, dpi=150)
    print(f"\nSaved plot to {out_path}")


if __name__ == "__main__":
    main()
