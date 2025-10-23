"""Unit tests for MCP cache manager."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from src.mcp_server.cache_manager import MCPCacheManager


class TestMCPCacheManager:
    """Test cases for MCPCacheManager."""

    @pytest.fixture
    def mock_cache_manager(self):
        """Create mock cache manager."""
        cache_manager = AsyncMock()
        cache_manager.get_stats.return_value = {
            "hits": 100,
            "misses": 50,
            "total_requests": 150,
            "hit_rate_percent": 66.67,
        }
        return cache_manager

    @pytest.fixture
    def mock_memory_backend(self):
        """Create mock memory backend with cleanup method."""
        backend = AsyncMock()
        backend.cleanup_expired = AsyncMock(return_value=5)
        return backend

    @pytest.fixture
    def mcp_cache_manager(self, mock_cache_manager):
        """Create MCPCacheManager instance with mock."""
        return MCPCacheManager(mock_cache_manager)

    @pytest.mark.asyncio
    async def test_get_cache_info_success(self, mcp_cache_manager, mock_cache_manager):
        """Test successful cache info retrieval."""
        # Setup mock cache manager
        mock_cache_manager.default_ttl = 300
        mock_cache_manager.ttl_by_type = {"projects": 300, "metrics": 300}
        mock_cache_manager.backend = MagicMock()
        mock_cache_manager.backend.__class__.__name__ = "MemoryCache"
        
        result = await mcp_cache_manager.get_cache_info()
        
        # Verify result structure
        assert "statistics" in result
        assert "configuration" in result
        assert "health" in result
        
        # Verify statistics
        stats = result["statistics"]
        assert stats["hits"] == 100
        assert stats["misses"] == 50
        assert stats["hit_rate_percent"] == 66.67
        
        # Verify configuration
        config = result["configuration"]
        assert config["default_ttl"] == 300
        assert config["backend_type"] == "MemoryCache"
        
        # Verify health
        health = result["health"]
        assert health["status"] == "healthy"

    @pytest.mark.asyncio
    async def test_get_cache_info_error(self, mcp_cache_manager, mock_cache_manager):
        """Test cache info retrieval with error."""
        mock_cache_manager.get_stats.side_effect = Exception("Cache error")
        
        result = await mcp_cache_manager.get_cache_info()
        
        # Should return error status
        assert result["health"]["status"] == "error"
        assert "Cache error" in result["health"]["error"]

    @pytest.mark.asyncio
    async def test_clear_all_caches_success(self, mcp_cache_manager, mock_cache_manager):
        """Test successful cache clearing."""
        result = await mcp_cache_manager.clear_all_caches()
        
        # Verify cache clear was called
        mock_cache_manager.clear_all.assert_called_once()
        
        # Verify result
        assert result["success"] is True
        assert "cleared successfully" in result["message"]

    @pytest.mark.asyncio
    async def test_clear_all_caches_error(self, mcp_cache_manager, mock_cache_manager):
        """Test cache clearing with error."""
        mock_cache_manager.clear_all.side_effect = Exception("Clear error")
        
        result = await mcp_cache_manager.clear_all_caches()
        
        # Verify error handling
        assert result["success"] is False
        assert "Clear error" in result["error"]

    @pytest.mark.asyncio
    async def test_clear_cache_by_type_success(self, mcp_cache_manager, mock_cache_manager):
        """Test successful cache clearing by type."""
        result = await mcp_cache_manager.clear_cache_by_type("projects")
        
        # Verify invalidate pattern was called
        mock_cache_manager.invalidate_pattern.assert_called_once_with("projects", "*")
        
        # Verify result
        assert result["success"] is True
        assert result["cache_type"] == "projects"
        assert "projects" in result["message"]

    @pytest.mark.asyncio
    async def test_clear_cache_by_type_error(self, mcp_cache_manager, mock_cache_manager):
        """Test cache clearing by type with error."""
        mock_cache_manager.invalidate_pattern.side_effect = Exception("Invalidate error")
        
        result = await mcp_cache_manager.clear_cache_by_type("projects")
        
        # Verify error handling
        assert result["success"] is False
        assert "Invalidate error" in result["error"]
        assert result["cache_type"] == "projects"

    @pytest.mark.asyncio
    async def test_invalidate_project_caches(self, mcp_cache_manager, mock_cache_manager):
        """Test project-specific cache invalidation."""
        project_key = "test-project"
        
        await mcp_cache_manager.invalidate_project_caches(project_key)
        
        # Verify multiple delete calls for different cache types
        assert mock_cache_manager.delete.call_count >= 8  # At least 8 different cache patterns
        
        # Verify invalidate pattern call for project lists
        mock_cache_manager.invalidate_pattern.assert_called_with("projects", "list")

    @pytest.mark.asyncio
    async def test_invalidate_project_caches_error(self, mcp_cache_manager, mock_cache_manager):
        """Test project cache invalidation with error."""
        mock_cache_manager.delete.side_effect = Exception("Delete error")
        
        # Should not raise exception, just log error
        await mcp_cache_manager.invalidate_project_caches("test-project")
        
        # Verify delete was attempted
        mock_cache_manager.delete.assert_called()

    @pytest.mark.asyncio
    async def test_optimize_cache_performance_success(self, mcp_cache_manager, mock_cache_manager):
        """Test successful cache optimization."""
        # Setup mock backend with cleanup method
        mock_backend = AsyncMock()
        mock_backend.cleanup_expired = AsyncMock(return_value=10)
        mock_cache_manager.backend = mock_backend
        
        # Setup stats
        stats_before = {"hits": 100, "misses": 50}
        stats_after = {"hits": 100, "misses": 45}
        mock_cache_manager.get_stats.side_effect = [stats_before, stats_after]
        
        result = await mcp_cache_manager.optimize_cache_performance()
        
        # Verify result
        assert result["success"] is True
        assert "results" in result
        
        results = result["results"]
        assert "operations_performed" in results
        assert "statistics_before" in results
        assert "statistics_after" in results
        
        # Verify cleanup was performed
        assert "Cleaned up 10 expired entries" in results["operations_performed"]
        assert results["statistics_before"] == stats_before
        assert results["statistics_after"] == stats_after

    @pytest.mark.asyncio
    async def test_optimize_cache_performance_no_cleanup(self, mcp_cache_manager, mock_cache_manager):
        """Test cache optimization when backend doesn't support cleanup."""
        # Backend without cleanup_expired method
        mock_cache_manager.backend = MagicMock()
        
        result = await mcp_cache_manager.optimize_cache_performance()
        
        # Should still succeed but with no cleanup operations
        assert result["success"] is True
        assert len(result["results"]["operations_performed"]) == 0

    @pytest.mark.asyncio
    async def test_optimize_cache_performance_error(self, mcp_cache_manager, mock_cache_manager):
        """Test cache optimization with error."""
        mock_cache_manager.get_stats.side_effect = Exception("Stats error")
        
        result = await mcp_cache_manager.optimize_cache_performance()
        
        # Verify error handling
        assert result["success"] is False
        assert "Stats error" in result["error"]

    @pytest.mark.asyncio
    async def test_warm_up_project_cache(self, mcp_cache_manager, mock_cache_manager):
        """Test project cache warm-up."""
        # This is currently just a placeholder that logs
        await mcp_cache_manager.warm_up_project_cache("test-project")
        
        # Should not raise any exceptions
        # In a full implementation, this would pre-populate cache

    @pytest.mark.asyncio
    async def test_background_tasks_lifecycle(self, mcp_cache_manager, mock_cache_manager):
        """Test background task lifecycle management."""
        # Setup mock backend with cleanup method
        mock_backend = AsyncMock()
        mock_backend.cleanup_expired = AsyncMock(return_value=0)
        mock_cache_manager.backend = mock_backend
        
        # Start background tasks
        await mcp_cache_manager.start_background_tasks()
        
        # Verify tasks are created
        assert mcp_cache_manager._cleanup_task is not None
        assert mcp_cache_manager._stats_task is not None
        
        # Stop background tasks
        await mcp_cache_manager.stop_background_tasks()
        
        # Verify tasks are cancelled
        assert mcp_cache_manager._cleanup_task.cancelled()
        assert mcp_cache_manager._stats_task.cancelled()

    @pytest.mark.asyncio
    async def test_background_tasks_no_cleanup_method(self, mcp_cache_manager, mock_cache_manager):
        """Test background tasks when backend doesn't support cleanup."""
        # Backend without cleanup_expired method
        mock_cache_manager.backend = MagicMock()
        
        await mcp_cache_manager.start_background_tasks()
        
        # Should only start stats task, not cleanup task
        assert mcp_cache_manager._cleanup_task is None
        assert mcp_cache_manager._stats_task is not None
        
        await mcp_cache_manager.stop_background_tasks()

    def test_cache_manager_initialization(self, mock_cache_manager):
        """Test MCPCacheManager initialization."""
        mcp_cache = MCPCacheManager(mock_cache_manager)
        
        assert mcp_cache.cache == mock_cache_manager
        assert mcp_cache._cleanup_task is None
        assert mcp_cache._stats_task is None