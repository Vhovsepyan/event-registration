from datetime import UTC, datetime, timedelta

import httpx
import pytest
from sqlalchemy import Engine, update
from sqlalchemy.orm import Session

from app.event.models import Event

pytestmark = pytest.mark.asyncio


async def create_event(
    client: httpx.AsyncClient, title: str, *, days: float, capacity: int
) -> dict[str, object]:
    response = await client.post(
        "/api/events",
        json={
            "title": title,
            "description": "",
            "starts_at": (datetime.now(UTC) + timedelta(days=days)).isoformat(),
            "capacity": capacity,
        },
    )
    assert response.status_code == 201
    return response.json()


async def register(client: httpx.AsyncClient, event_id: object, email: str) -> dict[str, object]:
    response = await client.post(f"/api/events/{event_id}/registrations", json={"email": email})
    assert response.status_code == 201
    return response.json()


async def test_empty_list(client: httpx.AsyncClient) -> None:
    response = await client.get("/api/events")

    assert response.status_code == 200
    assert response.json() == []


async def test_upcoming_events_are_listed_soonest_first_with_counts(
    client: httpx.AsyncClient,
) -> None:
    later = await create_event(client, "Later", days=5, capacity=1)
    sooner = await create_event(client, "Sooner", days=2, capacity=2)
    confirmed = await register(client, sooner["id"], "one@example.com")
    await register(client, sooner["id"], "two@example.com")
    await register(client, sooner["id"], "three@example.com")

    response = await client.get("/api/events")

    assert response.status_code == 200
    listed = response.json()
    assert [item["title"] for item in listed] == ["Sooner", "Later"]
    assert listed[0] == {
        **sooner,
        "confirmed": 2,
        "waitlisted": 1,
        "seats_left": 0,
    }
    assert listed[1] == {**later, "confirmed": 0, "waitlisted": 0, "seats_left": 1}

    await client.post(f"/api/events/{sooner['id']}/registrations/{confirmed['id']}/cancel")
    after = (await client.get("/api/events")).json()[0]
    assert (after["confirmed"], after["waitlisted"], after["seats_left"]) == (2, 0, 0)

    stats = (await client.get(f"/api/events/{sooner['id']}/stats")).json()
    assert (stats["confirmed"], stats["waitlisted"]) == (after["confirmed"], after["waitlisted"])


async def test_past_events_only_with_include_past(
    client: httpx.AsyncClient, database_engine: Engine
) -> None:
    past = await create_event(client, "Past", days=1, capacity=1)
    await create_event(client, "Upcoming", days=3, capacity=1)
    # Events cannot be created in the past through the API; age this one directly.
    with Session(database_engine) as session, session.begin():
        session.execute(
            update(Event)
            .where(Event.id == past["id"])
            .values(starts_at=datetime.now(UTC) - timedelta(hours=1))
        )

    default = (await client.get("/api/events")).json()
    everything = (await client.get("/api/events", params={"include_past": "true"})).json()

    assert [item["title"] for item in default] == ["Upcoming"]
    assert [item["title"] for item in everything] == ["Past", "Upcoming"]
