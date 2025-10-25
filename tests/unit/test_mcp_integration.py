"""Unit tests for MCP integration components."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
import asyncio

from src.streamlit_app.services.mcp_client import (MCPClient, MCPToolResult,
                                                   MCPToolCall)
from src.streamlit_app.services.mcp_integration import (MCPIntegrationService,
                                                        DataSyncConfig,SyncedData)
from src.streamlit_app.utils.error_handler import (ErrorHandler, ErrorCategory,
                                                   ErrorSeverity, ErrorInfo)


class TestMCPClient:
    """Test MCP client functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.client = MCPClient()
    
    def test_client_initialization(self):
        """Test MCP client initialization."""
        assert self.client.server_url == "stdio"
        assert self.client.connection_status == "disconnected"
        assert isinstance(self.client._tool_cache, dict)
        assert isinstance(self.client._result_cache, dict)
    
    def test_get_available_tools(self):
        """Test getting available tools."""
        tools = self.client.get_available_tools()
        
        assert isinstance(tools, list)
        assert len(tools) > 0
        
        # Check tool structure
        tool = tools[0]
        assert "name" in tool
        assert "description" in tool
        assert "parameters" in tool
    
    def test_get_connection_info(self):
        """Test getting connection information."""
        info = self.client.get_connection_info()
        
        assert "status" in info
        assert "server_url" in info
        assert "active_calls_count" in info
        assert "total_calls" in info
        assert "error_stats" in info
        
        assert info["server_url"] == "stdio"
        assert info["status"] == "disconnected"
    
    def test_get_tool_history_empty(self):
        """Test getting tool history when empty."""
        history = self.client.get_tool_history()
        assert isinstance(history, list)
        assert len(history) == 0
    
    def test_get_active_calls_empty(self):
        """Test getting active calls when empty."""
        active_calls = self.client.get_active_calls()
        assert isinstance(active_calls, dict)
        assert len(active_calls) == 0
    
    def test_get_error_stats_empty(self):
        """Test getting error stats when empty."""
        stats = self.client.get_error_stats()
        
        assert "error_count" in stats
        assert "last_error" in stats
        assert "success_rate" in stats
        
        assert stats["error_count"] == 0
        assert stats["last_error"] is None
        assert stats["success_rate"] == 0.0
    
    def test_clear_history(self):
        """Test clearing tool call history."""
        # This should not raise any exceptions
        self.client.clear_history()
        
        history = self.client.get_tool_history()
        assert len(history) == 0
        
        stats = self.client.get_error_stats()
        assert stats["error_count"] == 0


