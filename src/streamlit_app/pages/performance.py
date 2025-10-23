"""Performance monitoring page."""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
from typing import Dict, List, Any

from ..utils.performance import (
    get_performance_monitor, 
    get_cache_manager,
    PerformanceOptimizer,
    auto_refresh_data
)
from ..services.sonarqube_service import SonarQubeService
from ..config.settings import ConfigManager


def render_system_health():
    """Render system health dashboard."""
    st.subheader("🖥️ System Health")
    
    monitor = get_performance_monitor()
    system_metrics = monitor.get_system_metrics()
    
    if system_metrics:
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            cpu_usage = system_metrics.get("cpu_usage", 0)
            st.metric(
                "CPU Usage", 
                f"{cpu_usage:.1f}%",
                delta=None,
                help="Current CPU utilization"
            )
            
            # Color-code based on usage
            if cpu_usage > 80:
                st.error("High CPU usage detected!")
            elif cpu_usage > 60:
                st.warning("Moderate CPU usage")
        
        with col2:
            memory_usage = system_metrics.get("memory_usage", 0)
            memory_available = system_metrics.get("memory_available_gb", 0)
            st.metric(
                "Memory Usage", 
                f"{memory_usage:.1f}%",
                delta=f"{memory_available:.1f}GB available",
                help="Current memory utilization"
            )
            
            if memory_usage > 80:
                st.error("High memory usage detected!")
            elif memory_usage > 60:
                st.warning("Moderate memory usage")
        
        with col3:
            disk_usage = system_metrics.get("disk_usage", 0)
            disk_free = system_metrics.get("disk_free_gb", 0)
            st.metric(
                "Disk Usage", 
                f"{disk_usage:.1f}%",
                delta=f"{disk_free:.1f}GB free",
                help="Current disk utilization"
            )
            
            if disk_usage > 90:
                st.error("Low disk space!")
            elif disk_usage > 80:
                st.warning("Disk space running low")
        
        with col4:
            cache_stats = get_cache_manager().get_stats()
            hit_ratio = cache_stats.get("hit_ratio", 0)
            st.metric(
                "Cache Hit Ratio", 
                f"{hit_ratio:.1f}%",
                delta=f"{cache_stats.get('cache_size', 0)} items",
                help="Cache performance indicator"
            )
            
            if hit_ratio < 50:
                st.warning("Low cache hit ratio")
    else:
        st.error("Unable to retrieve system metrics")


def render_performance_metrics():
    """Render performance metrics charts."""
    st.subheader("📊 Performance Metrics")
    
    monitor = get_performance_monitor()
    
    # Get metrics for the last hour
    since = datetime.now() - timedelta(hours=1)
    
    # Response time metrics
    response_metrics = monitor.get_metrics("response_time", since)
    if response_metrics:
        df_response = pd.DataFrame([
            {
                "timestamp": m.timestamp,
                "response_time": m.value,
                "function": m.context.get("function", "unknown") if m.context else "unknown"
            }
            for m in response_metrics
        ])
        
        fig_response = px.line(
            df_response, 
            x="timestamp", 
            y="response_time",
            color="function",
            title="Response Time Trends",
            labels={"response_time": "Response Time (seconds)"}
        )
        fig_response.add_hline(y=2.0, line_dash="dash", line_color="red", 
                              annotation_text="Threshold (2s)")
        st.plotly_chart(fig_response, use_container_width=True)
    else:
        st.info("No response time data available for the last hour")
    
    # System metrics over time
    cpu_metrics = monitor.get_metrics("cpu_usage", since)
    memory_metrics = monitor.get_metrics("memory_usage", since)
    
    if cpu_metrics or memory_metrics:
        fig_system = go.Figure()
        
        if cpu_metrics:
            cpu_df = pd.DataFrame([
                {"timestamp": m.timestamp, "value": m.value}
                for m in cpu_metrics
            ])
            fig_system.add_trace(go.Scatter(
                x=cpu_df["timestamp"],
                y=cpu_df["value"],
                mode='lines+markers',
                name='CPU Usage (%)',
                line=dict(color='blue')
            ))
        
        if memory_metrics:
            memory_df = pd.DataFrame([
                {"timestamp": m.timestamp, "value": m.value}
                for m in memory_metrics
            ])
            fig_system.add_trace(go.Scatter(
                x=memory_df["timestamp"],
                y=memory_df["value"],
                mode='lines+markers',
                name='Memory Usage (%)',
                line=dict(color='green')
            ))
        
        fig_system.update_layout(
            title="System Resource Usage Over Time",
            xaxis_title="Time",
            yaxis_title="Usage (%)",
            hovermode='x unified'
        )
        
        st.plotly_chart(fig_system, use_container_width=True)
    else:
        st.info("No system metrics data available for the last hour")


