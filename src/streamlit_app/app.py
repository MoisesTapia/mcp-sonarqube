"""Main Streamlit application for SonarQube MCP."""

import asyncio
import os
from typing import Dict, Any

import streamlit as st

from streamlit_app.config.settings import ConfigManager
from streamlit_app.views import configuration, dashboard, projects, issues, security, chat, performance, reports
from streamlit_app.utils.auth import AuthManager
from streamlit_app.utils.session import SessionManager
from streamlit_app.services import initialize_mcp_client, initialize_mcp_integration
from streamlit_app.utils.error_handler import get_error_handler


def main():
    """Main application entry point."""
    st.set_page_config(
        page_title="SonarQube MCP",
        page_icon="🔍",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    # Initialize session state
    SessionManager.initialize_session()
    
    # Initialize configuration manager
    config_manager = ConfigManager()
    
    # Initialize authentication manager
    auth_manager = AuthManager(config_manager)
    
    # Initialize MCP services
    mcp_client = initialize_mcp_client()
    mcp_integration = initialize_mcp_integration()
    
    # Initialize error handler
    error_handler = get_error_handler()
    
    # Store managers in session state
    st.session_state.config_manager = config_manager
    st.session_state.auth_manager = auth_manager
    st.session_state.mcp_client = mcp_client
    st.session_state.mcp_integration = mcp_integration
    st.session_state.error_handler = error_handler

    # Main navigation
    st.sidebar.title("🔍 SonarQube MCP")
    
    # Check if configuration is valid
    if not config_manager.is_configured():
        st.sidebar.warning("⚠️ Configuration required")
        page = "Configuration"
    else:
        # Show connection status
        connection_status = st.session_state.get("connection_status", "unknown")
        if connection_status == "connected":
            st.sidebar.success("✅ Connected to SonarQube")
        elif connection_status == "error":
            st.sidebar.error("❌ Connection failed")
        else:
            st.sidebar.info("🔄 Checking connection...")
    
    # Navigation menu
    pages = {
        "Configuration": "⚙️ Configuration",
        "Dashboard": "📊 Dashboard", 
        "Projects": "📁 Projects",
        "Issues": "🐛 Issues",
        "Security": "🔒 Security",
        "Reports": "📊 Reports & Analytics",
        "Performance": "⚡ Performance",
        "Chat": "💬 Chat"
    }
    
    # Disable pages if not configured
    if not config_manager.is_configured():
        disabled_pages = ["Dashboard", "Projects", "Issues", "Security", "Reports", "Chat"]
        for page_key in disabled_pages:
            pages[page_key] = f"🚫 {pages[page_key]}"
    
    page = st.sidebar.selectbox(
        "Navigate to:",
        options=list(pages.keys()),
        format_func=lambda x: pages[x],
        key="navigation"
    )
    
    # Route to appropriate page
    if page == "Configuration":
        configuration.render()
    elif page == "Dashboard" and config_manager.is_configured():
        dashboard.render()
    elif page == "Projects" and config_manager.is_configured():
        projects.render()
    elif page == "Issues" and config_manager.is_configured():
        issues.render()
    elif page == "Security" and config_manager.is_configured():
        security.render()
    elif page == "Reports" and config_manager.is_configured():
        reports.render()
    elif page == "Performance":
        performance.render()  # Performance monitoring available without SonarQube config
    elif page == "Chat" and config_manager.is_configured():
        chat.render()
    else:
        st.error("Please configure SonarQube connection first.")


if __name__ == "__main__":
    main()