class TestMCPIntegrationService:
    """Test MCP integration service functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        with patch('src.streamlit_app.services.mcp_integration.get_mcp_client') as mock_get_client:
            mock_client = Mock()
            mock_client.connection_status = "disconnected"
            mock_get_client.return_value = mock_client
            
            self.service = MCPIntegrationService(mock_client)
            self.mock_client = mock_client
    
    def test_service_initialization(self):
        """Test integration service initialization."""
        assert isinstance(self.service.sync_config, DataSyncConfig)
        assert self.service.sync_config.sync_interval == 30
        assert self.service.sync_config.auto_refresh is True
        assert self.service.sync_config.cache_ttl == 300
    
    def test_subscribe_to_data(self):
        """Test subscribing to data synchronization."""
        self.service.subscribe_to_data(
            "test_page",
            "test_data",
            "test_tool",
            {"param1": "value1"}
        )
        
        # Check subscription was created
        assert "test_page" in self.service._sync_subscriptions
        assert "test_data" in self.service._sync_subscriptions["test_page"]
        
        # Check synced data was created
        assert "test_data" in self.service._synced_data
        synced_data = self.service._synced_data["test_data"]
        assert synced_data.key == "test_data"
        assert synced_data.source_tool == "test_tool"
        assert synced_data.parameters == {"param1": "value1"}
    
    def test_unsubscribe_from_data_specific(self):
        """Test unsubscribing from specific data."""
        # First subscribe
        self.service.subscribe_to_data("test_page", "test_data", "test_tool")
        
        # Then unsubscribe
        self.service.unsubscribe_from_data("test_page", "test_data")
        
        # Check subscription was removed
        assert "test_data" not in self.service._synced_data
        if "test_page" in self.service._sync_subscriptions:
            assert "test_data" not in self.service._sync_subscriptions["test_page"]
    
    def test_unsubscribe_from_data_all(self):
        """Test unsubscribing from all data for a page."""
        # Subscribe to multiple data sources
        self.service.subscribe_to_data("test_page", "data1", "tool1")
        self.service.subscribe_to_data("test_page", "data2", "tool2")
        
        # Unsubscribe from all
        self.service.unsubscribe_from_data("test_page")
        
        # Check all subscriptions were removed
        assert "data1" not in self.service._synced_data
        assert "data2" not in self.service._synced_data
        assert "test_page" not in self.service._sync_subscriptions
    
    def test_get_synced_data(self):
        """Test getting synced data."""
        # No data initially
        assert self.service.get_synced_data("nonexistent") is None
        
        # Subscribe to data
        self.service.subscribe_to_data("test_page", "test_data", "test_tool")
        
        # Get synced data
        synced_data = self.service.get_synced_data("test_data")
        assert synced_data is not None
        assert synced_data.key == "test_data"
    
    def test_get_data_value(self):
        """Test getting data value."""
        # No data initially
        assert self.service.get_data_value("nonexistent") is None
        assert self.service.get_data_value("nonexistent", "default") == "default"
        
        # Subscribe and set data
        self.service.subscribe_to_data("test_page", "test_data", "test_tool")
        synced_data = self.service._synced_data["test_data"]
        synced_data.data = {"test": "value"}
        
        # Get data value
        value = self.service.get_data_value("test_data")
        assert value == {"test": "value"}
    
    def test_is_data_fresh(self):
        """Test checking if data is fresh."""
        # No data initially
        assert not self.service.is_data_fresh("nonexistent")
        
        # Subscribe to data
        self.service.subscribe_to_data("test_page", "test_data", "test_tool")
        synced_data = self.service._synced_data["test_data"]
        
        # Data exists but is None - should not be fresh
        synced_data.data = None
        synced_data.last_updated = datetime.now()
        assert not self.service.is_data_fresh("test_data")
        
        # Set fresh data
        synced_data.data = {"test": "value"}
        synced_data.last_updated = datetime.now()
        assert self.service.is_data_fresh("test_data")
        
        # Set old data
        synced_data.last_updated = datetime.now() - timedelta(seconds=400)
        assert not self.service.is_data_fresh("test_data")
    
    def test_has_data_error(self):
        """Test checking if data has error."""
        # No data initially
        assert not self.service.has_data_error("nonexistent")
        
        # Subscribe to data
        self.service.subscribe_to_data("test_page", "test_data", "test_tool")
        synced_data = self.service._synced_data["test_data"]
        
        # No error initially
        assert not self.service.has_data_error("test_data")
        
        # Set error
        synced_data.error = "Test error"
        assert self.service.has_data_error("test_data")
    
    def test_get_sync_status(self):
        """Test getting sync status."""
        status = self.service.get_sync_status()
        
        assert "status" in status
        assert "last_sync" in status
        assert "subscriptions_count" in status
        assert "active_subscriptions" in status
        assert "sync_interval" in status
        assert "auto_refresh" in status
        assert "errors" in status
        
        assert status["status"] == "stopped"
        assert status["subscriptions_count"] == 0
        assert isinstance(status["active_subscriptions"], list)
    
    def test_configure_sync(self):
        """Test configuring sync settings."""
        # Change settings
        self.service.configure_sync(
            sync_interval=60,
            auto_refresh=False,
            cache_ttl=600
        )
        
        # Check settings were updated
        assert self.service.sync_config.sync_interval == 60
        assert self.service.sync_config.auto_refresh is False
        assert self.service.sync_config.cache_ttl == 600
    
    def test_convenience_methods(self):
        """Test convenience methods for common data types."""
        # Test sync_projects_data
        data_key = self.service.sync_projects_data("test_page", search="test")
        assert data_key == "projects_test_page"
        assert "projects_test_page" in self.service._synced_data
        
        # Test sync_project_details
        data_key = self.service.sync_project_details("test_page", "project1")
        assert data_key == "project_details_project1_test_page"
        
        # Test sync_project_measures
        data_key = self.service.sync_project_measures("test_page", "project1", ["bugs", "coverage"])
        assert data_key == "project_measures_project1_test_page"
        
        # Test sync_quality_gate_status
        data_key = self.service.sync_quality_gate_status("test_page", "project1")
        assert data_key == "quality_gate_project1_test_page"
        
        # Test sync_issues_data
        data_key = self.service.sync_issues_data("test_page", ["project1"], severities=["MAJOR"])
        assert data_key == "issues_test_page"
        
        # Test sync_security_hotspots
        data_key = self.service.sync_security_hotspots("test_page", "project1", statuses=["TO_REVIEW"])
        assert data_key == "security_hotspots_project1_test_page"


class TestErrorHandler:
    """Test error handler functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.handler = ErrorHandler()
    
    def test_handler_initialization(self):
        """Test error handler initialization."""
        assert isinstance(self.handler._error_history, list)
        assert isinstance(self.handler._error_callbacks, dict)
        assert isinstance(self.handler._recovery_strategies, dict)
        assert len(self.handler._error_history) == 0
    
    def test_handle_error_with_exception(self):
        """Test handling error with exception."""
        test_exception = ValueError("Test error message")
        
        error_info = self.handler.handle_error(
            test_exception,
            ErrorCategory.VALIDATION,
            ErrorSeverity.MEDIUM,
            context={"test": True},
            show_notification=False
        )
        
        assert isinstance(error_info, ErrorInfo)
        assert error_info.message == "Test error message"
        assert error_info.category == ErrorCategory.VALIDATION
        assert error_info.severity == ErrorSeverity.MEDIUM
        assert error_info.context == {"test": True}
        assert error_info.stack_trace is not None
        assert error_info.user_message is not None
        assert len(error_info.suggested_actions) > 0
    
    def test_handle_error_with_string(self):
        """Test handling error with string message."""
        error_info = self.handler.handle_error(
            "String error message",
            ErrorCategory.API,
            ErrorSeverity.HIGH,
            show_notification=False
        )
        
        assert error_info.message == "String error message"
        assert error_info.category == ErrorCategory.API
        assert error_info.severity == ErrorSeverity.HIGH
        assert error_info.stack_trace is None
    
    def test_categorize_exception(self):
        """Test automatic exception categorization."""
        # Connection error
        conn_error = ConnectionError("Connection timeout")
        category = self.handler._categorize_exception(conn_error)
        assert category == ErrorCategory.CONNECTION
        
        # Authentication error
        auth_error = Exception("Invalid token provided")
        category = self.handler._categorize_exception(auth_error)
        assert category == ErrorCategory.AUTHENTICATION
        
        # Validation error
        val_error = ValueError("Invalid input format")
        category = self.handler._categorize_exception(val_error)
        assert category == ErrorCategory.VALIDATION
    
    def test_generate_user_message(self):
        """Test generating user-friendly messages."""
        message = self.handler._generate_user_message(ErrorCategory.CONNECTION, "Raw error")
        assert "connect" in message.lower()
        
        message = self.handler._generate_user_message(ErrorCategory.AUTHENTICATION, "Raw error")
        assert "authentication" in message.lower() or "token" in message.lower()
        
        message = self.handler._generate_user_message(ErrorCategory.VALIDATION, "Raw error")
        assert "invalid" in message.lower() or "input" in message.lower()
    
    def test_generate_suggested_actions(self):
        """Test generating suggested actions."""
        actions = self.handler._generate_suggested_actions(ErrorCategory.CONNECTION)
        assert isinstance(actions, list)
        assert len(actions) > 0
        assert any("connection" in action.lower() for action in actions)
        
        actions = self.handler._generate_suggested_actions(ErrorCategory.AUTHENTICATION)
        assert any("token" in action.lower() for action in actions)
    
    def test_is_recoverable(self):
        """Test determining if error is recoverable."""
        # Recoverable errors
        assert self.handler._is_recoverable(ErrorCategory.CONNECTION, Exception())
        assert self.handler._is_recoverable(ErrorCategory.MCP_TOOL, Exception())
        assert self.handler._is_recoverable(ErrorCategory.API, Exception())
        
        # Non-recoverable errors
        assert not self.handler._is_recoverable(ErrorCategory.AUTHENTICATION, Exception())
        assert not self.handler._is_recoverable(ErrorCategory.AUTHORIZATION, Exception())
    
    def test_get_error_history(self):
        """Test getting error history."""
        # Initially empty
        history = self.handler.get_error_history()
        assert len(history) == 0
        
        # Add some errors
        self.handler.handle_error("Error 1", show_notification=False)
        self.handler.handle_error("Error 2", show_notification=False)
        
        history = self.handler.get_error_history()
        assert len(history) == 2
        
        # Test filtering by category
        self.handler.handle_error("API Error", ErrorCategory.API, show_notification=False)
        api_history = self.handler.get_error_history(category=ErrorCategory.API)
        assert len(api_history) == 1
        assert api_history[0].category == ErrorCategory.API
    
    def test_get_error_stats(self):
        """Test getting error statistics."""
        # Initially empty
        stats = self.handler.get_error_stats()
        assert stats["total_errors"] == 0
        
        # Add some errors
        self.handler.handle_error("Error 1", ErrorCategory.API, show_notification=False)
        self.handler.handle_error("Error 2", ErrorCategory.CONNECTION, show_notification=False)
        self.handler.handle_error("Error 3", ErrorCategory.API, show_notification=False)
        
        stats = self.handler.get_error_stats()
        assert stats["total_errors"] == 3
        assert stats["category_breakdown"]["api"] == 2
        assert stats["category_breakdown"]["connection"] == 1
        assert stats["last_error"] is not None
    
    def test_clear_error_history(self):
        """Test clearing error history."""
        # Add some errors
        self.handler.handle_error("Error 1", show_notification=False)
        self.handler.handle_error("Error 2", show_notification=False)
        
        assert len(self.handler.get_error_history()) == 2
        
        # Clear history
        self.handler.clear_error_history()
        
        assert len(self.handler.get_error_history()) == 0
        stats = self.handler.get_error_stats()
        assert stats["total_errors"] == 0
    
    def test_register_error_callback(self):
        """Test registering error callbacks."""
        callback_called = False
        
        def test_callback(error_info):
            nonlocal callback_called
            callback_called = True
        
        self.handler.register_error_callback(ErrorCategory.API, test_callback)
        
        # Trigger error
        self.handler.handle_error("API Error", ErrorCategory.API, show_notification=False)
        
        assert callback_called
    
    def test_create_error_context(self):
        """Test creating error context."""
        context = self.handler.create_error_context(
            custom_field="custom_value",
            another_field=123
        )
        
        assert "timestamp" in context
        assert "page" in context
        assert "user_agent" in context
        assert context["custom_field"] == "custom_value"
        assert context["another_field"] == 123