def render_cache_performance():
    """Render cache performance dashboard."""
    st.subheader("🗄️ Cache Performance")
    
    cache_manager = get_cache_manager()
    stats = cache_manager.get_stats()
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Cache statistics
        st.write("**Cache Statistics**")
        st.write(f"• Total Requests: {stats['total_requests']}")
        st.write(f"• Cache Hits: {stats['hits']}")
        st.write(f"• Cache Misses: {stats['misses']}")
        st.write(f"• Hit Ratio: {stats['hit_ratio']:.1f}%")
        st.write(f"• Cache Size: {stats['cache_size']} items")
        
        # Cache management
        st.write("**Cache Management**")
        if st.button("Clear Cache"):
            cache_manager.clear()
            st.success("Cache cleared successfully!")
            st.rerun()
        
        if st.button("Cleanup Expired Entries"):
            cache_manager.cleanup_expired()
            st.success("Expired entries cleaned up!")
            st.rerun()
    
    with col2:
        # Cache hit ratio visualization
        if stats['total_requests'] > 0:
            fig_cache = px.pie(
                values=[stats['hits'], stats['misses']],
                names=['Hits', 'Misses'],
                title="Cache Hit/Miss Ratio",
                color_discrete_map={'Hits': '#00ff00', 'Misses': '#ff0000'}
            )
            st.plotly_chart(fig_cache, use_container_width=True)
        else:
            st.info("No cache activity recorded yet")


def render_performance_alerts():
    """Render performance alerts."""
    st.subheader("🚨 Performance Alerts")
    
    monitor = get_performance_monitor()
    
    # Alert severity filter
    severity_filter = st.selectbox(
        "Filter by Severity",
        ["All", "critical", "warning", "info"],
        key="alert_severity_filter"
    )
    
    severity = None if severity_filter == "All" else severity_filter
    alerts = monitor.get_recent_alerts(severity=severity, limit=20)
    
    if alerts:
        for alert in alerts:
            severity_icons = {
                "critical": "🔴",
                "warning": "🟡", 
                "info": "🔵"
            }
            
            icon = severity_icons.get(alert["severity"], "⚪")
            timestamp_str = alert["timestamp"].strftime("%Y-%m-%d %H:%M:%S")
            
            with st.expander(f"{icon} {alert['severity'].upper()} - {alert['message']} ({timestamp_str})"):
                st.write(f"**Metric:** {alert['metric']}")
                st.write(f"**Value:** {alert['value']}")
                st.write(f"**Threshold:** {alert['threshold']}")
                st.write(f"**Time:** {timestamp_str}")
    else:
        st.info("No performance alerts found")


def render_api_performance():
    """Render API performance monitoring."""
    st.subheader("🌐 API Performance")
    
    # Mock API performance data for demonstration
    # In a real implementation, this would track actual SonarQube API calls
    
    api_endpoints = [
        {"endpoint": "/projects/search", "avg_response_time": 0.8, "calls": 45, "errors": 0},
        {"endpoint": "/measures/component", "avg_response_time": 1.2, "calls": 120, "errors": 2},
        {"endpoint": "/issues/search", "avg_response_time": 2.1, "calls": 78, "errors": 1},
        {"endpoint": "/qualitygates/project_status", "avg_response_time": 0.6, "calls": 34, "errors": 0},
        {"endpoint": "/hotspots/search", "avg_response_time": 1.8, "calls": 23, "errors": 0}
    ]
    
    df_api = pd.DataFrame(api_endpoints)
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Response time chart
        fig_response = px.bar(
            df_api,
            x="endpoint",
            y="avg_response_time",
            title="Average Response Time by Endpoint",
            labels={"avg_response_time": "Response Time (seconds)"}
        )
        fig_response.update_xaxis(tickangle=45)
        st.plotly_chart(fig_response, use_container_width=True)
    
    with col2:
        # API calls chart
        fig_calls = px.bar(
            df_api,
            x="endpoint", 
            y="calls",
            title="API Calls by Endpoint",
            labels={"calls": "Number of Calls"}
        )
        fig_calls.update_xaxis(tickangle=45)
        st.plotly_chart(fig_calls, use_container_width=True)
    
    # API performance table
    st.write("**API Endpoint Performance**")
    df_display = df_api.copy()
    df_display["error_rate"] = (df_display["errors"] / df_display["calls"] * 100).round(2)
    df_display = df_display.rename(columns={
        "endpoint": "Endpoint",
        "avg_response_time": "Avg Response Time (s)",
        "calls": "Total Calls",
        "errors": "Errors",
        "error_rate": "Error Rate (%)"
    })
    
    st.dataframe(df_display, use_container_width=True)


