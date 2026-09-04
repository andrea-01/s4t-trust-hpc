import asyncio
import uuid
import json
import os
from typing import List, Dict, Optional
from fastapi import HTTPException
from config import settings
from gateway_leasing_client import GatewayLeasingClient
from iotronic_client import IotronicClient

class NodeRegistry:
    def __init__(
        self,
        iotronic_client: Optional[IotronicClient] = None,
        leasing_client: Optional[GatewayLeasingClient] = None
    ):
        if iotronic_client is None:
            from pipeline_client import iotronic_client as default_iotronic_client
            self.iotronic_client = default_iotronic_client
        else:
            self.iotronic_client = iotronic_client
            
        self.leasing_client = leasing_client or GatewayLeasingClient(settings.gateway_url)
        # Mapping from pipeline_id to list of leased device_ids
        self.pipelines: Dict[str, List[str]] = {}
        self.lock = asyncio.Lock()

    async def lease_nodes(self, count: int) -> str:
        online_candidates = await self.iotronic_client.list_online_boards()
        if count > len(online_candidates):
            raise HTTPException(
                status_code=400,
                detail=f"Not enough online nodes in IoTronic. Requested {count}, found {len(online_candidates)} online."
            )

        allocated = []
        for device_id in online_candidates:
            if len(allocated) == count:
                break
            
            # Try to lease via gateway (checks Approved state and Availability)
            success = await self.leasing_client.lease_node(device_id)
            if success:
                allocated.append(device_id)

        if len(allocated) < count:
            # Rollback partially allocated nodes
            for device_id in allocated:
                await self.leasing_client.release_node(device_id)
            raise HTTPException(
                status_code=400,
                detail=f"Failed to lease {count} nodes via Gateway (insufficient approved/available nodes)."
            )
            
        async with self.lock:
            pipeline_id = str(uuid.uuid4())
            self.pipelines[pipeline_id] = allocated
            return pipeline_id


    async def release_nodes(self, pipeline_id: str):
        async with self.lock:
            if pipeline_id not in self.pipelines:
                raise HTTPException(status_code=404, detail="Pipeline not found")
            allocated = self.pipelines.pop(pipeline_id)
            
        for device_id in allocated:
            await self.leasing_client.release_node(device_id)

    async def get_pipeline_nodes(self, pipeline_id: str) -> List[str]:
        async with self.lock:
            if pipeline_id not in self.pipelines:
                raise HTTPException(status_code=404, detail="Pipeline not found")
            
            return list(self.pipelines[pipeline_id])

registry = NodeRegistry()
