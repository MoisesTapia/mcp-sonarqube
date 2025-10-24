"""Base classes for MCP resources."""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
from urllib.parse import urlparse, parse_qs

from ...utils import get_logger

logger = get_logger(__name__)


class ResourceURI:
    """Represents a parsed MCP resource URI."""
    
    def __init__(self, uri: str):
        """Initialize ResourceURI from URI string."""
        self.original_uri = uri
        self.parsed = urlparse(uri)
        
        if self.parsed.scheme != "sonarqube":
            raise ValueError(f"Invalid scheme: {self.parsed.scheme}. Expected 'sonarqube'")
        
        # Parse path components
        # The netloc is the resource type, path contains the resource_id
        self.resource_type = self.parsed.netloc
        path_parts = [part for part in self.parsed.path.split("/") if part]
        self.resource_id = path_parts[0] if path_parts else None
        self.sub_resource = path_parts[1] if len(path_parts) > 1 else None
        
        # Parse query parameters
        self.query_params = {}
        if self.parsed.query:
            for key, values in parse_qs(self.parsed.query).items():
                self.query_params[key] = values[0] if len(values) == 1 else values
    
    def __str__(self) -> str:
        return self.original_uri
    
    def __repr__(self) -> str:
        return f"ResourceURI('{self.original_uri}')"


class BaseResource(ABC):
    """Base class for MCP resources."""
    
    def __init__(self, sonarqube_client, cache_manager=None):
        """Initialize base resource."""
        self.client = sonarqube_client
        self.cache = cache_manager
        self.logger = logger
    
    @abstractmethod
    async def get_resource(self, uri: ResourceURI) -> Dict[str, Any]:
        """Get resource data for the given URI."""
        pass
    
    @abstractmethod
    def supports_uri(self, uri: ResourceURI) -> bool:
        """Check if this resource handler supports the given URI."""
        pass
    
    def _build_cache_key(self, uri: ResourceURI, **kwargs) -> str:
        """Build cache key for the resource."""
        key_parts = [
            "resource",
            uri.resource_type or "unknown",
            uri.resource_id or "all",
            uri.sub_resource or "main"
        ]
        
        # Add query parameters to cache key
        if uri.query_params:
            sorted_params = sorted(uri.query_params.items())
            param_str = "&".join(f"{k}={v}" for k, v in sorted_params)
            key_parts.append(param_str)
        
        # Add additional kwargs
        if kwargs:
            sorted_kwargs = sorted(kwargs.items())
            kwargs_str = "&".join(f"{k}={v}" for k, v in sorted_kwargs)
            key_parts.append(kwargs_str)
        
        return ":".join(key_parts)
    
    async def _get_cached_or_fetch(
        self, 
        uri: ResourceURI, 
        fetch_func, 
        ttl: int = 300,
        **kwargs
    ) -> Dict[str, Any]:
        """Get data from cache or fetch if not cached."""
        if not self.cache:
            return await fetch_func()
        
        cache_key = self._build_cache_key(uri, **kwargs)
        
        # Try to get from cache
        cached_data = await self.cache.get("resources", cache_key)
        if cached_data:
            self.logger.debug(f"Cache hit for resource: {uri}")
            return cached_data
        
        # Fetch fresh data
        self.logger.debug(f"Cache miss for resource: {uri}")
        data = await fetch_func()
        
        # Cache the result
        await self.cache.set("resources", cache_key, data, ttl=ttl)
        
        return data
