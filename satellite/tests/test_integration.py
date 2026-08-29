import pytest
import asyncio
import os
import sys
from httpx import AsyncClient, ASGITransport

# Set dev defaults for environment before importing config if running locally
if "GATEWAY_URL" not in os.environ:
    os.environ["GATEWAY_URL"] = "http://localhost:8000"
if "OS_AUTH_URL" not in os.environ:
    os.environ["OS_AUTH_URL"] = "http://localhost:5000/v3"
if "IOTRONIC_URL" not in os.environ:
    os.environ["IOTRONIC_URL"] = "http://localhost:8812"
if "OS_PASSWORD" not in os.environ:
    os.environ["OS_PASSWORD"] = "s4t"

# Add satellite/app to pythonpath for tests
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../app')))

from config import settings

# If running on host outside Docker network, override defaults to localhost
if os.environ.get("GATEWAY_URL"):
    settings.gateway_url = os.environ["GATEWAY_URL"]
if os.environ.get("OS_AUTH_URL"):
    settings.os_auth_url = os.environ["OS_AUTH_URL"]
if os.environ.get("IOTRONIC_URL"):
    settings.iotronic_url = os.environ["IOTRONIC_URL"]

from main import app
from node_registry import registry
from pipeline_client import iotronic_client, run_pipeline_task

# Re-point clients to updated settings
registry.leasing_client.gateway_url = settings.gateway_url
iotronic_client.auth_url = settings.os_auth_url.rstrip("/")
iotronic_client.iotronic_url = settings.iotronic_url.rstrip("/")
iotronic_client.password = settings.os_password

import pytest_asyncio

@pytest_asyncio.fixture
async def async_client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test", timeout=60.0) as client:
        yield client

@pytest.mark.asyncio
async def test_full_pipeline_e2e_sequential(async_client):
    """
    Test 1: Full sequential execution of 3 nodes via real IoTronic REST + Gateway leasing.
    No mocks.
    """
    # 1. Lease 3 nodes
    lease_resp = await async_client.post("/pipeline/lease", json={"count": 3})
    assert lease_resp.status_code == 200, f"Lease failed: {lease_resp.text}"
    lease_data = lease_resp.json()
    assert "pipeline_id" in lease_data
    pipeline_id = lease_data["pipeline_id"]

    try:
        # 2. Run pipeline with initial value 42
        run_resp = await async_client.post(
            f"/pipeline/{pipeline_id}/run",
            json={"initial_value": 42}
        )
        assert run_resp.status_code == 200, f"Run failed: {run_resp.text}"
        run_data = run_resp.json()
        assert run_data["pipeline_id"] == pipeline_id

        result = run_data["result"]
        # 3 workers in series: 42 -> 43 -> 44 -> 45
        assert result["final_value"] == 45
        trace = result["trace"]
        assert len(trace) == 3
        assert [step["output"] for step in trace] == [43, 44, 45]
        assert [step["node_id"] for step in trace] == ["worker-1", "worker-2", "worker-3"]
    finally:
        # 3. Release pipeline
        release_resp = await async_client.post(f"/pipeline/{pipeline_id}/release")
        assert release_resp.status_code == 200
        assert release_resp.json()["status"] == "released"

@pytest.mark.asyncio
async def test_concurrent_leasing_two_pipelines(async_client):
    """
    Test 2: Scenario with at least 2 boards leased concurrently across 2 pipelines.
    - Pipeline A leases 2 nodes (e.g. worker-1, worker-2).
    - Pipeline B leases 1 node (worker-3).
    - Attempting to lease a 4th node fails with 400.
    - Both pipelines execute their tasks.
    - Both pipelines are released.
    """
    # Lease Pipeline A (2 nodes)
    resp_a = await async_client.post("/pipeline/lease", json={"count": 2})
    assert resp_a.status_code == 200, f"Lease A failed: {resp_a.text}"
    pipeline_a = resp_a.json()["pipeline_id"]

    try:
        # Lease Pipeline B (1 node)
        resp_b = await async_client.post("/pipeline/lease", json={"count": 1})
        assert resp_b.status_code == 200, f"Lease B failed: {resp_b.text}"
        pipeline_b = resp_b.json()["pipeline_id"]

        try:
            # Capacity exceeded: try to lease another node (should fail with 400)
            resp_c = await async_client.post("/pipeline/lease", json={"count": 1})
            assert resp_c.status_code == 400

            # Run Pipeline A (2 nodes: 10 -> 11 -> 12)
            run_a = await async_client.post(f"/pipeline/{pipeline_a}/run", json={"initial_value": 10})
            assert run_a.status_code == 200
            res_a = run_a.json()["result"]
            assert res_a["final_value"] == 12
            assert len(res_a["trace"]) == 2

            # Run Pipeline B (1 node: 50 -> 51)
            run_b = await async_client.post(f"/pipeline/{pipeline_b}/run", json={"initial_value": 50})
            assert run_b.status_code == 200
            res_b = run_b.json()["result"]
            assert res_b["final_value"] == 51
            assert len(res_b["trace"]) == 1

        finally:
            rel_b = await async_client.post(f"/pipeline/{pipeline_b}/release")
            assert rel_b.status_code == 200
    finally:
        rel_a = await async_client.post(f"/pipeline/{pipeline_a}/release")
        assert rel_a.status_code == 200

@pytest.mark.asyncio
async def test_error_handling_and_validation(async_client):
    """
    Test 3: Error handling for invalid inputs and non-existent pipelines.
    """
    # Count 0 or negative
    resp = await async_client.post("/pipeline/lease", json={"count": 0})
    assert resp.status_code == 422

    # Non-existent pipeline run
    resp = await async_client.post("/pipeline/non-existent-id/run", json={"initial_value": 10})
    assert resp.status_code == 404

    # Non-existent pipeline release
    resp = await async_client.post("/pipeline/non-existent-id/release")
    assert resp.status_code == 404

@pytest.mark.asyncio
async def test_unexpected_plugin_response_format(monkeypatch):
    """
    Test 4: Verify that unrecognized plugin response format explicitly raises Exception.
    """
    async def mock_call_plugin(board_name, plugin_name, parameters):
        return "UNKNOWN_RESPONSE_FORMAT_WITHOUT_REGEX_MATCH"

    monkeypatch.setattr(iotronic_client, "call_plugin", mock_call_plugin)

    with pytest.raises(Exception) as exc_info:
        await run_pipeline_task("test-pipe", ["worker-1"], 10)

    assert "Unexpected response format from plugin on node worker-1" in str(exc_info.value)
    assert "UNKNOWN_RESPONSE_FORMAT_WITHOUT_REGEX_MATCH" in str(exc_info.value)
