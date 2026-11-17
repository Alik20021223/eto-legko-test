"""Модели Keitaro Admin API: только те поля, которые использует приложение.

Сверено со спецификацией OpenAPI (Keitaro Admin API v1): схемы CampaignRequest,
StreamObject, FilterStreamRequest, OfferStreamRequest и ответы Campaign, Stream.
"""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class KeitaroModel(BaseModel):
    model_config = ConfigDict(extra="ignore", populate_by_name=True)


class Named(KeitaroModel):
    id: int
    name: str


class Offer(Named):
    pass


class Domain(Named):
    pass


class Group(Named):
    pass


class TrafficSource(Named):
    pass


class Campaign(Named):
    alias: str


class CampaignCreate(KeitaroModel):
    # Обязательны только name и alias, остальное — реквизиты нашего шаблона.
    name: str
    alias: str
    domain_id: int
    group_id: int
    traffic_source_id: int
    type: Literal["position", "weight"] = "position"
    state: Literal["active", "disabled"] = "active"


class StreamFilter(KeitaroModel):
    name: str
    mode: Literal["accept", "reject"]
    payload: list[str]


class StreamOffer(KeitaroModel):
    offer_id: int
    # Целый процент трафика.
    share: int
    # В запросе допустимы active и disabled; в ответе Keitaro отдаёт произвольную строку.
    # Приложение шлёт только active: убранный оффер просто не попадает в список.
    state: str = "active"


class StreamCreate(KeitaroModel):
    campaign_id: int
    name: str
    position: int
    type: Literal["regular", "forced", "default"] = "regular"
    schema_: Literal["redirect", "action", "landings"] = Field(alias="schema")
    # Обязателен для любого потока, в том числе для потока с офферами.
    action_type: str = "http"
    action_payload: str | None = None
    # В Keitaro по умолчанию false: без явного true поток не сохраняет клики.
    collect_clicks: bool = True
    filters: list[StreamFilter] = []
    offers: list[StreamOffer] = []


class Stream(KeitaroModel):
    """Ответ Keitaro. Фильтры и action_payload приходят в другом виде, чем отправляются,
    и приложению не нужны, поэтому здесь их нет."""

    id: int
    name: str = ""
    position: int = 0
    schema_: str = Field(default="", alias="schema")
    offers: list[StreamOffer] = []
