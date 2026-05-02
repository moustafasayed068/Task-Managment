"""Caching utilities using Redis."""
from functools import wraps
import json
import redis
from app.core.config_core import settings

# Initialize Redis connection
redis_client = redis.Redis(
    host=settings.redis_host,
    port=settings.redis_port,
    db=settings.redis_db,
    password=settings.redis_password,
    decode_responses=True,
    socket_connect_timeout=5,
    socket_keepalive=True
)

# Cache key prefixes
USER_CACHE_PREFIX = "cache:user:"
PROJECT_CACHE_PREFIX = "cache:project:"
TASK_CACHE_PREFIX = "cache:task:"
ALL_PROJECTS_CACHE_KEY = "cache:all_projects"


def cache_user_by_id(func):
    """Decorator to cache user lookups by ID in Redis."""
    @wraps(func)
    def wrapper(user_id: int, *args, **kwargs):
        cache_key = f"{USER_CACHE_PREFIX}{user_id}"
        
        # Try to get from Redis cache
        try:
            cached_data = redis_client.get(cache_key)
            if cached_data:
                print(f"✓ CACHE HIT: user {user_id}")
                return json.loads(cached_data)
        except Exception as e:
            print(f"Redis get error: {e}")
        
        # Cache miss - call original function (database query)
        print(f"✗ CACHE MISS: user {user_id}")
        result = func(user_id, *args, **kwargs)
        
        # Store in Redis with TTL
        if result:
            try:
                # Convert SQLAlchemy object to dict if needed
                if hasattr(result, '__dict__'):
                    data = {k: v for k, v in result.__dict__.items() if not k.startswith('_')}
                else:
                    data = result
                redis_client.setex(
                    cache_key,
                    settings.cache_user_ttl,
                    json.dumps(data, default=str)
                )
            except Exception as e:
                print(f"Redis set error: {e}")
        
        return result
    return wrapper


def cache_project_by_id(func):
    """Decorator to cache project lookups by ID in Redis."""
    @wraps(func)
    def wrapper(project_id: int, *args, **kwargs):
        cache_key = f"{PROJECT_CACHE_PREFIX}{project_id}"
        
        # Try to get from Redis cache
        try:
            cached_data = redis_client.get(cache_key)
            if cached_data:
                print(f"✓ CACHE HIT: project {project_id}")
                return json.loads(cached_data)
        except Exception as e:
            print(f"Redis get error: {e}")
        
        # Cache miss - call original function
        print(f"✗ CACHE MISS: project {project_id}")
        result = func(project_id, *args, **kwargs)
        
        # Store in Redis with TTL
        if result:
            try:
                if hasattr(result, '__dict__'):
                    data = {k: v for k, v in result.__dict__.items() if not k.startswith('_')}
                else:
                    data = result
                redis_client.setex(
                    cache_key,
                    settings.cache_project_ttl,
                    json.dumps(data, default=str)
                )
            except Exception as e:
                print(f"Redis set error: {e}")
        
        return result
    return wrapper


def cache_all_projects(func):
    """Decorator to cache all projects list in Redis."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        cache_key = ALL_PROJECTS_CACHE_KEY
        
        # Try to get from Redis cache
        try:
            cached_data = redis_client.get(cache_key)
            if cached_data:
                print(f"✓ CACHE HIT: all_projects")
                return json.loads(cached_data)
        except Exception as e:
            print(f"Redis get error: {e}")
        
        # Cache miss - call original function
        print(f"✗ CACHE MISS: all_projects")
        result = func(*args, **kwargs)
        
        # Store list in Redis with TTL
        if result:
            try:
                data = []
                for item in result:
                    if hasattr(item, '__dict__'):
                        item_dict = {k: v for k, v in item.__dict__.items() if not k.startswith('_')}
                    else:
                        item_dict = item
                    data.append(item_dict)
                redis_client.setex(
                    cache_key,
                    settings.cache_project_ttl,
                    json.dumps(data, default=str)
                )
            except Exception as e:
                print(f"Redis set error: {e}")
        
        return result
    return wrapper


def invalidate_user_cache(user_id: int = None):
    """Invalidate user cache for specific user or all users."""
    try:
        if user_id:
            # Clear cache for ONE user
            cache_key = f"{USER_CACHE_PREFIX}{user_id}"
            redis_client.delete(cache_key)
            print(f"Invalidated user cache: {user_id}")
        else:
            # Clear cache for ALL users - use pattern
            pattern = f"{USER_CACHE_PREFIX}*"
            keys = redis_client.keys(pattern)
            if keys:
                redis_client.delete(*keys)
            print(f"Invalidated all user cache")
    except Exception as e:
        print(f"Redis error during invalidation: {e}")


def invalidate_project_cache(project_id: int = None):
    """Invalidate project cache for specific project or all projects."""
    try:
        if project_id:
            # Clear cache for ONE project
            cache_key = f"{PROJECT_CACHE_PREFIX}{project_id}"
            redis_client.delete(cache_key)
            print(f"Invalidated project cache: {project_id}")
        else:
            # Clear cache for ALL projects
            pattern = f"{PROJECT_CACHE_PREFIX}*"
            keys = redis_client.keys(pattern)
            if keys:
                redis_client.delete(*keys)
        
        # Also clear all projects list cache
        redis_client.delete(ALL_PROJECTS_CACHE_KEY)
        print(f"Invalidated all project cache")
    except Exception as e:
        print(f"Redis error during invalidation: {e}")

