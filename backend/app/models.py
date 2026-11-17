from datetime import datetime

from sqlalchemy import JSON, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class Campaign(Base):
    """Локальная копия кампании Keitaro и черновик состава её потока с офферами."""

    __tablename__ = "campaigns"

    id: Mapped[int] = mapped_column(primary_key=True)
    keitaro_id: Mapped[int] = mapped_column(unique=True)
    name: Mapped[str] = mapped_column(String(255))
    alias: Mapped[str] = mapped_column(String(64))
    geo: Mapped[str] = mapped_column(String(2))
    offer_stream_id: Mapped[int]
    # Состав офферов на момент последнего fetch/push: с ним сравнивается черновик.
    snapshot: Mapped[list] = mapped_column(JSON, default=list)
    # Потоки кампании на момент последнего fetch/push (см. sync.describe_streams).
    streams: Mapped[list] = mapped_column(JSON, default=list, server_default="[]")
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    offers: Mapped[list["CampaignOffer"]] = relationship(
        back_populates="campaign",
        cascade="all, delete-orphan",
        order_by="CampaignOffer.id",
    )

    def state(self) -> list[dict]:
        return sorted((offer.state() for offer in self.offers), key=lambda o: o["offer_id"])

    @property
    def dirty(self) -> bool:
        return self.state() != self.snapshot


class CampaignOffer(Base):
    __tablename__ = "campaign_offers"
    __table_args__ = (UniqueConstraint("campaign_id", "offer_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    campaign_id: Mapped[int] = mapped_column(ForeignKey("campaigns.id", ondelete="CASCADE"))
    offer_id: Mapped[int]
    name: Mapped[str] = mapped_column(String(255))
    share: Mapped[int] = mapped_column(default=0)
    # Закреплённый вес не меняется при пересчёте. Понятие локальное, в Keitaro его нет.
    pinned: Mapped[bool] = mapped_column(default=False)
    # Убранный оффер остаётся в потоке Keitaro выключенным, чтобы его можно было вернуть.
    removed: Mapped[bool] = mapped_column(default=False)

    campaign: Mapped[Campaign] = relationship(back_populates="offers")

    @property
    def new(self) -> bool:
        """Добавлен в черновик после последнего fetch/push: в Keitaro его ещё нет."""
        return all(item["offer_id"] != self.offer_id for item in self.campaign.snapshot)

    def state(self) -> dict:
        return {
            "offer_id": self.offer_id,
            "name": self.name,
            "share": self.share,
            "pinned": self.pinned,
            "removed": self.removed,
        }
