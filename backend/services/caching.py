import asyncio
import time
from typing import Callable, Awaitable, Any, Optional
from dataclasses import dataclass


@dataclass
class CacheEntry:
    """Cache entry with value and expiration time."""
    value: Any
    expires_at: float


class AsyncCache:
    """
    Async cache with TTL (time-to-live) and size limits.
    
    Features:
    - Automatic expiration of stale entries
    - Size limit with LRU eviction
    - Thread-safe with asyncio.Lock
    """
    
    def __init__(self, max_size: int = 1000, default_ttl: int = 300):
        """
        Initialize cache.
        
        Args:
            max_size: Maximum number of entries (default 1000)
            default_ttl: Default time-to-live in seconds (default 5 minutes)
        """
        self._cache: dict[str, CacheEntry] = {}
        self._lock = asyncio.Lock()
        self._max_size = max_size
        self._default_ttl = default_ttl
        self._access_order: list[str] = []  # For LRU
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache if not expired."""
        async with self._lock:
            entry = self._cache.get(key)
            
            if entry is None:
                return None
            
            # Check if expired
            if time.time() > entry.expires_at:
                del self._cache[key]
                self._access_order.remove(key)
                return None
            
            # Update access order (move to end for LRU)
            if key in self._access_order:
                self._access_order.remove(key)
            self._access_order.append(key)
            
            return entry.value
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None):
        """Set value in cache with optional TTL."""
        async with self._lock:
            expires_at = time.time() + (ttl if ttl is not None else self._default_ttl)
            self._cache[key] = CacheEntry(value=value, expires_at=expires_at)
            
            # Update access order
            if key in self._access_order:
                self._access_order.remove(key)
            self._access_order.append(key)
            
            # Evict oldest entries if over size limit
            while len(self._cache) > self._max_size:
                oldest_key = self._access_order.pop(0)
                del self._cache[oldest_key]
    
    async def get_or_set(
        self,
        key: str,
        fetcher: Callable[[], Awaitable[Any]],
        ttl: Optional[int] = None
    ) -> Any:
        """Get value from cache or fetch and cache it."""
        # Try to get from cache first
        value = await self.get(key)
        if value is not None:
            return value
        
        # Fetch new value
        value = await fetcher()
        
        # Cache it
        await self.set(key, value, ttl)
        
        return value
    
    async def delete(self, key: str):
        """Delete key from cache."""
        async with self._lock:
            if key in self._cache:
                del self._cache[key]
                self._access_order.remove(key)
    
    async def clear(self):
        """Clear all entries."""
        async with self._lock:
            self._cache.clear()
            self._access_order.clear()
    
    async def cleanup_expired(self):
        """Remove all expired entries (call periodically)."""
        async with self._lock:
            now = time.time()
            expired_keys = [
                key for key, entry in self._cache.items()
                if now > entry.expires_at
            ]
            for key in expired_keys:
                del self._cache[key]
                self._access_order.remove(key)
    
    def size(self) -> int:
        """Get current cache size."""
        return len(self._cache)


# Global cache instance
_global_cache = AsyncCache(max_size=1000, default_ttl=300)


# Convenience functions for backward compatibility
async def cache_get_or_set(
    key: str,
    fetcher: Callable[[], Awaitable[Any]],
    ttl: Optional[int] = None
) -> Any:
    """Get value from global cache or fetch and cache it."""
    return await _global_cache.get_or_set(key, fetcher, ttl)


async def cache_get(key: str) -> Optional[Any]:
    """Get value from global cache."""
    return await _global_cache.get(key)


async def cache_set(key: str, value: Any, ttl: Optional[int] = None):
    """Set value in global cache."""
    await _global_cache.set(key, value, ttl)


async def cache_clear():
    """Clear global cache."""
    await _global_cache.clear()