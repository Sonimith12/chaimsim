"""SimulationEngine: SimPy-based runner that ties nodes, edges, policies, demand, and disruptions together.

To be implemented in Phase 1. Advances simulation time using SimPy
processes, triggers replenishment decisions per node per period, applies
disruptions, and records history (inventory levels, orders, shipments,
stockouts, costs) into a structured log (e.g. a pandas DataFrame) for
downstream metrics.
"""
