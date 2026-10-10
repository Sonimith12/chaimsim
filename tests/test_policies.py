"""Tests for chainsim.core.policies.

Validates OrderUpTo and sSPolicy mechanics directly, and validates
BaseStockPolicy / economic_order_quantity against known analytical results
(the newsvendor critical-ratio formula and the classic EOQ formula) for
credibility.
"""

import math

import numpy as np
import pytest

from chainsim.core.policies import (
    BaseStockPolicy,
    NodeState,
    OrderUpTo,
    RQPolicy,
    economic_order_quantity,
    norm_ppf,
    sSPolicy,
)


def _state(inventory_position: float) -> NodeState:
    return NodeState(
        period=0,
        on_hand=inventory_position,
        backlog=0.0,
        pipeline=0.0,
        inventory_position=inventory_position,
    )


# -- OrderUpTo -----------------------------------------------------------


def test_order_up_to_orders_the_shortfall():
    policy = OrderUpTo(S=100)
    assert policy.decide(_state(60)) == 40


def test_order_up_to_never_orders_negative():
    policy = OrderUpTo(S=100)
    assert policy.decide(_state(150)) == 0.0


# -- sSPolicy --------------------------------------------------------------


def test_sS_orders_up_to_S_when_at_or_below_s():
    policy = sSPolicy(s=20, S=100)
    assert policy.decide(_state(20)) == 80
    assert policy.decide(_state(5)) == 95


def test_sS_orders_nothing_above_reorder_point():
    policy = sSPolicy(s=20, S=100)
    assert policy.decide(_state(21)) == 0.0


def test_sS_rejects_S_below_s():
    with pytest.raises(ValueError):
        sSPolicy(s=50, S=10)


# -- RQPolicy ----------------------------------------------------------------


def test_RQ_orders_fixed_quantity_at_reorder_point():
    policy = RQPolicy(R=30, Q=50)
    assert policy.decide(_state(30)) == 50
    assert policy.decide(_state(10)) == 50


def test_RQ_orders_nothing_above_reorder_point():
    policy = RQPolicy(R=30, Q=50)
    assert policy.decide(_state(31)) == 0.0


# -- norm_ppf (needed for the newsvendor-based BaseStockPolicy) -------------


@pytest.mark.parametrize(
    ("p", "expected_z"),
    [
        (0.5, 0.0),
        (0.8, 0.8416212),
        (0.90, 1.2815516),
        (0.95, 1.6448536),
        (0.975, 1.9599640),
        (0.99, 2.3263479),
    ],
)
def test_norm_ppf_matches_known_standard_normal_quantiles(p, expected_z):
    assert norm_ppf(p) == pytest.approx(expected_z, abs=1e-6)


# -- economic_order_quantity (EOQ) ------------------------------------------


def test_eoq_matches_textbook_example():
    # D = 1000 units/year, K = $50/order, h = $2/unit/year -> Q* = sqrt(2*1000*50/2) = 223.607
    q = economic_order_quantity(demand_rate=1000, order_cost=50, holding_cost=2)
    assert q == pytest.approx(223.6068, rel=1e-4)


def test_eoq_minimizes_total_annual_cost():
    """The EOQ formula is derived by minimizing D/Q*K + Q/2*h; verify Q* actually
    beats nearby order quantities on that cost function (the analytical property
    EOQ is famous for).
    """
    D, K, h = 1200, 75, 3
    q_star = economic_order_quantity(D, K, h)

    def total_cost(q: float) -> float:
        return (D / q) * K + (q / 2) * h

    cost_at_star = total_cost(q_star)
    for perturbation in (0.5, 0.8, 1.2, 1.5, 2.0):
        assert cost_at_star <= total_cost(q_star * perturbation)


# -- BaseStockPolicy / newsvendor -------------------------------------------


def test_base_stock_from_costs_uses_newsvendor_critical_ratio():
    # Classic textbook newsvendor: mu=100, sigma=20, co=1 (holding), cu=4 (backlog)
    # critical ratio = cu / (cu + co) = 0.8 -> z = 0.8416, S = 100 + 0.8416*20 = 116.83
    policy = BaseStockPolicy.from_costs(
        mean_demand=100, std_demand=20, lead_time=0, holding_cost=1, backlog_cost=4
    )
    assert policy.z == pytest.approx(norm_ppf(0.8), abs=1e-9)
    assert pytest.approx(100 + norm_ppf(0.8) * 20, abs=1e-6) == policy.S


def test_base_stock_scales_with_lead_time_protection_period():
    mu, sigma, service = 50, 10, 0.95
    lt0 = BaseStockPolicy(mean_demand=mu, std_demand=sigma, lead_time=0, service_level=service)
    lt3 = BaseStockPolicy(mean_demand=mu, std_demand=sigma, lead_time=3, service_level=service)
    z = norm_ppf(service)
    assert pytest.approx(mu * 1 + z * sigma * math.sqrt(1)) == lt0.S
    assert pytest.approx(mu * 4 + z * sigma * math.sqrt(4)) == lt3.S
    assert lt3.S > lt0.S


def test_base_stock_satisfies_newsvendor_service_level_via_monte_carlo():
    """The defining analytical property of the newsvendor solution: ordering up to
    S = F^-1(critical_ratio) achieves a stockout probability of (1 - critical_ratio)
    for single-period (lead_time=0) demand. Verify empirically via simulation.
    """
    mu, sigma = 200, 40
    holding_cost, backlog_cost = 2, 8
    critical_ratio = backlog_cost / (backlog_cost + holding_cost)  # 0.8

    policy = BaseStockPolicy.from_costs(
        mean_demand=mu,
        std_demand=sigma,
        lead_time=0,
        holding_cost=holding_cost,
        backlog_cost=backlog_cost,
    )

    rng = np.random.default_rng(123)
    demand_draws = np.clip(rng.normal(mu, sigma, size=200_000), 0, None)
    no_stockout_rate = float(np.mean(demand_draws <= policy.S))

    assert no_stockout_rate == pytest.approx(critical_ratio, abs=0.01)


def test_base_stock_rejects_ambiguous_or_missing_target():
    with pytest.raises(ValueError):
        BaseStockPolicy(mean_demand=10, std_demand=2, lead_time=1)  # neither given
    with pytest.raises(ValueError):
        BaseStockPolicy(mean_demand=10, std_demand=2, lead_time=1, service_level=0.9, z=1.0)


def test_base_stock_decide_orders_shortfall_to_S():
    policy = BaseStockPolicy(mean_demand=50, std_demand=5, lead_time=1, z=1.0)
    order = policy.decide(_state(policy.S - 15))
    assert order == pytest.approx(15)
