import asyncio
import threading
import uuid
from datetime import UTC, datetime, timedelta

import httpx
import pytest
from sqlalchemy import Engine
from sqlalchemy.orm import Session

from app.ticket.models import Ticket
from app.ticket.routes import service

pytestmark = pytest.mark.asyncio


async def create_ticket(client: httpx.AsyncClient) -> tuple[str, dict[str, object]]:
    event_response = await client.post(
        "/api/events",
        json={
            "title": "Check-in Test",
            "description": "",
            "starts_at": (datetime.now(UTC) + timedelta(days=2)).isoformat(),
            "capacity": 1,
        },
    )
    event_id = event_response.json()["id"]
    registration_response = await client.post(
        f"/api/events/{event_id}/registrations", json={"email": "checkin@example.com"}
    )
    return event_id, registration_response.json()


async def test_ticket_checks_in_once(client: httpx.AsyncClient, database_engine: Engine) -> None:
    _, registration = await create_ticket(client)
    code = registration["ticket"]["code"]

    first = await client.post("/api/check-ins", json={"code": code.lower()})
    repeated = await client.post("/api/check-ins", json={"code": code})

    assert first.json()["result"] == "SUCCESS"
    assert repeated.json()["result"] == "ALREADY_CHECKED_IN"
    assert repeated.json()["checked_in_at"] == first.json()["checked_in_at"]
    with Session(database_engine) as session:
        assert (
            session.get(Ticket, uuid.UUID(registration["ticket"]["id"])).checked_in_at is not None
        )


async def test_unknown_and_cancelled_tickets_are_invalid(client: httpx.AsyncClient) -> None:
    unknown = await client.post("/api/check-ins", json={"code": "AAAA-BBBB-CCCC"})
    assert unknown.json() == {"result": "INVALID_TICKET", "checked_in_at": None}

    event_id, registration = await create_ticket(client)
    await client.post(f"/api/events/{event_id}/registrations/{registration['id']}/cancel")
    cancelled = await client.post("/api/check-ins", json={"code": registration["ticket"]["code"]})
    assert cancelled.json()["result"] == "INVALID_TICKET"


async def test_cancelled_ticket_is_invalid_even_after_prior_check_in(
    client: httpx.AsyncClient,
) -> None:
    event_id, registration = await create_ticket(client)
    code = registration["ticket"]["code"]
    successful = await client.post("/api/check-ins", json={"code": code})
    assert successful.json()["result"] == "SUCCESS"
    await client.post(f"/api/events/{event_id}/registrations/{registration['id']}/cancel")

    cancelled = await client.post("/api/check-ins", json={"code": code})

    assert cancelled.json()["result"] == "INVALID_TICKET"


async def test_concurrent_check_in_has_exactly_one_success(
    client: httpx.AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    _, registration = await create_ticket(client)
    code = registration["ticket"]["code"]
    rendezvous = threading.Barrier(2, timeout=5)
    original_check_in = service.repository.check_in

    def overlap_before_update(session: Session, selected_code: str) -> Ticket | None:
        rendezvous.wait()
        return original_check_in(session, selected_code)

    monkeypatch.setattr(service.repository, "check_in", overlap_before_update)

    first, second = await asyncio.gather(
        client.post("/api/check-ins", json={"code": code}),
        client.post("/api/check-ins", json={"code": code}),
    )

    assert sorted([first.json()["result"], second.json()["result"]]) == [
        "ALREADY_CHECKED_IN",
        "SUCCESS",
    ]
