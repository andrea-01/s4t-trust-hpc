import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock
from app.main import app
from app import gateway_client as gc_module

client = TestClient(app)

AUTH_HEADER = ("admin", "adminpassword")

def test_ui_auth_rejection():
    # 1. Access without credentials -> 401
    assert client.get("/").status_code == 401
    assert client.get("/api/requests").status_code == 401
    assert client.post("/request", data={"device_id": "d1", "owner_address": "0x123"}).status_code == 401
    assert client.get("/trust").status_code == 401
    assert client.post("/trust", data={"stack_id": "s1", "prefixes": "p1"}).status_code == 401
    assert client.post("/trust/delete/s1").status_code == 401

    # 2. Access with wrong credentials -> 401
    assert client.get("/", auth=("wrong", "pass")).status_code == 401
    assert client.get("/trust", auth=("wrong", "pass")).status_code == 401

def test_ui_dashboard_authenticated(monkeypatch):
    mock_events = AsyncMock(return_value=[])
    monkeypatch.setattr(gc_module.gateway_client, "get_recent_events", mock_events)

    resp = client.get("/", auth=AUTH_HEADER)
    assert resp.status_code == 200
    assert "S4T Trust HPC Dashboard" in resp.text
    assert "Stack Fidati (Allowlist)" in resp.text

def test_ui_trust_view_and_actions(monkeypatch):
    # Mock gateway client trust methods
    sample_stacks = [
        {
            "stackId": "test-stack-1",
            "description": "Test stack 1 description",
            "deviceIdPrefixes": ["worker-", "test-"]
        }
    ]
    mock_get = AsyncMock(return_value=sample_stacks)
    mock_add = AsyncMock(return_value={"status": "success"})
    mock_delete = AsyncMock(return_value={"status": "success"})

    monkeypatch.setattr(gc_module.gateway_client, "get_trusted_stacks", mock_get)
    monkeypatch.setattr(gc_module.gateway_client, "add_trusted_stack", mock_add)
    monkeypatch.setattr(gc_module.gateway_client, "delete_trusted_stack", mock_delete)

    # 1. GET /trust
    resp = client.get("/trust", auth=AUTH_HEADER)
    assert resp.status_code == 200
    assert "test-stack-1" in resp.text
    assert "worker-" in resp.text
    assert "Aggiungi Nuovo Stack Fidato" in resp.text

    # 2. POST /trust (Add stack)
    resp = client.post(
        "/trust",
        data={
            "stack_id": "new-edge-stack",
            "description": "Edge nodes",
            "prefixes": "edge-, rpi-"
        },
        auth=AUTH_HEADER,
        follow_redirects=False
    )
    assert resp.status_code == 303
    assert resp.headers["location"] == "/trust"
    mock_add.assert_called_once_with(
        stack_id="new-edge-stack",
        description="Edge nodes",
        device_id_prefixes=["edge-", "rpi-"]
    )

    # 3. POST /trust/delete/test-stack-1
    resp = client.post(
        "/trust/delete/test-stack-1",
        auth=AUTH_HEADER,
        follow_redirects=False
    )
    assert resp.status_code == 303
    assert resp.headers["location"] == "/trust"
    mock_delete.assert_called_once_with("test-stack-1")
