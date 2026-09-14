import uuid
from datetime import UTC, datetime, timedelta

import httpx
import pytest

pytestmark = pytest.mark.asyncio


async def create_event(client: httpx.AsyncClient, capacity: int = 2) -> str:
    response = await client.post(
        "/api/events",
        json={
            "title": "Statistics Test",
            "description": "",
            "starts_at": (datetime.now(UTC) + timedelta(days=2)).isoformat(),
            "capacity": capacity,
        },
    )
    return response.json()["id"]


async def register(client: httpx.AsyncClient, event_id: str, email: str) -> dict[str, object]:
    response = await client.post(f"/api/events/{event_id}/registrations", json={"email": email})
    return response.json()


async def test_statistics_follow_authoritative_lifecycle_state(client: httpx.AsyncClient) -> None:
    event_id = await create_event(client)
    first = await register(client, event_id, "first@example.com")
    await register(client, event_id, "second@example.com")
    await register(client, event_id, "waitlisted@example.com")

    initial = await client.get(f"/api/events/{event_id}/stats")
    assert initial.json() == {
        "event_id": event_id,
        "capacity": 2,
        "confirmed": 2,
        "waitlisted": 1,
        "checked_in": 0,
    }

    await client.post("/api/check-ins", json={"code": first["ticket"]["code"]})
    checked_in = await client.get(f"/api/events/{event_id}/stats")
    assert checked_in.json()["checked_in"] == 1

    await client.post(f"/api/events/{event_id}/registrations/{first['id']}/cancel")
    after_promotion = await client.get(f"/api/events/{event_id}/stats")
    assert after_promotion.json() == {
        "event_id": event_id,
        "capacity": 2,
        "confirmed": 2,
        "waitlisted": 0,
        "checked_in": 0,
    }


async def test_unknown_event_statistics_return_not_found(client: httpx.AsyncClient) -> None:
    event_id = uuid.uuid4()

    response = await client.get(f"/api/events/{event_id}/stats")

    assert response.status_code == 404
