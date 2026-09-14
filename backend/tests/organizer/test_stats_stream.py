import json
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
