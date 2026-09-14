import uuid
from datetime import UTC, datetime, timedelta

import httpx
import pytest
from sqlalchemy import Engine, func, select
from sqlalchemy.orm import Session

from app.registration.models import Registration

pytestmark = pytest.mark.asyncio


async def create_event(client: httpx.AsyncClient) -> str:
    response = await client.post(
        "/api/events",
        json={
            "title": "Registration Test",
            "description": "",
            "starts_at": (datetime.now(UTC) + timedelta(days=2)).isoformat(),
            "capacity": 10,
        },
    )
    assert response.status_code == 201
    return response.json()["id"]


async def test_registers_participant_as_confirmed(client: httpx.AsyncClient) -> None:
    event_id = await create_event(client)

    response = await client.post(
        f"/api/events/{event_id}/registrations", json={"email": "Person@Example.COM"}
    )

    assert response.status_code == 201
    registration = response.json()
    assert registration["event_id"] == event_id
    assert registration["email"] == "Person@example.com"
    assert registration["status"] == "CONFIRMED"
    assert registration["confirmed_at"] is not None
    assert registration["waitlist_order"] is None


async def test_equivalent_email_is_idempotent(
    client: httpx.AsyncClient, database_engine: Engine
) -> None:
    event_id = await create_event(client)

    first = await client.post(
        f"/api/events/{event_id}/registrations", json={"email": "person@example.com"}
    )
    repeated = await client.post(
        f"/api/events/{event_id}/registrations", json={"email": "  PERSON@example.com  "}
    )

    assert first.status_code == 201
    assert repeated.status_code == 201
    assert repeated.json()["id"] == first.json()["id"]
    with Session(database_engine) as session:
        count = session.scalar(select(func.count()).select_from(Registration))
    assert count == 1


async def test_rejects_invalid_email(client: httpx.AsyncClient) -> None:
    event_id = await create_event(client)

    response = await client.post(
        f"/api/events/{event_id}/registrations", json={"email": "not-an-email"}
    )

    assert response.status_code == 422


async def test_unknown_event_returns_not_found(client: httpx.AsyncClient) -> None:
    event_id = uuid.uuid4()

    response = await client.post(
        f"/api/events/{event_id}/registrations", json={"email": "person@example.com"}
    )

    assert response.status_code == 404
