"""Pytest fixtures for offline backend testing."""

from collections.abc import Generator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend.app import main
from backend.app.db import Database
from backend.app.llm.agent import RapportAgentService
from backend.app.main import app
from backend.app.memory.fake import FakeMemory


@pytest.fixture
def fake_memory() -> FakeMemory:
    return FakeMemory(bank_id="test-bank")


@pytest.fixture
def test_db(tmp_path: Path) -> Database:
    db_file = tmp_path / "test_rapport.db"
    test_database = Database(db_path=str(db_file))
    test_database.init_db()
    test_database.create_client("c1_apex", "Apex Dynamics", primary_quirk="Async preferred")
    test_database.create_client("c2_horizon", "Horizon Retail", primary_quirk="Pays late")
    return test_database


@pytest.fixture
def test_client(fake_memory: FakeMemory, test_db: Database) -> Generator[TestClient, None, None]:
    app.state.memory = fake_memory
    app.state.agent = RapportAgentService(memory_backend=fake_memory)

    old_path = main.db.db_path
    main.db.db_path = test_db.db_path
    main.db.init_db()

    with TestClient(app) as client:
        yield client

    main.db.db_path = old_path
