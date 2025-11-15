from __future__ import annotations

import os
import sys
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

ROOT_PATH = Path(__file__).resolve().parents[1]
if str(ROOT_PATH) not in sys.path:
    sys.path.insert(0, str(ROOT_PATH))

from app.core.config import get_settings
from app.db.base import Base
from app.db.session import dispose_engine, get_session
from app.main import app as fastapi_app

TEST_DB_PATH = ROOT_PATH / "test_container_guard.db"
TEST_DATABASE_URL = f"sqlite:///{TEST_DB_PATH}"


@pytest.fixture(autouse=True)
def clear_settings_cache(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    monkeypatch.setenv("JIRA_BROWSE_URL", "https://jira.test")
    monkeypatch.setenv("DATABASE_URL", TEST_DATABASE_URL)
    monkeypatch.delenv("AUTH_MODE", raising=False)
    monkeypatch.delenv("JWT_SECRET", raising=False)
    monkeypatch.delenv("AUTH_VALIDATION_URL", raising=False)
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture(scope="session")
def db_engine() -> Iterator[tuple[sessionmaker[Session], Engine]]:
    engine = create_engine(TEST_DATABASE_URL, future=True)
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    try:
        yield factory, engine
    finally:
        Base.metadata.drop_all(engine)
        engine.dispose()
        if TEST_DB_PATH.exists():
            TEST_DB_PATH.unlink()
        dispose_engine()


@pytest.fixture()
def session(db_engine: tuple[sessionmaker[Session], Engine]) -> Iterator[Session]:
    factory, engine = db_engine
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    db_session = factory()
    try:
        yield db_session
        db_session.rollback()
    finally:
        db_session.close()


@pytest.fixture()
def app(session: Session) -> Iterator[FastAPI]:
    def override_session() -> Iterator[Session]:
        yield session

    fastapi_app.dependency_overrides[get_session] = override_session
    try:
        yield fastapi_app
    finally:
        fastapi_app.dependency_overrides.clear()


@pytest.fixture()
def client(app: FastAPI) -> Iterator[TestClient]:
    with TestClient(app) as test_client:
        yield test_client
