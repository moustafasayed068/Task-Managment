"""Caching utilities – works with or without Redis.

When Redis is not installed / not running the app falls back
to a lightweight in-memory dict cache so that every code path
that calls the cache decorators still works correctly.
"""
from functools import wraps
import json
import time
from app.core.config_core import settings
from app.core.logger_core import logger

# ---------------------------------------------------------------------------
# Try to import redis; if the package isn't installed, we go straight to
# in-memory mode without any connection attempts.
# ---------------------------------------------------------------------------
try:
    import redis as _redis_lib
    _REDIS_PKG_AVAILABLE = True
except ImportError:
    _redis_lib = None
    _REDIS_PKG_AVAILABLE = False


# ---------------------------------------------------------------------------
# Circuit Breaker State
# ---------------------------------------------------------------------------
class CacheState:
    AVAILABLE = False          # Start pessimistic – will be set True on successful ping
    LAST_CHECK = 0
    COOLDOWN_SECONDS = 60      # Don't retry more often than once per minute


# ---------------------------------------------------------------------------
# In-memory fallback cache  (simple dict with TTL support)
# ---------------------------------------------------------------------------
_mem_cache: dict[str, tuple[float, str]] = {}   # key -> (expire_timestamp, json_value)


def _mem_get(key: str) -> str | None:
    entry = _mem_cache.get(key)
    if entry is None:
        return None
    expire_ts, value = entry
    if time.time() > expire_ts:
        _mem_cache.pop(key, None)
        return None
    return value


def _mem_setex(key: str, ttl: int, value: str):
    _mem_cache[key] = (time.time() + ttl, value)


def _mem_delete(key: str):
    _mem_cache.pop(key, None)


def _mem_delete_pattern(pattern: str):
    """Delete keys matching a simple glob pattern (only trailing * supported)."""
    prefix = pattern.rstrip("*")
    to_delete = [k for k in _mem_cache if k.startswith(prefix)]
    for k in to_delete:
        _mem_cache.pop(k, None)


# ---------------------------------------------------------------------------
# Redis client  (created lazily, only if the redis package exists)
# ---------------------------------------------------------------------------
redis_client = None

if _REDIS_PKG_AVAILABLE:
    try:
        redis_client = _redis_lib.Redis(
            host=settings.redis_host,
            port=settings.redis_port,
            db=settings.redis_db,
            password=settings.redis_password,
            decode_responses=True,
            socket_connect_timeout=0.5,
            socket_timeout=0.5,
            socket_keepalive=True
        )
    except Exception:
        redis_client = None


# Cache key prefixes
USER_CACHE_PREFIX = "cache:user:"
PROJECT_CACHE_PREFIX = "cache:project:"
TASK_CACHE_PREFIX = "cache:task:"
ALL_PROJECTS_CACHE_KEY = "cache:all_projects"


# ---------------------------------------------------------------------------
# Health check  (called once at startup from lifespan)
# ---------------------------------------------------------------------------
def check_redis_health(retries=1, backoff=0.5):
    """Test Redis connection on startup.

    Uses only 1 retry with a very short backoff so that local-dev startup
    is never blocked.  When Redis is genuinely available (e.g. via Docker)
    it will connect on the first try.
    """
    if redis_client is None:
        CacheState.AVAILABLE = False
        logger.info("ℹ️  Redis package not installed or client not created – using in-memory cache.")
        return False

    for attempt in range(retries):
        try:
            redis_client.ping()
            CacheState.AVAILABLE = True
            logger.info(f"✅ Redis connected at {settings.redis_host}:{settings.redis_port}")
            return True
        except Exception:
            if attempt < retries - 1:
                logger.warning(f"⏳ Redis connection failed. Retrying in {backoff}s …")
                time.sleep(backoff)
                backoff *= 2
            else:
                CacheState.AVAILABLE = False
                CacheState.LAST_CHECK = time.time()
                logger.info(
                    f"ℹ️  Redis not available at {settings.redis_host}:{settings.redis_port} "
                    f"– using in-memory cache (app works fine without Redis)."
                )
                return False


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------
def _is_redis_available():
    """Check if Redis is available, respecting the circuit breaker cooldown."""
    if CacheState.AVAILABLE:
        return True

    if redis_client is None:
        return False

    # If currently unavailable, check if cooldown has passed
    if time.time() - CacheState.LAST_CHECK > CacheState.COOLDOWN_SECONDS:
        try:
            redis_client.ping()
            CacheState.AVAILABLE = True
            logger.info("✅ Redis recovered! Re-enabling Redis cache.")
            return True
        except Exception:
            CacheState.LAST_CHECK = time.time()
            return False

    return False


def _mark_redis_failed():
    if CacheState.AVAILABLE:
        CacheState.AVAILABLE = False
        CacheState.LAST_CHECK = time.time()
        logger.warning("⚠️ Redis connection lost. Falling back to in-memory cache.")


