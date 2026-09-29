"""
Pytest configuration and shared test fixtures.
"""

import os
import tempfile
from typing import AsyncGenerator, Generator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from backend.app.api.router import set_test_dependencies
from backend.app.db.database import init_db
from backend.app.llm.client import GroqLLMClient
from backend.app.main import app
from backend.app.memory.fake import FakeMemory


@pytest.fixture(scope="function", autouse=True)
def test_db() -> Generator[str, None, None]:
    """Create a temporary SQLite database for each test function."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = tmp.name

    os.environ["SQLITE_DB_PATH"] = db_path
    init_db(db_path)

    yield db_path

    if os.path.exists(db_path):
        try:
            os.remove(db_path)
        except OSError:
            pass


@pytest.fixture
def fake_memory() -> FakeMemory:
    return FakeMemory()


@pytest.fixture
def fake_llm_client() -> GroqLLMClient:
    # Initialize without API key so it defaults to degraded mode unless mocked
    return GroqLLMClient(api_key="")


@pytest_asyncio.fixture
async def async_client(
    fake_memory: FakeMemory, fake_llm_client: GroqLLMClient, test_db: str
) -> AsyncGenerator[AsyncClient, None]:
    """Provide an AsyncClient for testing FastAPI routes with test dependencies."""
    set_test_dependencies(memory_backend=fake_memory, llm_client=fake_llm_client)

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        yield client
