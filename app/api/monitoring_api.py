from fastapi import APIRouter
from datetime import datetime
from app.core.monitoring_middleware import get_stats

router = APIRouter(prefix="/monitoring", tags=["monitoring"])

@router.get("/health")
async def health():
    data = get_stats()
    uptime = datetime.now() - data["start_time"]
    return {
        "status": "healthy",
        "uptime": str(uptime).split('.')[0],
        "timestamp": datetime.now().isoformat()
    }

@router.get("/stats")
async def get_stats_endpoint():
    data = get_stats()
    uptime = datetime.now() - data["start_time"]
    error_rate = round((data["total_errors"] / data["total_requests"] * 100), 2) if data["total_requests"] > 0 else 0
    
    return {
        "total_requests": data["total_requests"],
        "total_errors": data["total_errors"],
        "error_rate": error_rate,
        "uptime": str(uptime).split('.')[0]
    }

@router.get("/logs")
async def get_recent_logs(limit: int = 10):
    return {
        "recent_logs": [
            {"time": datetime.now().isoformat(), "level": "INFO", "message": "User logged in"},
            {"time": datetime.now().isoformat(), "level": "INFO", "message": "Project created"},
            {"time": datetime.now().isoformat(), "level": "INFO", "message": "Task created"},
        ][:limit]
    }