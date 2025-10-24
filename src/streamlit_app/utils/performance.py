"""Performance monitoring and optimization utilities."""

import time
import psutil
import streamlit as st
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Callable
from functools import wraps
import threading
import queue
import json
from dataclasses import dataclass, asdict


@dataclass
class PerformanceMetric:
    """Performance metric data structure."""
    timestamp: datetime
    metric_name: str
    value: float
    unit: str
    context: Dict[str, Any] = None


class PerformanceMonitor:
    """Performance monitoring system."""
    
    def __init__(self):
        self.metrics: List[PerformanceMetric] = []
        self.alerts: List[Dict[str, Any]] = []
        self.thresholds = {
            "response_time": 2.0,  # seconds
            "memory_usage": 80.0,  # percentage
            "cpu_usage": 80.0,     # percentage
            "cache_hit_ratio": 70.0,  # percentage
        }
        self._lock = threading.Lock()
    
    def record_metric(self, name: str, value: float, unit: str, context: Dict[str, Any] = None):
        """Record a performance metric."""
        with self._lock:
            metric = PerformanceMetric(
                timestamp=datetime.now(),
                metric_name=name,
                value=value,
                unit=unit,
                context=context or {}
            )
            self.metrics.append(metric)
            
            # Keep only last 1000 metrics to prevent memory issues
            if len(self.metrics) > 1000:
                self.metrics = self.metrics[-1000:]
            
            # Check for alerts
            self._check_alert_thresholds(metric)
    
    def _check_alert_thresholds(self, metric: PerformanceMetric):
        """Check if metric exceeds alert thresholds."""
        threshold = self.thresholds.get(metric.metric_name)
        if threshold is None:
            return
        
        # Different logic for different metrics
        should_alert = False
        if metric.metric_name == "cache_hit_ratio":
            should_alert = metric.value < threshold
        else:
            should_alert = metric.value > threshold
        
        if should_alert:
            alert = {
                "timestamp": metric.timestamp,
                "metric": metric.metric_name,
                "value": metric.value,
                "threshold": threshold,
                "severity": self._get_alert_severity(metric.metric_name, metric.value, threshold),
                "message": self._generate_alert_message(metric, threshold)
            }
            self.alerts.append(alert)
            
            # Keep only last 50 alerts
            if len(self.alerts) > 50:
                self.alerts = self.alerts[-50:]
    
    def _get_alert_severity(self, metric_name: str, value: float, threshold: float) -> str:
        """Determine alert severity."""
        if metric_name == "cache_hit_ratio":
            if value < threshold * 0.5:
                return "critical"
            elif value < threshold * 0.7:
                return "warning"
            else:
                return "info"
        else:
            if value > threshold * 1.5:
                return "critical"
            elif value > threshold * 1.2:
                return "warning"
            else:
                return "info"
    
    def _generate_alert_message(self, metric: PerformanceMetric, threshold: float) -> str:
        """Generate alert message."""
        if metric.metric_name == "response_time":
            return f"Response time ({metric.value:.2f}s) exceeds threshold ({threshold}s)"
        elif metric.metric_name == "memory_usage":
            return f"Memory usage ({metric.value:.1f}%) exceeds threshold ({threshold}%)"
        elif metric.metric_name == "cpu_usage":
            return f"CPU usage ({metric.value:.1f}%) exceeds threshold ({threshold}%)"
        elif metric.metric_name == "cache_hit_ratio":
            return f"Cache hit ratio ({metric.value:.1f}%) below threshold ({threshold}%)"
        else:
            return f"{metric.metric_name} ({metric.value}) threshold exceeded"
    
    def get_metrics(self, metric_name: str = None, since: datetime = None) -> List[PerformanceMetric]:
        """Get metrics with optional filtering."""
        with self._lock:
            filtered_metrics = self.metrics.copy()
            
            if metric_name:
                filtered_metrics = [m for m in filtered_metrics if m.metric_name == metric_name]
            
            if since:
                filtered_metrics = [m for m in filtered_metrics if m.timestamp >= since]
            
            return filtered_metrics
    
    def get_recent_alerts(self, severity: str = None, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent alerts."""
        with self._lock:
            alerts = self.alerts.copy()
            
            if severity:
                alerts = [a for a in alerts if a["severity"] == severity]
            
            # Sort by timestamp descending and limit
            alerts.sort(key=lambda x: x["timestamp"], reverse=True)
            return alerts[:limit]
    
    def get_system_metrics(self) -> Dict[str, float]:
        """Get current system metrics."""
        try:
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            return {
                "cpu_usage": cpu_percent,
                "memory_usage": memory.percent,
                "memory_available_gb": memory.available / (1024**3),
                "disk_usage": disk.percent,
                "disk_free_gb": disk.free / (1024**3)
            }
        except Exception as e:
            st.error(f"Failed to get system metrics: {e}")
            return {}
    
    def clear_metrics(self):
        """Clear all stored metrics."""
        with self._lock:
            self.metrics.clear()
            self.alerts.clear()


# Global performance monitor instance
_performance_monitor = PerformanceMonitor()


def get_performance_monitor() -> PerformanceMonitor:
    """Get the global performance monitor instance."""
    return _performance_monitor


def performance_timer(metric_name: str = None, context: Dict[str, Any] = None):
    """Decorator to time function execution."""
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                return result
            finally:
                end_time = time.time()
                execution_time = end_time - start_time
                
                name = metric_name or f"{func.__name__}_execution_time"
                monitor = get_performance_monitor()
                monitor.record_metric(
                    name=name,
                    value=execution_time,
                    unit="seconds",
                    context=context or {"function": func.__name__}
                )
        return wrapper
    return decorator


class CacheManager:
    """Enhanced cache manager with performance tracking."""
    
    def __init__(self):
        self.cache = {}
        self.cache_stats = {
            "hits": 0,
            "misses": 0,
            "total_requests": 0
        }
        self._lock = threading.Lock()
    
    def get(self, key: str, default=None):
        """Get value from cache with hit/miss tracking."""
        with self._lock:
            self.cache_stats["total_requests"] += 1
            
            if key in self.cache:
                entry = self.cache[key]
                # Check if expired
                if entry["expires_at"] > datetime.now():
                    self.cache_stats["hits"] += 1
                    self._update_cache_hit_ratio()
                    return entry["value"]
                else:
                    # Remove expired entry
                    del self.cache[key]
            
            self.cache_stats["misses"] += 1
            self._update_cache_hit_ratio()
            return default
    
    def set(self, key: str, value: Any, ttl_minutes: int = 5):
        """Set value in cache with TTL."""
        with self._lock:
            expires_at = datetime.now() + timedelta(minutes=ttl_minutes)
            self.cache[key] = {
                "value": value,
                "expires_at": expires_at,
                "created_at": datetime.now()
            }
    
    def clear(self):
        """Clear all cache entries."""
        with self._lock:
            self.cache.clear()
            self.cache_stats = {"hits": 0, "misses": 0, "total_requests": 0}
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        with self._lock:
            total = self.cache_stats["total_requests"]
            hit_ratio = (self.cache_stats["hits"] / total * 100) if total > 0 else 0
            
            return {
                "hits": self.cache_stats["hits"],
                "misses": self.cache_stats["misses"],
                "total_requests": total,
                "hit_ratio": hit_ratio,
                "cache_size": len(self.cache)
            }
    
    def _update_cache_hit_ratio(self):
        """Update cache hit ratio metric."""
        stats = self.get_stats()
        monitor = get_performance_monitor()
        monitor.record_metric(
            name="cache_hit_ratio",
            value=stats["hit_ratio"],
            unit="percentage",
            context={"cache_size": stats["cache_size"]}
        )
    
    def cleanup_expired(self):
        """Remove expired cache entries."""
        with self._lock:
            now = datetime.now()
            expired_keys = [
                key for key, entry in self.cache.items()
                if entry["expires_at"] <= now
            ]
            for key in expired_keys:
                del self.cache[key]


# Global cache manager instance
_cache_manager = CacheManager()


def get_cache_manager() -> CacheManager:
    """Get the global cache manager instance."""
    return _cache_manager


class PerformanceOptimizer:
    """Performance optimization utilities."""
    
    @staticmethod
    def optimize_dataframe_display(df, max_rows: int = 1000):
        """Optimize DataFrame display for large datasets."""
        if len(df) > max_rows:
            st.warning(f"Dataset has {len(df)} rows. Showing first {max_rows} rows for performance.")
            return df.head(max_rows)
        return df
    
    @staticmethod
    def batch_api_calls(items: List[Any], batch_size: int = 10):
        """Batch API calls to improve performance."""
        for i in range(0, len(items), batch_size):
            yield items[i:i + batch_size]
    
    @staticmethod
    def lazy_load_data(data_loader: Callable, cache_key: str, ttl_minutes: int = 5):
        """Lazy load data with caching."""
        cache = get_cache_manager()
        cached_data = cache.get(cache_key)
        
        if cached_data is not None:
            return cached_data
        
        # Load data and cache it
        with st.spinner("Loading data..."):
            data = data_loader()
            cache.set(cache_key, data, ttl_minutes)
            return data
    
    @staticmethod
    def monitor_streamlit_performance():
        """Monitor Streamlit-specific performance metrics."""
        monitor = get_performance_monitor()
        
        # Monitor session state size
        session_size = len(str(st.session_state))
        monitor.record_metric(
            name="session_state_size",
            value=session_size,
            unit="bytes",
            context={"keys_count": len(st.session_state)}
        )
        
        # Monitor system resources
        system_metrics = monitor.get_system_metrics()
        for metric_name, value in system_metrics.items():
            monitor.record_metric(
                name=metric_name,
                value=value,
                unit="percentage" if "usage" in metric_name else "gb",
                context={"source": "system"}
            )


def auto_refresh_data(refresh_interval_seconds: int = 300):
    """Auto-refresh data at specified intervals."""
    if "last_refresh" not in st.session_state:
        st.session_state.last_refresh = datetime.now()
    
    time_since_refresh = datetime.now() - st.session_state.last_refresh
    
    if time_since_refresh.total_seconds() >= refresh_interval_seconds:
        st.session_state.last_refresh = datetime.now()
        st.rerun()
    
    # Show refresh status
    next_refresh = refresh_interval_seconds - time_since_refresh.total_seconds()
    if next_refresh > 0:
        st.sidebar.info(f"Next auto-refresh in {int(next_refresh)}s")
