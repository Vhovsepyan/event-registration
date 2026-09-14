import asyncio
import threading
import uuid
from datetime import UTC, datetime, timedelta

import httpx
import pytest
from sqlalchemy import Engine, func, select
from sqlalchemy.orm import Session

from app.event.models import Event
from app.notification.models import Notification, NotificationType
from app.registration.models import Registration, RegistrationStatus
from app.registration.routes import service
from app.ticket.models import Ticket

pytestmark = pytest.mark.asyncio


async def create_event(client: httpx.AsyncClient, capacity: int = 1) -> str:
    response = await client.post(
        "/api/events",
        json={
            "title": "Re-registration Test",
            "description": "",
            "starts_at": (datetime.now(UTC) + timedelta(days=2)).isoformat(),
            "capacity": capacity,
        },
    )
    assert response.status_code == 201
    return response.json()["id"]


async def register(client: httpx.AsyncClient, event_id: str, email: str) -> httpx.Response:
    return await client.post(f"/api/events/{event_id}/registrations", json={"email": email})


async def cancel(client: httpx.AsyncClient, event_id: str, registration_id: str) -> httpx.Response:
    return await client.post(f"/api/events/{event_id}/registrations/{registration_id}/cancel")


async def test_confirmed_can_cancel_and_reregister_when_capacity_is_available(
    client: httpx.AsyncClient,
) -> None:
    event_id = await create_event(client)
    original = (await register(client, event_id, "person@example.com")).json()
    await cancel(client, event_id, original["id"])

    response = await register(client, event_id, " PERSON@example.com ")

    assert response.status_code == 201
    current = response.json()
    assert current["id"] != original["id"]
    assert current["status"] == "CONFIRMED"
    assert current["ticket"] is not None
    assert current["cancelled_at"] is None


async def test_reregistering_after_another_participant_takes_seat_is_waitlisted(
    client: httpx.AsyncClient,
) -> None:
    event_id = await create_event(client)
    original = (await register(client, event_id, "original@example.com")).json()
    await cancel(client, event_id, original["id"])
    replacement = (await register(client, event_id, "replacement@example.com")).json()

    current = (await register(client, event_id, "original@example.com")).json()

    assert replacement["status"] == "CONFIRMED"
    assert current["id"] != original["id"]
    assert current["status"] == "WAITLISTED"
    assert current["waitlist_order"] == 1
    assert current["ticket"] is None


async def test_waitlisted_participant_can_cancel_and_reregister(
    client: httpx.AsyncClient,
) -> None:
    event_id = await create_event(client)
    await register(client, event_id, "holder@example.com")
    original = (await register(client, event_id, "waitlisted@example.com")).json()
    await cancel(client, event_id, original["id"])

    current = (await register(client, event_id, "waitlisted@example.com")).json()

    assert original["status"] == "WAITLISTED"
    assert current["id"] != original["id"]
    assert current["status"] == "WAITLISTED"
    assert current["waitlist_order"] == 2


async def test_reregistration_issues_fresh_ticket_and_old_ticket_stays_invalid(
    client: httpx.AsyncClient,
) -> None:
    event_id = await create_event(client)
    original = (await register(client, event_id, "ticket@example.com")).json()
    old_ticket = original["ticket"]
    await cancel(client, event_id, original["id"])

    current = (await register(client, event_id, "ticket@example.com")).json()
    new_ticket = current["ticket"]
    old_check_in = await client.post("/api/check-ins", json={"code": old_ticket["code"]})
    new_check_in = await client.post("/api/check-ins", json={"code": new_ticket["code"]})

    assert new_ticket["id"] != old_ticket["id"]
    assert new_ticket["code"] != old_ticket["code"]
    assert new_ticket["invalidated_at"] is None
    assert old_check_in.json()["result"] == "INVALID_TICKET"
    assert new_check_in.json()["result"] == "SUCCESS"


async def test_each_confirmed_attempt_and_promotion_has_its_own_notification(
    client: httpx.AsyncClient, database_engine: Engine
) -> None:
    event_id = await create_event(client)
    first = (await register(client, event_id, "repeat@example.com")).json()
    await cancel(client, event_id, first["id"])
    second = (await register(client, event_id, "repeat@example.com")).json()
    waiting = (await register(client, event_id, "waiting@example.com")).json()
    await cancel(client, event_id, waiting["id"])
    waiting_again = (await register(client, event_id, "waiting@example.com")).json()

    promotion = (await cancel(client, event_id, second["id"])).json()["promoted_registration"]

    assert promotion["id"] == waiting_again["id"]
    assert promotion["ticket"] is not None
    with Session(database_engine) as session:
        confirmations = list(
            session.scalars(
                select(Notification)
                .where(Notification.type == NotificationType.REGISTRATION_CONFIRMED)
                .order_by(Notification.created_at, Notification.id)
            )
        )
        promotions = list(
            session.scalars(
                select(Notification).where(Notification.type == NotificationType.WAITLIST_PROMOTED)
            )
        )

    assert {str(item.registration_id) for item in confirmations} == {first["id"], second["id"]}
    assert len(promotions) == 1
    assert str(promotions[0].registration_id) == waiting_again["id"]
    assert promotions[0].payload["ticket_code"] == promotion["ticket"]["code"]


async def test_concurrent_duplicate_reregistration_creates_one_active_attempt(
    client: httpx.AsyncClient, database_engine: Engine, monkeypatch: pytest.MonkeyPatch
) -> None:
    event_id = await create_event(client)
    original = (await register(client, event_id, "repeat@example.com")).json()
    await cancel(client, event_id, original["id"])
    rendezvous = threading.Barrier(2, timeout=5)
    original_get_for_update = service.event_repository.get_for_update

    def overlap_before_lock(session: Session, selected_event_id: uuid.UUID) -> Event | None:
        rendezvous.wait()
        return original_get_for_update(session, selected_event_id)

    monkeypatch.setattr(service.event_repository, "get_for_update", overlap_before_lock)

    first, second = await asyncio.gather(
        register(client, event_id, "repeat@example.com"),
        register(client, event_id, " REPEAT@example.com "),
    )

    assert first.status_code == 201
    assert second.status_code == 201
    assert first.json()["id"] == second.json()["id"]
    assert first.json()["id"] != original["id"]
    assert first.json()["status"] == "CONFIRMED"
    with Session(database_engine) as session:
        registrations = list(
            session.scalars(
                select(Registration).where(
                    Registration.event_id == uuid.UUID(event_id),
                    Registration.normalized_email == "repeat@example.com",
                )
            )
        )
        active_count = session.scalar(
            select(func.count())
            .select_from(Registration)
            .where(
                Registration.event_id == uuid.UUID(event_id),
                Registration.status.in_(
                    [RegistrationStatus.CONFIRMED, RegistrationStatus.WAITLISTED]
                ),
            )
        )
        tickets = list(
            session.scalars(
                select(Ticket)
                .join(Registration)
                .where(Registration.event_id == uuid.UUID(event_id))
            )
        )

    assert len(registrations) == 2
    assert active_count == 1
    assert len(tickets) == 2
    assert sum(ticket.invalidated_at is None for ticket in tickets) == 1
