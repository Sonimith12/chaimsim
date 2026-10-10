"""SupplyChainNetwork: a directed-graph representation of a supply chain, built on networkx.DiGraph.

Exposes methods to add nodes/edges, validate the graph topology (no
orphan nodes, at least one sink/retailer-like node, no cycles, etc.), and
export/import to/from a plain dict for serialization. Graph edges point in
the direction of material flow: an edge ``u -> v`` means ``u`` ships to
``v``.
"""

from __future__ import annotations

import networkx as nx

from chainsim.core.edges import TransportLink
from chainsim.core.nodes import Node


class NetworkValidationError(ValueError):
    """Raised when a :class:`SupplyChainNetwork` fails topology validation."""


class SupplyChainNetwork:
    """A supply chain topology: :class:`~chainsim.core.nodes.Node` objects connected by
    :class:`~chainsim.core.edges.TransportLink` edges, backed by a ``networkx.DiGraph``.
    """

    def __init__(self) -> None:
        self.graph: nx.DiGraph = nx.DiGraph()

    # -- construction -----------------------------------------------------

    def add_node(self, node: Node) -> Node:
        """Add a node to the network. Returns the node for chaining."""
        if node.id in self.graph.nodes:
            raise ValueError(f"node id already present in network: {node.id!r}")
        self.graph.add_node(node.id, obj=node)
        return node

    def add_edge(self, edge: TransportLink) -> TransportLink:
        """Add a directed transportation link. Both endpoints must already exist."""
        for endpoint in (edge.source, edge.destination):
            if endpoint not in self.graph.nodes:
                raise ValueError(f"cannot add edge referencing unknown node id: {endpoint!r}")
        self.graph.add_edge(edge.source, edge.destination, obj=edge)
        return edge

    # -- accessors ----------------------------------------------------------

    def get_node(self, node_id: str) -> Node:
        return self.graph.nodes[node_id]["obj"]

    def get_edge(self, source: str, destination: str) -> TransportLink:
        return self.graph.edges[source, destination]["obj"]

    @property
    def nodes(self) -> list[Node]:
        return [data["obj"] for _, data in self.graph.nodes(data=True)]

    @property
    def edges(self) -> list[TransportLink]:
        return [data["obj"] for _, _, data in self.graph.edges(data=True)]

    def predecessors(self, node_id: str) -> list[Node]:
        """Upstream nodes that ship directly to ``node_id``."""
        return [self.get_node(n) for n in self.graph.predecessors(node_id)]

    def successors(self, node_id: str) -> list[Node]:
        """Downstream nodes that ``node_id`` ships directly to."""
        return [self.get_node(n) for n in self.graph.successors(node_id)]

    def sinks(self) -> list[Node]:
        """Nodes with no successors (typically customer-facing retailers)."""
        return [self.get_node(n) for n, d in self.graph.out_degree() if d == 0]

    def sources(self) -> list[Node]:
        """Nodes with no predecessors (roots that replenish from outside the network)."""
        return [self.get_node(n) for n, d in self.graph.in_degree() if d == 0]

    def topological_order(self, *, downstream_first: bool = False) -> list[Node]:
        """Nodes in topological order (sources before sinks by default).

        Args:
            downstream_first: If True, return sinks before sources — the
                order the engine processes nodes in, so a node's downstream
                orders are known before it decides its own replenishment.
        """
        try:
            order = list(nx.topological_sort(self.graph))
        except nx.NetworkXUnfeasible as exc:
            raise NetworkValidationError("network graph contains a cycle") from exc
        if downstream_first:
            order = list(reversed(order))
        return [self.get_node(n) for n in order]

    # -- validation ---------------------------------------------------------

    def validate(self) -> None:
        """Validate topology invariants. Raises :class:`NetworkValidationError` on failure."""
        if self.graph.number_of_nodes() == 0:
            raise NetworkValidationError("network has no nodes")
        if not nx.is_directed_acyclic_graph(self.graph):
            raise NetworkValidationError("network graph contains a cycle")
        isolated = list(nx.isolates(self.graph))
        if isolated and self.graph.number_of_nodes() > 1:
            raise NetworkValidationError(f"orphan node(s) with no connections: {isolated}")
        if not self.sinks():
            raise NetworkValidationError("network has no sink node (e.g. a retailer)")
        if not self.sources():
            raise NetworkValidationError("network has no source node (e.g. a supplier)")

    # -- serialization --------------------------------------------------------

    def to_dict(self) -> dict:
        """Export node ids/roles and edge endpoints to a plain, JSON-friendly dict.

        Node and edge *objects* are not fully serialized (callables such as
        lead-time distributions aren't portable); this captures topology and
        scalar configuration for inspection/round-tripping simple setups.
        """
        return {
            "nodes": [
                {
                    "id": n.id,
                    "name": n.name,
                    "type": type(n).__name__,
                    "capacity": (
                        None if n.base_capacity in (None, float("inf")) else n.base_capacity
                    ),
                    "holding_cost": n.holding_cost,
                    "backlog_cost": n.backlog_cost,
                    "shelf_life": n.shelf_life,
                    "skus": list(n.skus),
                }
                for n in self.nodes
            ],
            "edges": [
                {
                    "source": e.source,
                    "destination": e.destination,
                    "capacity": e.base_capacity,
                    "cost_per_unit": e.cost_per_unit,
                    "mode": e.mode,
                }
                for e in self.edges
            ],
        }

    def __repr__(self) -> str:
        return (
            f"SupplyChainNetwork(nodes={self.graph.number_of_nodes()}, "
            f"edges={self.graph.number_of_edges()})"
        )
