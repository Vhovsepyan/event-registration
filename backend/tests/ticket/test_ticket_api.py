import re
from datetime import UTC, datetime, timedelta

import httpx
import pytest

pytestmark = pytest.mark.asyncio


async def create_event(client: httpx.AsyncClient, capacity: int = 1) -> str:
    response = await client.post(
        "/api/events",
        json={
            "title": "Ticket Test",
            "description": "Ticket details",
            "starts_at": (datetime.now(UTC) + timedelta(days=2)).isoformat(),
            "capacity": capacity,
        },
    )
    assert response.status_code == 201
    return response.json()["id"]


async def register(client: httpx.AsyncClient, event_id: str, email: str) -> httpx.Response:
    return await client.post(f"/api/events/{event_id}/registrations", json={"email": email})


async def test_confirmed_registration_receives_retrievable_ticket(
    client: httpx.AsyncClient,
) -> None:
    event_id = await create_event(client)

    response = await register(client, event_id, "ticket@example.com")

    assert response.status_code == 201
    ticket = response.json()["ticket"]
    assert ticket is not None
    assert re.fullmatch(r"[2-9A-HJ-NP-Z]{4}(?:-[2-9A-HJ-NP-Z]{4}){2}", ticket["code"])

    details_response = await client.get(f"/api/tickets/{ticket['code'].lower()}")
    assert details_response.status_code == 200
    details = details_response.json()
    assert details["id"] == ticket["id"]
    assert details["registration_status"] == "CONFIRMED"
    assert details["event"]["id"] == event_id
    assert details["event"]["title"] == "Ticket Test"

    repeated = await register(client, event_id, " TICKET@example.com ")
    assert repeated.json()["ticket"]["id"] == ticket["id"]


async def test_waitlisted_registration_has_no_ticket(client: httpx.AsyncClient) -> None:
    event_id = await create_event(client)
    await register(client, event_id, "confirmed@example.com")

    waitlisted = await register(client, event_id, "waitlisted@example.com")

    assert waitlisted.json()["status"] == "WAITLISTED"
    assert waitlisted.json()["ticket"] is None


async def test_unknown_ticket_returns_not_found(client: httpx.AsyncClient) -> None:
    response = await client.get("/api/tickets/AAAA-BBBB-CCCC")

    assert response.status_code == 404
