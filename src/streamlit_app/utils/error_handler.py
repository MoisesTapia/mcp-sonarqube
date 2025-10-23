"""Unified error handling for MCP and Streamlit UI layers."""

import traceback
from typing import Dict, Any, Optional, List, Callable, Union
from datetime import datetime
from enum import Enum
from dataclasses import dataclass, field
import streamlit as st

from ...utils.logger import get_logger
from ..utils.session import SessionManager


class ErrorSeverity(Enum):
    """Error severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ErrorCategory(Enum):
    """Error categories."""
    CONNECTION = "connection"
    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"
    VALIDATION = "validation"
    MCP_TOOL = "mcp_tool"
    API = "api"
    UI = "ui"
    SYSTEM = "system"
    UNKNOWN = "unknown"


@dataclass
class ErrorInfo:
    """Comprehensive error information."""
    error_id: str
    message: str
    category: ErrorCategory
    severity: ErrorSeverity
    timestamp: datetime = field(default_factory=datetime.now)
    context: Dict[str, Any] = field(default_factory=dict)
    stack_trace: Optional[str] = None
    user_message: Optional[str] = None
    suggested_actions: List[str] = field(default_factory=list)
    recoverable: bool = True
    retry_count: int = 0
    max_retries: int = 3


class ErrorHandler:
    """Unified error handler for MCP and UI layers."""
    
    def __init__(self):
        """Initialize error handler."""
        self.logger = get_logger(__name__)
        self._error_history: List[ErrorInfo] = []
        self._error_callbacks: Dict[ErrorCategory, List[Callable]] = {}
        self._recovery_strategies: Dict[ErrorCategory, Callable] = {}
        
        # Initialize session state
        if "error_handler_state" not in st.session_state:
            st.session_state.error_handler_state = {
                "error_history": [],
                "error_count": 0,
                "last_error": None,
                "suppressed_errors": set(),
                "error_notifications": True
            }
        
        # Register default recovery strategies
        self._register_default_recovery_strategies()
    
    def _register_default_recovery_strategies(self) -> None:
        """Register default error recovery strategies."""
        self._recovery_strategies[ErrorCategory.CONNECTION] = self._recover_connection_error
        self._recovery_strategies[ErrorCategory.MCP_TOOL] = self._recover_mcp_tool_error
        self._recovery_strategies[ErrorCategory.API] = self._recover_api_error
        self._recovery_strategies[ErrorCategory.AUTHENTICATION] = self._recover_auth_error
    
    def handle_error(self, 
                    error: Union[Exception, str],
                    category: ErrorCategory = ErrorCategory.UNKNOWN,
                    severity: ErrorSeverity = ErrorSeverity.MEDIUM,
                    context: Dict[str, Any] = None,
                    user_message: str = None,
                    suggested_actions: List[str] = None,
                    show_notification: bool = True) -> ErrorInfo:
        """Handle an error with comprehensive processing."""
        
        if context is None:
            context = {}
        if suggested_actions is None:
            suggested_actions = []
        
        # Generate error ID
        error_id = f"{category.value}_{datetime.now().timestamp()}"
        
        # Extract error message and stack trace
        if isinstance(error, Exception):
            message = str(error)
            stack_trace = traceback.format_exc()
            
            # Categorize exception if not specified
            if category == ErrorCategory.UNKNOWN:
                category = self._categorize_exception(error)
        else:
            message = str(error)
            stack_trace = None
        
        # Create error info
        error_info = ErrorInfo(
            error_id=error_id,
            message=message,
            category=category,
            severity=severity,
            context=context,
            stack_trace=stack_trace,
            user_message=user_message or self._generate_user_message(category, message),
            suggested_actions=suggested_actions or self._generate_suggested_actions(category),
            recoverable=self._is_recoverable(category, error)
        )
        
        # Log error
        self._log_error(error_info)
        
        # Store in history
        self._error_history.append(error_info)
        st.session_state.error_handler_state["error_history"].append({
            "error_id": error_id,
            "message": message,
            "category": category.value,
            "severity": severity.value,
            "timestamp": error_info.timestamp.isoformat(),
            "user_message": error_info.user_message,
            "suggested_actions": error_info.suggested_actions,
            "recoverable": error_info.recoverable
        })
        
        # Update counters
        st.session_state.error_handler_state["error_count"] += 1
        st.session_state.error_handler_state["last_error"] = {
            "error_id": error_id,
            "message": message,
            "category": category.value,
            "severity": severity.value,
            "timestamp": error_info.timestamp.isoformat()
        }
        
        # Show notification if enabled
        if (show_notification and 
            st.session_state.error_handler_state.get("error_notifications", True) and
            error_id not in st.session_state.error_handler_state.get("suppressed_errors", set())):
            self._show_error_notification(error_info)
        
        # Execute error callbacks
        self._execute_error_callbacks(error_info)
        
        # Attempt recovery if possible
        if error_info.recoverable and error_info.retry_count < error_info.max_retries:
            self._attempt_recovery(error_info)
        
        return error_info
    
    def _categorize_exception(self, error: Exception) -> ErrorCategory:
        """Categorize exception based on type and message."""
        error_type = type(error).__name__
        error_message = str(error).lower()
        
        # Connection errors
        if any(keyword in error_message for keyword in ["connection", "timeout", "network", "unreachable"]):
            return ErrorCategory.CONNECTION
        
        # Authentication errors
        if any(keyword in error_message for keyword in ["auth", "token", "credential", "unauthorized"]):
            return ErrorCategory.AUTHENTICATION
        
        # Authorization errors
        if any(keyword in error_message for keyword in ["permission", "forbidden", "access denied"]):
            return ErrorCategory.AUTHORIZATION
        
        # Validation errors
        if any(keyword in error_message for keyword in ["validation", "invalid", "malformed"]):
            return ErrorCategory.VALIDATION
        
        # MCP tool errors
        if "mcp" in error_message or "tool" in error_message:
            return ErrorCategory.MCP_TOOL
        
        # API errors
        if any(keyword in error_message for keyword in ["api", "http", "request", "response"]):
            return ErrorCategory.API
        
        return ErrorCategory.UNKNOWN
    
    def _generate_user_message(self, category: ErrorCategory, message: str) -> str:
        """Generate user-friendly error message."""
        user_messages = {
            ErrorCategory.CONNECTION: "Unable to connect to SonarQube server. Please check your connection settings.",
            ErrorCategory.AUTHENTICATION: "Authentication failed. Please verify your SonarQube token.",
            ErrorCategory.AUTHORIZATION: "You don't have permission to perform this action.",
            ErrorCategory.VALIDATION: "Invalid input provided. Please check your data and try again.",
            ErrorCategory.MCP_TOOL: "An error occurred while executing the requested operation.",
            ErrorCategory.API: "SonarQube API error occurred. Please try again later.",
            ErrorCategory.UI: "A user interface error occurred. Please refresh the page.",
            ErrorCategory.SYSTEM: "A system error occurred. Please contact support if the issue persists.",
            ErrorCategory.UNKNOWN: "An unexpected error occurred. Please try again."
        }
        
        return user_messages.get(category, f"Error: {message}")
    
    def _generate_suggested_actions(self, category: ErrorCategory) -> List[str]:
        """Generate suggested actions based on error category."""
        actions = {
            ErrorCategory.CONNECTION: [
                "Check your internet connection",
                "Verify SonarQube server URL",
                "Check if SonarQube server is running",
                "Try again in a few moments"
            ],
            ErrorCategory.AUTHENTICATION: [
                "Verify your SonarQube token",
                "Check token permissions",
                "Generate a new token if needed",
                "Contact your SonarQube administrator"
            ],
            ErrorCategory.AUTHORIZATION: [
                "Contact your SonarQube administrator",
                "Check your project permissions",
                "Verify your user role"
            ],
            ErrorCategory.VALIDATION: [
                "Check your input data",
                "Verify required fields are filled",
                "Ensure data format is correct"
            ],
            ErrorCategory.MCP_TOOL: [
                "Try the operation again",
                "Check MCP server status",
                "Verify tool parameters"
            ],
            ErrorCategory.API: [
                "Try again in a few moments",
                "Check SonarQube server status",
                "Verify API endpoint availability"
            ],
            ErrorCategory.UI: [
                "Refresh the page",
                "Clear browser cache",
                "Try a different browser"
            ],
            ErrorCategory.SYSTEM: [
                "Try again later",
                "Contact system administrator",
                "Check system logs"
            ]
        }
        
        return actions.get(category, ["Try again later", "Contact support if issue persists"])
    
    def _is_recoverable(self, category: ErrorCategory, error: Union[Exception, str]) -> bool:
        """Determine if error is recoverable."""
        recoverable_categories = {
            ErrorCategory.CONNECTION,
            ErrorCategory.MCP_TOOL,
            ErrorCategory.API,
            ErrorCategory.UI
        }
        
        return category in recoverable_categories
    
    def _log_error(self, error_info: ErrorInfo) -> None:
        """Log error information."""
        log_data = {
            "error_id": error_info.error_id,
            "category": error_info.category.value,
            "severity": error_info.severity.value,
            "message": error_info.message,
            "context": error_info.context
        }
        
        if error_info.severity == ErrorSeverity.CRITICAL:
            self.logger.critical(f"Critical error: {error_info.message}", extra=log_data)
        elif error_info.severity == ErrorSeverity.HIGH:
            self.logger.error(f"High severity error: {error_info.message}", extra=log_data)
        elif error_info.severity == ErrorSeverity.MEDIUM:
            self.logger.warning(f"Medium severity error: {error_info.message}", extra=log_data)
        else:
            self.logger.info(f"Low severity error: {error_info.message}", extra=log_data)
    
    def _show_error_notification(self, error_info: ErrorInfo) -> None:
        """Show error notification in Streamlit UI."""
        if error_info.severity == ErrorSeverity.CRITICAL:
            st.error(f"🚨 Critical Error: {error_info.user_message}")
        elif error_info.severity == ErrorSeverity.HIGH:
            st.error(f"❌ Error: {error_info.user_message}")
        elif error_info.severity == ErrorSeverity.MEDIUM:
            st.warning(f"⚠️ Warning: {error_info.user_message}")
        else:
            st.info(f"ℹ️ Notice: {error_info.user_message}")
        
        # Show suggested actions in expander
        if error_info.suggested_actions:
            with st.expander("💡 Suggested Actions"):
                for action in error_info.suggested_actions:
                    st.write(f"• {action}")
    
    def _execute_error_callbacks(self, error_info: ErrorInfo) -> None:
        """Execute registered error callbacks."""
        callbacks = self._error_callbacks.get(error_info.category, [])
        for callback in callbacks:
            try:
                callback(error_info)
            except Exception as e:
                self.logger.error(f"Error in error callback: {e}")
    
    def _attempt_recovery(self, error_info: ErrorInfo) -> bool:
        """Attempt to recover from error."""
        recovery_strategy = self._recovery_strategies.get(error_info.category)
        if recovery_strategy:
            try:
                return recovery_strategy(error_info)
            except Exception as e:
                self.logger.error(f"Error recovery failed: {e}")
                return False
        return False
    
    def _recover_connection_error(self, error_info: ErrorInfo) -> bool:
        """Recover from connection errors."""
        # Implement connection recovery logic
        # This could include retrying connection, checking network, etc.
        return False
    
    def _recover_mcp_tool_error(self, error_info: ErrorInfo) -> bool:
        """Recover from MCP tool errors."""
        # Implement MCP tool recovery logic
        # This could include retrying tool call, checking MCP server status, etc.
        return False
    
    def _recover_api_error(self, error_info: ErrorInfo) -> bool:
        """Recover from API errors."""
        # Implement API error recovery logic
        # This could include retrying API call, checking rate limits, etc.
        return False
    
    def _recover_auth_error(self, error_info: ErrorInfo) -> bool:
        """Recover from authentication errors."""
        # Implement authentication recovery logic
        # This could include token refresh, re-authentication, etc.
        return False
    
    def register_error_callback(self, category: ErrorCategory, callback: Callable[[ErrorInfo], None]) -> None:
        """Register error callback for specific category."""
        if category not in self._error_callbacks:
            self._error_callbacks[category] = []
        self._error_callbacks[category].append(callback)
    
    def register_recovery_strategy(self, category: ErrorCategory, strategy: Callable[[ErrorInfo], bool]) -> None:
        """Register recovery strategy for specific error category."""
        self._recovery_strategies[category] = strategy
    
    def get_error_history(self, limit: int = 50, category: ErrorCategory = None) -> List[ErrorInfo]:
        """Get error history with optional filtering."""
        errors = self._error_history
        
        if category:
            errors = [e for e in errors if e.category == category]
        
        return sorted(errors, key=lambda x: x.timestamp, reverse=True)[:limit]
    
    def get_error_stats(self) -> Dict[str, Any]:
        """Get error statistics."""
        total_errors = len(self._error_history)
        if total_errors == 0:
            return {"total_errors": 0}
        
        # Count by category
        category_counts = {}
        severity_counts = {}
        
        for error in self._error_history:
            category_counts[error.category.value] = category_counts.get(error.category.value, 0) + 1
            severity_counts[error.severity.value] = severity_counts.get(error.severity.value, 0) + 1
        
        # Recent errors (last hour)
        recent_errors = [
            e for e in self._error_history 
            if (datetime.now() - e.timestamp).total_seconds() < 3600
        ]
        
        return {
            "total_errors": total_errors,
            "recent_errors": len(recent_errors),
            "category_breakdown": category_counts,
            "severity_breakdown": severity_counts,
            "last_error": self._error_history[-1] if self._error_history else None
        }
    
    def clear_error_history(self) -> None:
        """Clear error history."""
        self._error_history.clear()
        st.session_state.error_handler_state["error_history"] = []
        st.session_state.error_handler_state["error_count"] = 0
        st.session_state.error_handler_state["last_error"] = None
    
    def suppress_error(self, error_id: str) -> None:
        """Suppress specific error from showing notifications."""
        st.session_state.error_handler_state["suppressed_errors"].add(error_id)
    
    def enable_error_notifications(self, enabled: bool = True) -> None:
        """Enable or disable error notifications."""
        st.session_state.error_handler_state["error_notifications"] = enabled
    
    def create_error_context(self, **kwargs) -> Dict[str, Any]:
        """Create error context with common information."""
        context = {
            "timestamp": datetime.now().isoformat(),
            "page": st.session_state.get("navigation", "unknown"),
            "user_agent": st.session_state.get("user_agent", "unknown")
        }
        context.update(kwargs)
        return context


# Global error handler instance
_error_handler_instance = None


def get_error_handler() -> ErrorHandler:
    """Get global error handler instance."""
    global _error_handler_instance
    
    if _error_handler_instance is None:
        _error_handler_instance = ErrorHandler()
    
    return _error_handler_instance


def handle_error(error: Union[Exception, str], 
                category: ErrorCategory = ErrorCategory.UNKNOWN,
                severity: ErrorSeverity = ErrorSeverity.MEDIUM,
                **kwargs) -> ErrorInfo:
    """Convenience function for handling errors."""
    return get_error_handler().handle_error(error, category, severity, **kwargs)


def handle_mcp_error(error: Union[Exception, str], **kwargs) -> ErrorInfo:
    """Convenience function for handling MCP errors."""
    return handle_error(error, ErrorCategory.MCP_TOOL, **kwargs)


def handle_api_error(error: Union[Exception, str], **kwargs) -> ErrorInfo:
    """Convenience function for handling API errors."""
    return handle_error(error, ErrorCategory.API, **kwargs)


def handle_ui_error(error: Union[Exception, str], **kwargs) -> ErrorInfo:
    """Convenience function for handling UI errors."""
    return handle_error(error, ErrorCategory.UI, **kwargs)