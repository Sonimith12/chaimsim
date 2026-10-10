"""Tests for chainsim.core.disruptions."""

import numpy as np
import pytest

from chainsim.core.disruptions import (
    CapacityReduction,
    DemandShock,
    LeadTimeShock,
    NodeOutage,
)
from chainsim.core.edges import TransportLink, uniform_lead_time
from chainsim.core.nodes import DistributionCenter


def test_applies_at_window():
    event = NodeOutage(target_id="DC", start=5, duration=3)
    assert not event.applies_at(4)
    assert event.applies_at(5)
    assert event.applies_at(7)
    assert not event.applies_at(8)


def test_node_outage_zeroes_capacity_and_deactivates():
    node = DistributionCenter(id="DC", capacity=100)
    event = NodeOutage(target_id="DC", start=0, duration=1)
    event.apply(node)
    assert node.active is False
    assert node.capacity == 0.0


def test_capacity_reduction_scales_finite_capacity():
    node = DistributionCenter(id="DC", capacity=100)
    event = CapacityReduction(target_id="DC", start=0, duration=1, factor=0.4)
    event.apply(node)
    assert node.capacity == 40.0


def test_capacity_reduction_noop_on_unlimited_capacity():
    node = DistributionCenter(id="DC")  # capacity=None -> unlimited
    event = CapacityReduction(target_id="DC", start=0, duration=1, factor=0.5)
    event.apply(node)
    assert node.capacity is None


def test_capacity_reduction_rejects_out_of_range_factor():
    with pytest.raises(ValueError):
        CapacityReduction(target_id="DC", start=0, duration=1, factor=1.5)


def test_lead_time_shock_scales_constant_lead_time():
    edge = TransportLink(source="A", destination="B", lead_time=2.0)
    event = LeadTimeShock(target_id="A->B", start=0, duration=1, multiplier=3.0)
    event.apply(edge)
    assert edge.lead_time == 6.0


def test_lead_time_shock_wraps_callable_lead_time():
    edge = TransportLink(source="A", destination="B", lead_time=uniform_lead_time(1, 1))
    event = LeadTimeShock(target_id="A->B", start=0, duration=1, multiplier=2.0)
    event.apply(edge)
    rng = np.random.default_rng(0)
    assert edge.sample_lead_time(rng) == pytest.approx(2.0)


def test_lead_time_shock_does_not_compound_across_periods():
    """Simulates the engine's per-period reset-then-apply discipline: repeated
    application across periods must not multiply the lead time further each time.
    """
    edge = TransportLink(source="A", destination="B", lead_time=2.0)
    event = LeadTimeShock(target_id="A->B", start=0, duration=3, multiplier=2.0)
    for _ in range(3):
        edge.clear_disruptions()
        event.apply(edge)
        assert edge.lead_time == 4.0


def test_demand_shock_scales_value():
    event = DemandShock(target_id="R", start=0, duration=1, multiplier=2.5)
    assert event.apply(10.0) == 25.0


def test_demand_shock_rejects_negative_multiplier():
    with pytest.raises(ValueError):
        DemandShock(target_id="R", start=0, duration=1, multiplier=-1)
