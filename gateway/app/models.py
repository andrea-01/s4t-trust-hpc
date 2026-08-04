from pydantic import BaseModel
from typing import Optional

class OnboardingRequest(BaseModel):
    device_id: str
    owner_address: str
    requester_key: Optional[str] = None
