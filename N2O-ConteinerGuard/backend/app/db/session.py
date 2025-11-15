from __future__ import annotations

from collections.abc import Iterator

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings


engine: Engine | None = None
SessionFactory: sessionmaker[Session] | None = None


def configure_engine(database_url: str | None = None) -> None:
    global engine, SessionFactory
    if engine is not None and SessionFactory is not None:
        return
    settings = get_settings()
    url = database_url or settings.database_url
    engine = create_engine(url, echo=False, future=True)
    SessionFactory = sessionmaker(bind=engine, expire_on_commit=False)


def get_session() -> Iterator[Session]:
    if SessionFactory is None:
        configure_engine()
    assert SessionFactory is not None
    session = SessionFactory()
    try:
        yield session
    finally:
        session.close()


def dispose_engine() -> None:
    global engine, SessionFactory
    if engine is not None:
        engine.dispose()
    engine = None
    SessionFactory = None
