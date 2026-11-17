"""Обмен состоянием потока с офферами между локальной базой и Keitaro."""

from sqlalchemy.orm import Session

from app.keitaro.client import KeitaroClient
from app.keitaro.types import Stream, StreamOffer
from app.models import Campaign, CampaignOffer
from app.services.errors import ConflictError, ServiceError
from app.services.weights import TOTAL


def fetch(db: Session, client: KeitaroClient, campaign: Campaign) -> None:
    """Заменяет локальный черновик тем, что сейчас лежит в Keitaro.

    Оффер, которого в потоке Keitaro больше нет, не пропадает: он остаётся убранным,
    и его можно вернуть через интерфейс. Веса остальных при этом не пересчитываются.
    """
    streams = client.list_streams(campaign.keitaro_id)
    stream = _offer_stream(streams, campaign)
    names = {offer.id: offer.name for offer in client.list_offers()}
    existing = {offer.offer_id: offer for offer in campaign.offers}
    synced = {item["offer_id"] for item in campaign.snapshot}

    for remote in stream.offers:
        removed = remote.state != "active"
        local = existing.pop(remote.offer_id, None)
        if local is None:
            local = CampaignOffer(offer_id=remote.offer_id, pinned=False)
            campaign.offers.append(local)
        # Закрепление живёт только локально: сохраняем его, пока вес в Keitaro не меняли.
        local.pinned = bool(local.pinned and not removed and local.share == remote.share)
        local.name = names.get(remote.offer_id, local.name or f"offer #{remote.offer_id}")
        local.share = 0 if removed else remote.share
        local.removed = removed
    for missing in existing.values():
        if missing.offer_id in synced:
            # Был в черновике на прошлой синхронизации, а в потоке Keitaro его нет.
            missing.share, missing.pinned, missing.removed = 0, False, True
        else:
            # Неотправленное добавление из черновика: Keitaro о нём не знал.
            campaign.offers.remove(missing)

    campaign.streams = describe_streams(streams, campaign.offer_stream_id)
    db.flush()
    campaign.snapshot = campaign.state()


def push(db: Session, client: KeitaroClient, campaign: Campaign) -> None:
    """Отправляет черновик в Keitaro и перечитывает поток, чтобы убедиться в результате.

    Убранные офферы в Keitaro не отправляются и поэтому исчезают из потока;
    локально они остаются, чтобы их можно было вернуть.
    """
    active = [offer for offer in campaign.offers if not offer.removed]
    if not active:
        raise ServiceError("В потоке должен остаться хотя бы один оффер")
    total = sum(offer.share for offer in active)
    if total != TOTAL:
        raise ServiceError(f"Сумма весов {total}%, должно быть {TOTAL}%: пересчитайте веса")

    sent = [StreamOffer(offer_id=offer.offer_id, share=offer.share) for offer in active]
    client.update_stream_offers(campaign.offer_stream_id, sent)

    streams = client.list_streams(campaign.keitaro_id)
    saved = _offer_stream(streams, campaign).offers
    if _comparable(saved) != _comparable(sent):
        raise ConflictError("Keitaro сохранил офферы не так, как они были отправлены")

    campaign.streams = describe_streams(streams, campaign.offer_stream_id)
    db.flush()
    campaign.snapshot = campaign.state()


def describe_streams(streams: list[Stream], offer_stream_id: int) -> list[dict]:
    """Короткое описание потоков кампании для интерфейса, в порядке их позиций."""
    return [
        {
            "id": stream.id,
            "name": stream.name,
            "position": stream.position,
            "kind": stream.schema_,
            # Редактируется только поток с офферами, поток-редирект показывается как есть.
            "editable": stream.id == offer_stream_id,
        }
        for stream in sorted(streams, key=lambda stream: stream.position)
    ]


def _offer_stream(streams: list[Stream], campaign: Campaign) -> Stream:
    for stream in streams:
        if stream.id == campaign.offer_stream_id:
            return stream
    raise ConflictError(
        f"В кампании Keitaro #{campaign.keitaro_id} нет потока #{campaign.offer_stream_id}"
    )


def _comparable(offers: list[StreamOffer]) -> list[tuple[int, int, str]]:
    return sorted((offer.offer_id, offer.share, offer.state) for offer in offers)
