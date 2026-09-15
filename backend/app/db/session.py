from collections.abc import Iterator

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.common.config import Settings, get_settings


def build_engine(settings: Settings) -> Engine:
    # Every API request and every SSE poll borrows one pooled connection briefly; the pool
    # therefore bounds how many organizer streams and requests can read at the same instant.
    return create_engine(
        settings.database_url,
        pool_pre_ping=True,
        pool_size=settings.database_pool_size,
        max_overflow=settings.database_max_overflow,
    )


engine = build_engine(get_settings())
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
