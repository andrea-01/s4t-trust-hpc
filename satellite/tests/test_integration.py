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
async def test_full_pipeline_e2e_sequential(async_client, monkeypatch):
    """
    Test 1: Full sequential execution of 3 worker nodes via real IoTronic REST + Gateway leasing.
    """
    async def mock_workers():
        return ["worker-1", "worker-2", "worker-3"]
    monkeypatch.setattr(registry.iotronic_client, "list_online_boards", mock_workers)

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
async def test_concurrent_leasing_two_pipelines(async_client, monkeypatch):
    """
    Test 2: Scenario with all 3 worker boards leased concurrently across 2 pipelines.
    - Pipeline A leases 2 nodes (worker-1, worker-2).
    - Pipeline B leases 1 node (worker-3).
    - Attempting to lease a 4th node fails with 400.
    - Both pipelines execute their tasks.
    - Both pipelines are released.
    """
    async def mock_workers():
        return ["worker-1", "worker-2", "worker-3"]
    monkeypatch.setattr(registry.iotronic_client, "list_online_boards", mock_workers)

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

@pytest.mark.asyncio
async def test_parallel_verification_e2e(async_client, monkeypatch):
    """
    Test 5: Full parallel batch verification across 3 leased worker nodes via real IoTronic REST + Gateway leasing.
    Checks chunking with remainder, 100% valid signatures verification, timing, throughput and response structure.
    """
    async def mock_workers():
        return ["worker-1", "worker-2", "worker-3"]
    monkeypatch.setattr(registry.iotronic_client, "list_online_boards", mock_workers)

    # 1. Lease 3 nodes
    lease_resp = await async_client.post("/pipeline/lease", json={"count": 3})
    assert lease_resp.status_code == 200, f"Lease failed: {lease_resp.text}"
    pipeline_id = lease_resp.json()["pipeline_id"]

    try:
        # 2. Run parallel verification with batch=100 (100 / 3 -> chunks 34, 33, 33)
        run_resp = await async_client.post(
            f"/pipeline/{pipeline_id}/run-parallel",
            json={"total_batch": 100, "num_threads": 1, "base_seed": 42}
        )
        assert run_resp.status_code == 200, f"Run parallel failed: {run_resp.text}"
        data = run_resp.json()
        assert data["pipeline_id"] == pipeline_id
        assert data["num_nodes"] == 3
        assert data["total_batch_size"] == 100
        assert data["total_valid_count"] == 100
        assert data["total_time_seconds"] > 0
        assert data["aggregate_throughput"] > 0
        assert len(data["node_results"]) == 3

        # Check chunk sizes & valid counts
        chunks = [r["chunk_size"] for r in data["node_results"]]
        assert chunks == [34, 33, 33]
        valid_counts = [r["valid_count"] for r in data["node_results"]]
        assert valid_counts == [34, 33, 33]
    finally:
        # 3. Release pipeline
        release_resp = await async_client.post(f"/pipeline/{pipeline_id}/release")
        assert release_resp.status_code == 200

@pytest.mark.asyncio
async def test_dynamic_leasing_all_four_nodes_and_backend_constraint(async_client):
    """
    Test 6: Dynamic on-chain leasing of all 4 online approved nodes (test_board + worker-1/2/3).
    Verifies that:
    1. A dynamic board (test_board) is discovered and successfully leased on-chain.
    2. Attempting to execute compute on a board without an assigned worker backend
       explicitly raises an Exception instead of silently masking the issue.
    """
    lease_resp = await async_client.post("/pipeline/lease", json={"count": 4})
    assert lease_resp.status_code == 200, f"Lease failed: {lease_resp.text}"
    pipeline_id = lease_resp.json()["pipeline_id"]

    try:
        # Execution on pipeline containing test_board must fail with HTTP 500
        run_resp = await async_client.post(
            f"/pipeline/{pipeline_id}/run",
            json={"initial_value": 42}
        )
        assert run_resp.status_code == 500, "Expected 500 error due to unconfigured backend"

        # Verify exact exception raised by pipeline_client
        with pytest.raises(Exception) as exc_info:
            await run_pipeline_task(pipeline_id, ["test_board"], 42)
        assert "Nessun backend di calcolo configurato per il device test_board" in str(exc_info.value)
    finally:
        rel_resp = await async_client.post(f"/pipeline/{pipeline_id}/release")
        assert rel_resp.status_code == 200

@pytest.mark.asyncio
async def test_fallback_unapproved_candidate(async_client, monkeypatch):
    """
    Test 7: Verify fallback selection when an online candidate is NOT approved on-chain.
    Candidate list includes an unapproved device first; the satellite should skip it,
    lease the next valid candidates, and fulfill the requested count without error.
    """
    async def mock_list_online_boards():
        return ["unapproved_random_device_xyz", "worker-1", "worker-2"]

    monkeypatch.setattr(registry.iotronic_client, "list_online_boards", mock_list_online_boards)

    lease_resp = await async_client.post("/pipeline/lease", json={"count": 2})
    assert lease_resp.status_code == 200, f"Fallback lease failed: {lease_resp.text}"
    pipeline_id = lease_resp.json()["pipeline_id"]

    try:
        nodes = await registry.get_pipeline_nodes(pipeline_id)
        assert nodes == ["worker-1", "worker-2"]
    finally:
        rel_resp = await async_client.post(f"/pipeline/{pipeline_id}/release")
        assert rel_resp.status_code == 200


