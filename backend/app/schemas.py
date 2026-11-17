from pydantic import BaseModel, ConfigDict, field_validator

from app.geo import COUNTRIES

# Сообщения валидаторов показываются пользователю как есть (см. обработчик в main.py).


class OfferOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    offer_id: int
    name: str
    share: int
    pinned: bool
    removed: bool
    # Добавлен в черновик, но ещё не отправлен в Keitaro.
    new: bool


class StreamOut(BaseModel):
    id: int
    name: str
    position: int
    # Схема потока в Keitaro: redirect, landings или action.
    kind: str
    editable: bool


class CampaignOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    keitaro_id: int
    name: str
    alias: str
    geo: str
    dirty: bool
    streams: list[StreamOut]
    offers: list[OfferOut]


class CampaignCreateIn(BaseModel):
    name: str
    geo: str
    offer_ids: list[int]

    @field_validator("name")
    @classmethod
    def name_is_not_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Название не может быть пустым")
        if len(value) > 255:
            raise ValueError("Название не может быть длиннее 255 символов")
        return value

    @field_validator("geo")
    @classmethod
    def geo_is_known_country(cls, value: str) -> str:
        if value not in COUNTRIES:
            raise ValueError(f"Неизвестный код страны «{value}»: нужен код вида AU")
        return value

    @field_validator("offer_ids")
    @classmethod
    def has_offers(cls, value: list[int]) -> list[int]:
        if not value:
            raise ValueError("Выберите хотя бы один оффер")
        return value


class OfferAddIn(BaseModel):
    offer_id: int


class PinIn(BaseModel):
    # Без share закрепляется текущий вес оффера.
    share: int | None = None

    @field_validator("share")
    @classmethod
    def share_is_percent(cls, value: int | None) -> int | None:
        if value is not None and not 1 <= value <= 100:
            raise ValueError("Вес — целое число от 1 до 100")
        return value


class KeitaroOfferOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str


class GeoOut(BaseModel):
    code: str
    name: str
