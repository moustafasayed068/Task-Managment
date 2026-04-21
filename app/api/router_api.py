from fastapi import APIRouter

from app.api import auth_api
from app.api import users_api
from app.api import projects_api
from app.api import tasks_api

api_router = APIRouter()

api_router.include_router(auth_api.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(users_api.router, prefix="/users", tags=["Users"])
api_router.include_router(projects_api.router, prefix="/projects", tags=["Projects"])
api_router.include_router(tasks_api.router, prefix="/tasks", tags=["Tasks"])