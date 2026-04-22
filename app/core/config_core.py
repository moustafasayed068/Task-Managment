from pydantic import BaseSettings

class Settings(BaseSettings):
    app_name: str = "Task Management API"
    api_prefix: str = "/api/v1"
    secret_key: str = "super-secret-key-change-me"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    database_url: str = "sqlite:///./task_management.db"

    class Config:
        env_file = ".env"


settings = Settings()