# ---------------------------------------------------------------------------
# Generic get / set / delete that transparently use Redis OR memory
# ---------------------------------------------------------------------------
def _cache_get(key: str) -> str | None:
    if _is_redis_available():
        try:
            return redis_client.get(key)
        except Exception:
            _mark_redis_failed()
    return _mem_get(key)


def _cache_setex(key: str, ttl: int, value: str):
    if _is_redis_available():
        try:
            redis_client.setex(key, ttl, value)
            return
        except Exception:
            _mark_redis_failed()
    _mem_setex(key, ttl, value)


def _cache_delete(key: str):
    if _is_redis_available():
        try:
            redis_client.delete(key)
            return
        except Exception:
            _mark_redis_failed()
    _mem_delete(key)


def _cache_delete_pattern(pattern: str):
    if _is_redis_available():
        try:
            cursor = 0
            while True:
                cursor, keys = redis_client.scan(cursor=cursor, match=pattern)
                if keys:
                    redis_client.delete(*keys)
                if cursor == 0:
                    break
            return
        except Exception:
            _mark_redis_failed()
    _mem_delete_pattern(pattern)


# ---------------------------------------------------------------------------
# Decorators
# ---------------------------------------------------------------------------
def cache_user_by_id(func):
    """Decorator to cache user lookups by ID."""
    @wraps(func)
    def wrapper(user_id: int, *args, **kwargs):
        cache_key = f"{USER_CACHE_PREFIX}{user_id}"

        cached_data = _cache_get(cache_key)
        if cached_data:
            return json.loads(cached_data)

        result = func(user_id, *args, **kwargs)

        if result:
            data = (
                {k: v for k, v in result.__dict__.items() if not k.startswith('_')}
                if hasattr(result, '__dict__') else result
            )
            _cache_setex(cache_key, settings.cache_user_ttl, json.dumps(data, default=str))

        return result
    return wrapper


def cache_project_by_id(func):
    """Decorator to cache project lookups by ID."""
    @wraps(func)
    def wrapper(project_id: int, *args, **kwargs):
        cache_key = f"{PROJECT_CACHE_PREFIX}{project_id}"

        cached_data = _cache_get(cache_key)
        if cached_data:
            return json.loads(cached_data)

        result = func(project_id, *args, **kwargs)

        if result:
            data = (
                {k: v for k, v in result.__dict__.items() if not k.startswith('_')}
                if hasattr(result, '__dict__') else result
            )
            _cache_setex(cache_key, settings.cache_project_ttl, json.dumps(data, default=str))

        return result
    return wrapper


def cache_all_projects(func):
    """Decorator to cache all projects list."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        cache_key = ALL_PROJECTS_CACHE_KEY

        cached_data = _cache_get(cache_key)
        if cached_data:
            return json.loads(cached_data)

        result = func(*args, **kwargs)

        if result:
            data = [
                ({k: v for k, v in item.__dict__.items() if not k.startswith('_')}
                 if hasattr(item, '__dict__') else item)
                for item in result
            ]
            _cache_setex(cache_key, settings.cache_project_ttl, json.dumps(data, default=str))

        return result
    return wrapper


def cache_task_by_id(func):
    """Decorator to cache task lookups by ID."""
    @wraps(func)
    def wrapper(task_id: int, *args, **kwargs):
        cache_key = f"{TASK_CACHE_PREFIX}{task_id}"

        cached_data = _cache_get(cache_key)
        if cached_data:
            return json.loads(cached_data)

        result = func(task_id, *args, **kwargs)

        if result:
            data = (
                {k: v for k, v in result.__dict__.items() if not k.startswith('_')}
                if hasattr(result, '__dict__') else result
            )
            _cache_setex(cache_key, settings.cache_task_ttl, json.dumps(data, default=str))

        return result
    return wrapper


# ---------------------------------------------------------------------------
# Invalidation helpers
# ---------------------------------------------------------------------------
def invalidate_user_cache(user_id: int = None):
    """Invalidate user cache."""
    if user_id:
        _cache_delete(f"{USER_CACHE_PREFIX}{user_id}")
    else:
        _cache_delete_pattern(f"{USER_CACHE_PREFIX}*")


def invalidate_project_cache(project_id: int = None):
    """Invalidate project cache."""
    if project_id:
        _cache_delete(f"{PROJECT_CACHE_PREFIX}{project_id}")
    else:
        _cache_delete_pattern(f"{PROJECT_CACHE_PREFIX}*")
    _cache_delete(ALL_PROJECTS_CACHE_KEY)


def invalidate_task_cache(task_id: int = None):
    """Invalidate task cache and also clear any 'all tasks' cache if needed."""
    if task_id:
        _cache_delete(f"{TASK_CACHE_PREFIX}{task_id}")
    else:
        _cache_delete_pattern(f"{TASK_CACHE_PREFIX}*")
    _cache_delete_pattern("cache:tasks:all:*")
