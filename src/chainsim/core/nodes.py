"""Node base class and concrete node types: Supplier, Manufacturer, DistributionCenter, Retailer.

To be implemented in Phase 1. The abstract `Node` base class will define
`id`, `name`, `inventory` (per-SKU dict), `capacity`, `holding_cost`, and
`lead_time_distribution`. Subclasses add role-specific behavior:
Supplier (near-infinite upstream capacity), Manufacturer (production
capacity + bill-of-materials), DistributionCenter, and Retailer (faces
external demand).
"""
