import re
import time
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
            node_id = device_id
            new_value = current_value + 1
            
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
