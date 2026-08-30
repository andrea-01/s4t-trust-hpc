from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from contextlib import asynccontextmanager
import secrets
from typing import List

from app.chain_client import chain_client
from app.event_poller import event_poller
from app.models import OnboardingRequest, LeasingRequest, TrustedStack
from app.leasing_client import LeasingClient
from app.trust_config_client import trust_config_client
from app.config import settings

security = HTTPBasic()

def authenticate_admin(credentials: HTTPBasicCredentials = Depends(security)):
    is_user_ok = secrets.compare_digest(
        credentials.username.encode("utf8"), settings.ui_admin_username.encode("utf8")
    )
    is_pass_ok = secrets.compare_digest(
        credentials.password.encode("utf8"), settings.ui_admin_password.encode("utf8")
    )
    if not (is_user_ok and is_pass_ok):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenziali non valide",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username

leasing_client = LeasingClient(
    rpc_url=settings.rpc_url,
    deployments_path=settings.leasing_deployments_path,
    abi_path=settings.leasing_abi_path,
    private_key=settings.admin_private_key
)

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
            owner_address=req.owner_address
        )
        return {"status": "success", "tx_hash": result["tx_hash"], "request_id": result["request_id"]}
    except Exception as e:
        error_msg = str(e).lower()
        if "connection" in error_msg or "timeout" in error_msg or "max retries exceeded" in error_msg:
            raise HTTPException(status_code=503, detail="Blockchain node unreachable")
        elif "revert" in error_msg or "execution reverted" in error_msg:
            raise HTTPException(status_code=400, detail=f"Contract reverted: {str(e)}")
        else:
            raise HTTPException(status_code=400, detail=f"Transaction failed: {str(e)}")

@app.get("/status/{request_id}")
async def get_status(request_id: int):
    status = chain_client.get_status(request_id)
    if "error" in status:
        raise HTTPException(status_code=500, detail=status["error"])
    return status

@app.get("/events/recent")
async def get_recent_events(limit: int = 50):
    return event_poller.get_recent_events(limit=limit)

@app.post("/leasing/lease")
async def lease_node(req: LeasingRequest):
    try:
        tx_hash = leasing_client.lease_node(req.device_id)
        return {"status": "success", "tx_hash": tx_hash}
    except Exception as e:
        error_msg = str(e).lower()
        if "node not approved" in error_msg:
            raise HTTPException(status_code=403, detail="Node is not approved for leasing")
        elif "already leased" in error_msg:
            raise HTTPException(status_code=409, detail="Node is already leased")
        elif "device not found" in error_msg:
            raise HTTPException(status_code=404, detail="Device not found")
        else:
            raise HTTPException(status_code=400, detail=f"Transaction failed: {str(e)}")

@app.post("/leasing/release")
async def release_node(req: LeasingRequest):
    try:
        tx_hash = leasing_client.release_node(req.device_id)
        return {"status": "success", "tx_hash": tx_hash}
    except Exception as e:
        error_msg = str(e).lower()
        if "not leased" in error_msg:
            raise HTTPException(status_code=400, detail="Node is not currently leased")
        elif "not the current leaser" in error_msg:
            raise HTTPException(status_code=403, detail="You are not the current leaser")
        else:
            raise HTTPException(status_code=400, detail=f"Transaction failed: {str(e)}")

@app.get("/leasing/status/{device_id}")
async def get_leasing_status(device_id: str):
    try:
        status = leasing_client.get_leasing_status(device_id)
        return {"status": "success", "data": status}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving status: {str(e)}")

@app.get("/trust/stacks", dependencies=[Depends(authenticate_admin)])
async def list_trusted_stacks():
    try:
        stacks = trust_config_client.list_stacks()
        return [s.model_dump(by_alias=True) for s in stacks]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading trust config: {str(e)}")

@app.post("/trust/stacks", dependencies=[Depends(authenticate_admin)])
async def add_trusted_stack(stack: TrustedStack):
    try:
        created = trust_config_client.add_stack(stack)
        return {"status": "success", "stack": created.model_dump(by_alias=True)}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error saving trusted stack: {str(e)}")

@app.delete("/trust/stacks/{stack_id}", dependencies=[Depends(authenticate_admin)])
async def delete_trusted_stack(stack_id: str):
    try:
        trust_config_client.delete_stack(stack_id)
        return {"status": "success", "message": f"Stack '{stack_id}' removed"}
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e).strip("'"))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting trusted stack: {str(e)}")

