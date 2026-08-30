from pydantic import BaseModel, ConfigDict, Field, field_validator
from typing import List, Optional
from web3 import Web3

class OnboardingRequest(BaseModel):
    device_id: str
    owner_address: str

    @field_validator('owner_address')
    @classmethod
    def validate_address(cls, v: str) -> str:
        if not Web3.is_address(v):
            raise ValueError('Invalid Ethereum address')
        return v

class LeasingRequest(BaseModel):
    device_id: str

class TrustedStack(BaseModel):
    stack_id: str = Field(..., alias="stackId")
    description: Optional[str] = ""
    device_id_prefixes: List[str] = Field(..., alias="deviceIdPrefixes")

    model_config = ConfigDict(populate_by_name=True)

    @field_validator("stack_id")
    @classmethod
    def validate_stack_id(cls, v: str) -> str:
        s = v.strip()
        if not s:
            raise ValueError("stackId non puo' essere vuoto")
        return s

    @field_validator("device_id_prefixes")
    @classmethod
    def validate_prefixes(cls, v: List[str]) -> List[str]:
        if not v:
            raise ValueError("deviceIdPrefixes non puo' essere vuoto")
        cleaned = []
        seen = set()
        for p in v:
            ps = p.strip()
            if not ps:
                raise ValueError("I prefissi in deviceIdPrefixes non possono essere vuoti")
            if ps in seen:
                raise ValueError(f"Prefisso duplicato rilevato: '{ps}'")
            seen.add(ps)
            cleaned.append(ps)
        return cleaned

class TrustedDevicesConfig(BaseModel):
    trusted_stacks: List[TrustedStack] = Field(default_factory=list, alias="trustedStacks")

    model_config = ConfigDict(populate_by_name=True)

