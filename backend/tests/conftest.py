import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.api.deps import get_keitaro
from app.db import Base, get_db
from app.keitaro.client import KeitaroClient
from app.main import app
from tests.fake_keitaro import API_KEY, FakeKeitaro


@pytest.fixture
def keitaro() -> FakeKeitaro:
    return FakeKeitaro()


@pytest.fixture
def client(keitaro: FakeKeitaro) -> KeitaroClient:
    return KeitaroClient("https://keitaro.test", API_KEY, transport=keitaro.transport())


@pytest.fixture
def api(client: KeitaroClient):
    engine = create_engine(
        "sqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False}
    )
    Base.metadata.create_all(engine)

    def override_db():
        with Session(engine, expire_on_commit=False) as session:
            yield session

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_keitaro] = lambda: client
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
