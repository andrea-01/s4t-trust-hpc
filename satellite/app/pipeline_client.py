import re
import time
import asyncio
import logging
from typing import List, Dict, Any
from config import settings
from iotronic_client import IotronicClient

logger = logging.getLogger(__name__)

iotronic_client = IotronicClient(
    auth_url=settings.os_auth_url,
    username=settings.os_username,
    password=settings.os_password,
    project_name=settings.os_project_name,
    user_domain_name=settings.os_user_domain_name,
    project_domain_name=settings.os_project_domain_name,
    iotronic_url=settings.iotronic_url
)

async def run_pipeline_task(pipeline_id: str, nodes: List[str], initial_value: int) -> Dict[str, Any]:
    current_value = initial_value
    trace = []
    
    for device_id in nodes:
        # device_id matches board_name e.g. "worker-1"
        worker_addr = f"{device_id}:50051"
        params = {
            "worker_addr": worker_addr,
            "input_value": current_value
        }
        
        result_text = await iotronic_client.call_plugin(
            board_name=device_id,
            plugin_name=settings.plugin_name,
            parameters=params
        )
        
        if result_text.startswith("ERROR:"):
            raise Exception(f"Plugin execution failed on {device_id}: {result_text}")
            
        # Parse output format: "SUCCESS: Worker worker-1 incremented 42 -> 43"
        match = re.search(r"SUCCESS: Worker (\S+) incremented (-?\d+) -> (-?\d+)", result_text)
        if match:
            node_id = match.group(1)
            new_value = int(match.group(3))
        else:
            raise Exception(f"Unexpected response format from plugin on node {device_id}: '{result_text}'")
            
        current_value = new_value
        trace.append({
            "node_id": node_id,
            "timestamp": int(time.time()),
            "output": current_value,
            "raw_response": result_text
        })
        
    return {
        "final_value": current_value,
        "trace": trace
    }

async def run_parallel_verification(
    pipeline_id: str,
    nodes: List[str],
    total_batch: int,
    num_threads: int = 1,
    base_seed: int = 42
) -> Dict[str, Any]:
    num_nodes = len(nodes)
    if num_nodes == 0:
        raise Exception("No leased nodes available for parallel verification")
    if total_batch <= 0:
        raise Exception("Total batch must be > 0")

    # Chunking with remainder distribution identical to main_mpi.cpp and run_benchmark.py
    base_chunk = total_batch // num_nodes
    remainder = total_batch % num_nodes
    chunks = [base_chunk + (1 if i < remainder else 0) for i in range(num_nodes)]

    async def _call_node(i: int, device_id: str, chunk_size: int) -> Dict[str, Any]:
        worker_addr = f"{device_id}:50051"
        seed = base_seed + i
        params = {
            "worker_addr": worker_addr,
            "operation": "VERIFY_SIGNATURES_BATCH",
            "batch_size": chunk_size,
            "num_threads": num_threads,
            "seed": seed
        }
        t0 = time.perf_counter()
        result_text = await iotronic_client.call_plugin(
            board_name=device_id,
            plugin_name=settings.plugin_name,
            parameters=params
        )
        t1 = time.perf_counter()

        if result_text.startswith("ERROR:"):
            raise Exception(f"Plugin execution failed on {device_id}: {result_text}")

        # Parse format: "SUCCESS: Worker worker-1 verified 20/20 signatures in 0.001095s throughput=18269.18"
        pattern = r"SUCCESS: Worker (\S+) verified (\d+)/(\d+) signatures in ([\d\.]+)s throughput=([\d\.]+)"
        match = re.search(pattern, result_text)
        if not match:
            raise Exception(f"Unexpected response format from plugin on node {device_id}: '{result_text}'")

        node_id = match.group(1)
        valid_count = int(match.group(2))
        worker_time = float(match.group(4))
        worker_throughput = float(match.group(5))

        return {
            "node_id": node_id,
            "chunk_size": chunk_size,
            "valid_count": valid_count,
            "worker_time_seconds": worker_time,
            "worker_throughput": worker_throughput,
            "round_trip_seconds": t1 - t0,
            "raw_response": result_text
        }

    tasks = [_call_node(i, device_id, chunk_size) for i, (device_id, chunk_size) in enumerate(zip(nodes, chunks))]

    t_start = time.perf_counter()
    responses = await asyncio.gather(*tasks)
    t_end = time.perf_counter()

    total_time = t_end - t_start
    total_valid = sum(r["valid_count"] for r in responses)

    # Strict correctness check: 100% of signatures must be verified
    if total_valid != total_batch:
        raise Exception(
            f"CORRECTNESS CHECK FAILED: Expected {total_batch} valid signatures, "
            f"but workers returned {total_valid} valid signatures!"
        )

    aggregate_throughput = total_batch / total_time if total_time > 0 else 0.0

    return {
        "pipeline_id": pipeline_id,
        "nodes": nodes,
        "num_nodes": num_nodes,
        "threads_per_node": num_threads,
        "effective_parallelism": num_nodes * num_threads,
        "total_batch_size": total_batch,
        "total_valid_count": total_valid,
        "total_time_seconds": total_time,
        "aggregate_throughput": aggregate_throughput,
        "node_results": responses
    }
