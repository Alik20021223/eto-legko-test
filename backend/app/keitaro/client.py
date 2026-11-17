"""Клиент Keitaro Admin API. Единственное место, которое знает его пути и форматы."""

import json
from typing import Any

import httpx

from app.keitaro.types import (
    Campaign,
    CampaignCreate,
    Domain,
    Group,
    Offer,
    Stream,
    StreamCreate,
    StreamOffer,
    TrafficSource,
)


class KeitaroError(Exception):
    def __init__(self, message: str, status_code: int | None = None):
        super().__init__(message)
        self.status_code = status_code


class KeitaroClient:
    def __init__(
        self,
        base_url: str,
        api_key: str,
        *,
        transport: httpx.BaseTransport | None = None,
        timeout: float = 20.0,
    ):
        self._http = httpx.Client(
            base_url=f"{base_url.rstrip('/')}/admin_api/v1",
            headers={"Api-Key": api_key},
            transport=transport,
            timeout=timeout,
        )

    def close(self) -> None:
        self._http.close()

    def _request(self, method: str, path: str, **kwargs: Any) -> Any:
        try:
            response = self._http.request(method, path, **kwargs)
        except httpx.HTTPError as exc:
            raise KeitaroError(f"Keitaro недоступен: {exc}") from exc
        if response.is_error:
            raise KeitaroError(_error_message(response), response.status_code)
        try:
            return response.json()
        except ValueError as exc:
            raise KeitaroError("Keitaro вернул не JSON", response.status_code) from exc

    def list_offers(self) -> list[Offer]:
        return [Offer.model_validate(item) for item in self._request("GET", "/offers")]

    def list_domains(self) -> list[Domain]:
        return [Domain.model_validate(item) for item in self._request("GET", "/domains")]

    def list_groups(self) -> list[Group]:
        data = self._request("GET", "/groups", params={"type": "campaigns"})
        return [Group.model_validate(item) for item in data]

    def list_traffic_sources(self) -> list[TrafficSource]:
        data = self._request("GET", "/traffic_sources")
        return [TrafficSource.model_validate(item) for item in data]

    def create_campaign(self, payload: CampaignCreate) -> Campaign:
        data = self._request("POST", "/campaigns", json=payload.model_dump())
        return Campaign.model_validate(data)

    def list_streams(self, campaign_id: int) -> list[Stream]:
        data = self._request("GET", f"/campaigns/{campaign_id}/streams")
        return [Stream.model_validate(item) for item in data]

    def create_stream(self, payload: StreamCreate) -> Stream:
        body = payload.model_dump(by_alias=True, exclude_none=True)
        return Stream.model_validate(self._request("POST", "/streams", json=body))

    def update_stream_offers(self, stream_id: int, offers: list[StreamOffer]) -> Stream:
        """PUT частичный: меняются только присланные поля, список offers заменяется целиком.

        Оффер, которого нет в списке, Keitaro удаляет из потока — так офферы и убираются.
        """
        body = {"offers": [offer.model_dump() for offer in offers]}
        return Stream.model_validate(self._request("PUT", f"/streams/{stream_id}", json=body))


def _error_message(response: httpx.Response) -> str:
    """Keitaro отвечает {"error": "..."}, а на ошибки валидации — {"поле": ["..."]}."""
    try:
        data = response.json()
    except ValueError:
        return f"Keitaro {response.status_code}: {response.text[:200]}"
    if isinstance(data, dict) and isinstance(data.get("error"), str):
        return f"Keitaro {response.status_code}: {data['error']}"
    return f"Keitaro {response.status_code}: {json.dumps(data, ensure_ascii=False)[:200]}"
