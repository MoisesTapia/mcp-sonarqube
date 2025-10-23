"""Caching utilities for SonarQube MCP."""

import asyncio
import hashlib
import json
import time
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, Union

try:
    import redis.asyncio as redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

from .logger import get_logger

logger = get_logger(__name__)


class CacheBackend(ABC):
    """Abstract base class for cache backends."""

    @abstractmethod
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        pass

    @abstractmethod
    async def set(self, key: str, value: Any, ttl: int) -> None:
        """Set value in cache with TTL."""
        pass

    @abstractmethod
    async def delete(self, key: str) -> None:
        """Delete value from cache."""
        pass

    @abstractmethod
    async def clear(self) -> None:
        """Clear all cache entries."""
        pass

    @abstractmethod
    async def exists(self, key: str) -> bool:
        """Check if key exists in cache."""
        pass


class MemoryCache(CacheBackend):
    """In-memory cache implementation."""

    def __init__(self):
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._lock = asyncio.Lock()

    async def get(self, key: str) -> Optional[Any]:
        """Get value from memory cache."""
        async with self._lock:
            if key not in self._cache:
                return None

            entry = self._cache[key]
            
            # Check if expired
            if time.time() > entry["expires_at"]:
                del self._cache[key]
                return None

            return entry["value"]

    async def set(self, key: str, value: Any, ttl: int) -> None:
        """Set value in memory cache."""
        async with self._lock:
            self._cache[key] = {
                "value": value,
                "expires_at": time.time() + ttl,
                "created_at": time.time(),
            }

    async def delete(self, key: str) -> None:
        """Delete value from memory cache."""
        async with self._lock:
            self._cache.pop(key, None)

    async def clear(self) -> None:
        """Clear all cache entries."""
        async with self._lock:
            self._cache.clear()

    async def exists(self, key: str) -> bool:
        """Check if key exists in memory cache."""
        async with self._lock:
            if key not in self._cache:
                return False

            entry = self._cache[key]
            
            # Check if expired
            if time.time() > entry["expires_at"]:
                del self._cache[key]
                return False

            return True

    async def cleanup_expired(self) -> int:
        """Remove expired entries and return count of removed items."""
        async with self._lock:
            current_time = time.time()
            expired_keys = [
                key for key, entry in self._cache.items()
                if current_time > entry["expires_at"]
            ]
            
            for key in expired_keys:
                del self._cache[key]
            
            return len(expired_keys)

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        return {
            "total_entries": len(self._cache),
            "memory_usage_bytes": sum(
                len(str(entry["value"])) for entry in self._cache.values()
            ),
        }


class RedisCache(CacheBackend):
    """Redis cache implementation."""

    def __init__(self, redis_url: str, key_prefix: str = "sonarqube_mcp:"):
        if not REDIS_AVAILABLE:
            raise ImportError("redis package is required for RedisCache")
        
        self.redis_url = redis_url
        self.key_prefix = key_prefix
        self._client: Optional[redis.Redis] = None

    async def _get_client(self) -> redis.Redis:
        """Get or create Redis client."""
        if self._client is None:
            self._client = redis.from_url(self.redis_url, decode_responses=True)
        return self._client

    def _make_key(self, key: str) -> str:
        """Add prefix to cache key."""
        return f"{self.key_prefix}{key}"

    async def get(self, key: str) -> Optional[Any]:
        """Get value from Redis cache."""
        try:
            client = await self._get_client()
            value = await client.get(self._make_key(key))
            
            if value is None:
                return None
            
            return json.loads(value)
        except Exception as e:
            logger.error(f"Redis get error: {e}")
            return None

    async def set(self, key: str, value: Any, ttl: int) -> None:
        """Set value in Redis cache."""
        try:
            client = await self._get_client()
            serialized_value = json.dumps(value, default=str)
            await client.setex(self._make_key(key), ttl, serialized_value)
        except Exception as e:
            logger.error(f"Redis set error: {e}")

    async def delete(self, key: str) -> None:
        """Delete value from Redis cache."""
        try:
            client = await self._get_client()
            await client.delete(self._make_key(key))
        except Exception as e:
            logger.error(f"Redis delete error: {e}")

    async def clear(self) -> None:
        """Clear all cache entries with our prefix."""
        try:
            client = await self._get_client()
            keys = await client.keys(f"{self.key_prefix}*")
            if keys:
                await client.delete(*keys)
        except Exception as e:
            logger.error(f"Redis clear error: {e}")

    async def exists(self, key: str) -> bool:
        """Check if key exists in Redis cache."""
        try:
            client = await self._get_client()
            return bool(await client.exists(self._make_key(key)))
        except Exception as e:
            logger.error(f"Redis exists error: {e}")
            return False

    async def close(self) -> None:
        """Close Redis connection."""
        if self._client:
            await self._client.close()


