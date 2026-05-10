from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
import time
from datetime import datetime
import asyncio

# Global stats
stats = {
    "total_requests": 0,
    "total_errors": 0,
    "start_time": datetime.now(),
    "requests_by_status": {},
}

class MonitoringMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        
        try:
            response = await call_next(request)
            
            # Update stats
            stats["total_requests"] += 1
            status_code = response.status_code
            
            if status_code >= 400:
                stats["total_errors"] += 1
                
            if status_code not in stats["requests_by_status"]:
                stats["requests_by_status"][status_code] = 0
            stats["requests_by_status"][status_code] += 1
            
            return response
            
        except Exception as e:
            stats["total_requests"] += 1
            stats["total_errors"] += 1
            raise


def get_stats():
    """Return current monitoring statistics"""
    return stats