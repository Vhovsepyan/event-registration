from datetime import UTC, datetime, timedelta

import httpx
import pytest
from sqlalchemy import Engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.common.config import Settings
from app.db.session import build_engine
from app.event.models import Event
from app.event.schemas import MAX_CAPACITY
from tests.conftest import TEST_DATABASE_URL, assert_safe_test_database

pytestmark = pytest.mark.asyncio


def payload(**overrides: object) -> dict[str, object]:
    return {
        "title": "Bounded",
        "description": "",
        "starts_at": (datetime.now(UTC) + timedelta(days=1)).isoformat(),
        "capacity": 10,
    } | overrides


@pytest.mark.parametrize("capacity", [MAX_CAPACITY + 1, 2_147_483_648, 10**12])
async def test_capacity_above_maximum_is_a_validation_error(
    client: httpx.AsyncClient, capacity: int
) -> None:
    response = await client.post("/api/events", json=payload(capacity=capacity))

    assert response.status_code == 422
    assert "capacity" in response.text


async def test_capacity_at_maximum_is_accepted(client: httpx.AsyncClient) -> None:
    response = await client.post("/api/events", json=payload(capacity=MAX_CAPACITY))

    assert response.status_code == 201
    assert response.json()["capacity"] == MAX_CAPACITY


@pytest.mark.parametrize("title", ["\t", "\t \t", " \r\n "])
async def test_database_rejects_titles_blank_after_all_whitespace(
    database_engine: Engine, title: str
) -> None:
    with Session(database_engine) as session:
        session.add(
            Event(
                title=title,
                description="",
                starts_at=datetime.now(UTC) + timedelta(days=1),
                capacity=1,
            )
        )
        with pytest.raises(IntegrityError, match="ck_events_title_not_blank"):
            session.commit()


async def test_test_database_guard() -> None:
    assert_safe_test_database(TEST_DATABASE_URL)
    assert_safe_test_database("postgresql+psycopg://u:p@localhost/event_registration_test")

    with pytest.raises(RuntimeError, match="must end with '_test'"):
        assert_safe_test_database("postgresql+psycopg://u:p@localhost/event_registration")
    with pytest.raises(RuntimeError, match="must end with '_test'"):
        assert_safe_test_database("postgresql+psycopg://u:p@localhost/production")
    with pytest.raises(RuntimeError, match="require PostgreSQL"):
        assert_safe_test_database("sqlite:///anything_test.db")
    # The override is explicit and only for someone who knows what they are doing.
    assert_safe_test_database("postgresql+psycopg://u:p@localhost/scratch", override="1")


async def test_pool_size_is_configurable() -> None:
    engine = build_engine(
        Settings(database_url=TEST_DATABASE_URL, database_pool_size=3, database_max_overflow=1)
    )
    try:
        assert engine.pool.size() == 3
        assert engine.pool._max_overflow == 1
    finally:
        engine.dispose()

    with pytest.raises(ValueError):
        Settings(database_pool_size=0)
