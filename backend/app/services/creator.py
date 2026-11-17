"""Создание кампании в Keitaro: два потока и локальная запись о ней."""

import secrets
import string
from collections.abc import Sequence

from sqlalchemy.orm import Session

from app.config import Settings
from app.keitaro.client import KeitaroClient
from app.keitaro.types import CampaignCreate, Named, StreamCreate, StreamFilter, StreamOffer
from app.models import Campaign, CampaignOffer
from app.services.errors import NotFoundError, ServiceError
from app.services.sync import describe_streams
from app.services.weights import TOTAL, split_evenly

ALIAS_ALPHABET = string.ascii_lowercase + string.digits


def create_campaign(
    db: Session,
    client: KeitaroClient,
    settings: Settings,
    *,
    name: str,
    geo: str,
    offer_ids: list[int],
) -> Campaign:
    if len(set(offer_ids)) != len(offer_ids):
        raise ServiceError("Офферы не должны повторяться")
    if len(offer_ids) > TOTAL:
        raise ServiceError(f"В потоке не может быть больше {TOTAL} офферов")

    # Сначала всё читаем и проверяем, чтобы не оставить в Keitaro кампанию-обрубок.
    known = {offer.id: offer for offer in client.list_offers()}
    missing = [offer_id for offer_id in offer_ids if offer_id not in known]
    if missing:
        raise NotFoundError(f"В Keitaro нет офферов: {missing}")
    domain = _by_name(client.list_domains(), settings.campaign_domain, "домен")
    group = _by_name(client.list_groups(), settings.campaign_group, "группа")
    source = _by_name(
        client.list_traffic_sources(), settings.campaign_traffic_source, "источник"
    )

    remote = client.create_campaign(
        CampaignCreate(
            name=name,
            alias="".join(secrets.choice(ALIAS_ALPHABET) for _ in range(8)),
            domain_id=domain.id,
            group_id=group.id,
            traffic_source_id=source.id,
        )
    )
    fallback_stream = client.create_stream(
        StreamCreate(
            campaign_id=remote.id,
            name=f"{geo} fallback",
            position=1,
            schema="redirect",
            action_type="http",
            action_payload=settings.fallback_url,
            filters=[StreamFilter(name="country", mode="accept", payload=[geo])],
        )
    )
    shares = split_evenly(TOTAL, len(offer_ids))
    offer_stream = client.create_stream(
        StreamCreate(
            campaign_id=remote.id,
            name="offers",
            position=2,
            schema="landings",
            offers=[
                StreamOffer(offer_id=offer_id, share=share)
                for offer_id, share in zip(offer_ids, shares)
            ],
        )
    )

    campaign = Campaign(
        keitaro_id=remote.id,
        name=remote.name,
        alias=remote.alias,
        geo=geo,
        offer_stream_id=offer_stream.id,
        streams=describe_streams([fallback_stream, offer_stream], offer_stream.id),
        offers=[
            CampaignOffer(offer_id=offer_id, name=known[offer_id].name, share=share)
            for offer_id, share in zip(offer_ids, shares)
        ],
    )
    db.add(campaign)
    db.flush()
    campaign.snapshot = campaign.state()
    return campaign


def _by_name[T: Named](items: Sequence[T], name: str, kind: str) -> T:
    for item in items:
        if item.name == name:
            return item
    raise NotFoundError(f"В Keitaro не найден(а) {kind} «{name}»")
