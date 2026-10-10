"""Tests for chainsim.core.perishability."""

import pytest

from chainsim.core.perishability import PerishableInventory


def test_receive_and_on_hand():
    inv = PerishableInventory(shelf_life=3)
    inv.receive(10, period=0)
    inv.receive(5, period=1)
    assert inv.on_hand == 15


def test_issue_fefo_consumes_soonest_expiring_first():
    inv = PerishableInventory(shelf_life=3)
    inv.receive(10, period=0)  # expires at period 3
    inv.receive(10, period=1)  # expires at period 4
    issued = inv.issue(6, period=1, mode="FEFO")
    assert issued == 6
    # the period-0 batch (expiring soonest) should be drawn down first
    assert inv.batches[0].expires_at == 3
    assert inv.batches[0].quantity == 4
    assert inv.batches[1].quantity == 10


def test_issue_fifo_consumes_oldest_receipt_first():
    inv = PerishableInventory(shelf_life=5)
    inv.receive(10, period=0)  # older receipt
    inv.receive(10, period=2)  # newer receipt
    issued = inv.issue(6, period=2, mode="FIFO")
    assert issued == 6
    assert inv.batches[0].received_at == 0
    assert inv.batches[0].quantity == 4


def test_issue_caps_at_available_non_expired_stock():
    inv = PerishableInventory(shelf_life=2)
    inv.receive(5, period=0)
    issued = inv.issue(100, period=0)
    assert issued == 5
    assert inv.on_hand == 0


def test_issue_skips_expired_batches():
    inv = PerishableInventory(shelf_life=2)
    inv.receive(5, period=0)  # expires_at = 2
    issued = inv.issue(5, period=2)  # already expired by period 2
    assert issued == 0.0


def test_expire_removes_and_tallies_waste():
    inv = PerishableInventory(shelf_life=2)
    inv.receive(10, period=0)  # expires_at = 2
    inv.receive(4, period=1)  # expires_at = 3
    wasted = inv.expire(period=2)
    assert wasted == 10
    assert inv.total_waste == 10
    assert inv.on_hand == 4
    # already-purged batches don't waste again
    assert inv.expire(period=2) == 0.0


def test_invalid_shelf_life_rejected():
    with pytest.raises(ValueError):
        PerishableInventory(shelf_life=0)


def test_invalid_issue_mode_rejected():
    inv = PerishableInventory(shelf_life=2)
    inv.receive(5, period=0)
    with pytest.raises(ValueError):
        inv.issue(1, period=0, mode="LIFO")
