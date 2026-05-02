"""Caching utilities for the application."""
from functools import wraps
from cachetools import TTLCache
import time

# Initialize caches with TTL (Time To Live) in seconds
user_cache = TTLCache(maxsize=1000, ttl=300)  # 5 minutes
project_cache = TTLCache(maxsize=500, ttl=600)  # 10 minutes
task_cache = TTLCache(maxsize=1000, ttl=300)  # 5 minutes


def cache_user_by_id(func):
    """Decorator to cache user lookups by ID."""
    @wraps(func)
    def wrapper(user_id: int, *args, **kwargs):
        if user_id in user_cache:
            return user_cache[user_id]
        result = func(user_id, *args, **kwargs)
        if result:
            user_cache[user_id] = result
        return result
    return wrapper


def cache_project_by_id(func):
    """Decorator to cache project lookups by ID."""
    @wraps(func)
    def wrapper(project_id: int, *args, **kwargs):
        if project_id in project_cache:
            return project_cache[project_id]
        result = func(project_id, *args, **kwargs)
        if result:
            project_cache[project_id] = result
        return result
    return wrapper


def cache_all_projects(func):
    """Decorator to cache all projects list."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        cache_key = "all_projects"
        if cache_key in project_cache:
            return project_cache[cache_key]
        result = func(*args, **kwargs)
        project_cache[cache_key] = result
        return result
    return wrapper


def invalidate_user_cache(user_id: int = None):
    """Invalidate user cache for specific user or all users."""
    if user_id:
        user_cache.pop(user_id, None)
    else:
        user_cache.clear()


def invalidate_project_cache(project_id: int = None):
    """Invalidate project cache for specific project or all projects."""
    if project_id:
        project_cache.pop(project_id, None)
    else:
        project_cache.clear()
    # Also clear all projects list cache
    project_cache.pop("all_projects", None)
