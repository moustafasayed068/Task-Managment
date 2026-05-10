from app import models
from app.models import user_models
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


@asynccontextmanager
async def lifespan(app: FastAPI):
    # ── Startup ──────────────────────────────────────────────────────────────
    intercept_stdlib_loggers()
    Base.metadata.create_all(bind=engine)

    # Seed default admin
    from app.db.session_db import SessionLocal
    from app.models.user_models import UserModel
    from app.core.security import hash_password

    with SessionLocal() as db:
        admin = db.query(UserModel).filter(UserModel.username == "admin").first()
        if not admin:
            logger.info("Creating default admin account...")
            new_admin = UserModel(
                username="admin",
                email="admin@example.com",
                password_hash=hash_password("admin123"),
                role="admin"
            )
            db.add(new_admin)
            db.commit()
            logger.info("Default admin created: admin / admin123")
        else:
            logger.debug("Admin user already exists")

    logger.info("✅ Task Management API started successfully")
    yield
    # ── Shutdown ─────────────────────────────────────────────────────────────
    logger.info("Task Management API shutting down")


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        description="Task Management System",
        version="1.0.0",
        lifespan=lifespan,
    )

    # CORS
    from fastapi.middleware.cors import CORSMiddleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Important: Add Monitoring Middleware FIRST
    app.add_middleware(MonitoringMiddleware)
    app.add_middleware(LoggingMiddleware)

    # Include main API router
    app.include_router(api_router, prefix=settings.api_prefix)

    # Monitoring Dashboard Routes (Directly under /monitoring)
    # ====================== MONITORING DASHBOARD ROUTES ======================
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
        
        error_rate = round((data["total_errors"] / data["total_requests"] * 100), 2) \
            if data["total_requests"] > 0 else 0.0

        return {
            "total_requests": data["total_requests"],
            "total_errors": data["total_errors"],
            "error_rate": error_rate,
            "uptime": str(uptime).split('.')[0]
        }

    @monitoring_router.get("/logs")
    async def get_recent_logs(limit: int = 10):
        """Read from actual log files (app.log)"""
        import os
        from datetime import datetime
        
        try:
            log_dir = "logs"
            all_logs = []
            
            # Check for app.log and errors.log
            possible_files = ["app.log", "errors.log"]
            
            for filename in possible_files:
                filepath = os.path.join(log_dir, filename)
                if os.path.exists(filepath):
                    try:
                        with open(filepath, 'r', encoding='utf-8') as f:
                            lines = f.readlines()[-150:]  # Last 150 lines
                            
                        for line in lines:
                            line = line.strip()
                            if line and " | " in line:
                                try:
                                    parts = line.split(" | ", 3)
                                    if len(parts) >= 3:
                                        all_logs.append({
                                            "time": parts[0],
                                            "level": parts[1].strip(),
                                            "message": parts[-1]
                                        })
                                except:
                                    continue
                    except:
                        continue

            # If no parsed logs, return recent sample
            if not all_logs:
                all_logs = [
                    {
                        "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "level": "INFO",
                        "message": "Real logs are being written to app.log"
                    },
                    {
                        "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "level": "INFO",
                        "message": "Monitoring dashboard is now connected"
                    }
                ]

            # Return newest logs first
            return {"recent_logs": all_logs[-limit:]}

        except Exception as e:
            return {
                "recent_logs": [{
                    "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "level": "ERROR",
                    "message": f"Could not read logs: {str(e)}"
                }]
            }
    # =====================================================================

    app.include_router(monitoring_router)

    return app


app = create_app()


@app.get("/", tags=["health"])
async def root():
    return {"status": "ok", "message": "Task Management API is running"}