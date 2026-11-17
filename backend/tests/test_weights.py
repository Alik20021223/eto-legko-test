from dataclasses import dataclass

import pytest

from app.services.errors import ServiceError
from app.services.weights import rebalance, split_evenly


@dataclass
class Item:
    share: int = 0
    pinned: bool = False
    removed: bool = False


def shares(items: list[Item]) -> list[int]:
    return [item.share for item in items]


def test_split_evenly_gives_remainder_to_first():
    assert split_evenly(100, 3) == [34, 33, 33]
    assert split_evenly(100, 4) == [25, 25, 25, 25]


def test_rebalance_splits_between_free_offers():
    items = [Item(), Item(), Item()]
    rebalance(items)
    assert shares(items) == [34, 33, 33]


def test_rebalance_keeps_pinned_and_splits_the_rest():
    items = [Item(share=50, pinned=True), Item(share=1), Item(share=99)]
    rebalance(items)
    assert shares(items) == [50, 25, 25]


def test_rebalance_zeroes_and_unpins_removed():
    items = [Item(share=40, pinned=True, removed=True), Item(share=60)]
    rebalance(items)
    assert shares(items) == [0, 100]
    assert items[0].pinned is False


def test_rebalance_rejects_pins_leaving_nothing_for_free_offers():
    items = [Item(share=100, pinned=True), Item()]
    with pytest.raises(ServiceError):
        rebalance(items)


def test_rebalance_rejects_all_pinned_not_summing_to_100():
    items = [Item(share=60, pinned=True), Item(share=30, pinned=True)]
    with pytest.raises(ServiceError):
        rebalance(items)


def test_rebalance_without_active_offers_is_noop():
    items = [Item(share=10, removed=True)]
    rebalance(items)
    assert shares(items) == [0]
