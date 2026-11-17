"""Keitaro Admin API в памяти: HTTP-контракт, под который написан keitaro/client.py."""

import json
import re
from collections.abc import Callable

import httpx

API_KEY = "test-key"
PREFIX = "/admin_api/v1"


class FakeKeitaro:
    def __init__(self) -> None:
        self.offers = [
            {"id": 1, "name": "Offer A", "state": "active"},
            {"id": 2, "name": "Offer B", "state": "active"},
            {"id": 3, "name": "Offer C", "state": "active"},
        ]
        self.domains = [{"id": 10, "name": "other.example"}, {"id": 11, "name": "kylovoa.com"}]
        self.groups = [{"id": 20, "name": "FORTESTS", "type": "campaigns"}]
        self.traffic_sources = [{"id": 30, "name": "FORTESTS"}]
        self.campaigns: dict[int, dict] = {}
        self.streams: dict[int, dict] = {}
        self.requests: list[httpx.Request] = []
        self._next_id = 100
        self._routes: list[tuple[str, re.Pattern[str], Callable[..., httpx.Response]]] = [
            ("GET", re.compile(r"/offers"), lambda _: _ok(self.offers)),
            ("GET", re.compile(r"/domains"), lambda _: _ok(self.domains)),
            ("GET", re.compile(r"/groups"), self._list_groups),
            ("GET", re.compile(r"/traffic_sources"), lambda _: _ok(self.traffic_sources)),
            ("POST", re.compile(r"/campaigns"), self._create_campaign),
            ("GET", re.compile(r"/campaigns/(\d+)/streams"), self._list_streams),
            ("POST", re.compile(r"/streams"), self._create_stream),
            ("PUT", re.compile(r"/streams/(\d+)"), self._update_stream),
        ]

    def transport(self) -> httpx.MockTransport:
        return httpx.MockTransport(self._handle)

    def _handle(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        if request.headers.get("Api-Key") != API_KEY:
            return _error(401, "Unauthorized")
        path = request.url.path.removeprefix(PREFIX)
        for method, pattern, handler in self._routes:
            match = pattern.fullmatch(path)
            if match and method == request.method:
                return handler(request, *map(int, match.groups()))
        return _error(404, "Not found")

    def _list_groups(self, request: httpx.Request) -> httpx.Response:
        if request.url.params.get("type") != "campaigns":
            return _error(400, "type is required")
        return _ok(self.groups)

    def _create_campaign(self, request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        missing = [field for field in ("name", "alias") if not body.get(field)]
        if missing:
            return httpx.Response(406, json={field: ["is required"] for field in missing})
        if any(c["alias"] == body["alias"] for c in self.campaigns.values()):
            return httpx.Response(406, json={"alias": ["is not unique"]})
        campaign = {"id": self._new_id(), **body}
        self.campaigns[campaign["id"]] = campaign
        return _ok(campaign)

    def _list_streams(self, _: httpx.Request, campaign_id: int) -> httpx.Response:
        if campaign_id not in self.campaigns:
            return _error(404, "Campaign not found")
        streams = [s for s in self.streams.values() if s["campaign_id"] == campaign_id]
        return _ok(sorted(streams, key=lambda s: s["position"]))

    def _create_stream(self, request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        required = ("campaign_id", "schema", "type", "name", "action_type")
        missing = [field for field in required if field not in body]
        if missing:
            return httpx.Response(406, json={field: ["is required"] for field in missing})
        if body["campaign_id"] not in self.campaigns:
            return _error(404, "Campaign not found")
        invalid = self._validate_offers(body.get("offers", []))
        if invalid:
            return invalid
        stream = {
            "id": self._new_id(),
            "state": "active",
            "position": 1,
            "filters": [],
            "offers": [],
            **body,
        }
        self.streams[stream["id"]] = stream
        return _ok(stream)

    def _update_stream(self, request: httpx.Request, stream_id: int) -> httpx.Response:
        if stream_id not in self.streams:
            return _error(404, "Stream not found")
        body = json.loads(request.content)
        invalid = self._validate_offers(body.get("offers", []))
        if invalid:
            return invalid
        # PUT частичный: меняются только присланные поля, список offers заменяется целиком,
        # то есть оффер, которого нет в запросе, из потока удаляется.
        self.streams[stream_id].update(body)
        return _ok(self.streams[stream_id])

    def _validate_offers(self, offers: list[dict]) -> httpx.Response | None:
        known = {offer["id"] for offer in self.offers}
        for offer in offers:
            if offer["offer_id"] not in known:
                return _error(422, "Offer not found")
            if type(offer["share"]) is not int:
                return _error(422, "share must be integer")
        return None

    def _new_id(self) -> int:
        self._next_id += 1
        return self._next_id


def _ok(data: object) -> httpx.Response:
    return httpx.Response(200, json=data)


def _error(status: int, message: str) -> httpx.Response:
    return httpx.Response(status, json={"error": message})
