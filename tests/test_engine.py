"""Tests for chainsim.core.engine.SimulationEngine."""

import numpy as np
import pytest

from chainsim.core.demand import StationaryDemand
from chainsim.core.disruptions import NodeOutage
from chainsim.core.edges import TransportLink
from chainsim.core.engine import SimulationEngine
from chainsim.core.network import SupplyChainNetwork
from chainsim.core.nodes import DEFAULT_SKU, DistributionCenter, Retailer, Supplier
from chainsim.core.policies import OrderUpTo


def _two_node_chain(lead_time=2, retailer_init=50, s_capacity=None, s_initial=100_000):
    net = SupplyChainNetwork()
    net.add_node(
        Supplier(
            id="S",
            capacity=s_capacity,
            holding_cost=0.1,
            initial_inventory={DEFAULT_SKU: s_initial},
        )
    )
    net.add_node(
        Retailer(
            id="R",
            holding_cost=1.0,
            backlog_cost=5.0,
            initial_inventory={DEFAULT_SKU: retailer_init},
        )
    )
    net.add_edge(TransportLink(source="S", destination="R", lead_time=lead_time))
    return net


def test_history_shape_and_columns():
    net = _two_node_chain()
    engine = SimulationEngine(
        network=net,
        demand={"R": StationaryDemand(mean=10)},
        policies={"R": OrderUpTo(60), "S": OrderUpTo(1000)},
        n_periods=15,
        seed=1,
    )
    df = engine.run()
    assert len(df) == 15 * 2  # 2 nodes x 15 periods
    for col in ("period", "node_id", "on_hand", "backlog", "order_placed", "fulfilled"):
        assert col in df.columns


def test_reproducible_with_same_seed():
    def build_and_run(seed):
        net = _two_node_chain()
        engine = SimulationEngine(
            network=net,
            demand={"R": StationaryDemand(mean=10, distribution="poisson")},
            policies={"R": OrderUpTo(60), "S": OrderUpTo(1000)},
            n_periods=20,
            seed=seed,
        )
        return engine.run()

    df1 = build_and_run(42)
    df2 = build_and_run(42)
    assert np.allclose(df1["on_hand"], df2["on_hand"])

    df3 = build_and_run(43)
    assert not np.allclose(df1["on_hand"], df3["on_hand"])


def test_deterministic_lead_time_delays_delivery_by_exact_periods():
    """With zero demand variance and a fixed lead time, an order placed to bring
    inventory position up to S should land exactly `lead_time` periods later.
    """
    net = _two_node_chain(lead_time=3, retailer_init=0)
    engine = SimulationEngine(
        network=net,
        demand={"R": StationaryDemand(mean=10, std=0, distribution="normal")},
        policies={"R": OrderUpTo(10), "S": OrderUpTo(10_000)},
        n_periods=10,
        seed=0,
    )
    df = engine.run()
    retailer = df[df.node_id == "R"].set_index("period")

    # period 0: no stock, order placed but nothing arrives yet -> all demand backlogged
    assert retailer.loc[0, "on_hand"] == 0
    assert retailer.loc[0, "backlog"] == pytest.approx(10)
    # the period-0 order (for 10 units) should arrive by period 3 (lead time 3)
    assert retailer.loc[2, "on_hand"] == 0
    assert retailer.loc[3, "backlog"] < retailer.loc[2, "backlog"]


def test_conservation_inventory_position_matches_state():
    net = _two_node_chain()
    engine = SimulationEngine(
        network=net,
        demand={"R": StationaryDemand(mean=8)},
        policies={"R": OrderUpTo(40), "S": OrderUpTo(1000)},
        n_periods=25,
        seed=5,
    )
    df = engine.run()
    computed = df["on_hand"] + df["pipeline"] - df["backlog"]
    assert np.allclose(df["inventory_position"], computed)


def test_no_policy_means_node_never_orders():
    net = _two_node_chain()
    engine = SimulationEngine(
        network=net,
        demand={"R": StationaryDemand(mean=10)},
        policies={"S": OrderUpTo(1000)},  # retailer has no policy
        n_periods=10,
        seed=0,
    )
    df = engine.run()
    retailer = df[df.node_id == "R"]
    assert (retailer["order_placed"] == 0).all()
    # with no replenishment and finite starting stock, backlog should eventually appear
    assert retailer["backlog"].iloc[-1] > 0


