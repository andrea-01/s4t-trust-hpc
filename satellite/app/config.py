from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    worker_nodes: str = "worker-1:50051,worker-2:50051,worker-3:50051"
    gateway_url: str = "http://gateway:8000"

    class Config:
        env_file = ".env"

settings = Settings()
