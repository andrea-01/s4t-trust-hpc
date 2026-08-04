from pydantic_settings import BaseSettings, SettingsConfigDict
import os

class Settings(BaseSettings):
    rpc_url: str = "http://hardhat-node:8545"
    deployments_path: str = "/app/deployments/localhost.json"
    abi_path: str = "/app/artifacts/contracts/OnboardingTrust.sol/OnboardingTrust.json"
    poll_interval: int = 5
    
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

settings = Settings()
