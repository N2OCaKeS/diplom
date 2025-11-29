from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

ROOT_PATH = Path(__file__).resolve().parents[1]

from backend.app.core.config import get_settings
from backend.app.db.base import Base
from backend.app.db.session import dispose_engine, get_session
from backend.app.main import app as fastapi_app

TEST_DB_PATH = ROOT_PATH / "test_container_guard.db"
TEST_DATABASE_URL = f"sqlite:///{TEST_DB_PATH}"


@pytest.fixture(autouse=True)
def clear_settings_cache(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    monkeypatch.setenv("JIRA_URL", "https://jira.test")
    monkeypatch.setenv("JIRA_USER", "")
    monkeypatch.setenv("JIRA_API_TOKEN", "")
    monkeypatch.setenv("JIRA_PROJECT_KEY", "")
    monkeypatch.setenv("CONFLUENCE_URL", "https://confluence.test/wiki")
    monkeypatch.setenv("CONFLUENCE_USER", "")
    monkeypatch.setenv("CONFLUENCE_API_TOKEN", "")
    monkeypatch.setenv("CONFLUENCE_SPACE_KEY", "")
    monkeypatch.setenv("CONFLUENCE_PARENT_PAGE_ID", "")
    monkeypatch.setenv("POLICIES_STORAGE_PATH", str(ROOT_PATH / "policies_storage"))
    monkeypatch.setenv("POLICY_TEMPLATES_PATH", str(ROOT_PATH / "policy_templates"))
    monkeypatch.setenv("DATABASE_URL", TEST_DATABASE_URL)
    monkeypatch.setenv("AUTH_MODE", "none")
    monkeypatch.setenv("GUARD_TOKEN", "")
    monkeypatch.setenv("JWT_SECRET", "")
    monkeypatch.setenv("AUTH_VALIDATION_URL", "")
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
