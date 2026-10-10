"""Tests for chainsim.core.nodes."""

import numpy as np

from chainsim.core.edges import constant_lead_time
from chainsim.core.nodes import DEFAULT_SKU, DistributionCenter, Retailer, Supplier


def test_initial_inventory_and_defaults():
    node = Retailer(id="R1", initial_inventory={DEFAULT_SKU: 25}, holding_cost=2.0)
    assert node.name == "R1"
    assert node.on_hand_qty() == 25
    assert node.backlog[DEFAULT_SKU] == 0.0
    assert node.pipeline[DEFAULT_SKU] == 0.0
    assert node.inventory_position() == 25


def test_supplier_defaults_to_infinite_capacity():
    node = Supplier(id="S1")
    assert node.capacity == float("inf")


def test_explicit_capacity_respected_for_supplier():
    node = Supplier(id="S1", capacity=100)
    assert node.capacity == 100


def test_receive_increases_on_hand_and_decreases_pipeline():
    node = DistributionCenter(id="DC1")
    node.pipeline[DEFAULT_SKU] = 10
    node.receive(10, period=1)
    assert node.on_hand_qty() == 10
    assert node.pipeline[DEFAULT_SKU] == 0.0


def test_receive_pipeline_never_goes_negative():
    node = DistributionCenter(id="DC1")
    node.receive(5, period=1)  # nothing was on order
    assert node.pipeline[DEFAULT_SKU] == 0.0


def test_issue_limited_to_on_hand():
    node = DistributionCenter(id="DC1", initial_inventory={DEFAULT_SKU: 5})
    issued = node.issue(20)
    assert issued == 5
    assert node.on_hand_qty() == 0


def test_inventory_position_formula():
    node = DistributionCenter(id="DC1", initial_inventory={DEFAULT_SKU: 10})
    node.pipeline[DEFAULT_SKU] = 15
    node.backlog[DEFAULT_SKU] = 4
    assert node.inventory_position() == 10 + 15 - 4


def test_reset_restores_initial_conditions():
    node = Retailer(id="R1", initial_inventory={DEFAULT_SKU: 30}, capacity=50)
    node.issue(10)
    node.pipeline[DEFAULT_SKU] = 5
    node.backlog[DEFAULT_SKU] = 2
    node.capacity = 0
    node.active = False

    node.reset()

    assert node.on_hand_qty() == 30
    assert node.pipeline[DEFAULT_SKU] == 0.0
    assert node.backlog[DEFAULT_SKU] == 0.0
    assert node.capacity == 50
    assert node.active is True


def test_clear_disruptions_leaves_inventory_state_untouched():
    node = Retailer(id="R1", initial_inventory={DEFAULT_SKU: 30}, capacity=50)
    node.issue(10)
    node.capacity = 5
    node.active = False

    node.clear_disruptions()

    assert node.on_hand_qty() == 20  # untouched
    assert node.capacity == 50
    assert node.active is True


def test_perishable_node_delegates_to_batch_inventory():
    node = Retailer(id="R1", shelf_life=2)
    node.receive(10, period=0)
    assert node.on_hand_qty() == 10
    issued = node.issue(4, period=0)
    assert issued == 4
    wasted = node.expire(period=2)
    assert wasted == 6  # remaining 6 units expire at period 2


def test_lead_time_distribution_default_is_constant_one():
    node = Supplier(id="S1")
    rng = np.random.default_rng(0)
    assert node.lead_time_distribution(rng) == 1.0


def test_custom_lead_time_distribution():
    node = Supplier(id="S1", lead_time_distribution=constant_lead_time(3.0))
    rng = np.random.default_rng(0)
    assert node.lead_time_distribution(rng) == 3.0
