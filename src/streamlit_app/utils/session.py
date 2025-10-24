"""Session management utilities for Streamlit app."""

from typing import Any, Dict, Optional
import streamlit as st
from datetime import datetime, timedelta
from streamlit_app.utils.performance import get_cache_manager


class SessionManager:
    """Manages Streamlit session state and user sessions."""
    
    @staticmethod
    def initialize_session() -> None:
        """Initialize session state with default values."""
        defaults = {
            "connection_status": "unknown",
            "last_connection_check": None,
            "user_info": None,
            "user_permissions": {},
            "system_info": None,
            "cached_projects": None,
            "cached_projects_timestamp": None,
            "cached_quality_gates": None,
            "cached_quality_gates_timestamp": None,
            "selected_project": None,
            "filter_settings": {},
            "page_state": {},
        }
        
        for key, value in defaults.items():
            if key not in st.session_state:
                st.session_state[key] = value
    
    @staticmethod
    def set_connection_status(status: str, system_info: Optional[Dict[str, Any]] = None) -> None:
        """Set connection status and system info."""
        st.session_state.connection_status = status
        st.session_state.last_connection_check = datetime.now()
        if system_info:
            st.session_state.system_info = system_info
    
    @staticmethod
    def get_connection_status() -> str:
        """Get current connection status."""
        return st.session_state.get("connection_status", "unknown")
    
    @staticmethod
    def is_connection_recent(max_age_minutes: int = 5) -> bool:
        """Check if connection status is recent."""
        last_check = st.session_state.get("last_connection_check")
        if not last_check:
            return False
        
        age = datetime.now() - last_check
        return age < timedelta(minutes=max_age_minutes)
    
    @staticmethod
    def set_user_info(user_info: Dict[str, Any]) -> None:
        """Set user information."""
        st.session_state.user_info = user_info
    
    @staticmethod
    def get_user_info() -> Optional[Dict[str, Any]]:
        """Get user information."""
        return st.session_state.get("user_info")
    
    @staticmethod
    def set_user_permissions(permissions: Dict[str, bool]) -> None:
        """Set user permissions."""
        st.session_state.user_permissions = permissions
    
    @staticmethod
    def get_user_permissions() -> Dict[str, bool]:
        """Get user permissions."""
        return st.session_state.get("user_permissions", {})
    
    @staticmethod
    def has_permission(permission: str) -> bool:
        """Check if user has specific permission."""
        permissions = SessionManager.get_user_permissions()
        return permissions.get(permission, False)
    
    @staticmethod
    def cache_data(key: str, data: Any, ttl_minutes: int = 5) -> None:
        """Cache data with timestamp and performance tracking."""
        # Use both session state and performance cache manager
        st.session_state[key] = data
        st.session_state[f"{key}_timestamp"] = datetime.now()
        
        # Also use the performance cache manager for tracking
        cache_manager = get_cache_manager()
        cache_manager.set(key, data, ttl_minutes)
    
    @staticmethod
    def get_cached_data(key: str, ttl_minutes: int = 5) -> Optional[Any]:
        """Get cached data if still valid."""
        # Try performance cache manager first (has better tracking)
        cache_manager = get_cache_manager()
        cached_data = cache_manager.get(key)
        if cached_data is not None:
            return cached_data
        
        # Fallback to session state cache
        data = st.session_state.get(key)
        timestamp = st.session_state.get(f"{key}_timestamp")
        
        if data is None or timestamp is None:
            return None
        
        age = datetime.now() - timestamp
        if age > timedelta(minutes=ttl_minutes):
            # Clear expired cache
            st.session_state[key] = None
            st.session_state[f"{key}_timestamp"] = None
            return None
        
        return data
    
    @staticmethod
    def clear_cache(key: Optional[str] = None) -> None:
        """Clear cached data."""
        if key:
            st.session_state[key] = None
            st.session_state[f"{key}_timestamp"] = None
        else:
            # Clear all cached data
            cache_keys = [
                "cached_projects",
                "cached_quality_gates",
            ]
            for cache_key in cache_keys:
                st.session_state[cache_key] = None
                st.session_state[f"{cache_key}_timestamp"] = None
    
    @staticmethod
    def set_selected_project(project_key: str) -> None:
        """Set selected project."""
        st.session_state.selected_project = project_key
    
    @staticmethod
    def get_selected_project() -> Optional[str]:
        """Get selected project."""
        return st.session_state.get("selected_project")
    
    @staticmethod
    def set_filter_settings(page: str, filters: Dict[str, Any]) -> None:
        """Set filter settings for a page."""
        if "filter_settings" not in st.session_state:
            st.session_state.filter_settings = {}
        st.session_state.filter_settings[page] = filters
    
    @staticmethod
    def get_filter_settings(page: str) -> Dict[str, Any]:
        """Get filter settings for a page."""
        return st.session_state.get("filter_settings", {}).get(page, {})
    
    @staticmethod
    def set_page_state(page: str, state: Dict[str, Any]) -> None:
        """Set page-specific state."""
        if "page_state" not in st.session_state:
            st.session_state.page_state = {}
        st.session_state.page_state[page] = state
    
    @staticmethod
    def get_page_state(page: str) -> Dict[str, Any]:
        """Get page-specific state."""
        return st.session_state.get("page_state", {}).get(page, {})
    
    @staticmethod
    def clear_session() -> None:
        """Clear all session data."""
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        SessionManager.initialize_session()
