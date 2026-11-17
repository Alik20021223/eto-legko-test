import pytest
from fastapi.testclient import TestClient

from tests.fake_keitaro import FakeKeitaro


@pytest.fixture
def campaign(api: TestClient) -> dict:
    response = api.post("/api/campaigns", json={"name": "test_au", "geo": "AU", "offer_ids": [1]})
    assert response.status_code == 201, response.text
    return response.json()


def offers(campaign: dict) -> dict[int, tuple[int, bool, bool]]:
    return {o["offer_id"]: (o["share"], o["pinned"], o["removed"]) for o in campaign["offers"]}


def remote_offers(keitaro: FakeKeitaro) -> dict[int, tuple[int, str]]:
    stream = max(keitaro.streams.values(), key=lambda s: s["position"])
    return {o["offer_id"]: (o["share"], o["state"]) for o in stream["offers"]}


def test_create_builds_campaign_with_two_streams(campaign: dict, keitaro: FakeKeitaro):
    (remote,) = keitaro.campaigns.values()
    assert remote["name"] == "test_au"
    assert (remote["domain_id"], remote["group_id"], remote["traffic_source_id"]) == (11, 20, 30)

    first, second = sorted(keitaro.streams.values(), key=lambda s: s["position"])
    assert first["filters"] == [{"name": "country", "mode": "accept", "payload": ["AU"]}]
    assert (first["action_type"], first["action_payload"]) == ("http", "https://google.com")
    assert first["offers"] == []
    assert second["filters"] == []
    assert second["offers"] == [{"offer_id": 1, "share": 100, "state": "active"}]

    assert campaign["keitaro_id"] == remote["id"]
    assert campaign["dirty"] is False
    assert offers(campaign) == {1: (100, False, False)}


def test_create_with_unknown_offer_creates_nothing(api: TestClient, keitaro: FakeKeitaro):
    response = api.post("/api/campaigns", json={"name": "x", "geo": "AU", "offer_ids": [999]})
    assert response.status_code == 404
    assert keitaro.campaigns == {}


def test_create_validates_geo(api: TestClient):
    response = api.post("/api/campaigns", json={"name": "x", "geo": "au", "offer_ids": [1]})
    assert response.status_code == 422


def test_create_rejects_unknown_country(api: TestClient, keitaro: FakeKeitaro):
    response = api.post("/api/campaigns", json={"name": "x", "geo": "ZZ", "offer_ids": [1]})
    assert response.status_code == 422
    assert keitaro.campaigns == {}


def test_geos_lists_country_codes(api: TestClient):
    geos = api.get("/api/geos").json()
    assert {"code": "AU", "name": "Австралия"} in geos
    assert len(geos) == 249
    assert all(len(geo["code"]) == 2 and geo["code"].isupper() for geo in geos)


def test_full_edit_cycle(api: TestClient, campaign: dict, keitaro: FakeKeitaro):
    url = f"/api/campaigns/{campaign['id']}"

    assert api.post(f"{url}/fetch").json()["dirty"] is False

    # Добавление — правка черновика: Keitaro не меняется до push.
    added = api.post(f"{url}/offers", json={"offer_id": 2}).json()
    assert offers(added) == {1: (50, False, False), 2: (50, False, False)}
    assert added["dirty"] is True
    assert remote_offers(keitaro) == {1: (100, "active")}

    pushed = api.post(f"{url}/push").json()
    assert pushed["dirty"] is False
    assert remote_offers(keitaro) == {1: (50, "active"), 2: (50, "active")}

    removed = api.delete(f"{url}/offers/2").json()
    assert offers(removed) == {1: (100, False, False), 2: (0, False, True)}
    # Убранный оффер после push исчезает из потока Keitaro, а локально остаётся.
    pushed = api.post(f"{url}/push").json()
    assert remote_offers(keitaro) == {1: (100, "active")}
    assert offers(pushed) == {1: (100, False, False), 2: (0, False, True)}
    assert offers(api.post(f"{url}/fetch").json()) == {1: (100, False, False), 2: (0, False, True)}

    restored = api.post(f"{url}/offers/2/restore").json()
    assert offers(restored) == {1: (50, False, False), 2: (50, False, False)}

    pinned = api.put(f"{url}/offers/1/pin", json={"share": 70}).json()
    assert offers(pinned) == {1: (70, True, False), 2: (30, False, False)}

    api.post(f"{url}/offers", json={"offer_id": 3})
    recalculated = api.post(f"{url}/weights/recalculate").json()
    assert offers(recalculated) == {
        1: (70, True, False),
        2: (15, False, False),
        3: (15, False, False),
    }

    cancelled = api.post(f"{url}/cancel").json()
    assert cancelled["dirty"] is False
    assert offers(cancelled) == {1: (100, False, False), 2: (0, False, True)}
    assert remote_offers(keitaro) == {1: (100, "active")}


