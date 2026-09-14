import os
from collections.abc import AsyncIterator, Iterator

import httpx
import pytest
import pytest_asyncio
from sqlalchemy import Engine, create_engine
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


@pytest.fixture
def database_engine() -> Iterator[Engine]:
    engine = create_engine(TEST_DATABASE_URL)
    if engine.dialect.name != "postgresql":
        raise RuntimeError("Backend integration tests require PostgreSQL")
    Base.metadata.drop_all(engine)
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