class CacheManager:
    """High-level cache manager with multiple backends and TTL configuration."""

    def __init__(
        self,
        backend: CacheBackend,
        default_ttl: int = 300,
        ttl_by_type: Optional[Dict[str, int]] = None,
    ):
        self.backend = backend
        self.default_ttl = default_ttl
        self.ttl_by_type = ttl_by_type or {}
        
        # Cache hit/miss statistics
        self._stats = {
            "hits": 0,
            "misses": 0,
            "sets": 0,
            "deletes": 0,
        }

    def _get_cache_key(self, key_type: str, identifier: str, **kwargs) -> str:
        """Generate cache key from type and identifier."""
        # Create a deterministic key from parameters
        if kwargs:
            params_str = json.dumps(kwargs, sort_keys=True, default=str)
            params_hash = hashlib.md5(params_str.encode()).hexdigest()[:8]
            return f"{key_type}:{identifier}:{params_hash}"
        else:
            return f"{key_type}:{identifier}"

    def _get_ttl(self, key_type: str) -> int:
        """Get TTL for specific key type."""
        return self.ttl_by_type.get(key_type, self.default_ttl)

    async def get(
        self,
        key_type: str,
        identifier: str,
        **kwargs,
    ) -> Optional[Any]:
        """
        Get value from cache.

        Args:
            key_type: Type of cached data (e.g., 'projects', 'metrics')
            identifier: Unique identifier for the data
            **kwargs: Additional parameters for cache key generation

        Returns:
            Cached value or None if not found
        """
        cache_key = self._get_cache_key(key_type, identifier, **kwargs)
        
        try:
            value = await self.backend.get(cache_key)
            
            if value is not None:
                self._stats["hits"] += 1
                logger.debug(f"Cache hit for key: {cache_key}")
                return value
            else:
                self._stats["misses"] += 1
                logger.debug(f"Cache miss for key: {cache_key}")
                return None
                
        except Exception as e:
            logger.error(f"Cache get error for key {cache_key}: {e}")
            self._stats["misses"] += 1
            return None

    async def set(
        self,
        key_type: str,
        identifier: str,
        value: Any,
        ttl: Optional[int] = None,
        **kwargs,
    ) -> None:
        """
        Set value in cache.

        Args:
            key_type: Type of cached data
            identifier: Unique identifier for the data
            value: Value to cache
            ttl: Time to live in seconds (optional)
            **kwargs: Additional parameters for cache key generation
        """
        cache_key = self._get_cache_key(key_type, identifier, **kwargs)
        cache_ttl = ttl or self._get_ttl(key_type)
        
        try:
            await self.backend.set(cache_key, value, cache_ttl)
            self._stats["sets"] += 1
            logger.debug(f"Cache set for key: {cache_key} (TTL: {cache_ttl}s)")
            
        except Exception as e:
            logger.error(f"Cache set error for key {cache_key}: {e}")

    async def delete(
        self,
        key_type: str,
        identifier: str,
        **kwargs,
    ) -> None:
        """
        Delete value from cache.

        Args:
            key_type: Type of cached data
            identifier: Unique identifier for the data
            **kwargs: Additional parameters for cache key generation
        """
        cache_key = self._get_cache_key(key_type, identifier, **kwargs)
        
        try:
            await self.backend.delete(cache_key)
            self._stats["deletes"] += 1
            logger.debug(f"Cache delete for key: {cache_key}")
            
        except Exception as e:
            logger.error(f"Cache delete error for key {cache_key}: {e}")

    async def invalidate_pattern(self, key_type: str, pattern: str = "*") -> None:
        """
        Invalidate cache entries matching a pattern.

        Args:
            key_type: Type of cached data
            pattern: Pattern to match (basic wildcard support)
        """
        # This is a simplified implementation
        # In production, you might want more sophisticated pattern matching
        if pattern == "*":
            # Clear all entries of this type
            # This would require backend support for pattern-based deletion
            logger.info(f"Invalidating all cache entries of type: {key_type}")
        else:
            logger.info(f"Invalidating cache entries: {key_type}:{pattern}")

    async def clear_all(self) -> None:
        """Clear all cache entries."""
        try:
            await self.backend.clear()
            logger.info("All cache entries cleared")
        except Exception as e:
            logger.error(f"Cache clear error: {e}")

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        total_requests = self._stats["hits"] + self._stats["misses"]
        hit_rate = (self._stats["hits"] / total_requests * 100) if total_requests > 0 else 0
        
        stats = {
            **self._stats,
            "total_requests": total_requests,
            "hit_rate_percent": round(hit_rate, 2),
        }
        
        # Add backend-specific stats if available
        if hasattr(self.backend, "get_stats"):
            stats["backend_stats"] = self.backend.get_stats()
        
        return stats

    async def close(self) -> None:
        """Close cache backend."""
        if hasattr(self.backend, "close"):
            await self.backend.close()


def create_cache_manager(
    redis_url: Optional[str] = None,
    default_ttl: int = 300,
    ttl_by_type: Optional[Dict[str, int]] = None,
) -> CacheManager:
    """
    Create cache manager with appropriate backend.

    Args:
        redis_url: Redis URL (if None, uses memory cache)
        default_ttl: Default TTL in seconds
        ttl_by_type: TTL configuration by data type

    Returns:
        Configured cache manager
    """
    if redis_url and REDIS_AVAILABLE:
        try:
            backend = RedisCache(redis_url)
            logger.info("Using Redis cache backend")
        except Exception as e:
            logger.warning(f"Failed to initialize Redis cache, falling back to memory: {e}")
            backend = MemoryCache()
    else:
        backend = MemoryCache()
        logger.info("Using memory cache backend")

    return CacheManager(
        backend=backend,
        default_ttl=default_ttl,
        ttl_by_type=ttl_by_type,
    )