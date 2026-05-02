from pydantic import BaseSettings

class Settings(BaseSettings):
    app_name: str = "Task Management API"
    api_prefix: str = "/api/v1"
    secret_key: str = "super-secret-key-change-me"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    database_url: str = "sqlite:///./task_management.db"
    
    # Redis settings
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0
    redis_password: str = None
    
    # Cache TTL in seconds (Redis)
    cache_user_ttl: int = 300  # 5 minutes
    cache_project_ttl: int = 600  # 10 minutes
    cache_task_ttl: int = 300  # 5 minutes

    class Config:
        env_file = ".env"


settings = Settings()
