from pydantic_settings import BaseSettings, SettingsConfigDict
import os

class Settings(BaseSettings):
    rpc_url: str = "http://hardhat-node:8545"
    deployments_path: str = "/app/deployments/localhost.json"
    leasing_deployments_path: str = "/app/deployments/leasing-localhost.json"
    abi_path: str = "/app/artifacts/contracts/OnboardingTrust.sol/OnboardingTrust.json"
    leasing_abi_path: str = "/app/artifacts/contracts/LeasingRegistry.sol/LeasingRegistry.json"
    trusted_devices_config: str = "/app/config/trusted-devices.json"
    poll_interval: int = 5
    admin_private_key: str
    ui_admin_username: str
    ui_admin_password: str
    
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

settings = Settings()