def test_fetch_replaces_draft_with_keitaro_state(
    api: TestClient, campaign: dict, keitaro: FakeKeitaro
):
    url = f"/api/campaigns/{campaign['id']}"
    api.post(f"{url}/offers", json={"offer_id": 2})
    stream = max(keitaro.streams.values(), key=lambda s: s["position"])
    stream["offers"] = [
        {"offer_id": 1, "share": 20, "state": "active"},
        {"offer_id": 3, "share": 80, "state": "active"},
    ]

    fetched = api.post(f"{url}/fetch").json()

    assert fetched["dirty"] is False
    assert offers(fetched) == {1: (20, False, False), 3: (80, False, False)}
    assert [o["name"] for o in fetched["offers"]] == ["Offer A", "Offer C"]


def test_offer_deleted_in_keitaro_stays_removed_and_can_be_restored(
    api: TestClient, campaign: dict, keitaro: FakeKeitaro
):
    url = f"/api/campaigns/{campaign['id']}"
    api.post(f"{url}/offers", json={"offer_id": 2})
    api.post(f"{url}/push")
    stream = max(keitaro.streams.values(), key=lambda s: s["position"])
    stream["offers"] = [{"offer_id": 1, "share": 100, "state": "active"}]

    fetched = api.post(f"{url}/fetch").json()
    assert fetched["dirty"] is False
    assert offers(fetched) == {1: (100, False, False), 2: (0, False, True)}

    restored = api.post(f"{url}/offers/2/restore").json()
    assert offers(restored) == {1: (50, False, False), 2: (50, False, False)}
    api.post(f"{url}/push")
    assert remote_offers(keitaro) == {1: (50, "active"), 2: (50, "active")}


def test_fetch_does_not_rebalance_after_offer_deleted_in_keitaro(
    api: TestClient, campaign: dict, keitaro: FakeKeitaro
):
    url = f"/api/campaigns/{campaign['id']}"
    for offer_id in (2, 3):
        api.post(f"{url}/offers", json={"offer_id": offer_id})
    api.post(f"{url}/push")
    stream = max(keitaro.streams.values(), key=lambda s: s["position"])
    stream["offers"] = [o for o in stream["offers"] if o["offer_id"] != 3]

    fetched = api.post(f"{url}/fetch").json()

    # Сумма активных весов 67%: интерфейс предупреждает, push отказывает до пересчёта.
    assert offers(fetched) == {1: (34, False, False), 2: (33, False, False), 3: (0, False, True)}
    assert api.post(f"{url}/push").status_code == 400
    api.post(f"{url}/weights/recalculate")
    assert api.post(f"{url}/push").status_code == 200
    assert remote_offers(keitaro) == {1: (50, "active"), 2: (50, "active")}


def test_push_refuses_weights_that_do_not_sum_to_100(
    api: TestClient, campaign: dict, keitaro: FakeKeitaro
):
    url = f"/api/campaigns/{campaign['id']}"
    stream = max(keitaro.streams.values(), key=lambda s: s["position"])
    stream["offers"] = [{"offer_id": 1, "share": 75, "state": "active"}]
    api.post(f"{url}/fetch")

    response = api.post(f"{url}/push")

    assert response.status_code == 400
    assert "Сумма весов 75%, должно быть 100%" in response.json()["detail"]


