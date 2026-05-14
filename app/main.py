from contextlib import asynccontextmanager
from fastapi import FastAPI, APIRouter
from datetime import datetime

from app.core.logger_core import logger, intercept_stdlib_loggers
from app.core.middleware import LoggingMiddleware
from app.core.monitoring_middleware import MonitoringMiddleware
from app.api.router_api import api_router
from app.core.config_core import settings
from app.db.base_db import Base
from app.db.session_db import engine
from fastapi.middleware.cors import CORSMiddleware


@asynccontextmanager
async def lifespan(app: FastAPI):
    intercept_stdlib_loggers()
    Base.metadata.create_all(bind=engine)

    # Health check for Redis connection on startup
    from app.core.cache_core import check_redis_health
    check_redis_health()

    # Seed default admin
    from app.db.session_db import SessionLocal
    from app.models.user_models import UserModel
    from app.core.security import hash_password

    with SessionLocal() as db:
        admin_username = settings.default_admin_user
        admin = db.query(UserModel).filter(UserModel.username == admin_username).first()
        if not admin:
            logger.info("Creating default admin account...")
            new_admin = UserModel(
                username=admin_username,
                email=f"{admin_username}@example.com",
                password_hash=hash_password(settings.default_admin_password),
                role="admin"
            )
            db.add(new_admin)
            db.commit()
            logger.info(f"Default admin created: {admin_username}")
        else:
            logger.debug("Admin user already exists")

    logger.info("✅ Task Management API started successfully")
    yield
    logger.info("Task Management API shutting down")


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        description="Task Management System",
        version="1.0.0",
        lifespan=lifespan,
    )
        # Middlewares (order matters: last added = first to run)
    # LoggingMiddleware and MonitoringMiddleware run AFTER CORS
    app.add_middleware(LoggingMiddleware)
    app.add_middleware(MonitoringMiddleware)

    # ====================== CORS (MUST be added last = runs first) ======================
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["*"],
    )
    # ====================================================================================

    # Routers
    app.include_router(api_router, prefix=settings.api_prefix)

    # Monitoring Dashboard
    monitoring_router = APIRouter(prefix="/monitoring", tags=["monitoring"])

    @monitoring_router.get("/health")
    async def health():
        from app.core.monitoring_middleware import get_stats
        data = get_stats()
        uptime = datetime.now() - data["start_time"]
        return {
            "status": "healthy",
            "uptime": str(uptime).split('.')[0],
            "timestamp": datetime.now().isoformat(),
            "total_requests": data["total_requests"]
        }

    @monitoring_router.get("/stats")
    async def get_stats_endpoint():
        from app.core.monitoring_middleware import get_stats
        data = get_stats()
        uptime = datetime.now() - data["start_time"]
        error_rate = round((data["total_errors"] / data["total_requests"] * 100), 2) if data["total_requests"] > 0 else 0.0

        return {
            "total_requests": data["total_requests"],
            "total_errors": data["total_errors"],
            "error_rate": error_rate,
            "uptime": str(uptime).split('.')[0]
        }

    @monitoring_router.get("/logs")
    async def get_recent_logs(limit: int = 10):
        import os
        from datetime import datetime
        try:
            log_dir = "logs"
            all_logs = []
            possible_files = ["app.log", "errors.log"]
            
            for filename in possible_files:
                filepath = os.path.join(log_dir, filename)
                if os.path.exists(filepath):
                    with open(filepath, 'r', encoding='utf-8') as f:
                        # Safely read just the end of the file
                        # This avoids loading massive log files into memory
                        f.seek(0, os.SEEK_END)
                        file_size = f.tell()
                        
                        # Read at most 10KB from the end
                        read_size = min(10240, file_size)
                        f.seek(file_size - read_size)
                        lines = f.readlines()
                        
                        # Ensure we get complete lines and take the last 100
                        if file_size > read_size:
                            lines = lines[1:]  # First line might be partial
                        lines = lines[-100:]
                        
                    for line in lines:
                        if " | " in line:
                            parts = line.strip().split(" | ", 3)
                            if len(parts) >= 3:
                                all_logs.append({
                                    "time": parts[0],
                                    "level": parts[1].strip(),
                                    "message": parts[-1]
                                })
            if not all_logs:
                all_logs = [{"time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "level": "INFO", "message": "No logs yet. Make API calls."}]
            return {"recent_logs": all_logs[-limit:]}
        except Exception as e:
            logger.error(f"Failed to read logs: {e}")
            return {"recent_logs": []}

    app.include_router(monitoring_router)

    return app


app = create_app()


@app.get("/", tags=["health"])
async def root():
    return {"status": "ok", "message": "Task Management API is running"}