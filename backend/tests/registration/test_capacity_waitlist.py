import asyncio
import threading
import uuid
from datetime import UTC, datetime, timedelta

import httpx
import pytest
from sqlalchemy import Engine, func, select
from sqlalchemy.orm import Session

from app.event.models import Event
from app.registration.models import Registration, RegistrationStatus
from app.registration.routes import service

pytestmark = pytest.mark.asyncio


async def create_event(client: httpx.AsyncClient, capacity: int) -> str:
    response = await client.post(
        "/api/events",
        json={
            "title": "Capacity Test",
            "description": "",
            "starts_at": (datetime.now(UTC) + timedelta(days=2)).isoformat(),
            "capacity": capacity,
        },
    )
    assert response.status_code == 201
    return response.json()["id"]


async def register(client: httpx.AsyncClient, event_id: str, email: str) -> httpx.Response:
    return await client.post(f"/api/events/{event_id}/registrations", json={"email": email})


async def test_full_event_creates_fifo_waitlist(client: httpx.AsyncClient) -> None:
    event_id = await create_event(client, capacity=1)

    responses = [
        await register(client, event_id, "confirmed@example.com"),
        await register(client, event_id, "first@example.com"),
        await register(client, event_id, "second@example.com"),
    ]

    assert [response.status_code for response in responses] == [201, 201, 201]
    assert [response.json()["status"] for response in responses] == [
        "CONFIRMED",
        "WAITLISTED",
        "WAITLISTED",
    ]
    assert [response.json()["waitlist_order"] for response in responses] == [None, 1, 2]


async def test_duplicate_does_not_consume_second_seat(client: httpx.AsyncClient) -> None:
    event_id = await create_event(client, capacity=1)

    first = await register(client, event_id, "same@example.com")
    duplicate = await register(client, event_id, " SAME@example.com ")
    other = await register(client, event_id, "other@example.com")

    assert duplicate.json()["id"] == first.json()["id"]
    assert other.json()["status"] == "WAITLISTED"
    assert other.json()["waitlist_order"] == 1


async def test_concurrent_requests_compete_for_one_seat(
    client: httpx.AsyncClient, database_engine: Engine, monkeypatch: pytest.MonkeyPatch
) -> None:
    event_id = await create_event(client, capacity=1)
    rendezvous = threading.Barrier(2, timeout=5)
    original_get_for_update = service.event_repository.get_for_update

    def overlap_before_lock(session: Session, selected_event_id: uuid.UUID) -> Event | None:
        rendezvous.wait()
        return original_get_for_update(session, selected_event_id)

    monkeypatch.setattr(service.event_repository, "get_for_update", overlap_before_lock)

    first, second = await asyncio.gather(
        register(client, event_id, "first@example.com"),
        register(client, event_id, "second@example.com"),
    )

    assert first.status_code == 201
    assert second.status_code == 201
    assert sorted([first.json()["status"], second.json()["status"]]) == [
        "CONFIRMED",
        "WAITLISTED",
    ]
    with Session(database_engine) as session:
        confirmed = session.scalar(
            select(func.count())
            .select_from(Registration)
            .where(Registration.status == RegistrationStatus.CONFIRMED)
        )
        waitlisted = session.scalar(
            select(func.count())
            .select_from(Registration)
            .where(Registration.status == RegistrationStatus.WAITLISTED)
        )
    assert confirmed == 1
    assert waitlisted == 1
