from fastapi import FastAPI

from app.api.router_api import api_router
from app.core import settings
from app.db.base_db import Base
from app.db.session_db import engine


def create_app() -> FastAPI:
    Base.metadata.create_all(bind=engine)
    app = FastAPI(
        title=settings.app_name,
        description="Core infrastructure for the Task Management API.",
        version="0.1.0",
    )
    app.include_router(api_router, prefix=settings.api_prefix)
    return app


app = create_app()


@app.get("/", tags=["health"])
async def health_check() -> dict:
    return {"status": "ok", "message": "Task Management API core is ready."}
