"""DisruptionEvent ABC and implementations: outages, capacity reduction, lead-time/demand shocks.

To be implemented in Phase 1. The `DisruptionEvent` ABC exposes
`applies_at(t) -> bool` and `apply(node_or_edge)`. Implementations:
NodeOutage, CapacityReduction, LeadTimeShock, DemandShock. Events are
schedulable at specific times or triggered probabilistically.
"""
