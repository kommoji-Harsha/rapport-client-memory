"""
Tests for API endpoints (/health, /clients, /respond, /feedback, /import, /memory/observations).
"""

import pytest
from httpx import AsyncClient

from backend.app.memory.fake import FakeMemory
from backend.app.memory.models import RetainItem


@pytest.mark.asyncio
async def test_health_endpoint(async_client: AsyncClient) -> None:
    res = await async_client.get("/api/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"
    assert data["memory_backend"] == "FakeMemory"


@pytest.mark.asyncio
async def test_create_and_get_clients(async_client: AsyncClient) -> None:
    client_payload = {
        "id": "test-c1",
        "name": "Test Client One",
        "industry": "FinTech",
        "primary_contact": "Jane Doe",
        "quirks": "Prefers async communication.",
    }
    create_res = await async_client.post("/api/clients", json=client_payload)
    assert create_res.status_code == 201
    created_data = create_res.json()
    assert created_data["id"] == "test-c1"

    list_res = await async_client.get("/api/clients")
    assert list_res.status_code == 200
    clients_list = list_res.json()
    assert len(clients_list) >= 1
    assert any(c["id"] == "test-c1" for c in clients_list)


@pytest.mark.asyncio
async def test_respond_endpoint(async_client: AsyncClient, fake_memory: FakeMemory) -> None:
    # Retain a test interaction first
    await fake_memory.retain_interaction(
        client_id="test-c1",
        item=RetainItem(
            content="Client prefers email communication.",
            context="Preference recording",
            document_id="interaction-int-1",
            tags=["client:test-c1"],
        ),
    )

    req_payload = {
        "client_id": "test-c1",
        "incoming_text": "Can we schedule a call tomorrow?",
        "memory_enabled": True,
        "compare": False,
    }
    res = await async_client.post("/api/respond", json=req_payload)
    assert res.status_code == 200
    data = res.json()
    assert "response_id" in data
    assert data["compare"] is False
    assert "draft_reply" in data["package"]


@pytest.mark.asyncio
async def test_respond_compare_endpoint(
    async_client: AsyncClient, fake_memory: FakeMemory
) -> None:
    await fake_memory.retain_interaction(
        client_id="test-c1",
        item=RetainItem(
            content="Client prefers Slack.",
            context="Preference recording",
            document_id="interaction-int-2",
            tags=["client:test-c1"],
        ),
    )

    req_payload = {
        "client_id": "test-c1",
        "incoming_text": "How do we get in touch?",
        "memory_enabled": True,
        "compare": True,
    }
    res = await async_client.post("/api/respond", json=req_payload)
    assert res.status_code == 200
    data = res.json()
    assert data["compare"] is True
    assert "memory_on" in data["package"]
    assert "memory_off" in data["package"]


@pytest.mark.asyncio
async def test_feedback_idempotency(async_client: AsyncClient) -> None:
    payload = {
        "response_id": "resp-12345",
        "outcome": "went_well",
        "notes": "Client was very satisfied with draft.",
    }
    res1 = await async_client.post("/api/feedback", json=payload)
    assert res1.status_code == 200
    data1 = res1.json()
    assert data1["status"] == "success"

    # Idempotent re-submission with updated notes
    payload["notes"] = "Client was satisfied, confirmed via Slack."
    res2 = await async_client.post("/api/feedback", json=payload)
    assert res2.status_code == 200
    data2 = res2.json()
    assert data2["status"] == "success"
    assert data2["response_id"] == "resp-12345"


@pytest.mark.asyncio
async def test_import_endpoint(async_client: AsyncClient) -> None:
    import_payload = {
        "client_id": "test-c1",
        "text": "Imported call transcript: Client requested 10% scope expansion.",
    }
    res = await async_client.post("/api/import", json=import_payload)
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert data["client_id"] == "test-c1"
    assert "retained_id" in data


@pytest.mark.asyncio
async def test_empty_and_oversized_input_validation(async_client: AsyncClient) -> None:
    # Empty incoming_text
    empty_res = await async_client.post(
        "/api/respond",
        json={"client_id": "test-c1", "incoming_text": "   "},
    )
    assert empty_res.status_code == 400

    # Oversized incoming_text
    oversized_text = "A" * 10001
    oversized_res = await async_client.post(
        "/api/respond",
        json={"client_id": "test-c1", "incoming_text": oversized_text},
    )
    assert oversized_res.status_code == 400
