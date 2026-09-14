from datetime import UTC, datetime, timedelta

import httpx
import pytest

pytestmark = pytest.mark.asyncio


async def create_event(client: httpx.AsyncClient, capacity: int = 1) -> str:
    response = await client.post(
        "/api/events",
        json={
            "title": "Cancellation Test",
            "description": "",
            "starts_at": (datetime.now(UTC) + timedelta(days=2)).isoformat(),
            "capacity": capacity,
        },
    )
    assert response.status_code == 201
    return response.json()["id"]


async def register(client: httpx.AsyncClient, event_id: str, email: str) -> dict[str, object]:
    response = await client.post(f"/api/events/{event_id}/registrations", json={"email": email})
    assert response.status_code == 201
    return response.json()


async def cancel(
    client: httpx.AsyncClient, event_id: str, registration_id: object
) -> httpx.Response:
    return await client.post(f"/api/events/{event_id}/registrations/{registration_id}/cancel")


async def test_confirmed_cancellation_promotes_first_waitlisted(client: httpx.AsyncClient) -> None:
    event_id = await create_event(client)
    confirmed = await register(client, event_id, "confirmed@example.com")
    first = await register(client, event_id, "first@example.com")
    await register(client, event_id, "second@example.com")
    original_ticket = confirmed["ticket"]

    response = await cancel(client, event_id, confirmed["id"])

    assert response.status_code == 200
    result = response.json()
    assert result["registration"]["status"] == "CANCELLED"
    assert result["registration"]["ticket"]["invalidated_at"] is not None
    promoted = result["promoted_registration"]
    assert promoted["id"] == first["id"]
    assert promoted["status"] == "CONFIRMED"
    assert promoted["waitlist_order"] == 1
    assert promoted["ticket"] is not None

    second_repeat = await register(client, event_id, "second@example.com")
    assert second_repeat["status"] == "WAITLISTED"
    assert second_repeat["waitlist_order"] == 2

    old_ticket = await client.get(f"/api/tickets/{original_ticket['code']}")
    assert old_ticket.json()["registration_status"] == "CANCELLED"
    assert old_ticket.json()["invalidated_at"] is not None


async def test_repeated_cancellation_does_not_promote_again(client: httpx.AsyncClient) -> None:
    event_id = await create_event(client)
    confirmed = await register(client, event_id, "confirmed@example.com")
    await register(client, event_id, "first@example.com")
    await register(client, event_id, "second@example.com")
    await cancel(client, event_id, confirmed["id"])

    repeated = await cancel(client, event_id, confirmed["id"])

    assert repeated.status_code == 200
    assert repeated.json()["promoted_registration"] is None
    first_state = await register(client, event_id, "first@example.com")
    second_state = await register(client, event_id, "second@example.com")
    assert first_state["status"] == "CONFIRMED"
    assert second_state["status"] == "WAITLISTED"


async def test_waitlisted_cancellation_does_not_promote(client: httpx.AsyncClient) -> None:
    event_id = await create_event(client)
    await register(client, event_id, "confirmed@example.com")
    waitlisted = await register(client, event_id, "waitlisted@example.com")

    result = await cancel(client, event_id, waitlisted["id"])

    assert result.json()["registration"]["status"] == "CANCELLED"
    assert result.json()["promoted_registration"] is None

    later = await register(client, event_id, "later@example.com")
    assert later["status"] == "WAITLISTED"
    assert later["waitlist_order"] == 2
