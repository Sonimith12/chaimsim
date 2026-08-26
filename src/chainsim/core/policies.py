"""ReplenishmentPolicy ABC and implementations: OrderUpTo, sSPolicy, BaseStock, RQPolicy.

To be implemented in Phase 1. The `ReplenishmentPolicy` ABC exposes
`.decide(node_state) -> order_quantity` and is designed to be easy for
users to subclass with their own ordering logic.
"""
