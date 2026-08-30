import os
import json
import pytest
import tempfile
from fastapi.testclient import TestClient
from app.main import app
from app.trust_config_client import TrustConfigClient
from app.models import TrustedStack, TrustedDevicesConfig
from app.config import settings

client = TestClient(app)

AUTH_HEADER = ("admin", "adminpassword")

@pytest.fixture
def temp_trust_file():
    with tempfile.NamedTemporaryFile(mode="w+", suffix=".json", delete=False) as f:
        initial_data = {
            "trustedStacks": [
                {
                    "stackId": "initial-stack",
                    "description": "Initial stack description",
                    "deviceIdPrefixes": ["init-"]
                }
            ]
        }
        json.dump(initial_data, f, indent=2)
        temp_path = f.name
    
    yield temp_path
    if os.path.exists(temp_path):
        os.remove(temp_path)

def test_auth_rejection():
    # 1. Without credentials -> 401
    resp = client.get("/trust/stacks")
    assert resp.status_code == 401
    assert "WWW-Authenticate" in resp.headers

    # 2. With wrong credentials -> 401
    resp = client.get("/trust/stacks", auth=("wronguser", "wrongpass"))
    assert resp.status_code == 401

    # 3. Non-trust routes (like /events/recent) remain unauthenticated
    resp = client.get("/events/recent")
    assert resp.status_code == 200

def test_trust_config_client_direct(temp_trust_file):
    trust_client = TrustConfigClient(config_path=temp_trust_file)
    
    # 1. List stacks
    stacks = trust_client.list_stacks()
    assert len(stacks) == 1
    assert stacks[0].stack_id == "initial-stack"
    assert stacks[0].device_id_prefixes == ["init-"]

    # 2. Add stack
    new_stack = TrustedStack(
        stackId="test-stack-2",
        description="Second test stack",
        deviceIdPrefixes=["prefix-a", "prefix-b"]
    )
    trust_client.add_stack(new_stack)

    stacks_after = trust_client.list_stacks()
    assert len(stacks_after) == 2
    assert any(s.stack_id == "test-stack-2" for s in stacks_after)

    # Verify real file on disk is valid JSON and contains the added stack
    with open(temp_trust_file, "r") as f:
        disk_data = json.load(f)
    assert len(disk_data["trustedStacks"]) == 2

    # 3. Add duplicate stack -> ValueError
    with pytest.raises(ValueError, match="esiste gia"):
        trust_client.add_stack(new_stack)

    # 4. Delete stack
    trust_client.delete_stack("initial-stack")
    stacks_final = trust_client.list_stacks()
    assert len(stacks_final) == 1
    assert stacks_final[0].stack_id == "test-stack-2"

    # 5. Delete non-existent stack -> KeyError
    with pytest.raises(KeyError):
        trust_client.delete_stack("non-existent")

def test_trust_endpoints_crud(temp_trust_file, monkeypatch):
    # Point the global trust_config_client to our temporary file
    from app import main
    test_trust_client = TrustConfigClient(config_path=temp_trust_file)
    monkeypatch.setattr(main, "trust_config_client", test_trust_client)

    # 1. GET /trust/stacks with valid auth
    resp = client.get("/trust/stacks", auth=AUTH_HEADER)
    assert resp.status_code == 200
    stacks = resp.json()
    assert len(stacks) == 1
    assert stacks[0]["stackId"] == "initial-stack"

    # 2. POST /trust/stacks with valid data
    new_stack_payload = {
        "stackId": "api-stack",
        "description": "Added via API",
        "deviceIdPrefixes": ["api-device-", "custom-"]
    }
    resp = client.post("/trust/stacks", json=new_stack_payload, auth=AUTH_HEADER)
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "success"
    assert data["stack"]["stackId"] == "api-stack"

    # 3. POST /trust/stacks with duplicate stackId -> 400
    resp = client.post("/trust/stacks", json=new_stack_payload, auth=AUTH_HEADER)
    assert resp.status_code == 400
    assert "esiste gia" in resp.json()["detail"]

    # 4. POST /trust/stacks with invalid data (empty prefixes) -> 422
    invalid_payload = {
        "stackId": "invalid-stack",
        "description": "Invalid",
        "deviceIdPrefixes": []
    }
    resp = client.post("/trust/stacks", json=invalid_payload, auth=AUTH_HEADER)
    assert resp.status_code == 422

    # 5. POST /trust/stacks with duplicate prefixes in payload -> 422
    dup_prefix_payload = {
        "stackId": "dup-stack",
        "description": "Duplicate prefix",
        "deviceIdPrefixes": ["dup-", "dup-"]
    }
    resp = client.post("/trust/stacks", json=dup_prefix_payload, auth=AUTH_HEADER)
    assert resp.status_code == 422

    # 6. DELETE /trust/stacks/{stack_id}
    resp = client.delete("/trust/stacks/initial-stack", auth=AUTH_HEADER)
    assert resp.status_code == 200

    # 7. DELETE non-existent stack -> 404
    resp = client.delete("/trust/stacks/non-existent-id", auth=AUTH_HEADER)
    assert resp.status_code == 404
