from pathlib import Path
from pydantic import Field
from pydantic_settings import BaseSettings

import os
import secrets

_ENV_FILE = Path(__file__).resolve().parent.parent.parent / ".env"

def is_docker():
    return os.path.exists('/.dockerenv')

class Settings(BaseSettings):
    app_name: str = "Task Management API"
    api_prefix: str = "/api/v1"
    # ponytail: random per-process secret when SECRET_KEY is unset, so tokens die on restart
    # and differ between workers. Set SECRET_KEY in .env for anything beyond local dev.
    secret_key: str = Field(default_factory=lambda: secrets.token_urlsafe(32))
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    database_url: str = "sqlite:///./task_management.db"

    default_admin_user: str = "admin"
    default_admin_password: str | None = None

    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0
    redis_password: str | None = None

    cache_user_ttl: int = 300
    cache_project_ttl: int = 600
    cache_task_ttl: int = 300

    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_use_tls: bool = True
    smtp_username: str = ""
    smtp_password: str = ""
    alert_email_from: str = ""
    alert_email_to: str = ""

    model_config = {
        "env_file": str(_ENV_FILE),
        "extra": "ignore",
    }


settings = Settings()