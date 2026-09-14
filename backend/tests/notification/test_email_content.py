from datetime import UTC, datetime, timedelta

import httpx
import pytest
from sqlalchemy import Engine, select
from sqlalchemy.orm import Session

from app.notification.models import Notification, NotificationType

pytestmark = pytest.mark.asyncio


async def create_event(client: httpx.AsyncClient) -> tuple[str, str]:
    starts_at = datetime.now(UTC) + timedelta(days=2)
    response = await client.post(
        "/api/events",
        json={
            "title": "Email Content Test",
            "description": "",
            "starts_at": starts_at.isoformat(),
            "capacity": 1,
        },
    )
    return response.json()["id"], response.json()["starts_at"]


async def register(client: httpx.AsyncClient, event_id: str, email: str) -> dict[str, object]:
    response = await client.post(f"/api/events/{event_id}/registrations", json={"email": email})
    return response.json()


async def test_confirmation_and_promotion_payloads_include_event_time_and_ticket(
    client: httpx.AsyncClient, database_engine: Engine
) -> None:
    event_id, starts_at = await create_event(client)
    confirmed = await register(client, event_id, "confirmed@example.com")
    waitlisted = await register(client, event_id, "promoted@example.com")
    await client.post(f"/api/events/{event_id}/registrations/{confirmed['id']}/cancel")

    with Session(database_engine) as session:
        notifications = list(
            session.scalars(select(Notification).order_by(Notification.created_at))
        )

    assert [notification.type for notification in notifications] == [
        NotificationType.REGISTRATION_CONFIRMED,
        NotificationType.WAITLIST_PROMOTED,
    ]
    confirmation, promotion = notifications
    rendered_starts_at = datetime.fromisoformat(starts_at).isoformat()
    assert "Email Content Test" in str(confirmation.payload["subject"])
    assert rendered_starts_at in str(confirmation.payload["body"])
    assert confirmed["ticket"]["code"] in str(confirmation.payload["body"])
    assert "Email Content Test" in str(promotion.payload["subject"])
    assert rendered_starts_at in str(promotion.payload["body"])
    assert promotion.payload["ticket_code"] != confirmed["ticket"]["code"]
    assert promotion.payload["ticket_code"] in str(promotion.payload["body"])
    assert str(promotion.registration_id) == waitlisted["id"]
