from pydantic import BaseModel, field_validator
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
