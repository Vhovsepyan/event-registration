import uuid
from datetime import UTC, datetime, timedelta

import httpx
import pytest

pytestmark = pytest.mark.asyncio


def event_payload() -> dict[str, object]:
    return {
        "title": "  Community Meetup  ",
        "description": "A local gathering.",
        "starts_at": (datetime.now(UTC) + timedelta(days=7)).isoformat(),
        "capacity": 25,
    }


async def test_create_and_get_event(client: httpx.AsyncClient) -> None:
    create_response = await client.post("/api/events", json=event_payload())

    assert create_response.status_code == 201
    created = create_response.json()
    assert created["title"] == "Community Meetup"
    assert created["description"] == "A local gathering."
    assert created["capacity"] == 25
    assert uuid.UUID(created["id"])
    assert created["created_at"]
    assert created["updated_at"]

    get_response = await client.get(f"/api/events/{created['id']}")

    assert get_response.status_code == 200
    assert get_response.json() == created


async def test_rejects_invalid_capacity(client: httpx.AsyncClient) -> None:
    payload = event_payload() | {"capacity": 0}

    response = await client.post("/api/events", json=payload)

    assert response.status_code == 422


async def test_rejects_nonfuture_date(client: httpx.AsyncClient) -> None:
    payload = event_payload() | {
        "starts_at": (datetime.now(UTC) - timedelta(minutes=1)).isoformat()
    }

    response = await client.post("/api/events", json=payload)

    assert response.status_code == 422


async def test_rejects_blank_title(client: httpx.AsyncClient) -> None:
    response = await client.post("/api/events", json=event_payload() | {"title": "   "})

    assert response.status_code == 422


async def test_unknown_event_returns_not_found(client: httpx.AsyncClient) -> None:
    event_id = uuid.uuid4()

    response = await client.get(f"/api/events/{event_id}")

    assert response.status_code == 404
    assert response.json() == {"detail": f"Event '{event_id}' was not found"}
