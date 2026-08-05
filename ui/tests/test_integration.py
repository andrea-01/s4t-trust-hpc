import pytest
import uuid
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

@pytest.mark.asyncio
async def test_dashboard_integration():
    device_id = f"test-ui-{uuid.uuid4().hex[:6]}"
    # Using the owner address from Hardhat test node (Account #1)
    owner_address = "0x70997970C51812dc3A010C7d01b50e0d17dc79C8"
    
    # 1. Create a request via UI form
    response = client.post(
        "/request", 
        data={"device_id": device_id, "owner_address": owner_address},
        follow_redirects=True
    )
    assert response.status_code == 200
    assert device_id in response.text
    
    # 2. Check API endpoint for polling
    response = client.get("/api/requests")
    assert response.status_code == 200
    data = response.json()
    assert "events" in data
    
    # Verify the event is in the list returned by the polling endpoint
    events = data["events"]
    found = any(e.get("args", {}).get("deviceId") == device_id for e in events)
    assert found, f"Device ID {device_id} not found in recent events. Events: {events}"
