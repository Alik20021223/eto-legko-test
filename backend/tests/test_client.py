import json

import httpx
import pytest

from app.keitaro.client import KeitaroClient, KeitaroError
from app.keitaro.types import CampaignCreate, StreamCreate, StreamFilter, StreamOffer
from tests.fake_keitaro import API_KEY, FakeKeitaro


def make_campaign(client: KeitaroClient) -> int:
    payload = CampaignCreate(
        name="test", alias="abc", domain_id=11, group_id=20, traffic_source_id=30
    )
    return client.create_campaign(payload).id


def test_sends_api_key_to_admin_api(client: KeitaroClient, keitaro: FakeKeitaro):
    client.list_offers()
    request = keitaro.requests[-1]
    assert request.headers["Api-Key"] == API_KEY
    assert request.url.path == "/admin_api/v1/offers"


def test_wrong_key_raises_keitaro_error(keitaro: FakeKeitaro):
    client = KeitaroClient("https://keitaro.test", "wrong", transport=keitaro.transport())
    with pytest.raises(KeitaroError) as error:
        client.list_offers()
    assert error.value.status_code == 401
    assert "Unauthorized" in str(error.value)


def test_network_failure_raises_keitaro_error():
    def fail(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("boom", request=request)

    client = KeitaroClient("https://keitaro.test", API_KEY, transport=httpx.MockTransport(fail))
    with pytest.raises(KeitaroError):
        client.list_offers()


def test_lists_reference_data(client: KeitaroClient):
    assert [offer.name for offer in client.list_offers()] == ["Offer A", "Offer B", "Offer C"]
    assert "kylovoa.com" in [domain.name for domain in client.list_domains()]
    assert [group.name for group in client.list_groups()] == ["FORTESTS"]
    assert [source.name for source in client.list_traffic_sources()] == ["FORTESTS"]


def test_create_stream_sends_keitaro_field_names(client: KeitaroClient, keitaro: FakeKeitaro):
    campaign_id = make_campaign(client)
    stream = client.create_stream(
        StreamCreate(
            campaign_id=campaign_id,
            name="not AU",
            position=1,
            schema="redirect",
            action_type="http",
            action_payload="https://google.com",
            filters=[StreamFilter(name="country", mode="reject", payload=["AU"])],
        )
    )
    body = json.loads(keitaro.requests[-1].content)
    assert body["schema"] == "redirect"
    assert "schema_" not in body
    assert body["filters"] == [{"name": "country", "mode": "reject", "payload": ["AU"]}]
    assert body["action_payload"] == "https://google.com"
    assert body["collect_clicks"] is True
    assert client.list_streams(campaign_id) == [stream]


def test_update_stream_offers_sends_only_offers(client: KeitaroClient, keitaro: FakeKeitaro):
    campaign_id = make_campaign(client)
    stream = client.create_stream(
        StreamCreate(
            campaign_id=campaign_id,
            name="offers",
            position=2,
            schema="landings",
            offers=[StreamOffer(offer_id=1, share=100)],
        )
    )
    assert json.loads(keitaro.requests[-1].content)["action_type"] == "http"
    offers = [
        StreamOffer(offer_id=1, share=60),
        StreamOffer(offer_id=2, share=40),
        StreamOffer(offer_id=3, share=0, state="disabled"),
    ]
    updated = client.update_stream_offers(stream.id, offers)

    request = keitaro.requests[-1]
    assert request.method == "PUT"
    assert list(json.loads(request.content)) == ["offers"]
    assert updated.offers == offers
    assert keitaro.streams[stream.id]["schema"] == "landings"


def test_validation_error_body_is_reported(client: KeitaroClient):
    make_campaign(client)
    with pytest.raises(KeitaroError) as error:
        make_campaign(client)
    assert error.value.status_code == 406
    assert "alias" in str(error.value)
