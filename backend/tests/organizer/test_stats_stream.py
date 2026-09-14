import json
import uuid
from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta

import httpx
import pytest
from sqlalchemy import Engine
from sqlalchemy.orm import sessionmaker

from app.organizer.routes import service

pytestmark = pytest.mark.asyncio


async def create_event(client: httpx.AsyncClient, capacity: int = 2) -> str:
    response = await client.post(
        "/api/events",
        json={
            "title": "SSE Test",
            "description": "",
            "starts_at": (datetime.now(UTC) + timedelta(days=2)).isoformat(),
            "capacity": capacity,
        },
    )
    return response.json()["id"]


def event_data(event: str) -> dict[str, object]:
    lines = event.strip().splitlines()
    assert lines[0] == "event: stats"
    assert lines[1].startswith("data: ")
    return json.loads(lines[1].removeprefix("data: "))


async def never_disconnected() -> bool:
    return False


async def test_two_independent_streams_observe_changed_statistics(
    client: httpx.AsyncClient, database_engine: Engine
) -> None:
    event_id = await create_event(client)
    factory = sessionmaker(bind=database_engine, expire_on_commit=False)
    first_stream = service.stats_events(event_id, factory, never_disconnected, poll_interval=0.001)
    second_stream = service.stats_events(event_id, factory, never_disconnected, poll_interval=0.001)

    assert event_data(await anext(first_stream))["confirmed"] == 0
    assert event_data(await anext(second_stream))["confirmed"] == 0

    await client.post(f"/api/events/{event_id}/registrations", json={"email": "stream@example.com"})

    assert event_data(await anext(first_stream))["confirmed"] == 1
    assert event_data(await anext(second_stream))["confirmed"] == 1
    await first_stream.aclose()
    await second_stream.aclose()


async def test_stream_endpoint_has_sse_headers(
    client: httpx.AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    event_id = await create_event(client)

    async def finite_events(**_kwargs: object) -> AsyncIterator[str]:
        yield 'event: stats\ndata: {"confirmed":0}\n\n'

    monkeypatch.setattr(service, "stats_events", finite_events)

    response = await client.get(f"/api/events/{event_id}/stats/stream")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert response.headers["cache-control"] == "no-cache"
    assert response.text.startswith("event: stats\n")


async def test_stream_route_holds_no_pooled_connection_between_polls(
    client: httpx.AsyncClient, database_engine: Engine, monkeypatch: pytest.MonkeyPatch
) -> None:
    event_id = await create_event(client)
    observed: list[int] = []

    async def observing_events(**kwargs: object) -> AsyncIterator[str]:
        # Runs after the route has finished its preliminary work and the response has started:
        # nothing from the request itself may still hold a connection from the shared pool.
        observed.append(database_engine.pool.checkedout())
        factory = kwargs["session_factory"]
        assert isinstance(factory, sessionmaker)
        assert factory.kw["bind"] is database_engine
        yield 'event: stats\ndata: {"confirmed":0}\n\n'

    monkeypatch.setattr(service, "stats_events", observing_events)

    response = await client.get(f"/api/events/{event_id}/stats/stream")

    assert response.status_code == 200
    assert observed == [0]


async def test_stream_route_returns_404_before_streaming(client: httpx.AsyncClient) -> None:
    response = await client.get(f"/api/events/{uuid.uuid4()}/stats/stream")

    assert response.status_code == 404
    assert response.headers["content-type"].startswith("application/json")
