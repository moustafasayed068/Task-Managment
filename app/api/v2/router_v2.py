"""
router_v2.py
============
Assembles all v2 routers (authorization + business-logic layer) under
a single APIRouter that can be included in the main app.

To wire this into the application add these two lines to
app/api/router_api.py:

    from app.api.v2.router_v2 import v2_router
    api_router.include_router(v2_router)

The resulting URL prefixes will be:
    /api/v1/v2/projects/...
    /api/v1/v2/tasks/...

If you prefer a cleaner prefix (e.g. /api/v2/...) include v2_router
directly in main.py with  prefix="/api/v2"  instead.
"""

from fastapi import APIRouter

from app.api.v2 import projects_api_v2, tasks_api_v2

v2_router = APIRouter(prefix="/v2")

v2_router.include_router(
    projects_api_v2.router,
    prefix="/projects",
    tags=["Projects v2 – Authorization & Business Logic"],
)

v2_router.include_router(
    tasks_api_v2.router,
    prefix="/tasks",
    tags=["Tasks v2 – Authorization, Filtering & Workflow"],
)
