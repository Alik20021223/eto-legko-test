from fastapi import APIRouter
from sqlalchemy import select

from app.api.deps import AppSettings, CurrentCampaign, Db, Keitaro
from app.geo import COUNTRIES
from app.models import Campaign
from app.schemas import (
    CampaignCreateIn,
    CampaignOut,
    GeoOut,
    KeitaroOfferOut,
    OfferAddIn,
    PinIn,
)
from app.services import creator, editor, sync

router = APIRouter(prefix="/api")


@router.get("/offers", response_model=list[KeitaroOfferOut])
def list_keitaro_offers(keitaro: Keitaro):
    return keitaro.list_offers()


@router.get("/geos", response_model=list[GeoOut])
def list_geos():
    """Справочник гео: код ISO 3166-1 alpha-2 и название, по алфавиту названий."""
    countries = sorted(COUNTRIES.items(), key=lambda item: item[1])
    return [GeoOut(code=code, name=name) for code, name in countries]


@router.get("/campaigns", response_model=list[CampaignOut])
def list_campaigns(db: Db):
    return db.scalars(select(Campaign).order_by(Campaign.id.desc())).all()


@router.post("/campaigns", response_model=CampaignOut, status_code=201)
def create_campaign(body: CampaignCreateIn, db: Db, keitaro: Keitaro, settings: AppSettings):
    campaign = creator.create_campaign(
        db, keitaro, settings, name=body.name, geo=body.geo, offer_ids=body.offer_ids
    )
    db.commit()
    return campaign


@router.get("/campaigns/{campaign_id}", response_model=CampaignOut)
def get_campaign(campaign: CurrentCampaign):
    return campaign


@router.post("/campaigns/{campaign_id}/fetch", response_model=CampaignOut)
def fetch(campaign: CurrentCampaign, db: Db, keitaro: Keitaro):
    sync.fetch(db, keitaro, campaign)
    db.commit()
    return campaign


@router.post("/campaigns/{campaign_id}/push", response_model=CampaignOut)
def push(campaign: CurrentCampaign, db: Db, keitaro: Keitaro):
    sync.push(db, keitaro, campaign)
    db.commit()
    return campaign


@router.post("/campaigns/{campaign_id}/cancel", response_model=CampaignOut)
def cancel(campaign: CurrentCampaign, db: Db):
    editor.cancel(db, campaign)
    db.commit()
    return campaign


@router.post("/campaigns/{campaign_id}/weights/recalculate", response_model=CampaignOut)
def recalculate_weights(campaign: CurrentCampaign, db: Db):
    editor.recalculate(campaign)
    db.commit()
    return campaign


@router.post("/campaigns/{campaign_id}/offers", response_model=CampaignOut)
def add_offer(body: OfferAddIn, campaign: CurrentCampaign, db: Db, keitaro: Keitaro):
    editor.add_offer(db, keitaro, campaign, body.offer_id)
    db.commit()
    return campaign


@router.delete("/campaigns/{campaign_id}/offers/{offer_id}", response_model=CampaignOut)
def remove_offer(offer_id: int, campaign: CurrentCampaign, db: Db):
    editor.remove_offer(campaign, offer_id)
    db.commit()
    return campaign


@router.post("/campaigns/{campaign_id}/offers/{offer_id}/restore", response_model=CampaignOut)
def restore_offer(offer_id: int, campaign: CurrentCampaign, db: Db):
    editor.restore_offer(campaign, offer_id)
    db.commit()
    return campaign


@router.put("/campaigns/{campaign_id}/offers/{offer_id}/pin", response_model=CampaignOut)
def pin_offer(offer_id: int, campaign: CurrentCampaign, db: Db, body: PinIn | None = None):
    editor.pin_offer(campaign, offer_id, body.share if body else None)
    db.commit()
    return campaign


@router.delete("/campaigns/{campaign_id}/offers/{offer_id}/pin", response_model=CampaignOut)
def unpin_offer(offer_id: int, campaign: CurrentCampaign, db: Db):
    editor.unpin_offer(campaign, offer_id)
    db.commit()
    return campaign
