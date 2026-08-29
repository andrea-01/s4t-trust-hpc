from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    worker_nodes: str = "worker-1,worker-2,worker-3"
    gateway_url: str = "http://gateway:8000"
    
    # Keystone Auth Settings
    os_auth_url: str = "http://keystone:5000/v3"
    os_project_name: str = "admin"
    os_user_domain_name: str = "Default"
    os_project_domain_name: str = "Default"
    os_username: str = "admin"
    os_password: str = "s4t"
    
    # IoTronic Settings
    iotronic_url: str = "http://iotronic-conductor:8812"
    plugin_name: str = "grpc_client"

    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()
