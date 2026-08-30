from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    gateway_url: str = "http://localhost:8000"
    ui_admin_username: str
    ui_admin_password: str

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

settings = Settings()

