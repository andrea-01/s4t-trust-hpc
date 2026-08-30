import pytest
import uuid
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)
client.auth = ("admin", "adminpassword")


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
    
    # Wait for the gateway event poller to catch up (default interval is 5s)
    import asyncio
    await asyncio.sleep(6)
    
    # 2. Check API endpoint for polling
    response = client.get("/api/requests")
    assert response.status_code == 200
    data = response.json()
    assert "events" in data
    
    # Verify the event is in the list returned by the polling endpoint
    events = data["events"]
    found = any(e.get("args", {}).get("deviceId") == device_id for e in events)
    assert found, f"Device ID {device_id} not found in recent events. Events: {events}"
    
    # Explicitly test that requestId=0 is present (if this test creates the very first event, or if it already exists)
    # Just to be safe, check if ANY event has requestId == 0 to cover the falsy bug
    found_zero_id = any(e.get("args", {}).get("requestId") == 0 for e in events)
    assert found_zero_id or len(events) == 0, f"Expected at least one event with requestId=0 if events exist, but got: {events}"
