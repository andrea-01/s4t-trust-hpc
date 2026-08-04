from fastapi import FastAPI, HTTPException
from contextlib import asynccontextmanager
from app.chain_client import chain_client
from app.event_poller import event_poller
from app.models import OnboardingRequest

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Start event poller on startup
    await event_poller.start()
    yield
    # Stop poller on shutdown
    await event_poller.stop()

app = FastAPI(title="S4T Trust HPC Gateway", lifespan=lifespan)

@app.post("/onboarding-request")
async def request_onboarding(req: OnboardingRequest):
    try:
        result = chain_client.request_onboarding(
            device_id=req.device_id,
            owner_address=req.owner_address,
            requester_key=req.requester_key
        )
        return {"status": "success", "tx_hash": result["tx_hash"], "request_id": result["request_id"]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/status/{request_id}")
async def get_status(request_id: int):
    status = chain_client.get_status(request_id)
    if "error" in status:
        raise HTTPException(status_code=500, detail=status["error"])
    return status

@app.get("/events/recent")
async def get_recent_events(limit: int = 50):
    return event_poller.get_recent_events(limit=limit)
