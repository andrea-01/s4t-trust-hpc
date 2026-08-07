import asyncio
import uuid
from typing import List, Dict, Set
from fastapi import HTTPException
from config import settings

class NodeRegistry:
    def __init__(self):
        # All available nodes
        self.all_nodes: List[str] = [n.strip() for n in settings.worker_nodes.split(",") if n.strip()]
        # Set of leased nodes
        self.leased_nodes: Set[str] = set()
        # Mapping from pipeline_id to list of leased nodes
        self.pipelines: Dict[str, List[str]] = {}
        # Lock for concurrent access
        self.lock = asyncio.Lock()

    async def lease_nodes(self, count: int) -> str:
        async with self.lock:
            available = [n for n in self.all_nodes if n not in self.leased_nodes]
            if len(available) < count:
                raise HTTPException(status_code=400, detail=f"Not enough nodes available. Requested {count}, but only {len(available)} free.")
            
            allocated = available[:count]
            for node in allocated:
                self.leased_nodes.add(node)
                
            pipeline_id = str(uuid.uuid4())
            self.pipelines[pipeline_id] = allocated
            return pipeline_id

    async def release_nodes(self, pipeline_id: str):
        async with self.lock:
            if pipeline_id not in self.pipelines:
                raise HTTPException(status_code=404, detail="Pipeline not found")
            
            allocated = self.pipelines.pop(pipeline_id)
            for node in allocated:
                self.leased_nodes.discard(node)

    async def get_pipeline_nodes(self, pipeline_id: str) -> List[str]:
        async with self.lock:
            if pipeline_id not in self.pipelines:
                raise HTTPException(status_code=404, detail="Pipeline not found")
            return list(self.pipelines[pipeline_id])

registry = NodeRegistry()
