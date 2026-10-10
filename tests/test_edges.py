"""Tests for chainsim.core.edges."""

import numpy as np

from chainsim.core.edges import TransportLink, poisson_lead_time, uniform_lead_time


def test_constant_lead_time_sampling():
    edge = TransportLink(source="A", destination="B", lead_time=4.0)
    rng = np.random.default_rng(0)
    assert edge.sample_lead_time(rng) == 4.0


def test_callable_lead_time_sampling():
    edge = TransportLink(source="A", destination="B", lead_time=uniform_lead_time(1, 3))
    rng = np.random.default_rng(0)
    value = edge.sample_lead_time(rng)
    assert 1 <= value <= 3


def test_poisson_lead_time_is_at_least_one():
    sampler = poisson_lead_time(mean=0.1)
    rng = np.random.default_rng(1)
    for _ in range(50):
        assert sampler(rng) >= 1.0


def test_edge_id():
    edge = TransportLink(source="A", destination="B")
    assert edge.id == "A->B"


def test_clear_disruptions_restores_capacity_and_lead_time():
    edge = TransportLink(source="A", destination="B", lead_time=2.0, capacity=100)
    edge.capacity = 10
    edge.lead_time = 20.0

    edge.clear_disruptions()

    assert edge.capacity == 100
    assert edge.lead_time == 2.0


def test_unlimited_capacity_default():
    edge = TransportLink(source="A", destination="B")
    assert edge.capacity is None
