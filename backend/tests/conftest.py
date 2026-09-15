import os
from collections.abc import AsyncIterator, Iterator

import httpx
import pytest
import pytest_asyncio
from sqlalchemy import Engine, create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session, sessionmaker

from app.db.base import Base
from app.db.models import Event
from app.db.session import get_db_session, get_session_factory
from app.main import app

_ = Event

TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql+psycopg://event_registration:event_registration@localhost:5434/"
    "event_registration_test",
)


def assert_safe_test_database(url: str, *, override: str | None = None) -> None:
    """Refuse to drop tables anywhere that is not unmistakably a test database."""
    engine_url = make_url(url)
    if engine_url.get_backend_name() != "postgresql":
        raise RuntimeError("Backend integration tests require PostgreSQL")
    if override == "1":
        return
    if not (engine_url.database or "").endswith("_test"):
        raise RuntimeError(
            f"Refusing to reset {engine_url.database!r}: the test database name must end with "
            "'_test' (set ALLOW_UNSAFE_TEST_DATABASE=1 to override deliberately)"
        )


@pytest.fixture
def database_engine() -> Iterator[Engine]:
    assert_safe_test_database(TEST_DATABASE_URL, override=os.getenv("ALLOW_UNSAFE_TEST_DATABASE"))
    engine = create_engine(TEST_DATABASE_URL)
    Base.metadata.drop_all(engine)
    # The suite builds tables from metadata, not migrations; a stale Alembic stamp would make a
    # later `alembic upgrade head` a no-op against an empty schema.
    with engine.begin() as connection:
        connection.execute(text("DROP TABLE IF EXISTS alembic_version"))
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest_asyncio.fixture
async def client(database_engine: Engine) -> AsyncIterator[httpx.AsyncClient]:
    session_factory = sessionmaker(bind=database_engine, expire_on_commit=False)

    def override_db_session() -> Iterator[Session]:
        with session_factory() as session:
            yield session

    app.dependency_overrides[get_db_session] = override_db_session
    app.dependency_overrides[get_session_factory] = lambda: session_factory
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as test_client:
        yield test_client
    app.dependency_overrides.clear()
