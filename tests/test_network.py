"""Tests for chainsim.core.network.SupplyChainNetwork."""

import pytest

from chainsim.core.edges import TransportLink
from chainsim.core.network import NetworkValidationError, SupplyChainNetwork
from chainsim.core.nodes import DistributionCenter, Retailer, Supplier


def _serial_chain() -> SupplyChainNetwork:
    net = SupplyChainNetwork()
    s = net.add_node(Supplier(id="S"))
    dc = net.add_node(DistributionCenter(id="DC"))
    r = net.add_node(Retailer(id="R"))
    net.add_edge(TransportLink(source=s.id, destination=dc.id))
    net.add_edge(TransportLink(source=dc.id, destination=r.id))
    return net


def test_add_node_rejects_duplicate_id():
    net = SupplyChainNetwork()
    net.add_node(Supplier(id="S"))
    with pytest.raises(ValueError):
        net.add_node(Supplier(id="S"))


def test_add_edge_rejects_unknown_endpoint():
    net = SupplyChainNetwork()
    net.add_node(Supplier(id="S"))
    with pytest.raises(ValueError):
        net.add_edge(TransportLink(source="S", destination="missing"))


def test_predecessors_and_successors():
    net = _serial_chain()
    assert [n.id for n in net.successors("S")] == ["DC"]
    assert [n.id for n in net.predecessors("R")] == ["DC"]
    assert net.predecessors("S") == []
    assert net.successors("R") == []


def test_sources_and_sinks():
    net = _serial_chain()
    assert [n.id for n in net.sources()] == ["S"]
    assert [n.id for n in net.sinks()] == ["R"]


def test_topological_order_upstream_first_by_default():
    net = _serial_chain()
    order = [n.id for n in net.topological_order()]
    assert order == ["S", "DC", "R"]


def test_topological_order_downstream_first():
    net = _serial_chain()
    order = [n.id for n in net.topological_order(downstream_first=True)]
    assert order == ["R", "DC", "S"]


def test_validate_passes_for_serial_chain():
    net = _serial_chain()
    net.validate()  # should not raise


def test_validate_rejects_empty_network():
    net = SupplyChainNetwork()
    with pytest.raises(NetworkValidationError):
        net.validate()


def test_validate_rejects_orphan_node():
    net = _serial_chain()
    net.add_node(Retailer(id="orphan"))
    with pytest.raises(NetworkValidationError):
        net.validate()


def test_validate_rejects_cycle():
    net = SupplyChainNetwork()
    a = net.add_node(Supplier(id="A"))
    b = net.add_node(DistributionCenter(id="B"))
    net.add_edge(TransportLink(source=a.id, destination=b.id))
    net.add_edge(TransportLink(source=b.id, destination=a.id))
    with pytest.raises(NetworkValidationError):
        net.validate()


def test_to_dict_captures_topology():
    net = _serial_chain()
    data = net.to_dict()
    assert {n["id"] for n in data["nodes"]} == {"S", "DC", "R"}
    assert {(e["source"], e["destination"]) for e in data["edges"]} == {("S", "DC"), ("DC", "R")}
