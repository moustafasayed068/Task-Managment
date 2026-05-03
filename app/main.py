from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.core.logger_core import logger, intercept_stdlib_loggers
from app.core.middleware import LoggingMiddleware
from app.api.router_api import api_router
from app.core.config_core import settings
from app.db.base_db import Base
from app.db.session_db import engine


@asynccontextmanager
async def lifespan(app: FastAPI):
    # ── startup ──────────────────────────────────────────────────────────────
    intercept_stdlib_loggers()           # redirect uvicorn logs → Loguru
    Base.metadata.create_all(bind=engine)

    # ── seed default admin ───────────────────────────────────────────────────
    from app.db.session_db import SessionLocal
    from app.models.user_models import UserModel
    from app.core.security import hash_password

    with SessionLocal() as db:
        admin = db.query(UserModel).filter(UserModel.username == "admin").first()
        if not admin:
            logger.info("No admin user found — creating default 'admin' account")
            new_admin = UserModel(
                username="admin",
                email="admin@example.com",
                password_hash=hash_password("admin123"),
                role="admin"
            )
            db.add(new_admin)
            db.commit()
            logger.info("Default admin account created: admin / admin123")
        else:
            logger.debug("Admin user already exists — skipping seed")

    logger.info("Task Management API starting up — all systems go")
    yield
    # ── shutdown ─────────────────────────────────────────────────────────────
    logger.info("Task Management API shutting down")


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        description="Core infrastructure for the Task Management API.",
        version="0.1.0",
        lifespan=lifespan,
    )
    app.add_middleware(LoggingMiddleware)
    app.include_router(api_router, prefix=settings.api_prefix)
    return app


app = create_app()


@app.get("/", tags=["health"])
async def health_check() -> dict:
    logger.debug("Health check endpoint called")
    return {"status": "ok", "message": "Task Management API is ready."}


@app.get("/test-email", tags=["diagnostics"])
def test_email() -> dict:
    """
    Fire a test email synchronously and report success/failure.
    Useful for validating SMTP configuration without triggering a real alert.
    """
    from app.services.email_service import send_email_sync

    logger.info("Test email endpoint triggered")
    ok = send_email_sync(
        subject="Task Management — SMTP Test",
        html="""\
        <html><body style="font-family:Arial,sans-serif;padding:20px;color:#333">
          <h2 style="color:#27ae60">SMTP Configuration Verified</h2>
          <p>If you received this email, your SMTP settings are correct.</p>
          <p style="font-size:11px;color:#aaa">Automated diagnostic — Task Management System</p>
        </body></html>
        """,
    )
    if ok:
        return {"status": "ok", "message": "Test email sent successfully. Check your inbox."}
    return {"status": "error", "message": "Email failed — check the terminal logs for details."}