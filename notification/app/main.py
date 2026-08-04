import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI
from notification.app.owners_registry import OwnersRegistry
from notification.app.chain_listener import ChainListener

registry = OwnersRegistry()
listener = ChainListener(registry)
listener_task = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global listener_task
    listener_task = asyncio.create_task(listener.poll_events())
    yield
    listener.stop()
    if listener_task:
        await listener_task

app = FastAPI(title="S4T Trust HPC - Notification Service", lifespan=lifespan)

@app.get("/health")
async def health_check():
    return {"status": "ok", "listener_running": listener.is_running}
