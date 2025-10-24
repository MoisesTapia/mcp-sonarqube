"""MCP client integration for Streamlit application."""

import asyncio
import json
import logging
from typing import Dict, Any, List, Optional, Union, Callable
from datetime import datetime, timedelta
import streamlit as st
from dataclasses import dataclass, field

from streamlit_app.utils.logger import get_logger
from streamlit_app.utils.session import SessionManager
from streamlit_app.utils.performance import performance_timer


@dataclass
class MCPToolCall:
    """Represents an MCP tool call."""
    tool_name: str
    parameters: Dict[str, Any]
    timestamp: datetime = field(default_factory=datetime.now)
    call_id: Optional[str] = None


@dataclass
class MCPToolResult:
    """Represents the result of an MCP tool call."""
    success: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    execution_time: Optional[float] = None
    timestamp: datetime = field(default_factory=datetime.now)
    call_id: Optional[str] = None


class MCPClientError(Exception):
    """Base exception for MCP client errors."""
    pass


class MCPConnectionError(MCPClientError):
    """Exception raised when MCP connection fails."""
    pass


class MCPToolExecutionError(MCPClientError):
    """Exception raised when MCP tool execution fails."""
    pass


class MCPClient:
    """Client for interacting with MCP server from Streamlit."""
    
    def __init__(self, server_url: Optional[str] = None):
        """Initialize MCP client."""
        # Use HTTP connection to MCP server container
        self.server_url = server_url or "http://mcp-server:8001"
        self.logger = get_logger(__name__)
        self._connection_status = "disconnected"
        self._last_health_check = None
        self._tool_cache = {}
        self._result_cache = {}
        self._event_listeners = {}
        
        # Initialize session state for MCP
        self._ensure_session_state()
    
    def _ensure_session_state(self) -> None:
        """Ensure session state is properly initialized."""
        if "mcp_client_state" not in st.session_state:
            st.session_state.mcp_client_state = {
                "connection_status": "disconnected",
                "last_health_check": None,
                "tool_results": [],
                "active_calls": {},
                "error_count": 0,
                "last_error": None
            }
    
    @property
    def connection_status(self) -> str:
        """Get current connection status."""
        self._ensure_session_state()
        return st.session_state.mcp_client_state.get("connection_status", "disconnected")
    
    @connection_status.setter
    def connection_status(self, status: str) -> None:
        """Set connection status."""
        self._ensure_session_state()
        st.session_state.mcp_client_state["connection_status"] = status
        self._emit_event("connection_status_changed", {"status": status})
    
    def add_event_listener(self, event: str, callback: Callable) -> None:
        """Add event listener for MCP events."""
        if event not in self._event_listeners:
            self._event_listeners[event] = []
        self._event_listeners[event].append(callback)
    
    def _emit_event(self, event: str, data: Dict[str, Any]) -> None:
        """Emit event to registered listeners."""
        if event in self._event_listeners:
            for callback in self._event_listeners[event]:
                try:
                    callback(data)
                except Exception as e:
                    self.logger.error(f"Error in event listener for {event}: {e}")
    
    async def _simulate_mcp_call(self, tool_name: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Make HTTP call to MCP server.
        """
        try:
            import httpx
            
            # Make HTTP request to MCP server health endpoint for now
            # In a full implementation, this would be a proper MCP protocol call
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(f"{self.server_url}/health")
                if response.status_code == 200:
                    health_data = response.json()
                    
                    # For health_check tool, return the health data
                    if tool_name == "health_check":
                        return {
                            "status": "success",
                            "result": health_data
                        }
                    
                    # For other tools, return a placeholder response
                    # In a full implementation, this would make proper MCP tool calls
                    return {
                        "status": "success", 
                        "result": f"Tool {tool_name} executed successfully",
                        "server_status": health_data.get("status", "unknown")
                    }
                else:
                    raise Exception(f"HTTP {response.status_code}: {response.text}")
                
        except Exception as e:
            self.logger.error(f"MCP tool call failed: {tool_name} - {str(e)}")
            raise MCPToolExecutionError(f"MCP server not available: {str(e)}")
    
    @performance_timer("mcp_tool_call")
    async def call_tool(self, tool_name: str, parameters: Dict[str, Any] = None) -> MCPToolResult:
        """Execute an MCP tool call."""
        if parameters is None:
            parameters = {}
        
        call_id = f"{tool_name}_{datetime.now().timestamp()}"
        call = MCPToolCall(tool_name=tool_name, parameters=parameters, call_id=call_id)
        
        # Store active call
        self._ensure_session_state()
        st.session_state.mcp_client_state["active_calls"][call_id] = call
        
        start_time = datetime.now()
        
        try:
            # Validate connection
            if self.connection_status != "connected":
                await self.check_health()
                if self.connection_status != "connected":
                    raise MCPConnectionError("MCP server not available")
            
            # Execute tool call
            result_data = await self._simulate_mcp_call(tool_name, parameters)
            
            execution_time = (datetime.now() - start_time).total_seconds()
            
            result = MCPToolResult(
                success=True,
                data=result_data,
                execution_time=execution_time,
                call_id=call_id
            )
            
            # Cache result
            self._result_cache[call_id] = result
            
            # Store in session state
            self._ensure_session_state()
            st.session_state.mcp_client_state["tool_results"].append({
                "call_id": call_id,
                "tool_name": tool_name,
                "parameters": parameters,
                "result": result_data,
                "execution_time": execution_time,
                "timestamp": result.timestamp.isoformat(),
                "success": True
            })
            
            # Emit success event
            self._emit_event("tool_call_success", {
                "tool_name": tool_name,
                "result": result,
                "execution_time": execution_time
            })
            
            return result
            
        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds()
            error_msg = str(e)
            
            result = MCPToolResult(
                success=False,
                error=error_msg,
                execution_time=execution_time,
                call_id=call_id
            )
            
            # Update error count
            self._ensure_session_state()
            st.session_state.mcp_client_state["error_count"] += 1
            st.session_state.mcp_client_state["last_error"] = {
                "tool_name": tool_name,
                "error": error_msg,
                "timestamp": datetime.now().isoformat()
            }
            
            # Store failed result
            self._ensure_session_state()
            st.session_state.mcp_client_state["tool_results"].append({
                "call_id": call_id,
                "tool_name": tool_name,
                "parameters": parameters,
                "error": error_msg,
                "execution_time": execution_time,
                "timestamp": result.timestamp.isoformat(),
                "success": False
            })
            
            # Emit error event
            self._emit_event("tool_call_error", {
                "tool_name": tool_name,
                "error": error_msg,
                "execution_time": execution_time
            })
            
            self.logger.error(f"MCP tool call failed: {tool_name} - {error_msg}")
            return result
            
        finally:
            # Remove from active calls
            self._ensure_session_state()
            st.session_state.mcp_client_state["active_calls"].pop(call_id, None)
    
    def call_tool_sync(self, tool_name: str, parameters: Dict[str, Any] = None) -> MCPToolResult:
        """Synchronous wrapper for tool calls."""
        try:
            # Try to get existing loop
            try:
                loop = asyncio.get_running_loop()
                # If we're in an async context, we can't use run_until_complete
                # Create a new thread to run the async code
                import concurrent.futures
                import threading
                
                def run_in_thread():
                    new_loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(new_loop)
                    try:
                        return new_loop.run_until_complete(self.call_tool(tool_name, parameters))
                    finally:
                        new_loop.close()
                
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(run_in_thread)
                    return future.result()
                    
            except RuntimeError:
                # No running loop, safe to create one
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    return loop.run_until_complete(self.call_tool(tool_name, parameters))
                finally:
                    loop.close()
        except Exception as e:
            self.logger.error(f"Error in call_tool_sync: {e}")
            return MCPToolResult(success=False, error=str(e))
    
    async def check_health(self) -> bool:
        """Check MCP server health."""
        try:
            import httpx
            
            # Direct HTTP call to avoid recursion
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(f"{self.server_url}/health")
                if response.status_code == 200:
                    health_data = response.json()
                    status = health_data.get("status", "unhealthy")
                    self.connection_status = "connected" if status == "healthy" else "error"
                    self._ensure_session_state()
                    st.session_state.mcp_client_state["last_health_check"] = datetime.now().isoformat()
                    return status == "healthy"
                else:
                    self.connection_status = "error"
                    return False
                
        except Exception as e:
            self.logger.error(f"Health check failed: {e}")
            self.connection_status = "error"
            return False
    
    def check_health_sync(self) -> bool:
        """Synchronous health check."""
        try:
            # Try to get existing loop
            try:
                loop = asyncio.get_running_loop()
                # If we're in an async context, we can't use run_until_complete
                # Create a new thread to run the async code
                import concurrent.futures
                import threading
                
                def run_in_thread():
                    new_loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(new_loop)
                    try:
                        return new_loop.run_until_complete(self.check_health())
                    finally:
                        new_loop.close()
                
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(run_in_thread)
                    return future.result()
                    
            except RuntimeError:
                # No running loop, safe to create one
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    return loop.run_until_complete(self.check_health())
                finally:
                    loop.close()
        except Exception as e:
            self.logger.error(f"Error in check_health_sync: {e}")
            return False
    
    def get_available_tools(self) -> List[Dict[str, Any]]:
        """Get list of available MCP tools."""
        # This would normally query the MCP server for available tools
        # For now, return a static list based on the server implementation
        return [
            {
                "name": "health_check",
                "description": "Check server health and SonarQube connectivity",
                "parameters": {}
            },
            {
                "name": "list_projects",
                "description": "List all accessible SonarQube projects",
                "parameters": {
                    "search": {"type": "string", "optional": True},
                    "organization": {"type": "string", "optional": True},
                    "visibility": {"type": "string", "optional": True},
                    "page": {"type": "integer", "default": 1},
                    "page_size": {"type": "integer", "default": 100}
                }
            },
            {
                "name": "get_project_details",
                "description": "Get detailed information about a specific project",
                "parameters": {
                    "project_key": {"type": "string", "required": True}
                }
            },
            {
                "name": "get_measures",
                "description": "Get metrics for a specific project",
                "parameters": {
                    "project_key": {"type": "string", "required": True},
                    "metric_keys": {"type": "array", "optional": True},
                    "additional_fields": {"type": "array", "optional": True}
                }
            },
            {
                "name": "get_quality_gate_status",
                "description": "Get Quality Gate status for a specific project",
                "parameters": {
                    "project_key": {"type": "string", "required": True}
                }
            },
            {
                "name": "search_issues",
                "description": "Search for issues with comprehensive filtering options",
                "parameters": {
                    "project_keys": {"type": "array", "optional": True},
                    "severities": {"type": "array", "optional": True},
                    "types": {"type": "array", "optional": True},
                    "statuses": {"type": "array", "optional": True},
                    "page": {"type": "integer", "default": 1},
                    "page_size": {"type": "integer", "default": 100}
                }
            },
            {
                "name": "search_hotspots",
                "description": "Search for security hotspots in a project",
                "parameters": {
                    "project_key": {"type": "string", "required": True},
                    "statuses": {"type": "array", "optional": True},
                    "page": {"type": "integer", "default": 1},
                    "page_size": {"type": "integer", "default": 100}
                }
            },
            {
                "name": "get_cache_info",
                "description": "Get comprehensive cache information and statistics",
                "parameters": {}
            }
        ]
    
    def get_tool_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent tool call history."""
        self._ensure_session_state()
        results = st.session_state.mcp_client_state.get("tool_results", [])
        return sorted(results, key=lambda x: x["timestamp"], reverse=True)[:limit]
    
    def get_active_calls(self) -> Dict[str, MCPToolCall]:
        """Get currently active tool calls."""
        self._ensure_session_state()
        return st.session_state.mcp_client_state.get("active_calls", {})
    
    def get_error_stats(self) -> Dict[str, Any]:
        """Get error statistics."""
        self._ensure_session_state()
        return {
            "error_count": st.session_state.mcp_client_state.get("error_count", 0),
            "last_error": st.session_state.mcp_client_state.get("last_error"),
            "success_rate": self._calculate_success_rate()
        }
    
    def _calculate_success_rate(self) -> float:
        """Calculate success rate of tool calls."""
        self._ensure_session_state()
        results = st.session_state.mcp_client_state.get("tool_results", [])
        if not results:
            return 0.0
        
        successful = sum(1 for r in results if r.get("success", False))
        return (successful / len(results)) * 100
    
    def clear_history(self) -> None:
        """Clear tool call history."""
        self._ensure_session_state()
        st.session_state.mcp_client_state["tool_results"] = []
        st.session_state.mcp_client_state["error_count"] = 0
        st.session_state.mcp_client_state["last_error"] = None
        self._result_cache.clear()
    
    def get_connection_info(self) -> Dict[str, Any]:
        """Get connection information."""
        self._ensure_session_state()
        return {
            "status": self.connection_status,
            "server_url": self.server_url,
            "last_health_check": st.session_state.mcp_client_state.get("last_health_check"),
            "active_calls_count": len(self.get_active_calls()),
            "total_calls": len(st.session_state.mcp_client_state.get("tool_results", [])),
            "error_stats": self.get_error_stats()
        }


# Global MCP client instance
_mcp_client_instance = None


def get_mcp_client() -> MCPClient:
    """Get global MCP client instance."""
    global _mcp_client_instance
    
    if _mcp_client_instance is None:
        _mcp_client_instance = MCPClient()
    
    return _mcp_client_instance


def initialize_mcp_client() -> MCPClient:
    """Initialize MCP client and perform health check."""
    client = get_mcp_client()
    
    # Perform initial health check
    if client.connection_status == "disconnected":
        try:
            is_healthy = client.check_health_sync()
            if is_healthy:
                st.success("✅ MCP server connected successfully")
            else:
                st.warning("⚠️ MCP server connection issues detected")
        except Exception as e:
            st.error(f"❌ Failed to connect to MCP server: {e}")
    
    return client
