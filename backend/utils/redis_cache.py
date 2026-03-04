import os
import redis.asyncio as redis
import json
from functools import wraps

_redis_client = None

async def get_redis_pool():
    global _redis_client
    if _redis_client is None:
        redis_url = os.environ.get("REDIS_URL", "redis://localhost")
        _redis_client = redis.from_url(redis_url, encoding="utf-8", decode_responses=True)
    return _redis_client

# Decorator for caching expensive endpoints
# Usage: @redis_cache(ttl=60)
def redis_cache(ttl=60):
    import decimal
    import datetime
    def custom_json_default(obj):
        if isinstance(obj, decimal.Decimal):
            return float(obj)
        if isinstance(obj, (datetime.datetime, datetime.date)):
            return obj.isoformat()
        raise TypeError(f"Object of type {obj.__class__.__name__} is not JSON serializable")
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            key = f"{func.__name__}:{json.dumps(args, default=str)}:{json.dumps(kwargs, default=str)}"
            redis_client = await get_redis_pool()
            cached = await redis_client.get(key)
            if cached:
                return json.loads(cached)
            result = await func(*args, **kwargs)
            await redis_client.set(key, json.dumps(result, default=custom_json_default), ex=ttl)
            return result
        return wrapper
    return decorator
