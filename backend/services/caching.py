import asyncio
from typing import Callable, Awaitable, Any

_cache: dict[str, Any] = {}
_lock = asyncio.Lock()


async def cache_get_or_set(key: str, fetcher: Callable[[], Awaitable[Any]]) -> Any:
    async with _lock:
        if key in _cache:
            return _cache[key]
    value = await fetcher()
    async with _lock:
        _cache[key] = value
    return value