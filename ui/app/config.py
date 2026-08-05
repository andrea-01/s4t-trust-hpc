from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    gateway_url: str = "http://localhost:8000"

settings = Settings()
