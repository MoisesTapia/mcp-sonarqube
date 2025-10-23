"""Tests for Streamlit session management."""

import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta

from src.streamlit_app.utils.session import SessionManager


class TestSessionManager:
    """Test session manager functionality."""
    
    def setup_method(self):
        """Set up test environment."""
        # Mock streamlit session state
        self.mock_session_state = MagicMock()
        # Make it behave like a dict for contains checks
        self.mock_session_state.__contains__ = lambda key: hasattr(self.mock_session_state, key)
        self.mock_session_state.get = lambda key, default=None: getattr(self.mock_session_state, key, default)
        
    def test_initialize_session(self):
        """Test session initialization."""
        with patch("streamlit.session_state", self.mock_session_state):
            SessionManager.initialize_session()
            
            # Check that all default values are set
            assert "connection_status" in self.mock_session_state
            assert "last_connection_check" in self.mock_session_state
            assert "user_info" in self.mock_session_state
            assert "user_permissions" in self.mock_session_state
            assert "system_info" in self.mock_session_state
            assert "cached_projects" in self.mock_session_state
            assert "cached_projects_timestamp" in self.mock_session_state
            assert "cached_quality_gates" in self.mock_session_state
            assert "cached_quality_gates_timestamp" in self.mock_session_state
            assert "selected_project" in self.mock_session_state
            assert "filter_settings" in self.mock_session_state
            assert "page_state" in self.mock_session_state
            
            # Check default values
            assert self.mock_session_state["connection_status"] == "unknown"
            assert self.mock_session_state["user_info"] is None
            assert self.mock_session_state["user_permissions"] == {}
            assert self.mock_session_state["filter_settings"] == {}
            assert self.mock_session_state["page_state"] == {}
    
    def test_initialize_session_preserves_existing(self):
        """Test that initialization preserves existing values."""
        self.mock_session_state["connection_status"] = "connected"
        self.mock_session_state["user_info"] = {"login": "testuser"}
        
        with patch("streamlit.session_state", self.mock_session_state):
            SessionManager.initialize_session()
            
            # Existing values should be preserved
            assert self.mock_session_state["connection_status"] == "connected"
            assert self.mock_session_state["user_info"] == {"login": "testuser"}
    
    def test_set_connection_status(self):
        """Test setting connection status."""
        with patch("streamlit.session_state", self.mock_session_state):
            system_info = {"status": "UP", "version": "9.9"}
            
            SessionManager.set_connection_status("connected", system_info)
            
            assert self.mock_session_state.connection_status == "connected"
            assert self.mock_session_state.system_info == system_info
            assert hasattr(self.mock_session_state, "last_connection_check")
            assert isinstance(self.mock_session_state.last_connection_check, datetime)
    
    def test_get_connection_status(self):
        """Test getting connection status."""
        self.mock_session_state["connection_status"] = "connected"
        
        with patch("streamlit.session_state", self.mock_session_state):
            status = SessionManager.get_connection_status()
            
            assert status == "connected"
    
    def test_get_connection_status_default(self):
        """Test getting connection status with default value."""
        with patch("streamlit.session_state", self.mock_session_state):
            status = SessionManager.get_connection_status()
            
            assert status == "unknown"
    
    def test_is_connection_recent_true(self):
        """Test connection is recent."""
        self.mock_session_state["last_connection_check"] = datetime.now() - timedelta(minutes=2)
        
        with patch("streamlit.session_state", self.mock_session_state):
            is_recent = SessionManager.is_connection_recent(max_age_minutes=5)
            
            assert is_recent is True
    
    def test_is_connection_recent_false(self):
        """Test connection is not recent."""
        self.mock_session_state["last_connection_check"] = datetime.now() - timedelta(minutes=10)
        
        with patch("streamlit.session_state", self.mock_session_state):
            is_recent = SessionManager.is_connection_recent(max_age_minutes=5)
            
            assert is_recent is False
    
    def test_is_connection_recent_no_check(self):
        """Test connection recent with no previous check."""
        with patch("streamlit.session_state", self.mock_session_state):
            is_recent = SessionManager.is_connection_recent()
            
            assert is_recent is False
    
    def test_set_user_info(self):
        """Test setting user information."""
        user_info = {"login": "testuser", "name": "Test User"}
        
        with patch("streamlit.session_state", self.mock_session_state):
            SessionManager.set_user_info(user_info)
            
            assert self.mock_session_state["user_info"] == user_info
    
    def test_get_user_info(self):
        """Test getting user information."""
        user_info = {"login": "testuser", "name": "Test User"}
        self.mock_session_state["user_info"] = user_info
        
        with patch("streamlit.session_state", self.mock_session_state):
            result = SessionManager.get_user_info()
            
            assert result == user_info
    
    def test_get_user_info_none(self):
        """Test getting user information when none exists."""
        with patch("streamlit.session_state", self.mock_session_state):
            result = SessionManager.get_user_info()
            
            assert result is None
    
    def test_set_user_permissions(self):
        """Test setting user permissions."""
        permissions = {"admin": True, "scan": False}
        
        with patch("streamlit.session_state", self.mock_session_state):
            SessionManager.set_user_permissions(permissions)
            
            assert self.mock_session_state["user_permissions"] == permissions
    
    def test_get_user_permissions(self):
        """Test getting user permissions."""
        permissions = {"admin": True, "scan": False}
        self.mock_session_state["user_permissions"] = permissions
        
        with patch("streamlit.session_state", self.mock_session_state):
            result = SessionManager.get_user_permissions()
            
            assert result == permissions
    
    def test_get_user_permissions_default(self):
        """Test getting user permissions with default value."""
        with patch("streamlit.session_state", self.mock_session_state):
            result = SessionManager.get_user_permissions()
            
            assert result == {}
    
    def test_has_permission_true(self):
        """Test has_permission returns True."""
        self.mock_session_state["user_permissions"] = {"admin": True, "scan": False}
        
        with patch("streamlit.session_state", self.mock_session_state):
            result = SessionManager.has_permission("admin")
            
            assert result is True
    
    def test_has_permission_false(self):
        """Test has_permission returns False."""
        self.mock_session_state["user_permissions"] = {"admin": True, "scan": False}
        
        with patch("streamlit.session_state", self.mock_session_state):
            result = SessionManager.has_permission("scan")
            
            assert result is False
    
    def test_has_permission_not_exists(self):
        """Test has_permission for non-existent permission."""
        self.mock_session_state["user_permissions"] = {"admin": True}
        
        with patch("streamlit.session_state", self.mock_session_state):
            result = SessionManager.has_permission("nonexistent")
            
            assert result is False
    
    def test_cache_data(self):
        """Test caching data."""
        test_data = {"key": "value"}
        
        with patch("streamlit.session_state", self.mock_session_state):
            SessionManager.cache_data("test_cache", test_data, ttl_minutes=10)
            
            assert self.mock_session_state["test_cache"] == test_data
            assert "test_cache_timestamp" in self.mock_session_state
            assert isinstance(self.mock_session_state["test_cache_timestamp"], datetime)
    
    def test_get_cached_data_valid(self):
        """Test getting valid cached data."""
        test_data = {"key": "value"}
        self.mock_session_state["test_cache"] = test_data
        self.mock_session_state["test_cache_timestamp"] = datetime.now() - timedelta(minutes=2)
        
        with patch("streamlit.session_state", self.mock_session_state):
            result = SessionManager.get_cached_data("test_cache", ttl_minutes=5)
            
            assert result == test_data
    
    def test_get_cached_data_expired(self):
        """Test getting expired cached data."""
        test_data = {"key": "value"}
        self.mock_session_state["test_cache"] = test_data
        self.mock_session_state["test_cache_timestamp"] = datetime.now() - timedelta(minutes=10)
        
        with patch("streamlit.session_state", self.mock_session_state):
            result = SessionManager.get_cached_data("test_cache", ttl_minutes=5)
            
            assert result is None
            assert self.mock_session_state["test_cache"] is None
            assert self.mock_session_state["test_cache_timestamp"] is None
    
    def test_get_cached_data_no_data(self):
        """Test getting cached data when none exists."""
        with patch("streamlit.session_state", self.mock_session_state):
            result = SessionManager.get_cached_data("test_cache")
            
            assert result is None
    
    def test_clear_cache_specific(self):
        """Test clearing specific cache."""
        self.mock_session_state["test_cache"] = {"key": "value"}
        self.mock_session_state["test_cache_timestamp"] = datetime.now()
        
        with patch("streamlit.session_state", self.mock_session_state):
            SessionManager.clear_cache("test_cache")
            
            assert self.mock_session_state["test_cache"] is None
            assert self.mock_session_state["test_cache_timestamp"] is None
    
    def test_clear_cache_all(self):
        """Test clearing all cache."""
        self.mock_session_state["cached_projects"] = [{"key": "project1"}]
        self.mock_session_state["cached_projects_timestamp"] = datetime.now()
        self.mock_session_state["cached_quality_gates"] = [{"name": "gate1"}]
        self.mock_session_state["cached_quality_gates_timestamp"] = datetime.now()
        
        with patch("streamlit.session_state", self.mock_session_state):
            SessionManager.clear_cache()
            
            assert self.mock_session_state["cached_projects"] is None
            assert self.mock_session_state["cached_projects_timestamp"] is None
            assert self.mock_session_state["cached_quality_gates"] is None
            assert self.mock_session_state["cached_quality_gates_timestamp"] is None
    
    def test_set_selected_project(self):
        """Test setting selected project."""
        with patch("streamlit.session_state", self.mock_session_state):
            SessionManager.set_selected_project("project1")
            
            assert self.mock_session_state["selected_project"] == "project1"
    
    def test_get_selected_project(self):
        """Test getting selected project."""
        self.mock_session_state["selected_project"] = "project1"
        
        with patch("streamlit.session_state", self.mock_session_state):
            result = SessionManager.get_selected_project()
            
            assert result == "project1"
    
    def test_get_selected_project_none(self):
        """Test getting selected project when none exists."""
        with patch("streamlit.session_state", self.mock_session_state):
            result = SessionManager.get_selected_project()
            
            assert result is None
    
    def test_set_filter_settings(self):
        """Test setting filter settings."""
        filters = {"status": "ERROR", "severity": "MAJOR"}
        
        with patch("streamlit.session_state", self.mock_session_state):
            SessionManager.set_filter_settings("issues", filters)
            
            assert self.mock_session_state["filter_settings"]["issues"] == filters
    
    def test_get_filter_settings(self):
        """Test getting filter settings."""
        filters = {"status": "ERROR", "severity": "MAJOR"}
        self.mock_session_state["filter_settings"] = {"issues": filters}
        
        with patch("streamlit.session_state", self.mock_session_state):
            result = SessionManager.get_filter_settings("issues")
            
            assert result == filters
    
    def test_get_filter_settings_default(self):
        """Test getting filter settings with default value."""
        with patch("streamlit.session_state", self.mock_session_state):
            result = SessionManager.get_filter_settings("issues")
            
            assert result == {}
    
    def test_set_page_state(self):
        """Test setting page state."""
        state = {"selected_tab": "details", "sort_by": "name"}
        
        with patch("streamlit.session_state", self.mock_session_state):
            SessionManager.set_page_state("projects", state)
            
            assert self.mock_session_state["page_state"]["projects"] == state
    
    def test_get_page_state(self):
        """Test getting page state."""
        state = {"selected_tab": "details", "sort_by": "name"}
        self.mock_session_state["page_state"] = {"projects": state}
        
        with patch("streamlit.session_state", self.mock_session_state):
            result = SessionManager.get_page_state("projects")
            
            assert result == state
    
    def test_get_page_state_default(self):
        """Test getting page state with default value."""
        with patch("streamlit.session_state", self.mock_session_state):
            result = SessionManager.get_page_state("projects")
            
            assert result == {}
    
    def test_clear_session(self):
        """Test clearing entire session."""
        self.mock_session_state["connection_status"] = "connected"
        self.mock_session_state["user_info"] = {"login": "testuser"}
        self.mock_session_state["custom_key"] = "custom_value"
        
        with patch("streamlit.session_state", self.mock_session_state):
            SessionManager.clear_session()
            
            # All keys should be cleared and defaults restored
            assert "custom_key" not in self.mock_session_state
            assert self.mock_session_state["connection_status"] == "unknown"
            assert self.mock_session_state["user_info"] is None