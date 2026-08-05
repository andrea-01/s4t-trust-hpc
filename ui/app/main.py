from fastapi import FastAPI, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from app.gateway_client import gateway_client, GatewayUnavailableError
import os

app = FastAPI(title="S4T Trust HPC Dashboard")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))
app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "static")), name="static")

@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    events = []
    error_message = None
    try:
        events = await gateway_client.get_recent_events()
    except GatewayUnavailableError as e:
        error_message = str(e)
    
    return templates.TemplateResponse(
        "dashboard.html", 
        {"request": request, "events": events, "error_message": error_message}
    )

@app.get("/api/requests")
async def get_requests():
    try:
        events = await gateway_client.get_recent_events()
        return {"events": events}
    except GatewayUnavailableError as e:
        raise HTTPException(status_code=503, detail=str(e))

@app.post("/request")
async def create_request(request: Request, device_id: str = Form(...), owner_address: str = Form(...)):
    error_message = None
    try:
        await gateway_client.request_onboarding(device_id, owner_address)
    except (GatewayUnavailableError, ValueError) as e:
        error_message = str(e)
    
    if error_message:
        events = []
        try:
            events = await gateway_client.get_recent_events()
        except GatewayUnavailableError:
            pass
        return templates.TemplateResponse(
            "dashboard.html",
            {"request": request, "events": events, "error_message": error_message}
        )
        
    return RedirectResponse(url="/", status_code=303)