def test_node_outage_blocks_shipping_during_window():
    net = _two_node_chain(lead_time=1, s_capacity=1000)
    outage = NodeOutage(target_id="S", start=2, duration=3)
    engine = SimulationEngine(
        network=net,
        demand={"R": StationaryDemand(mean=10, std=0, distribution="normal")},
        policies={"R": OrderUpTo(100), "S": OrderUpTo(1_000_000)},
        disruptions=[outage],
        n_periods=10,
        seed=0,
    )
    df = engine.run()
    supplier = df[df.node_id == "S"].set_index("period")
    for t in range(2, 5):
        assert supplier.loc[t, "fulfilled"] == 0
        assert supplier.loc[t, "active"] == False  # noqa: E712
    assert supplier.loc[5, "active"] == True  # noqa: E712


def test_perishable_retailer_accumulates_waste():
    net = SupplyChainNetwork()
    net.add_node(Supplier(id="S", holding_cost=0.1))
    net.add_node(
        Retailer(id="R", holding_cost=1.0, shelf_life=2, initial_inventory={DEFAULT_SKU: 0})
    )
    net.add_edge(TransportLink(source="S", destination="R", lead_time=1))
    engine = SimulationEngine(
        network=net,
        demand={"R": StationaryDemand(mean=1, std=0, distribution="normal")},
        policies={"R": OrderUpTo(50), "S": OrderUpTo(1_000_000)},
        n_periods=15,
        seed=0,
    )
    df = engine.run()
    retailer = df[df.node_id == "R"]
    assert retailer["waste"].sum() > 0  # ordering far above demand forces expiry


def test_engine_resets_stateful_policies_between_runs():
    """A policy with internal state (e.g. an exponential-smoothing forecast) must
    start clean on every SimulationEngine.run() call, not leak state from a
    previous run on the same engine instance.
    """

    class CountingPolicy(OrderUpTo):
        def __init__(self, S):
            super().__init__(S)
            self.reset_count = 0

        def reset(self):
            self.reset_count += 1

    policy = CountingPolicy(S=50)
    net = _two_node_chain()
    engine = SimulationEngine(
        network=net,
        demand={"R": StationaryDemand(mean=10)},
        policies={"R": policy, "S": OrderUpTo(1000)},
        n_periods=5,
        seed=0,
    )
    engine.run()
    engine.run()
    assert policy.reset_count == 2


def test_four_echelon_serial_chain_runs_and_stays_bounded():
    net = SupplyChainNetwork()
    net.add_node(Supplier(id="Supplier", holding_cost=0.2))
    net.add_node(
        DistributionCenter(id="Plant", holding_cost=0.5, initial_inventory={DEFAULT_SKU: 100})
    )
    net.add_node(
        DistributionCenter(id="DC", holding_cost=0.8, initial_inventory={DEFAULT_SKU: 100})
    )
    net.add_node(
        Retailer(id="Store", holding_cost=1.5, backlog_cost=10, initial_inventory={DEFAULT_SKU: 60})
    )
    net.add_edge(TransportLink(source="Supplier", destination="Plant", lead_time=2))
    net.add_edge(TransportLink(source="Plant", destination="DC", lead_time=2))
    net.add_edge(TransportLink(source="DC", destination="Store", lead_time=1))

    engine = SimulationEngine(
        network=net,
        demand={"Store": StationaryDemand(mean=20, distribution="poisson")},
        policies={
            "Store": OrderUpTo(80),
            "DC": OrderUpTo(120),
            "Plant": OrderUpTo(140),
            "Supplier": OrderUpTo(160),
        },
        n_periods=100,
        seed=0,
    )
    df = engine.run()
    assert len(df) == 100 * 4
    assert (df["on_hand"] >= 0).all()
    assert (df["backlog"] >= 0).all()
    # bullwhip: upstream order variance should typically exceed the retailer's
    store_order_var = df[df.node_id == "Store"]["order_placed"].var()
    supplier_order_var = df[df.node_id == "Supplier"]["order_placed"].var()
    assert supplier_order_var >= store_order_var * 0.5  # sanity, not a strict bound
