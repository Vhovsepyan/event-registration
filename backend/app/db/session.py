from collections.abc import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.common.config import get_settings

engine = create_engine(get_settings().database_url, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)


def get_db_session() -> Iterator[Session]:
    with SessionLocal() as session:
        yield session


def get_session_factory() -> sessionmaker[Session]:
    """For handlers that must open and close their own short-lived sessions.

    A yield dependency stays open for the whole request, which would pin a pooled connection
    for the lifetime of a streaming response; long-lived handlers take the factory instead.
    """
    return SessionLocal
