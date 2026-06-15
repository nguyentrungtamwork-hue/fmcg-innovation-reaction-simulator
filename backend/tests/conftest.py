import os
import tempfile
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.storage import database
from app.storage.database import Base, get_db


@pytest.fixture
def client() -> Iterator[TestClient]:
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    tmp.close()
    engine = create_engine(
        f"sqlite:///{tmp.name}", connect_args={"check_same_thread": False}, future=True
    )
    TestingSessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, future=True)
    Base.metadata.create_all(bind=engine)

    def _override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = _override_get_db
    # Phase 24: app_log_service.record() opens its own session via
    # database.SessionLocal — point it at the per-test DB too.
    _orig_session_local = database.SessionLocal
    database.SessionLocal = TestingSessionLocal
    try:
        with TestClient(app) as c:
            yield c
    finally:
        database.SessionLocal = _orig_session_local
        app.dependency_overrides.pop(get_db, None)
        engine.dispose()
        try:
            os.unlink(tmp.name)
        except OSError:
            pass
