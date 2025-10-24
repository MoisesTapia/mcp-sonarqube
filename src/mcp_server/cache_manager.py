"""Advanced cache management for SonarQube MCP server."""

import asyncio
from typing import Any, Dict, List, Optional

from utils import CacheManager, get_logger

logger = get_logger(__name__)


class MCPCacheManager:
    """Advanced cache manager for MCP server with intelligent invalidation."""

    def __init__(self, cache_manager: CacheManager):
        """Initialize MCP cache manager."""
        self.cache = cache_manager
        self.logger = logger
        self._cleanup_task: Optional[asyncio.Task] = None
        self._stats_task: Optional[asyncio.Task] = None

    async def start_background_tasks(self) -> None:
        """Start background cache management tasks."""
        # Start cleanup task for memory cache
        if hasattr(self.cache.backend, "cleanup_expired"):
            self._cleanup_task = asyncio.create_task(self._periodic_cleanup())
            self.logger.info("Started cache cleanup task")

        # Start stats logging task
        self._stats_task = asyncio.create_task(self._periodic_stats_logging())
        self.logger.info("Started cache stats logging task")

    async def stop_background_tasks(self) -> None:
        """Stop background cache management tasks."""
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
            self.logger.info("Stopped cache cleanup task")

        if self._stats_task:
            self._stats_task.cancel()
            try:
                await self._stats_task
            except asyncio.CancelledError:
                pass
            self.logger.info("Stopped cache stats logging task")

    async def _periodic_cleanup(self) -> None:
        """Periodically clean up expired cache entries."""
        while True:
            try:
                await asyncio.sleep(300)  # Run every 5 minutes
                
                if hasattr(self.cache.backend, "cleanup_expired"):
                    removed_count = await self.cache.backend.cleanup_expired()
                    if removed_count > 0:
                        self.logger.debug(f"Cleaned up {removed_count} expired cache entries")
                        
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in cache cleanup: {e}")
                await asyncio.sleep(60)  # Wait before retrying

    async def _periodic_stats_logging(self) -> None:
        """Periodically log cache statistics."""
        while True:
            try:
                await asyncio.sleep(600)  # Log every 10 minutes
                
                stats = self.cache.get_stats()
                self.logger.info(
                    "Cache statistics",
                    **stats
                )
                        
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error logging cache stats: {e}")
                await asyncio.sleep(60)

    async def invalidate_project_caches(self, project_key: str) -> None:
        """
        Invalidate all caches related to a specific project.
        
        Args:
            project_key: Project key to invalidate caches for
        """
        try:
            # Invalidate project-specific caches
            cache_patterns = [
                ("projects", "details", {"project_key": project_key}),
                ("projects", "branches", {"project_key": project_key}),
                ("projects", "analyses", {"project_key": project_key}),
                ("metrics", "measures", {"project_key": project_key}),
                ("metrics", "history", {"project_key": project_key}),
                ("quality_gates", "status", {"project_key": project_key}),
                ("issues", "search", {"project_key": project_key}),
                ("security", "hotspots", {"project_key": project_key}),
            ]
            
            for cache_type, identifier, params in cache_patterns:
                await self.cache.delete(cache_type, identifier, **params)
            
            # Also invalidate project lists that might include this project
            await self.cache.invalidate_pattern("projects", "list")
            
            self.logger.info(f"Invalidated all caches for project {project_key}")
            
        except Exception as e:
            self.logger.error(f"Error invalidating project caches for {project_key}: {e}")

    async def warm_up_project_cache(self, project_key: str) -> None:
        """
        Pre-populate cache with commonly accessed project data.
        
        Args:
            project_key: Project key to warm up cache for
        """
        try:
            from .tools.projects import ProjectTools
            from .tools.measures import MeasureTools
            
            # This would need access to the client and cache manager
            # For now, just log the intent
            self.logger.info(f"Cache warm-up requested for project {project_key}")
            
        except Exception as e:
            self.logger.error(f"Error warming up cache for project {project_key}: {e}")

    async def get_cache_info(self) -> Dict[str, Any]:
        """
        Get comprehensive cache information.
        
        Returns:
            Dictionary containing cache statistics and configuration
        """
        try:
            stats = self.cache.get_stats()
            
            # Add cache configuration info
            cache_info = {
                "statistics": stats,
                "configuration": {
                    "default_ttl": self.cache.default_ttl,
                    "ttl_by_type": self.cache.ttl_by_type,
                    "backend_type": type(self.cache.backend).__name__,
                },
                "health": {
                    "status": "healthy",
                    "background_tasks_running": {
                        "cleanup": self._cleanup_task is not None and not self._cleanup_task.done(),
                        "stats_logging": self._stats_task is not None and not self._stats_task.done(),
                    }
                }
            }
            
            return cache_info
            
        except Exception as e:
            self.logger.error(f"Error getting cache info: {e}")
            return {
                "statistics": {},
                "configuration": {},
                "health": {"status": "error", "error": str(e)},
            }

    async def clear_all_caches(self) -> Dict[str, Any]:
        """
        Clear all cache entries.
        
        Returns:
            Dictionary containing operation result
        """
        try:
            await self.cache.clear_all()
            
            self.logger.info("Cleared all cache entries")
            return {
                "success": True,
                "message": "All cache entries cleared successfully",
            }
            
        except Exception as e:
            self.logger.error(f"Error clearing all caches: {e}")
            return {
                "success": False,
                "error": str(e),
            }

    async def clear_cache_by_type(self, cache_type: str) -> Dict[str, Any]:
        """
        Clear cache entries of a specific type.
        
        Args:
            cache_type: Type of cache to clear (projects, metrics, etc.)
            
        Returns:
            Dictionary containing operation result
        """
        try:
            await self.cache.invalidate_pattern(cache_type, "*")
            
            self.logger.info(f"Cleared cache entries of type: {cache_type}")
            return {
                "success": True,
                "message": f"Cache entries of type '{cache_type}' cleared successfully",
                "cache_type": cache_type,
            }
            
        except Exception as e:
            self.logger.error(f"Error clearing cache type {cache_type}: {e}")
            return {
                "success": False,
                "error": str(e),
                "cache_type": cache_type,
            }

    async def optimize_cache_performance(self) -> Dict[str, Any]:
        """
        Perform cache optimization operations.
        
        Returns:
            Dictionary containing optimization results
        """
        try:
            results = {
                "operations_performed": [],
                "statistics_before": self.cache.get_stats(),
            }
            
            # Clean up expired entries
            if hasattr(self.cache.backend, "cleanup_expired"):
                removed_count = await self.cache.backend.cleanup_expired()
                results["operations_performed"].append(
                    f"Cleaned up {removed_count} expired entries"
                )
            
            # Get updated statistics
            results["statistics_after"] = self.cache.get_stats()
            
            self.logger.info("Cache optimization completed", **results)
            return {
                "success": True,
                "results": results,
            }
            
        except Exception as e:
            self.logger.error(f"Error optimizing cache: {e}")
            return {
                "success": False,
                "error": str(e),
            }
