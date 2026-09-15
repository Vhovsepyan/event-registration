from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta

import httpx
import pytest
import pytest_asyncio
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.common.config import Settings, get_settings
from app.db.session import get_session_factory
from app.main import app
from app.organizer.routes import service as organizer_service

pytestmark = pytest.mark.asyncio

KEY = "organizer-secret"


@pytest_asyncio.fixture
async def keyed_client(client: httpx.AsyncClient) -> AsyncIterator[httpx.AsyncClient]:
    app.dependency_overrides[get_settings] = lambda: Settings(organizer_key=KEY)
    try:
        yield client
    finally:
        app.dependency_overrides.pop(get_settings, None)


def event_payload() -> dict[str, object]:
    return {
        "title": "Keyed",
        "description": "",
        "starts_at": (datetime.now(UTC) + timedelta(days=2)).isoformat(),
        "capacity": 1,
    }


async def seed(client: httpx.AsyncClient) -> tuple[str, str, str]:
    """Create an event, a confirmed registration, and its ticket using the key."""
    event = (
        await client.post("/api/events", json=event_payload(), headers={"X-Organizer-Key": KEY})
    ).json()
    registration = (
        await client.post(
            f"/api/events/{event['id']}/registrations", json={"email": "open@example.com"}
        )
    ).json()
    return event["id"], registration["id"], registration["ticket"]["code"]


async def test_protected_routes_require_the_key(keyed_client: httpx.AsyncClient) -> None:
    event_id, _, code = await seed(keyed_client)
    reschedule = {"starts_at": (datetime.now(UTC) + timedelta(days=3)).isoformat()}
    attempts = [
        ("POST", "/api/events", event_payload(), 201),
        ("PATCH", f"/api/events/{event_id}", reschedule, 200),
        ("GET", f"/api/events/{event_id}/stats", None, 200),
        ("POST", "/api/check-ins", {"code": code}, 200),
    ]
    for method, url, body, ok_status in attempts:
        missing = await keyed_client.request(method, url, json=body)
        assert missing.status_code == 401, (method, url)
        assert missing.json()["detail"] == "This action requires the organizer key"
        assert missing.headers["www-authenticate"] == "X-Organizer-Key"
        wrong = await keyed_client.request(
            method, url, json=body, headers={"X-Organizer-Key": "nope"}
        )
        assert wrong.status_code == 401, (method, url)
        accepted = await keyed_client.request(
            method, url, json=body, headers={"X-Organizer-Key": KEY}
        )
        assert accepted.status_code == ok_status, (method, url, accepted.text)


async def test_stream_accepts_the_key_as_a_query_parameter(
    keyed_client: httpx.AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    event_id, _, _ = await seed(keyed_client)

    async def finite_events(**_kwargs: object) -> AsyncIterator[str]:
        yield 'event: stats\ndata: {"confirmed":1}\n\n'

    monkeypatch.setattr(organizer_service, "stats_events", finite_events)

    assert (await keyed_client.get(f"/api/events/{event_id}/stats/stream")).status_code == 401
    denied = await keyed_client.get(
        f"/api/events/{event_id}/stats/stream", params={"organizer_key": "nope"}
    )
    assert denied.status_code == 401
    allowed = await keyed_client.get(
        f"/api/events/{event_id}/stats/stream", params={"organizer_key": KEY}
    )
    assert allowed.status_code == 200
    assert allowed.text.startswith("event: stats\n")


async def test_participant_routes_stay_open(keyed_client: httpx.AsyncClient) -> None:
    event_id, registration_id, code = await seed(keyed_client)
    open_requests = [
        ("GET", "/api/events", None),
        ("GET", f"/api/events/{event_id}", None),
        ("POST", f"/api/events/{event_id}/registrations", {"email": "second@example.com"}),
        ("GET", f"/api/events/{event_id}/registrations/{registration_id}", None),
        ("GET", f"/api/tickets/{code}", None),
        ("POST", f"/api/events/{event_id}/registrations/{registration_id}/cancel", None),
    ]
    for method, url, body in open_requests:
        response = await keyed_client.request(method, url, json=body)
        assert response.status_code in (200, 201), (method, url, response.text)


async def test_readiness_reflects_database_availability(client: httpx.AsyncClient) -> None:
    ready = await client.get("/ready")
    assert ready.status_code == 200
    assert ready.json() == {"status": "ready"}
    assert (await client.get("/health")).json() == {"status": "ok"}

    unreachable = create_engine(
        "postgresql+psycopg://nobody:nothing@localhost:1/nowhere?connect_timeout=1"
    )
    app.dependency_overrides[get_session_factory] = lambda: sessionmaker(bind=unreachable)
    try:
        not_ready = await client.get("/ready")
    finally:
        app.dependency_overrides.pop(get_session_factory, None)
        unreachable.dispose()
    assert not_ready.status_code == 503
    assert not_ready.json()["status"] == "unavailable"
    assert not_ready.json()["reason"] == "OperationalError"
    # Liveness is unaffected by database availability.
    assert (await client.get("/health")).status_code == 200
