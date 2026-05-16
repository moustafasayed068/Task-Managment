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
from app.api.monitoring_api import router as monitoring_router


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

    # ====================== CORS (Runs first) ======================
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:5500",
            "http://127.0.0.1:5500",
            "http://localhost:8000",
            "http://127.0.0.1:8000",
            "*",
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["*"],
    )
    # ===============================================================

    # Routers are included after middlewares
    app.include_router(api_router, prefix=settings.api_prefix)
    app.include_router(monitoring_router)

    return app


app = create_app()


@app.get("/", tags=["health"])
async def root():
    return {"status": "ok", "message": "Task Management API is running"}