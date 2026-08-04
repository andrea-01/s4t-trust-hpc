from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    smtp_host: str = "mailpit"
    smtp_port: int = 1025
    rpc_url: str = "http://hardhat-node:8545"
    deployments_path: str = "/app/deployments/localhost.json"
    abi_path: str = "/app/artifacts/contracts/OnboardingTrust.sol/OnboardingTrust.json"
    checkpoint_file: str = "/app/state/last_processed_block.txt"
    poll_interval: int = 5

    class Config:
        env_file = ".env"

settings = Settings()