def test_fetch_returns_streams_and_new_flag(api: TestClient, campaign: dict):
    url = f"/api/campaigns/{campaign['id']}"
    assert [(s["position"], s["name"], s["kind"], s["editable"]) for s in campaign["streams"]] == [
        (1, "AU fallback", "redirect", False),
        (2, "offers", "landings", True),
    ]

    added = api.post(f"{url}/offers", json={"offer_id": 2}).json()
    assert {o["offer_id"]: o["new"] for o in added["offers"]} == {1: False, 2: True}

    pushed = api.post(f"{url}/push").json()
    assert {o["offer_id"]: o["new"] for o in pushed["offers"]} == {1: False, 2: False}
    assert api.post(f"{url}/fetch").json()["streams"] == campaign["streams"]


def test_create_with_unknown_domain_is_explicit_error(api: TestClient, keitaro: FakeKeitaro):
    keitaro.domains = [{"id": 10, "name": "other.example"}]

    response = api.post("/api/campaigns", json={"name": "x", "geo": "AU", "offer_ids": [1]})

    assert response.status_code == 404
    assert "kylovoa.com" in response.json()["detail"]
    assert keitaro.campaigns == {}


@pytest.mark.parametrize("name", ["", "   "])
def test_create_rejects_blank_name_with_readable_message(api: TestClient, name: str):
    response = api.post("/api/campaigns", json={"name": name, "geo": "AU", "offer_ids": [1]})
    assert response.status_code == 422
    assert response.json()["detail"] == "Название не может быть пустым"


def test_pin_without_share_keeps_current_weight(api: TestClient, campaign: dict):
    url = f"/api/campaigns/{campaign['id']}"
    api.post(f"{url}/offers", json={"offer_id": 2})

    assert offers(api.put(f"{url}/offers/1/pin").json()) == {1: (50, True, False), 2: (50, False, False)}
    assert api.put(f"{url}/offers/2/pin", json={"share": 0}).json()["detail"] == (
        "Вес — целое число от 1 до 100"
    )


def test_fetch_keeps_pin_while_share_is_unchanged(api: TestClient, campaign: dict):
    url = f"/api/campaigns/{campaign['id']}"
    api.post(f"{url}/offers", json={"offer_id": 2})
    api.put(f"{url}/offers/1/pin", json={"share": 70})
    api.post(f"{url}/push")

    assert offers(api.post(f"{url}/fetch").json()) == {1: (70, True, False), 2: (30, False, False)}


def test_pin_that_leaves_no_room_is_rejected_and_reverted(api: TestClient, campaign: dict):
    url = f"/api/campaigns/{campaign['id']}"
    api.post(f"{url}/offers", json={"offer_id": 2})

    response = api.put(f"{url}/offers/1/pin", json={"share": 100})

    assert response.status_code == 400
    assert offers(api.get(url).json()) == {1: (50, False, False), 2: (50, False, False)}


def test_cannot_remove_last_offer(api: TestClient, campaign: dict):
    response = api.delete(f"/api/campaigns/{campaign['id']}/offers/1")
    assert response.status_code == 400


def test_cannot_add_same_offer_twice(api: TestClient, campaign: dict):
    response = api.post(f"/api/campaigns/{campaign['id']}/offers", json={"offer_id": 1})
    assert response.status_code == 409


def test_keitaro_failure_becomes_502(api: TestClient, campaign: dict, keitaro: FakeKeitaro):
    keitaro.streams.clear()
    response = api.post(f"/api/campaigns/{campaign['id']}/push")
    assert response.status_code == 502
    assert "Stream not found" in response.json()["detail"]


def test_unknown_campaign_is_404(api: TestClient):
    assert api.get("/api/campaigns/999").status_code == 404
