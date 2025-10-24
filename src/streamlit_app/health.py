"""Health check endpoint for Streamlit application."""

import streamlit as st
import json
from datetime import datetime
from typing import Dict, Any


def create_health_endpoint():
    """Create a health check endpoint for Streamlit."""
    
    # This creates a simple health check page that can be accessed via /_stcore/health
    # Streamlit automatically provides this endpoint, but we can customize the response
    
    def health_check() -> Dict[str, Any]:
        """Perform health check."""
        try:
            # Basic health check
            health_data = {
                "status": "healthy",
                "timestamp": datetime.now().isoformat(),
                "service": "sonarqube-streamlit-app",
                "version": "1.0.0"
            }
            
            # Check if session state is working
            if hasattr(st, 'session_state'):
                health_data["session_state"] = "available"
            else:
                health_data["session_state"] = "unavailable"
                health_data["status"] = "degraded"
            
            # Check MCP client if available
            if hasattr(st.session_state, 'mcp_client') and st.session_state.mcp_client:
                try:
                    connection_info = st.session_state.mcp_client.get_connection_info()
                    health_data["mcp_connection"] = connection_info.get("status", "unknown")
                    if connection_info.get("status") != "connected":
                        health_data["status"] = "degraded"
                except Exception as e:
                    health_data["mcp_connection"] = "error"
                    health_data["mcp_error"] = str(e)
                    health_data["status"] = "degraded"
            else:
                health_data["mcp_connection"] = "not_initialized"
            
            return health_data
            
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
                "service": "sonarqube-streamlit-app"
            }
    
    return health_check


def render_health_page():
    """Render a health check page for debugging."""
    st.title("🏥 Health Check")
    
    health_check = create_health_endpoint()
    health_data = health_check()
    
    # Display status
    status = health_data.get("status", "unknown")
    if status == "healthy":
        st.success("✅ Application is healthy")
    elif status == "degraded":
        st.warning("⚠️ Application is running with degraded performance")
    else:
        st.error("❌ Application is unhealthy")
    
    # Display detailed information
    st.subheader("📊 Health Details")
    st.json(health_data)
    
    # Add refresh button
    if st.button("🔄 Refresh Health Check"):
        st.rerun()


# Add this to the main app navigation if needed
def add_health_check_to_sidebar():
    """Add health check option to sidebar."""
    if st.sidebar.button("🏥 Health Check"):
        st.session_state.current_page = "health"
