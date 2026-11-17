"""Правки локального черновика. В Keitaro они попадают только через sync.push."""

from sqlalchemy.orm import Session

from app.keitaro.client import KeitaroClient
from app.models import Campaign, CampaignOffer
from app.services.errors import ConflictError, NotFoundError, ServiceError
from app.services.weights import rebalance


def add_offer(db: Session, client: KeitaroClient, campaign: Campaign, offer_id: int) -> None:
    if any(offer.offer_id == offer_id for offer in campaign.offers):
        raise ConflictError("Оффер уже есть в кампании: если он убран, верните его")
    remote = next((offer for offer in client.list_offers() if offer.id == offer_id), None)
    if remote is None:
        raise NotFoundError(f"В Keitaro нет оффера #{offer_id}")
    campaign.offers.append(CampaignOffer(offer_id=offer_id, name=remote.name, share=0))
    rebalance(campaign.offers)
    db.flush()


def remove_offer(campaign: Campaign, offer_id: int) -> None:
    offer = _get(campaign, offer_id)
    if offer.removed:
        raise ConflictError("Оффер уже убран")
    if sum(not other.removed for other in campaign.offers) == 1:
        raise ServiceError("Нельзя убрать последний оффер")
    offer.removed = True
    rebalance(campaign.offers)


def restore_offer(campaign: Campaign, offer_id: int) -> None:
    offer = _get(campaign, offer_id)
    if not offer.removed:
        raise ConflictError("Оффер не был убран")
    offer.removed = False
    rebalance(campaign.offers)


def pin_offer(campaign: Campaign, offer_id: int, share: int | None = None) -> None:
    """Закрепляет вес оффера; без share закрепляется текущий."""
    offer = _get(campaign, offer_id)
    if offer.removed:
        raise ConflictError("Нельзя закрепить вес убранного оффера")
    if share is None:
        share = offer.share
    if share < 1:
        raise ServiceError("Вес — целое число от 1 до 100")
    previous = offer.share, offer.pinned
    offer.share, offer.pinned = share, True
    try:
        rebalance(campaign.offers)
    except ServiceError:
        offer.share, offer.pinned = previous
        raise


def unpin_offer(campaign: Campaign, offer_id: int) -> None:
    offer = _get(campaign, offer_id)
    if not offer.pinned:
        raise ConflictError("Вес оффера не закреплён")
    offer.pinned = False
    rebalance(campaign.offers)


def recalculate(campaign: Campaign) -> None:
    rebalance(campaign.offers)


def cancel(db: Session, campaign: Campaign) -> None:
    """Откатывает черновик к состоянию последнего fetch/push."""
    saved = {item["offer_id"]: item for item in campaign.snapshot}
    for offer in list(campaign.offers):
        item = saved.get(offer.offer_id)
        if item is None:
            campaign.offers.remove(offer)
            continue
        offer.share = item["share"]
        offer.pinned = item["pinned"]
        offer.removed = item["removed"]
    db.flush()


def _get(campaign: Campaign, offer_id: int) -> CampaignOffer:
    for offer in campaign.offers:
        if offer.offer_id == offer_id:
            return offer
    raise NotFoundError(f"В кампании нет оффера #{offer_id}")
