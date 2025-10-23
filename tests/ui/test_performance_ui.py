"""Performance monitoring UI tests."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
import pandas as pd

from src.streamlit_app.utils.performance import (
    PerformanceMonitor, 
    CacheManager, 
    PerformanceOptimizer,
    performance_timer,
    get_performance_monitor,
    get_cache_manager
)


class TestPerformanceMonitorUI:
    """Test performance monitor UI integration."""
    
    def test_performance_monitor_initialization(self):
        """Test performance monitor initializes correctly."""
        monitor = PerformanceMonitor()
        
        assert monitor.metrics == []
        assert monitor.alerts == []
        assert "response_time" in monitor.thresholds
        assert "memory_usage" in monitor.thresholds
        assert "cpu_usage" in monitor.thresholds
        assert "cache_hit_ratio" in monitor.thresholds
    
    def test_metric_recording(self):
        """Test metric recording functionality."""
        monitor = PerformanceMonitor()
        
        # Record a metric
        monitor.record_metric("test_metric", 50.0, "percentage", {"context": "test"})
        
        assert len(monitor.metrics) == 1
        metric = monitor.metrics[0]
        assert metric.metric_name == "test_metric"
        assert metric.value == 50.0
        assert metric.unit == "percentage"
        assert metric.context["context"] == "test"
    
    def test_alert_generation(self):
        """Test alert generation when thresholds are exceeded."""
        monitor = PerformanceMonitor()
        
        # Record metric that exceeds threshold
        monitor.record_metric("cpu_usage", 85.0, "percentage")
        
        assert len(monitor.alerts) == 1
        alert = monitor.alerts[0]
        assert alert["metric"] == "cpu_usage"
        assert alert["value"] == 85.0
        assert alert["severity"] in ["critical", "warning", "info"]
    
    def test_cache_hit_ratio_alert(self):
        """Test cache hit ratio alert (inverse threshold)."""
        monitor = PerformanceMonitor()
        
        # Record low cache hit ratio
        monitor.record_metric("cache_hit_ratio", 50.0, "percentage")
        
        assert len(monitor.alerts) == 1
        alert = monitor.alerts[0]
        assert alert["metric"] == "cache_hit_ratio"
        assert alert["value"] == 50.0
    
    def test_metrics_filtering(self):
        """Test metrics filtering by name and time."""
        monitor = PerformanceMonitor()
        
        # Record different metrics
        monitor.record_metric("cpu_usage", 50.0, "percentage")
        monitor.record_metric("memory_usage", 60.0, "percentage")
        monitor.record_metric("cpu_usage", 55.0, "percentage")
        
        # Filter by metric name
        cpu_metrics = monitor.get_metrics("cpu_usage")
        assert len(cpu_metrics) == 2
        
        # Filter by time
        recent_metrics = monitor.get_metrics(since=datetime.now() - timedelta(minutes=1))
        assert len(recent_metrics) == 3
    
    def test_system_metrics_collection(self):
        """Test system metrics collection."""
        monitor = PerformanceMonitor()
        
        with patch('psutil.cpu_percent', return_value=45.5), \
             patch('psutil.virtual_memory') as mock_memory, \
             patch('psutil.disk_usage') as mock_disk:
            
            # Mock memory object
            mock_memory.return_value.percent = 67.2
            mock_memory.return_value.available = 4.8 * (1024**3)
            
            # Mock disk object
            mock_disk.return_value.percent = 78.1
            mock_disk.return_value.free = 25.3 * (1024**3)
            
            metrics = monitor.get_system_metrics()
            
            assert "cpu_usage" in metrics
            assert "memory_usage" in metrics
            assert "disk_usage" in metrics
            assert metrics["cpu_usage"] == 45.5
            assert metrics["memory_usage"] == 67.2


class TestCacheManagerUI:
    """Test cache manager UI integration."""
    
    def test_cache_operations(self):
        """Test basic cache operations."""
        cache = CacheManager()
        
        # Test set and get
        cache.set("test_key", "test_value", 5)
        value = cache.get("test_key")
        assert value == "test_value"
        
        # Test cache miss
        missing_value = cache.get("missing_key", "default")
        assert missing_value == "default"
    
    def test_cache_expiration(self):
        """Test cache expiration functionality."""
        cache = CacheManager()
        
        # Set with very short TTL
        cache.set("expire_key", "expire_value", ttl_minutes=0)
        
        # Should be expired immediately
        value = cache.get("expire_key")
        assert value is None
    
    def test_cache_statistics(self):
        """Test cache statistics tracking."""
        cache = CacheManager()
        
        # Perform cache operations
        cache.set("key1", "value1", 5)
        cache.set("key2", "value2", 5)
        
        # Generate hits and misses
        cache.get("key1")  # hit
        cache.get("key1")  # hit
        cache.get("missing")  # miss
        
        stats = cache.get_stats()
        assert stats["hits"] == 2
        assert stats["misses"] == 1
        assert stats["total_requests"] == 3
        assert stats["hit_ratio"] == 200/3  # 66.67%
        assert stats["cache_size"] == 2
    
    def test_cache_cleanup(self):
        """Test cache cleanup functionality."""
        cache = CacheManager()
        
        # Add entries with different expiration times
        cache.set("keep", "value", 10)  # Long TTL
        cache.set("expire", "value", 0)  # Immediate expiration
        
        # Cleanup expired entries
        cache.cleanup_expired()
        
        # Check that only non-expired entries remain
        assert cache.get("keep") == "value"
        assert cache.get("expire") is None
    
    def test_cache_clear(self):
        """Test cache clearing functionality."""
        cache = CacheManager()
        
        # Add some entries
        cache.set("key1", "value1", 5)
        cache.set("key2", "value2", 5)
        
        # Clear cache
        cache.clear()
        
        # Verify cache is empty
        stats = cache.get_stats()
        assert stats["cache_size"] == 0
        assert stats["total_requests"] == 0


class TestPerformanceDecorator:
    """Test performance timing decorator."""
    
    def test_performance_timer_decorator(self):
        """Test performance timer decorator functionality."""
        monitor = get_performance_monitor()
        initial_count = len(monitor.get_metrics("test_function_execution_time"))
        
        @performance_timer("test_function")
        def test_function():
            return "test_result"
        
        # Call the decorated function
        result = test_function()
        
        # Verify result is unchanged
        assert result == "test_result"
        
        # Verify metric was recorded
        metrics = monitor.get_metrics("test_function")
        assert len(metrics) > initial_count
        
        # Verify metric properties
        latest_metric = metrics[-1]
        assert latest_metric.metric_name == "test_function"
        assert latest_metric.unit == "seconds"
        assert latest_metric.value > 0
    
    def test_performance_timer_with_exception(self):
        """Test performance timer records metrics even when function raises exception."""
        monitor = get_performance_monitor()
        initial_count = len(monitor.get_metrics("failing_function"))
        
        @performance_timer("failing_function")
        def failing_function():
            raise ValueError("Test exception")
        
        # Call function that raises exception
        with pytest.raises(ValueError):
            failing_function()
        
        # Verify metric was still recorded
        metrics = monitor.get_metrics("failing_function")
        assert len(metrics) > initial_count


class TestPerformanceOptimizer:
    """Test performance optimizer utilities."""
    
    def test_dataframe_optimization(self):
        """Test DataFrame optimization for large datasets."""
        # Create large DataFrame
        large_df = pd.DataFrame({
            'col1': range(2000),
            'col2': ['value'] * 2000
        })
        
        # Optimize DataFrame
        optimized_df = PerformanceOptimizer.optimize_dataframe_display(large_df, max_rows=1000)
        
        # Should be truncated to max_rows
        assert len(optimized_df) == 1000
        assert optimized_df.equals(large_df.head(1000))
        
        # Small DataFrame should remain unchanged
        small_df = pd.DataFrame({'col1': [1, 2, 3]})
        result_df = PerformanceOptimizer.optimize_dataframe_display(small_df, max_rows=1000)
        assert result_df.equals(small_df)
    
    def test_batch_api_calls(self):
        """Test API call batching functionality."""
        items = list(range(25))  # 25 items
        batches = list(PerformanceOptimizer.batch_api_calls(items, batch_size=10))
        
        assert len(batches) == 3  # 3 batches: 10, 10, 5
        assert len(batches[0]) == 10
        assert len(batches[1]) == 10
        assert len(batches[2]) == 5
        assert batches[0] == list(range(10))
        assert batches[1] == list(range(10, 20))
        assert batches[2] == list(range(20, 25))
    
    def test_lazy_load_data(self):
        """Test lazy data loading with caching."""
        cache = get_cache_manager()
        cache.clear()  # Start with clean cache
        
        call_count = 0
        
        def data_loader():
            nonlocal call_count
            call_count += 1
            return {"data": "loaded", "call": call_count}
        
        # First call should load data
        with patch('streamlit.spinner'):
            result1 = PerformanceOptimizer.lazy_load_data(data_loader, "test_cache_key", 5)
        
        assert result1["data"] == "loaded"
        assert result1["call"] == 1
        assert call_count == 1
        
        # Second call should use cache
        with patch('streamlit.spinner'):
            result2 = PerformanceOptimizer.lazy_load_data(data_loader, "test_cache_key", 5)
        
        assert result2["data"] == "loaded"
        assert result2["call"] == 1  # Same call number from cache
        assert call_count == 1  # Data loader not called again
    
    def test_streamlit_performance_monitoring(self):
        """Test Streamlit-specific performance monitoring."""
        monitor = get_performance_monitor()
        initial_metrics_count = len(monitor.metrics)
        
        with patch('streamlit.session_state', {"key1": "value1", "key2": "value2"}), \
             patch('psutil.cpu_percent', return_value=45.0), \
             patch('psutil.virtual_memory') as mock_memory, \
             patch('psutil.disk_usage') as mock_disk:
            
            mock_memory.return_value.percent = 60.0
            mock_memory.return_value.available = 4.0 * (1024**3)
            mock_disk.return_value.percent = 70.0
            mock_disk.return_value.free = 30.0 * (1024**3)
            
            PerformanceOptimizer.monitor_streamlit_performance()
            
            # Should have recorded session state size and system metrics
            new_metrics = monitor.metrics[initial_metrics_count:]
            metric_names = [m.metric_name for m in new_metrics]
            
            assert "session_state_size" in metric_names
            assert "cpu_usage" in metric_names
            assert "memory_usage" in metric_names


class TestPerformanceIntegration:
    """Test performance monitoring integration with UI components."""
    
    def test_global_monitor_instance(self):
        """Test global performance monitor instance."""
        monitor1 = get_performance_monitor()
        monitor2 = get_performance_monitor()
        
        # Should be the same instance
        assert monitor1 is monitor2
        
        # Test that metrics persist across calls
        monitor1.record_metric("test", 100.0, "units")
        metrics = monitor2.get_metrics("test")
        assert len(metrics) >= 1
    
    def test_global_cache_instance(self):
        """Test global cache manager instance."""
        cache1 = get_cache_manager()
        cache2 = get_cache_manager()
        
        # Should be the same instance
        assert cache1 is cache2
        
        # Test that cache persists across calls
        cache1.set("test_key", "test_value", 5)
        value = cache2.get("test_key")
        assert value == "test_value"
    
    def test_performance_monitoring_with_ui_operations(self):
        """Test performance monitoring during UI operations."""
        monitor = get_performance_monitor()
        cache = get_cache_manager()
        
        # Simulate UI operations
        @performance_timer("ui_operation")
        def simulate_ui_operation():
            # Simulate some work
            import time
            time.sleep(0.01)  # 10ms
            return "ui_result"
        
        # Perform operation
        result = simulate_ui_operation()
        assert result == "ui_result"
        
        # Check that performance was recorded
        metrics = monitor.get_metrics("ui_operation")
        assert len(metrics) >= 1
        
        latest_metric = metrics[-1]
        assert latest_metric.value >= 0.01  # At least 10ms
        assert latest_metric.unit == "seconds"
    
    def test_error_handling_in_performance_monitoring(self):
        """Test error handling in performance monitoring."""
        monitor = PerformanceMonitor()
        
        # Test with invalid psutil calls
        with patch('psutil.cpu_percent', side_effect=Exception("Test error")):
            metrics = monitor.get_system_metrics()
            assert metrics == {}  # Should return empty dict on error
        
        # Test cache manager with invalid operations
        cache = CacheManager()
        
        # Should handle errors gracefully
        try:
            cache.set(None, "value", 5)  # Invalid key
            cache.get(None)  # Invalid key
        except Exception:
            pytest.fail("Cache manager should handle invalid operations gracefully")


if __name__ == "__main__":
    pytest.main([__file__])