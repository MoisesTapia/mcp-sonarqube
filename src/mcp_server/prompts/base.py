"""Base classes for MCP prompts."""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from ...utils import get_logger

logger = get_logger(__name__)


class BasePrompt(ABC):
    """Base class for MCP prompts."""
    
    def __init__(self, sonarqube_client, cache_manager=None):
        """Initialize base prompt."""
        self.client = sonarqube_client
        self.cache = cache_manager
        self.logger = logger
    
    @abstractmethod
    async def execute(self, arguments: Dict[str, Any]) -> str:
        """Execute the prompt with given arguments."""
        pass
    
    @abstractmethod
    def get_name(self) -> str:
        """Get the prompt name."""
        pass
    
    @abstractmethod
    def get_description(self) -> str:
        """Get the prompt description."""
        pass
    
    @abstractmethod
    def get_arguments(self) -> List[Dict[str, Any]]:
        """Get the prompt arguments schema."""
        pass
    
    def _build_cache_key(self, prompt_name: str, **kwargs) -> str:
        """Build cache key for the prompt result."""
        key_parts = ["prompt", prompt_name]
        
        # Add arguments to cache key
        if kwargs:
            sorted_kwargs = sorted(kwargs.items())
            kwargs_str = "&".join(f"{k}={v}" for k, v in sorted_kwargs)
            key_parts.append(kwargs_str)
        
        return ":".join(key_parts)
    
    async def _get_cached_or_execute(
        self, 
        prompt_name: str,
        execute_func,
        ttl: int = 300,
        **kwargs
    ) -> str:
        """Get prompt result from cache or execute if not cached."""
        if not self.cache:
            return await execute_func()
        
        cache_key = self._build_cache_key(prompt_name, **kwargs)
        
        # Try to get from cache
        cached_result = await self.cache.get("prompts", cache_key)
        if cached_result:
            self.logger.debug(f"Cache hit for prompt: {prompt_name}")
            return cached_result
        
        # Execute fresh prompt
        self.logger.debug(f"Cache miss for prompt: {prompt_name}")
        result = await execute_func()
        
        # Cache the result
        await self.cache.set("prompts", cache_key, result, ttl=ttl)
        
        return result
    
    def _format_metric_value(self, metric_key: str, value: Any) -> str:
        """Format metric value for display in prompts."""
        if value is None:
            return "N/A"
        
        # Percentage metrics
        if any(keyword in metric_key.lower() for keyword in ["coverage", "density", "rating"]):
            if isinstance(value, (int, float)):
                return f"{value:.1f}%"
        
        # Time metrics
        if "time" in metric_key.lower():
            if isinstance(value, (int, float)):
                if value < 60:
                    return f"{value:.0f}s"
                elif value < 3600:
                    return f"{value/60:.1f}m"
                else:
                    return f"{value/3600:.1f}h"
        
        # Large numbers
        if isinstance(value, (int, float)) and value >= 1000:
            if value >= 1000000:
                return f"{value/1000000:.1f}M"
            elif value >= 1000:
                return f"{value/1000:.1f}K"
        
        return str(value)
    
    def _get_current_timestamp(self) -> str:
        """Get current timestamp in ISO format."""
        from datetime import datetime
        return datetime.utcnow().isoformat() + "Z"