class TestMCPToolResult:
    """Test MCP tool result data class."""
    
    def test_tool_result_creation(self):
        """Test creating tool result."""
        result = MCPToolResult(
            success=True,
            data={"test": "data"},
            execution_time=1.5,
            call_id="test_call"
        )
        
        assert result.success is True
        assert result.data == {"test": "data"}
        assert result.error is None
        assert result.execution_time == 1.5
        assert result.call_id == "test_call"
        assert isinstance(result.timestamp, datetime)
    
    def test_tool_result_failure(self):
        """Test creating failed tool result."""
        result = MCPToolResult(
            success=False,
            error="Test error message",
            execution_time=0.5
        )
        
        assert result.success is False
        assert result.data is None
        assert result.error == "Test error message"
        assert result.execution_time == 0.5


class TestMCPToolCall:
    """Test MCP tool call data class."""
    
    def test_tool_call_creation(self):
        """Test creating tool call."""
        call = MCPToolCall(
            tool_name="test_tool",
            parameters={"param1": "value1"},
            call_id="test_call"
        )
        
        assert call.tool_name == "test_tool"
        assert call.parameters == {"param1": "value1"}
        assert call.call_id == "test_call"
        assert isinstance(call.timestamp, datetime)


class TestDataSyncConfig:
    """Test data sync configuration."""
    
    def test_sync_config_defaults(self):
        """Test sync config default values."""
        config = DataSyncConfig()
        
        assert config.sync_interval == 30
        assert config.auto_refresh is True
        assert config.cache_ttl == 300
        assert config.max_retries == 3
        assert config.retry_delay == 5
    
    def test_sync_config_custom(self):
        """Test sync config with custom values."""
        config = DataSyncConfig(
            sync_interval=60,
            auto_refresh=False,
            cache_ttl=600,
            max_retries=5,
            retry_delay=10
        )
        
        assert config.sync_interval == 60
        assert config.auto_refresh is False
        assert config.cache_ttl == 600
        assert config.max_retries == 5
        assert config.retry_delay == 10


class TestSyncedData:
    """Test synced data class."""
    
    def test_synced_data_creation(self):
        """Test creating synced data."""
        data = SyncedData(
            key="test_key",
            data={"test": "value"},
            source_tool="test_tool",
            parameters={"param": "value"}
        )
        
        assert data.key == "test_key"
        assert data.data == {"test": "value"}
        assert data.source_tool == "test_tool"
        assert data.parameters == {"param": "value"}
        assert data.error is None
        assert isinstance(data.last_updated, datetime)