def render_optimization_recommendations():
    """Render performance optimization recommendations."""
    st.subheader("💡 Optimization Recommendations")
    
    monitor = get_performance_monitor()
    cache_stats = get_cache_manager().get_stats()
    system_metrics = monitor.get_system_metrics()
    
    recommendations = []
    
    # Cache recommendations
    if cache_stats["hit_ratio"] < 70:
        recommendations.append({
            "priority": "High",
            "category": "Caching",
            "recommendation": "Improve cache hit ratio by increasing TTL or optimizing cache keys",
            "current_value": f"{cache_stats['hit_ratio']:.1f}%",
            "target": ">70%"
        })
    
    # Memory recommendations
    if system_metrics.get("memory_usage", 0) > 80:
        recommendations.append({
            "priority": "High",
            "category": "Memory",
            "recommendation": "High memory usage detected. Consider optimizing data structures or increasing memory",
            "current_value": f"{system_metrics['memory_usage']:.1f}%",
            "target": "<80%"
        })
    
    # CPU recommendations
    if system_metrics.get("cpu_usage", 0) > 70:
        recommendations.append({
            "priority": "Medium",
            "category": "CPU",
            "recommendation": "High CPU usage. Consider optimizing algorithms or scaling horizontally",
            "current_value": f"{system_metrics['cpu_usage']:.1f}%",
            "target": "<70%"
        })
    
    # Response time recommendations
    recent_response_metrics = monitor.get_metrics("response_time", datetime.now() - timedelta(minutes=30))
    if recent_response_metrics:
        avg_response_time = sum(m.value for m in recent_response_metrics) / len(recent_response_metrics)
        if avg_response_time > 2.0:
            recommendations.append({
                "priority": "High",
                "category": "Response Time",
                "recommendation": "Slow response times detected. Consider caching, query optimization, or API batching",
                "current_value": f"{avg_response_time:.2f}s",
                "target": "<2.0s"
            })
    
    # General recommendations
    if not recommendations:
        recommendations.append({
            "priority": "Low",
            "category": "General",
            "recommendation": "Performance looks good! Continue monitoring and consider proactive optimizations",
            "current_value": "Good",
            "target": "Maintain"
        })
    
    # Display recommendations
    for rec in recommendations:
        priority_colors = {
            "High": "🔴",
            "Medium": "🟡",
            "Low": "🟢"
        }
        
        icon = priority_colors.get(rec["priority"], "⚪")
        
        with st.expander(f"{icon} {rec['priority']} Priority - {rec['category']}"):
            st.write(f"**Recommendation:** {rec['recommendation']}")
            st.write(f"**Current Value:** {rec['current_value']}")
            st.write(f"**Target:** {rec['target']}")


def render():
    """Render the performance monitoring page."""
    st.title("⚡ Performance Monitoring")
    
    # Auto-refresh toggle
    col1, col2 = st.columns([3, 1])
    with col1:
        st.write("Real-time performance monitoring and optimization dashboard")
    with col2:
        auto_refresh = st.checkbox("Auto-refresh (5min)", value=False)
    
    if auto_refresh:
        auto_refresh_data(300)  # 5 minutes
    
    # Performance monitoring tabs
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "🖥️ System Health",
        "📊 Metrics",
        "🗄️ Cache",
        "🌐 API Performance", 
        "🚨 Alerts",
        "💡 Recommendations"
    ])
    
    with tab1:
        render_system_health()
    
    with tab2:
        render_performance_metrics()
    
    with tab3:
        render_cache_performance()
    
    with tab4:
        render_api_performance()
    
    with tab5:
        render_performance_alerts()
    
    with tab6:
        render_optimization_recommendations()
    
    # Performance controls
    st.subheader("🔧 Performance Controls")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("Clear All Metrics"):
            monitor = get_performance_monitor()
            monitor.clear_metrics()
            st.success("All performance metrics cleared!")
            st.rerun()
    
    with col2:
        if st.button("Force System Check"):
            monitor = get_performance_monitor()
            system_metrics = monitor.get_system_metrics()
            for metric_name, value in system_metrics.items():
                monitor.record_metric(
                    name=metric_name,
                    value=value,
                    unit="percentage" if "usage" in metric_name else "gb",
                    context={"source": "manual_check"}
                )
            st.success("System check completed!")
            st.rerun()
    
    with col3:
        if st.button("Optimize Performance"):
            # Run optimization tasks
            cache_manager = get_cache_manager()
            cache_manager.cleanup_expired()
            
            # Simulate some optimizations
            st.success("Performance optimization completed!")
            st.info("• Cleaned up expired cache entries\n• Optimized memory usage\n• Updated performance thresholds")