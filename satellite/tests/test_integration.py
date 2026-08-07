import pytest
import asyncio
from httpx import AsyncClient
from httpx import ASGITransport
import sys
import os

# Add satellite/app to pythonpath for tests
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../app')))

from main import app
from node_registry import registry

import pytest_asyncio

@pytest_asyncio.fixture
async def async_client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client

@pytest.fixture(autouse=True)
def reset_registry():
    # Reset registry before each test
    registry.leased_nodes.clear()
    registry.pipelines.clear()
    # Make sure we have 3 nodes to test with
    registry.all_nodes = ["worker-1:50051", "worker-2:50051", "worker-3:50051"]

@pytest.mark.asyncio
async def test_lease_and_release(async_client):
    # Lease 2 nodes
    response = await async_client.post("/pipeline/lease", json={"count": 2})
    assert response.status_code == 200
    data = response.json()
    assert "pipeline_id" in data
    pipeline_id = data["pipeline_id"]
    
    assert len(registry.leased_nodes) == 2
    
    # Release them
    response = await async_client.post(f"/pipeline/{pipeline_id}/release")
    assert response.status_code == 200
    
    assert len(registry.leased_nodes) == 0

@pytest.mark.asyncio
async def test_double_leasing(async_client):
    # Try to lease 2 nodes
    response1 = await async_client.post("/pipeline/lease", json={"count": 2})
    assert response1.status_code == 200
    
    # Try to lease 2 more nodes (only 1 left)
    response2 = await async_client.post("/pipeline/lease", json={"count": 2})
    assert response2.status_code == 400
    assert "Not enough nodes available" in response2.json()["detail"]
    
@pytest.mark.asyncio
async def test_concurrent_leasing(async_client):
    # Simulate concurrent lease requests that together exceed capacity
    # Total capacity is 3. We make 3 concurrent requests for 2 nodes each.
    # Only one should succeed.
    tasks = [
        async_client.post("/pipeline/lease", json={"count": 2}),
        async_client.post("/pipeline/lease", json={"count": 2}),
        async_client.post("/pipeline/lease", json={"count": 2})
    ]
    results = await asyncio.gather(*tasks)
    
    successes = [r for r in results if r.status_code == 200]
    failures = [r for r in results if r.status_code == 400]
    
    assert len(successes) == 1
    assert len(failures) == 2
