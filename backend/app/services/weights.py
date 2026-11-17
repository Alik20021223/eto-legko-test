"""Пересчёт весов офферов: целые проценты, у активных офферов в сумме ровно 100."""

from typing import Protocol

from app.services.errors import ServiceError

TOTAL = 100


class Weighted(Protocol):
    share: int
    pinned: bool
    removed: bool


def split_evenly(total: int, parts: int) -> list[int]:
    """Делит total на parts целых долей; остаток достаётся первым."""
    base, extra = divmod(total, parts)
    return [base + 1 if index < extra else base for index in range(parts)]


def rebalance(offers: list[Weighted]) -> None:
    """Закреплённые веса не трогает, остаток до 100 делит поровну между остальными.

    Убранные офферы получают 0 и теряют закрепление.
    """
    for offer in offers:
        if offer.removed:
            offer.share = 0
            offer.pinned = False

    active = [offer for offer in offers if not offer.removed]
    if not active:
        return
    free = [offer for offer in active if not offer.pinned]
    pinned_total = sum(offer.share for offer in active if offer.pinned)
    remainder = TOTAL - pinned_total

    if not free:
        if remainder != 0:
            raise ServiceError(
                f"Все офферы закреплены, но сумма весов {pinned_total}, а нужно {TOTAL}"
            )
        return
    if remainder < len(free):
        raise ServiceError(
            f"Закреплено {pinned_total}%: на {len(free)} незакреплённых офферов "
            "не остаётся хотя бы по 1%"
        )
    for offer, share in zip(free, split_evenly(remainder, len(free))):
        offer.share = share
