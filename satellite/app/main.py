from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from node_registry import registry
from pipeline_client import run_pipeline_task

app = FastAPI(title="S4T Trust HPC - Satellite")

class LeaseRequest(BaseModel):
    count: int

class RunRequest(BaseModel):
    initial_value: int

@app.post("/pipeline/lease")
async def lease_pipeline(req: LeaseRequest):
    if req.count <= 0:
        raise HTTPException(status_code=422, detail="Count must be > 0")
    pipeline_id = await registry.lease_nodes(req.count)
    return {"pipeline_id": pipeline_id}

@app.post("/pipeline/{pipeline_id}/release")
async def release_pipeline(pipeline_id: str):
    await registry.release_nodes(pipeline_id)
    return {"status": "released", "pipeline_id": pipeline_id}

@app.post("/pipeline/{pipeline_id}/run")
async def run_pipeline(pipeline_id: str, req: RunRequest):
    # Fetch nodes from registry
    nodes = await registry.get_pipeline_nodes(pipeline_id)
    try:
        result = await run_pipeline_task(pipeline_id, nodes, req.initial_value)
        return {"pipeline_id": pipeline_id, "result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
