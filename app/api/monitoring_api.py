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
        "timestamp": datetime.now().isoformat(),
        "total_requests": data["total_requests"]
    }


@router.get("/stats")
async def get_stats_endpoint():
    data = get_stats()
    uptime = datetime.now() - data["start_time"]
    
    error_rate = round((data["total_errors"] / data["total_requests"] * 100), 2) \
        if data["total_requests"] > 0 else 0.0

    return {
        "total_requests": data["total_requests"],
        "total_errors": data["total_errors"],
        "error_rate": error_rate,
        "uptime": str(uptime).split('.')[0],
        "requests_by_status": data["requests_by_status"]
    }


@router.get("/logs")
async def get_recent_logs(limit: int = 10):
    # TODO: Later connect to real log file
    # For now returning simulated logs
    return {
        "recent_logs": [
            {
                "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "level": "INFO",
                "message": "Task 'Design Login Page' status updated to In Progress"
            },
            {
                "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "level": "INFO",
                "message": "New Project 'Mobile App' created by Admin"
            },
            {
                "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "level": "WARNING",
                "message": "Unauthorized access attempt to admin endpoint"
            },
            {
                "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "level": "ERROR",
                "message": "Database connection timeout occurred"
            }
        ][:limit]
    }