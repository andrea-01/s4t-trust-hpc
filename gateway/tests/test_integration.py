import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.config import settings

client = TestClient(app)

def test_round_trip():
    # 1. Request onboarding
    request_data = {
        "device_id": "test-device-01",
        "owner_address": "0x70997970C51812dc3A010C7d01b50e0d17dc79C8"
    }
    
    response = client.post("/onboarding-request", json=request_data)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "tx_hash" in data
    assert "request_id" in data
    
    request_id = data["request_id"]
    
    # 2. Get status for the dynamically created request
    status_response = client.get(f"/status/{request_id}")
    assert status_response.status_code == 200
    status_data = status_response.json()
    
    assert status_data["device_id"] == "test-device-01"
    assert status_data["status"] == "Pending"
    
    # 3. Check recent events
    events_response = client.get("/events/recent")
    assert events_response.status_code == 200
    events_data = events_response.json()
    assert isinstance(events_data, list)

def test_malformed_owner_address():
    request_data = {
        "device_id": "test-device-02",
        "owner_address": "not-an-address"
    }
    response = client.post("/onboarding-request", json=request_data)
    assert response.status_code == 422

