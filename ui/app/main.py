from fastapi import FastAPI, Request, Form, HTTPException, Depends, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from app.gateway_client import gateway_client, GatewayUnavailableError
from app.config import settings
import secrets
import os

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

app = FastAPI(title="S4T Trust HPC Dashboard", dependencies=[Depends(authenticate_admin)])

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
    
    requests_dict = {}
    for event in events:
        args = event.get("args", {})
        req_id = args.get("requestId")
        if req_id is not None:
            if req_id not in requests_dict:
                requests_dict[req_id] = {
                    "requestId": req_id,
                    "deviceId": args.get("deviceId", "N/A"),
                    "owner": args.get("owner", "N/A"),
                    "status": "Unknown"
                }
            if args.get("deviceId"):
                requests_dict[req_id]["deviceId"] = args.get("deviceId")
            if args.get("owner"):
                requests_dict[req_id]["owner"] = args.get("owner")
                
            evt_type = event.get("event")
            if evt_type == "OnboardingRequested":
                requests_dict[req_id]["status"] = "Pending"
            elif evt_type == "OnboardingApproved":
                requests_dict[req_id]["status"] = "Approved"
            elif evt_type == "OnboardingRejected":
                requests_dict[req_id]["status"] = "Rejected"
            elif evt_type == "OnboardingRevoked":
                requests_dict[req_id]["status"] = "Revoked"

    aggregated_requests = list(requests_dict.values())
    
    return templates.TemplateResponse(
        "dashboard.html", 
        {"request": request, "requests": aggregated_requests, "error_message": error_message}
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
            
        requests_dict = {}
        for event in events:
            args = event.get("args", {})
            req_id = args.get("requestId")
            if req_id is not None:
                if req_id not in requests_dict:
                    requests_dict[req_id] = {
                        "requestId": req_id,
                        "deviceId": args.get("deviceId", "N/A"),
                        "owner": args.get("owner", "N/A"),
                        "status": "Unknown"
                    }
                if args.get("deviceId"):
                    requests_dict[req_id]["deviceId"] = args.get("deviceId")
                if args.get("owner"):
                    requests_dict[req_id]["owner"] = args.get("owner")
                    
                evt_type = event.get("event")
                if evt_type == "OnboardingRequested":
                    requests_dict[req_id]["status"] = "Pending"
                elif evt_type == "OnboardingApproved":
                    requests_dict[req_id]["status"] = "Approved"
                elif evt_type == "OnboardingRejected":
                    requests_dict[req_id]["status"] = "Rejected"
                elif evt_type == "OnboardingRevoked":
                    requests_dict[req_id]["status"] = "Revoked"

        aggregated_requests = list(requests_dict.values())
        
        return templates.TemplateResponse(
            "dashboard.html",
            {"request": request, "requests": aggregated_requests, "error_message": error_message}
        )
        
    return RedirectResponse(url="/", status_code=303)

@app.get("/trust", response_class=HTMLResponse)
async def trust_view(request: Request):
    stacks = []
    error_message = None
    try:
        stacks = await gateway_client.get_trusted_stacks()
    except GatewayUnavailableError as e:
        error_message = str(e)
    
    return templates.TemplateResponse(
        "trust.html",
        {"request": request, "stacks": stacks, "error_message": error_message}
    )

@app.post("/trust", response_class=HTMLResponse)
async def add_trusted_stack(
    request: Request,
    stack_id: str = Form(...),
    description: str = Form(""),
    prefixes: str = Form(...)
):
    error_message = None
    prefix_list = [p.strip() for p in prefixes.replace("\r\n", "\n").replace(",", "\n").split("\n") if p.strip()]
    
    if not prefix_list:
        error_message = "Almeno un prefisso deviceId e' richiesto"
    else:
        try:
            await gateway_client.add_trusted_stack(
                stack_id=stack_id.strip(),
                description=description.strip(),
                device_id_prefixes=prefix_list
            )
            return RedirectResponse(url="/trust", status_code=303)
        except (GatewayUnavailableError, ValueError) as e:
            error_message = str(e)

    stacks = []
    try:
        stacks = await gateway_client.get_trusted_stacks()
    except Exception:
        pass

    return templates.TemplateResponse(
        "trust.html",
        {
            "request": request,
            "stacks": stacks,
            "error_message": error_message,
            "form_stack_id": stack_id,
            "form_description": description,
            "form_prefixes": prefixes,
        }
    )

@app.post("/trust/delete/{stack_id}")
async def delete_trusted_stack(request: Request, stack_id: str):
    error_message = None
    try:
        await gateway_client.delete_trusted_stack(stack_id)
        return RedirectResponse(url="/trust", status_code=303)
    except (GatewayUnavailableError, ValueError) as e:
        error_message = str(e)

    stacks = []
    try:
        stacks = await gateway_client.get_trusted_stacks()
    except Exception:
        pass

    return templates.TemplateResponse(
        "trust.html",
        {"request": request, "stacks": stacks, "error_message": error_message}
    )

