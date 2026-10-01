"""Tests for FastAPI API endpoints."""

from fastapi.testclient import TestClient


def test_health_check_endpoint(test_client: TestClient) -> None:
    resp = test_client.get("/api/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert "memory_backend" in data


def test_get_and_create_clients(test_client: TestClient) -> None:
    resp = test_client.get("/api/clients")
    assert resp.status_code == 200
    clients = resp.json()
    assert len(clients) >= 2

    new_client = {
        "id": "c_test_corp",
        "name": "Test Corp",
        "contact_name": "Alice Smith",
        "contact_email": "alice@testcorp.example",
        "industry": "Tech",
        "primary_quirk": "Strict SLAs",
    }
    create_resp = test_client.post("/api/clients", json=new_client)
    assert create_resp.status_code in [200, 201]
    assert create_resp.json()["name"] == "Test Corp"


def test_respond_endpoint_and_empty_input_validation(test_client: TestClient) -> None:
    bad_resp = test_client.post("/api/respond", json={"client_id": "c1_apex", "incoming_text": "   "})
    assert bad_resp.status_code == 400

    resp = test_client.post(
        "/api/respond",
        json={"client_id": "c1_apex", "incoming_text": "Can we meet tomorrow at 9 AM?", "memory_enabled": True},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "draft_reply" in data
    assert "client_brief" in data
    assert "risk_flags" in data
    assert "response_id" in data


def test_respond_compare_mode(test_client: TestClient) -> None:
    resp = test_client.post(
        "/api/respond",
        json={"client_id": "c1_apex", "incoming_text": "Need project status update", "compare": True},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "memory_on" in data
    assert "memory_off" in data
    assert data["memory_on"]["memory_enabled"] is True
    assert data["memory_off"]["memory_enabled"] is False


def test_feedback_endpoint_idempotency(test_client: TestClient) -> None:
    resp = test_client.post(
        "/api/respond",
        json={"client_id": "c1_apex", "incoming_text": "Can we meet tomorrow?"},
    )
    resp_id = resp.json()["response_id"]

    fb1 = test_client.post(
        "/api/feedback",
        json={"response_id": resp_id, "outcome": "went_well", "notes": "Draft was accepted immediately"},
    )
    assert fb1.status_code == 200
    assert fb1.json()["status"] == "success"

    fb2 = test_client.post(
        "/api/feedback",
        json={"response_id": resp_id, "outcome": "pushback", "notes": "Client complained about meeting time"},
    )
    assert fb2.status_code == 200
    assert fb2.json()["status"] == "success"
    assert fb2.json()["feedback"]["outcome"] == "pushback"


def test_import_endpoint(test_client: TestClient) -> None:
    bad_import = test_client.post("/api/import", json={"client_id": "c1_apex", "text": ""})
    assert bad_import.status_code == 400

    good_import = test_client.post(
        "/api/import",
        json={"client_id": "c1_apex", "text": "Client emailed saying Slack channel #apex-dev is preferred for all tech updates."},
    )
    assert good_import.status_code == 200
    data = good_import.json()
    assert data["status"] == "imported"
    assert "recalled_extracted" in data


def test_get_observations_endpoint(test_client: TestClient) -> None:
    resp = test_client.get("/api/memory/observations?client_id=c1_apex")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)
