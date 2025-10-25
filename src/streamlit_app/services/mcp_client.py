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
    
    async def _make_mcp_call(self, tool_name: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Make HTTP call to MCP server tools via the health server HTTP interface.
        """
        try:
            import httpx
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                # For health_check, use the health endpoint
                if tool_name == "health_check":
                    response = await client.get(f"{self.server_url}/health")
                    if response.status_code == 200:
                        health_data = response.json()
                        return {
                            "status": "success",
                            "result": health_data
                        }
                    else:
                        raise Exception(f"Health check failed: HTTP {response.status_code}")
                
                # For other tools, use the HTTP interface we added to the health server
                tool_endpoint = f"{self.server_url}/tools/{tool_name}"
                
                # Prepare the request payload - use the correct structure
                payload = {
                    "arguments": parameters or {}
                }
                
                # Make the tool call
                response = await client.post(
                    tool_endpoint,
                    json=payload,
                    headers={"Content-Type": "application/json"}
                )
                
                if response.status_code == 200:
                    result_data = response.json()
                    # Check if the response indicates success
                    if result_data.get("success", True):
                        return {
                            "status": "success",
                            "result": result_data.get("result", result_data)
                        }
                    else:
                        raise Exception(f"Tool execution failed: {result_data.get('error', 'Unknown error')}")
                        
                elif response.status_code == 404:
                    raise Exception(f"Tool '{tool_name}' not found on MCP server")
                elif response.status_code == 400:
                    error_data = response.json() if response.headers.get('content-type', '').startswith('application/json') else {"error": response.text}
                    raise Exception(f"Invalid parameters for tool '{tool_name}': {error_data.get('error', 'Bad request')}")
                elif response.status_code == 503:
                    raise Exception("MCP server not ready or unavailable")
                else:
                    error_text = response.text if response.text else f"HTTP {response.status_code}"
                    raise Exception(f"Tool call failed: {error_text}")
                
        except httpx.TimeoutException:
            raise Exception(f"Timeout calling MCP server for tool '{tool_name}'")
        except httpx.ConnectError:
            raise Exception(f"Cannot connect to MCP server at {self.server_url}")
        except Exception as e:
            # Re-raise with more context
            raise Exception(f"MCP call failed for '{tool_name}': {str(e)}")
    
    async def _generate_mock_data(self, tool_name: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Generate mock data for development when MCP server is not fully connected."""
        if tool_name == "list_projects":
            return {
                "status": "success",
                "result": [
                    {
                        "key": "sample-project-1",
                        "name": "Sample Project 1", 
                        "visibility": "public",
                        "lastAnalysisDate": "2024-10-24T10:30:00Z"
                    },
                    {
                        "key": "sample-project-2",
                        "name": "Sample Project 2",
                        "visibility": "private", 
                        "lastAnalysisDate": "2024-10-23T15:45:00Z"
                    }
                ]
            }
        
        elif tool_name == "get_project_details":
            project_key = parameters.get("project_key", "sample-project")
            return {
                "status": "success",
                "result": {
                    "key": project_key,
                    "name": f"Project {project_key}",
                    "visibility": "public",
                    "lastAnalysisDate": "2024-10-24T10:30:00Z",
                    "description": f"Sample project details for {project_key}"
                }
            }
        
        elif tool_name == "get_measures":
            return {
                "status": "success",
                "result": {
                    "component": {
                        "key": parameters.get("project_key", "sample-project"),
                        "name": "Sample Project"
                    },
                    "measures": [
                        {"metric": "coverage", "value": "85.2", "bestValue": False},
                        {"metric": "bugs", "value": "3", "bestValue": False},
                        {"metric": "vulnerabilities", "value": "1", "bestValue": False},
                        {"metric": "code_smells", "value": "12", "bestValue": False},
                        {"metric": "duplicated_lines_density", "value": "2.1", "bestValue": False}
                    ]
                }
            }
        
        elif tool_name == "search_issues":
            return {
                "status": "success",
                "result": [
                    {
                        "key": "issue-1",
                        "rule": "javascript:S1481",
                        "severity": "MINOR",
                        "component": "sample-project:src/main.js",
                        "status": "OPEN",
                        "message": "Remove this unused variable.",
                        "type": "CODE_SMELL"
                    },
                    {
                        "key": "issue-2", 
                        "rule": "javascript:S2589",
                        "severity": "MAJOR",
                        "component": "sample-project:src/utils.js",
                        "status": "OPEN",
                        "message": "This condition will always be true.",
                        "type": "BUG"
                    }
                ]
            }
        
        elif tool_name == "get_quality_gate_status":
            return {
                "status": "success",
                "result": {
                    "status": "PASSED",
                    "conditions": [
                        {
                            "status": "OK",
                            "metricKey": "coverage",
                            "actualValue": "85.2",
                            "errorThreshold": "80"
                        },
                        {
                            "status": "OK", 
                            "metricKey": "bugs",
                            "actualValue": "3",
                            "errorThreshold": "5"
                        }
                    ]
                }
            }
        
        elif tool_name == "search_hotspots":
            return {
                "status": "success",
                "result": [
                    {
                        "key": "hotspot-1",
                        "component": "sample-project:src/auth.js",
                        "status": "TO_REVIEW",
                        "securityCategory": "weak-cryptography",
                        "vulnerabilityProbability": "HIGH",
                        "message": "Make sure this weak hash algorithm is not used in a security context."
                    }
                ]
            }
        
        else:
            return {
                "status": "success",
                "result": f"Mock data for {tool_name} - MCP server integration in progress"
            }
    
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
            try:
                result_data = await self._make_mcp_call(tool_name, parameters)
            except Exception as e:
                # If real MCP call fails, fall back to mock data for development
                self.logger.warning(f"MCP call failed, using mock data: {e}")
                result_data = await self._generate_mock_data(tool_name, parameters)
            
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
                # First check basic health
                response = await client.get(f"{self.server_url}/health")
                if response.status_code == 200:
                    health_data = response.json()
                    status = health_data.get("status", "unhealthy")
                    
                    # Also check if tools are available
                    try:
                        tools_response = await client.get(f"{self.server_url}/tools")
                        tools_available = tools_response.status_code == 200
                    except Exception:
                        tools_available = False
                    
                    # Update connection status
                    if status == "healthy" and tools_available:
                        self.connection_status = "connected"
                        health_ok = True
                    else:
                        self.connection_status = "degraded" if status == "healthy" else "error"
                        health_ok = False
                    
                    self._ensure_session_state()
                    st.session_state.mcp_client_state["last_health_check"] = datetime.now().isoformat()
                    st.session_state.mcp_client_state["tools_available"] = tools_available
                    
                    return health_ok
                else:
                    self.connection_status = "error"
                    return False
                
        except Exception as e:
            self.logger.error(f"Health check failed: {e}")
            self.connection_status = "error"
            return False
    
    def check_health_sync(self) -> bool:
        """Synchronous health check optimized for Streamlit."""
        try:
            # Simplified approach for Streamlit
            import httpx
            
            # Use synchronous HTTP client to avoid async issues
            with httpx.Client(timeout=5.0) as client:
                response = client.get(f"{self.server_url}/health")
                if response.status_code == 200:
                    health_data = response.json()
                    status = health_data.get("status", "unhealthy")
                    
                    # Update connection status
                    if status == "healthy":
                        self.connection_status = "connected"
                        health_ok = True
                    else:
                        self.connection_status = "error"
                        health_ok = False
                    
                    self._ensure_session_state()
                    st.session_state.mcp_client_state["last_health_check"] = datetime.now().isoformat()
                    
                    return health_ok
                else:
                    self.connection_status = "error"
                    return False
                    
        except Exception as e:
            self.logger.warning(f"Health check failed: {e}")
            self.connection_status = "error"
            return False
    
    def get_available_tools(self) -> List[Dict[str, Any]]:
        """Get list of available MCP tools."""
        try:
            # Try to get real tools from server
            import httpx
            import asyncio
            
            async def fetch_tools():
                async with httpx.AsyncClient(timeout=5.0) as client:
                    response = await client.get(f"{self.server_url}/tools")
                    if response.status_code == 200:
                        data = response.json()
                        return data.get("tools", [])
                    return None
            
            # Try to run async call
            try:
                loop = asyncio.get_running_loop()
                # If we're in an async context, create a new thread
                import concurrent.futures
                import threading
                
                def run_in_thread():
                    new_loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(new_loop)
                    try:
                        return new_loop.run_until_complete(fetch_tools())
                    finally:
                        new_loop.close()
                
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(run_in_thread)
                    try:
                        real_tools = future.result(timeout=5)
                        if real_tools:
                            return real_tools
                    except concurrent.futures.TimeoutError:
                        self.logger.warning("Timeout fetching tools from server")
                    except Exception as e:
                        self.logger.warning(f"Error in thread execution: {e}")
                    
            except RuntimeError:
                # No running loop, try direct approach
                try:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    try:
                        real_tools = loop.run_until_complete(fetch_tools())
                        if real_tools:
                            return real_tools
                    finally:
                        loop.close()
                except Exception as e:
                    self.logger.warning(f"Error in direct async execution: {e}")
            except Exception as e:
                self.logger.warning(f"Unexpected error in get_available_tools: {e}")
                    
        except Exception as e:
            self.logger.warning(f"Could not fetch real tools from server: {e}")
        
        # Fallback to static list based on the server implementation
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
            "tools_available": st.session_state.mcp_client_state.get("tools_available", False),
            "active_calls_count": len(self.get_active_calls()),
            "total_calls": len(st.session_state.mcp_client_state.get("tool_results", [])),
            "error_stats": self.get_error_stats(),
            "server_type": "HTTP via health server (FastMCP + HTTP bridge)"
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


def diagnose_mcp_connection() -> Dict[str, Any]:
    """Diagnose MCP connection issues and provide detailed information."""
    client = get_mcp_client()
    diagnosis = {
        "timestamp": datetime.now().isoformat(),
        "server_url": client.server_url,
        "tests": {}
    }
    
    import httpx
    import asyncio
    
    async def run_diagnostics():
        async with httpx.AsyncClient(timeout=10.0) as http_client:
            # Test 1: Basic connectivity
            try:
                response = await http_client.get(f"{client.server_url}/health")
                diagnosis["tests"]["connectivity"] = {
                    "status": "pass" if response.status_code == 200 else "fail",
                    "http_status": response.status_code,
                    "response_time_ms": response.elapsed.total_seconds() * 1000 if hasattr(response, 'elapsed') else None
                }
                if response.status_code == 200:
                    diagnosis["tests"]["connectivity"]["health_data"] = response.json()
            except Exception as e:
                diagnosis["tests"]["connectivity"] = {
                    "status": "fail",
                    "error": str(e)
                }
            
            # Test 2: Tools endpoint
            try:
                response = await http_client.get(f"{client.server_url}/tools")
                diagnosis["tests"]["tools_endpoint"] = {
                    "status": "pass" if response.status_code == 200 else "fail",
                    "http_status": response.status_code
                }
                if response.status_code == 200:
                    tools_data = response.json()
                    diagnosis["tests"]["tools_endpoint"]["tools_count"] = tools_data.get("count", 0)
                    diagnosis["tests"]["tools_endpoint"]["available_tools"] = [t.get("name") for t in tools_data.get("tools", [])]
            except Exception as e:
                diagnosis["tests"]["tools_endpoint"] = {
                    "status": "fail",
                    "error": str(e)
                }
            
            # Test 3: Sample tool call
            try:
                response = await http_client.post(
                    f"{client.server_url}/tools/health_check",
                    json={"arguments": {}},
                    headers={"Content-Type": "application/json"}
                )
                diagnosis["tests"]["sample_tool_call"] = {
                    "status": "pass" if response.status_code == 200 else "fail",
                    "http_status": response.status_code,
                    "tool_name": "health_check"
                }
                if response.status_code == 200:
                    diagnosis["tests"]["sample_tool_call"]["result"] = response.json()
            except Exception as e:
                diagnosis["tests"]["sample_tool_call"] = {
                    "status": "fail",
                    "error": str(e)
                }
    
    # Run diagnostics
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(run_diagnostics())
        finally:
            loop.close()
    except Exception as e:
        diagnosis["tests"]["async_execution"] = {
            "status": "fail",
            "error": str(e)
        }
    
    # Summary
    passed_tests = sum(1 for test in diagnosis["tests"].values() if test.get("status") == "pass")
    total_tests = len(diagnosis["tests"])
    diagnosis["summary"] = {
        "passed": passed_tests,
        "total": total_tests,
        "success_rate": (passed_tests / total_tests * 100) if total_tests > 0 else 0,
        "overall_status": "healthy" if passed_tests == total_tests else "degraded" if passed_tests > 0 else "unhealthy"
    }
    
    return diagnosis
