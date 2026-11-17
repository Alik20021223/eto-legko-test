from collections.abc import Iterator
from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.db import get_db
from app.keitaro.client import KeitaroClient
from app.models import Campaign
from app.services.errors import NotFoundError


def get_keitaro(settings: Annotated[Settings, Depends(get_settings)]) -> Iterator[KeitaroClient]:
    client = KeitaroClient(settings.keitaro_url, settings.keitaro_api_key)
    try:
        yield client
    finally:
        client.close()


Db = Annotated[Session, Depends(get_db)]
Keitaro = Annotated[KeitaroClient, Depends(get_keitaro)]
AppSettings = Annotated[Settings, Depends(get_settings)]


def get_campaign(campaign_id: int, db: Db) -> Campaign:
    campaign = db.get(Campaign, campaign_id)
    if campaign is None:
        raise NotFoundError(f"Кампания #{campaign_id} не найдена")
    return campaign


CurrentCampaign = Annotated[Campaign, Depends(get_campaign)]
