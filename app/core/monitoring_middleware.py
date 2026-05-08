from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from datetime import datetime

# Global stats
stats = {
    "total_requests": 0,
    "total_errors": 0,
    "start_time": datetime.now()
}

class MonitoringMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Count every request
        stats["total_requests"] += 1
        
        try:
            response = await call_next(request)
            
            if response.status_code >= 400:
                stats["total_errors"] += 1
                
            return response
        except Exception:
            stats["total_errors"] += 1
            raise


def get_stats():
    """Return current monitoring statistics"""
    return stats