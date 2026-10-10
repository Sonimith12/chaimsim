"""Perishable inventory tracking: batch expiry, FIFO/FEFO issuance, waste calculation.

Tracks expiry per inventory batch and supports FIFO (first-in-first-out)
and FEFO (first-expired-first-out) issuance policies, plus waste (expired
stock) accounting. Used internally by :class:`~chainsim.core.nodes.Node`
when ``shelf_life`` is set; also usable standalone.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Batch:
    """A single receipt of inventory with a known expiry period.

    Attributes:
        quantity: Remaining (non-issued, non-expired) quantity in the batch.
        received_at: Period the batch was received.
        expires_at: Period at which the batch expires. A batch is usable
            through (and including) period ``expires_at - 1``; from
            ``expires_at`` onward it is waste.
    """

    quantity: float
    received_at: int
    expires_at: int

    def is_expired(self, period: int) -> bool:
        return period >= self.expires_at


class PerishableInventory:
    """Batch-tracked inventory for one SKU at one node.

    Args:
        shelf_life: Number of periods a batch remains usable after receipt.
    """

    def __init__(self, shelf_life: int) -> None:
        if shelf_life <= 0:
            raise ValueError("shelf_life must be positive")
        self.shelf_life = shelf_life
        self.batches: list[Batch] = []
        self.total_waste: float = 0.0

    @property
    def on_hand(self) -> float:
        """Total non-expired quantity currently held (does not itself purge expiry)."""
        return sum(b.quantity for b in self.batches)

    def receive(self, quantity: float, period: int) -> None:
        """Add a new batch of ``quantity`` received at ``period``."""
        if quantity <= 0:
            return
        self.batches.append(
            Batch(quantity=quantity, received_at=period, expires_at=period + self.shelf_life)
        )

    def expire(self, period: int) -> float:
        """Purge batches expired as of ``period``; return the quantity wasted."""
        remaining: list[Batch] = []
        wasted = 0.0
        for batch in self.batches:
            if batch.is_expired(period):
                wasted += batch.quantity
            else:
                remaining.append(batch)
        self.batches = remaining
        self.total_waste += wasted
        return wasted

    def issue(self, quantity: float, period: int, mode: str = "FEFO") -> float:
        """Issue up to ``quantity`` units, consuming non-expired batches first.

        Args:
            quantity: Amount requested.
            period: Current period (used to skip already-expired batches).
            mode: ``"FEFO"`` (first-expired-first-out, the default and the
                usual choice for perishables) or ``"FIFO"`` (first-in-first-out).

        Returns:
            The quantity actually issued (may be less than requested if
            insufficient non-expired stock is available).
        """
        if mode not in ("FEFO", "FIFO"):
            raise ValueError(f"unknown issuance mode: {mode!r}")
        if quantity <= 0:
            return 0.0

        usable = [b for b in self.batches if not b.is_expired(period)]
        key = (lambda b: b.expires_at) if mode == "FEFO" else (lambda b: b.received_at)
        usable.sort(key=key)

        remaining_request = quantity
        issued = 0.0
        for batch in usable:
            if remaining_request <= 0:
                break
            take = min(batch.quantity, remaining_request)
            batch.quantity -= take
            remaining_request -= take
            issued += take

        self.batches = [b for b in self.batches if b.quantity > 1e-12]
        return issued
