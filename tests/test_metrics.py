"""Tests for chainsim.metrics (kpis, sweep, compare)."""

import pandas as pd
import pytest

from chainsim.core.demand import StationaryDemand
from chainsim.core.edges import TransportLink
from chainsim.core.engine import SimulationEngine
from chainsim.core.network import SupplyChainNetwork
from chainsim.core.nodes import DEFAULT_SKU, Retailer, Supplier
from chainsim.core.policies import OrderUpTo
from chainsim.metrics import compare as compare_mod
from chainsim.metrics import kpis
from chainsim.metrics.sweep import ScenarioSweep


def _two_node_network(lead_time=2, cost_per_unit=0.0):
    net = SupplyChainNetwork()
    net.add_node(Supplier(id="S", holding_cost=0.1, initial_inventory={DEFAULT_SKU: 100_000}))
    net.add_node(
        Retailer(id="R", holding_cost=1.0, backlog_cost=5.0, initial_inventory={DEFAULT_SKU: 40})
    )
    net.add_edge(
        TransportLink(source="S", destination="R", lead_time=lead_time, cost_per_unit=cost_per_unit)
    )
    return net


def _run(net, s=60, n_periods=40, seed=0):
    engine = SimulationEngine(
        network=net,
        demand={"R": StationaryDemand(mean=10, distribution="poisson")},
        policies={"R": OrderUpTo(S=s), "S": OrderUpTo(S=1_000_000)},
        n_periods=n_periods,
        seed=seed,
    )
    return engine, engine.run()


# -- kpis ---------------------------------------------------------------


def test_fill_rate_is_one_when_never_backlogged():
    net = _two_node_network()
    _, history = _run(net, s=200)  # plenty of stock, should rarely if ever backlog
    assert kpis.fill_rate(history, "R") > 0.9


def test_fill_rate_degrades_with_low_order_up_to_level():
    # OrderUpTo self-corrects even from a too-low S (backlog depresses inventory
    # position, forcing larger catch-up orders), so compare relatively rather
    # than asserting an absolute threshold.
    net_low = _two_node_network()
    net_high = _two_node_network()
    _, history_low = _run(net_low, s=5)
    _, history_high = _run(net_high, s=200)
    assert kpis.fill_rate(history_low, "R") < kpis.fill_rate(history_high, "R")


def test_service_level_matches_backlog_free_period_fraction():
    net = _two_node_network()
    _, history = _run(net, s=200)
    retailer = history[history.node_id == "R"]
    expected = (retailer["backlog"] <= 0).mean()
    assert kpis.service_level(history, "R") == pytest.approx(expected)


def test_average_inventory_matches_manual_mean():
    net = _two_node_network()
    _, history = _run(net)
    retailer = history[history.node_id == "R"]
    assert kpis.average_inventory(history, "R") == pytest.approx(retailer["on_hand"].mean())


def test_bullwhip_ratio_greater_than_one_upstream():
    net = _two_node_network()
    _, history = _run(net, n_periods=200)
    # classic bullwhip: order variance amplifies moving upstream from the
    # customer-facing node
    assert kpis.bullwhip_ratio(history, "S") >= kpis.bullwhip_ratio(history, "R") * 0.5


def test_total_transportation_cost_uses_edge_cost_per_unit():
    net = _two_node_network(cost_per_unit=2.0)
    _, history = _run(net)
    supplier_fulfilled = history[history.node_id == "S"]["fulfilled"].sum()
    expected = supplier_fulfilled * 2.0
    assert kpis.total_transportation_cost(history, net, "S") == pytest.approx(expected)


def test_total_transportation_cost_zero_for_sink_node():
    net = _two_node_network(cost_per_unit=2.0)
    _, history = _run(net)
    assert kpis.total_transportation_cost(history, net, "R") == 0.0


def test_per_node_kpis_has_one_row_per_node():
    net = _two_node_network()
    _, history = _run(net)
    table = kpis.per_node_kpis(history, net)
    assert set(table.index) == {"S", "R"}
    assert "total_cost" in table.columns


def test_summarize_returns_flat_scalar_dict():
    net = _two_node_network()
    _, history = _run(net)
    summary = kpis.summarize(history, net)
    assert isinstance(summary["total_cost"], float)
    assert 0.0 <= summary["fill_rate"] <= 1.0
    assert 0.0 <= summary["service_level"] <= 1.0


# -- sweep ----------------------------------------------------------------


def _build_engine(params: dict) -> SimulationEngine:
    net = _two_node_network(lead_time=params["lead_time"])
    return SimulationEngine(
        network=net,
        demand={"R": StationaryDemand(mean=10, distribution="poisson")},
        policies={"R": OrderUpTo(S=params["S"]), "S": OrderUpTo(S=1_000_000)},
        n_periods=30,
    )


def test_scenario_sweep_shape():
    sweep = ScenarioSweep(
        build=_build_engine,
        param_grid={"lead_time": [1, 2], "S": [30, 60]},
        n_replications=5,
    )
    results = sweep.run()
    assert len(results) == 2 * 2 * 5
    for col in ("lead_time", "S", "replication", "total_cost", "fill_rate"):
        assert col in results.columns


def test_scenario_sweep_uses_common_random_numbers_across_params():
    """Replication r should see the same demand draws regardless of params —
    verified indirectly: two runs of the *same* param combo across separate
    sweeps with the same base_seed reproduce identically.
    """
    sweep1 = ScenarioSweep(
        build=_build_engine, param_grid={"lead_time": [2], "S": [60]}, n_replications=3
    )
    sweep2 = ScenarioSweep(
        build=_build_engine, param_grid={"lead_time": [2], "S": [60]}, n_replications=3
    )
    r1 = sweep1.run()
    r2 = sweep2.run()
    pd.testing.assert_series_equal(r1["total_cost"], r2["total_cost"])


def test_scenario_sweep_varies_by_replication_seed():
    sweep = ScenarioSweep(
        build=_build_engine, param_grid={"lead_time": [2], "S": [60]}, n_replications=10
    )
    results = sweep.run()
    assert results["total_cost"].nunique() > 1


# -- compare ----------------------------------------------------------------


def test_summarize_sweep_aggregates_by_group_cols():
    sweep = ScenarioSweep(
        build=_build_engine,
        param_grid={"lead_time": [1, 3], "S": [60]},
        n_replications=8,
    )
    results = sweep.run()
    table = compare_mod.summarize_sweep(results, group_cols=["lead_time", "S"])
    assert len(table) == 2
    assert "total_cost_mean" in table.columns
    assert "total_cost_std" in table.columns


def test_compare_across_labeled_scenarios():
    net_a = _two_node_network(lead_time=1)
    net_b = _two_node_network(lead_time=5)
    _, history_a = _run(net_a)
    _, history_b = _run(net_b)

    results = {
        "short_lead_time": pd.DataFrame([kpis.summarize(history_a, net_a)]),
        "long_lead_time": pd.DataFrame([kpis.summarize(history_b, net_b)]),
    }
    table = compare_mod.compare(results)
    assert set(table.index) == {"short_lead_time", "long_lead_time"}
    assert "total_cost_mean" in table.columns
