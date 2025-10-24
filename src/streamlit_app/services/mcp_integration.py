"""MCP-Streamlit integration service for real-time data synchronization."""

import asyncio
import threading
import time
from typing import Dict, Any, List, Optional, Callable, Set
from datetime import datetime, timedelta
from dataclasses import dataclass, field
import streamlit as st

from .mcp_client import MCPClient, MCPToolResult, get_mcp_client
from streamlit_app.utils.session import SessionManager
from streamlit_app.utils.performance import performance_timer
from streamlit_app.utils.logger import get_logger


@dataclass
class DataSyncConfig:
    """Configuration for data synchronization."""
    sync_interval: int = 30  # seconds
    auto_refresh: bool = True
    cache_ttl: int = 300  # 5 minutes
    max_retries: int = 3
    retry_delay: int = 5  # seconds


@dataclass
class SyncedData:
    """Represents synchronized data from MCP."""
    key: str
    data: Any
    last_updated: datetime = field(default_factory=datetime.now)
    source_tool: str = ""
    parameters: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None


class MCPIntegrationService:
    """Service for integrating MCP with Streamlit UI components."""
    
    def __init__(self, mcp_client: Optional[MCPClient] = None):
        """Initialize MCP integration service."""
        self.mcp_client = mcp_client or get_mcp_client()
        self.logger = get_logger(__name__)
        self.sync_config = DataSyncConfig()
        
        # Data synchronization state
        self._synced_data: Dict[str, SyncedData] = {}
        self._sync_subscriptions: Dict[str, Set[str]] = {}  # page_id -> set of data_keys
        self._sync_thread: Optional[threading.Thread] = None
        self._sync_stop_event = threading.Event()
        self._last_sync_time = None
        
        # Initialize session state safely
        self._ensure_session_state()
        
        # Set up event listeners
        try:
            self.mcp_client.add_event_listener("connection_status_changed", self._on_connection_changed)
            self.mcp_client.add_event_listener("tool_call_success", self._on_tool_success)
            self.mcp_client.add_event_listener("tool_call_error", self._on_tool_error)
        except Exception as e:
            self.logger.warning(f"Could not set up MCP event listeners: {e}")
    
    def _ensure_session_state(self):
        """Ensure session state is properly initialized."""
        try:
            if "mcp_integration_state" not in st.session_state:
                st.session_state.mcp_integration_state = {
                    "synced_data": {},
                    "sync_status": "stopped",
                    "last_sync": None,
                    "sync_errors": [],
                    "subscriptions": {}
                }
        except Exception as e:
            self.logger.warning(f"Could not initialize session state: {e}")
            # Create a fallback state
            self._fallback_state = {
                "synced_data": {},
                "sync_status": "stopped",
                "last_sync": None,
                "sync_errors": [],
                "subscriptions": {}
            }
    
    def _on_connection_changed(self, data: Dict[str, Any]) -> None:
        """Handle MCP connection status changes."""
        status = data.get("status")
        if status == "connected" and self.sync_config.auto_refresh:
            self.start_sync()
        elif status in ["disconnected", "error"]:
            self.stop_sync()
    
    def _on_tool_success(self, data: Dict[str, Any]) -> None:
        """Handle successful tool calls."""
        tool_name = data.get("tool_name")
        result = data.get("result")
        
        # Update synced data if this tool is being tracked
        for key, synced_data in self._synced_data.items():
            if synced_data.source_tool == tool_name:
                synced_data.data = result.data
                synced_data.last_updated = datetime.now()
                synced_data.error = None
    
    def _on_tool_error(self, data: Dict[str, Any]) -> None:
        """Handle tool call errors."""
        tool_name = data.get("tool_name")
        error = data.get("error")
        
        # Update synced data error status
        for key, synced_data in self._synced_data.items():
            if synced_data.source_tool == tool_name:
                synced_data.error = error
                synced_data.last_updated = datetime.now()
    
    def subscribe_to_data(self, page_id: str, data_key: str, tool_name: str, 
                         parameters: Dict[str, Any] = None, sync_interval: int = None) -> None:
        """Subscribe a page to synchronized data."""
        if parameters is None:
            parameters = {}
        
        # Add subscription
        if page_id not in self._sync_subscriptions:
            self._sync_subscriptions[page_id] = set()
        self._sync_subscriptions[page_id].add(data_key)
        
        # Create synced data entry
        self._synced_data[data_key] = SyncedData(
            key=data_key,
            data=None,
            source_tool=tool_name,
            parameters=parameters
        )
        
        # Store in session state
        try:
            if hasattr(st.session_state, 'mcp_integration_state'):
                st.session_state.mcp_integration_state["subscriptions"][data_key] = {
                    "page_id": page_id,
                    "tool_name": tool_name,
                    "parameters": parameters,
                    "sync_interval": sync_interval or self.sync_config.sync_interval
                }
        except Exception as e:
            self.logger.warning(f"Could not store subscription in session state: {e}")
        
        # Perform initial data fetch
        self._fetch_data_async(data_key)
    
    def unsubscribe_from_data(self, page_id: str, data_key: str = None) -> None:
        """Unsubscribe from data synchronization."""
        if data_key:
            # Remove specific subscription
            if page_id in self._sync_subscriptions:
                self._sync_subscriptions[page_id].discard(data_key)
            self._synced_data.pop(data_key, None)
            try:
                if hasattr(st.session_state, 'mcp_integration_state'):
                    st.session_state.mcp_integration_state["subscriptions"].pop(data_key, None)
            except Exception:
                pass
        else:
            # Remove all subscriptions for page
            if page_id in self._sync_subscriptions:
                for key in list(self._sync_subscriptions[page_id]):
                    self._synced_data.pop(key, None)
                    try:
                        if hasattr(st.session_state, 'mcp_integration_state'):
                            st.session_state.mcp_integration_state["subscriptions"].pop(key, None)
                    except Exception:
                        pass
                del self._sync_subscriptions[page_id]
    
    def get_synced_data(self, data_key: str) -> Optional[SyncedData]:
        """Get synchronized data by key."""
        return self._synced_data.get(data_key)
    
    def get_data_value(self, data_key: str, default: Any = None) -> Any:
        """Get the actual data value for a key."""
        synced_data = self.get_synced_data(data_key)
        if synced_data and synced_data.data is not None:
            return synced_data.data
        return default
    
    def is_data_fresh(self, data_key: str, max_age_seconds: int = None) -> bool:
        """Check if data is fresh (within cache TTL)."""
        synced_data = self.get_synced_data(data_key)
        if not synced_data or synced_data.data is None:
            return False
        
        max_age = max_age_seconds or self.sync_config.cache_ttl
        age = (datetime.now() - synced_data.last_updated).total_seconds()
        return age <= max_age
    
    def has_data_error(self, data_key: str) -> bool:
        """Check if data has an error."""
        synced_data = self.get_synced_data(data_key)
        return synced_data is not None and synced_data.error is not None
    
    def get_data_error(self, data_key: str) -> Optional[str]:
        """Get data error message."""
        synced_data = self.get_synced_data(data_key)
        return synced_data.error if synced_data else None
    
    def refresh_data(self, data_key: str) -> None:
        """Manually refresh specific data."""
        self._fetch_data_async(data_key)
    
    def refresh_all_data(self) -> None:
        """Manually refresh all synchronized data."""
        for data_key in self._synced_data.keys():
            self._fetch_data_async(data_key)
    
    def _fetch_data_async(self, data_key: str) -> None:
        """Fetch data asynchronously."""
        synced_data = self._synced_data.get(data_key)
        if not synced_data:
            return
        
        def fetch_data():
            try:
                result = self.mcp_client.call_tool_sync(
                    synced_data.source_tool,
                    synced_data.parameters
                )
                
                if result.success:
                    synced_data.data = result.data
                    synced_data.error = None
                else:
                    synced_data.error = result.error
                
                synced_data.last_updated = datetime.now()
                
                # Note: Cannot update session state from background thread
                # Session state will be updated when data is accessed from main thread
                
            except Exception as e:
                self.logger.error(f"Error fetching data for {data_key}: {e}")
                synced_data.error = str(e)
                synced_data.last_updated = datetime.now()
        
        # Run in background thread
        thread = threading.Thread(target=fetch_data, daemon=True)
        thread.start()
    
    def start_sync(self) -> None:
        """Start background data synchronization."""
        if self._sync_thread and self._sync_thread.is_alive():
            return  # Already running
        
        self._sync_stop_event.clear()
        self._sync_thread = threading.Thread(target=self._sync_loop, daemon=True)
        self._sync_thread.start()
        
        try:
            if hasattr(st.session_state, 'mcp_integration_state'):
                st.session_state.mcp_integration_state["sync_status"] = "running"
        except Exception:
            pass
        self.logger.info("Started MCP data synchronization")
    
    def stop_sync(self) -> None:
        """Stop background data synchronization."""
        if self._sync_thread:
            self._sync_stop_event.set()
            self._sync_thread.join(timeout=5)
        
        try:
            if hasattr(st.session_state, 'mcp_integration_state'):
                st.session_state.mcp_integration_state["sync_status"] = "stopped"
        except Exception:
            pass
        self.logger.info("Stopped MCP data synchronization")
    
    def _sync_loop(self) -> None:
        """Background synchronization loop."""
        while not self._sync_stop_event.is_set():
            try:
                # Check if MCP client is connected
                if self.mcp_client.connection_status != "connected":
                    time.sleep(self.sync_config.sync_interval)
                    continue
                
                # Sync all subscribed data
                for data_key, synced_data in self._synced_data.items():
                    if self._sync_stop_event.is_set():
                        break
                    
                    # Check if data needs refresh
                    if not self.is_data_fresh(data_key):
                        self._fetch_data_async(data_key)
                
                self._last_sync_time = datetime.now()
                try:
                    if hasattr(st.session_state, 'mcp_integration_state'):
                        st.session_state.mcp_integration_state["last_sync"] = self._last_sync_time.isoformat()
                except Exception:
                    pass
                
                # Wait for next sync interval
                self._sync_stop_event.wait(self.sync_config.sync_interval)
                
            except Exception as e:
                self.logger.error(f"Error in sync loop: {e}")
                try:
                    if hasattr(st.session_state, 'mcp_integration_state'):
                        st.session_state.mcp_integration_state["sync_errors"].append({
                            "error": str(e),
                            "timestamp": datetime.now().isoformat()
                        })
                except Exception:
                    pass
                time.sleep(self.sync_config.retry_delay)
    
    def get_sync_status(self) -> Dict[str, Any]:
        """Get synchronization status information."""
        try:
            state = getattr(st.session_state, 'mcp_integration_state', None)
            if state is None:
                # Use fallback state if session state is not available
                state = getattr(self, '_fallback_state', {
                    "sync_status": "stopped",
                    "sync_errors": []
                })
            
            return {
                "status": state.get("sync_status", "stopped"),
                "last_sync": self._last_sync_time,
                "subscriptions_count": len(self._synced_data),
                "active_subscriptions": list(self._synced_data.keys()),
                "sync_interval": self.sync_config.sync_interval,
                "auto_refresh": self.sync_config.auto_refresh,
                "errors": state.get("sync_errors", [])
            }
        except Exception as e:
            self.logger.warning(f"Could not get sync status: {e}")
            return {
                "status": "error",
                "last_sync": None,
                "subscriptions_count": 0,
                "active_subscriptions": [],
                "sync_interval": self.sync_config.sync_interval,
                "auto_refresh": self.sync_config.auto_refresh,
                "errors": [f"Session state error: {e}"]
            }
    
    def configure_sync(self, **kwargs) -> None:
        """Configure synchronization settings."""
        for key, value in kwargs.items():
            if hasattr(self.sync_config, key):
                setattr(self.sync_config, key, value)
        
        # Restart sync if running
        if st.session_state.mcp_integration_state.get("sync_status") == "running":
            self.stop_sync()
            self.start_sync()
    
    def clear_sync_errors(self) -> None:
        """Clear synchronization errors."""
        try:
            if hasattr(st.session_state, 'mcp_integration_state'):
                st.session_state.mcp_integration_state["sync_errors"] = []
        except Exception:
            pass
    
    # Convenience methods for common data types
    
    def sync_projects_data(self, page_id: str, search: str = None, organization: str = None) -> str:
        """Subscribe to projects data synchronization."""
        data_key = f"projects_{page_id}"
        parameters = {}
        if search:
            parameters["search"] = search
        if organization:
            parameters["organization"] = organization
        
        self.subscribe_to_data(page_id, data_key, "list_projects", parameters)
        return data_key
    
    def sync_project_details(self, page_id: str, project_key: str) -> str:
        """Subscribe to project details synchronization."""
        data_key = f"project_details_{project_key}_{page_id}"
        self.subscribe_to_data(page_id, data_key, "get_project_details", {"project_key": project_key})
        return data_key
    
    def sync_project_measures(self, page_id: str, project_key: str, metrics: List[str] = None) -> str:
        """Subscribe to project measures synchronization."""
        data_key = f"project_measures_{project_key}_{page_id}"
        parameters = {"project_key": project_key}
        if metrics:
            parameters["metric_keys"] = metrics
        
        self.subscribe_to_data(page_id, data_key, "get_measures", parameters)
        return data_key
    
    def sync_quality_gate_status(self, page_id: str, project_key: str) -> str:
        """Subscribe to quality gate status synchronization."""
        data_key = f"quality_gate_{project_key}_{page_id}"
        self.subscribe_to_data(page_id, data_key, "get_quality_gate_status", {"project_key": project_key})
        return data_key
    
    def sync_issues_data(self, page_id: str, project_keys: List[str] = None, **filters) -> str:
        """Subscribe to issues data synchronization."""
        data_key = f"issues_{page_id}"
        parameters = {}
        if project_keys:
            parameters["project_keys"] = project_keys
        parameters.update(filters)
        
        self.subscribe_to_data(page_id, data_key, "search_issues", parameters)
        return data_key
    
    def sync_security_hotspots(self, page_id: str, project_key: str, **filters) -> str:
        """Subscribe to security hotspots synchronization."""
        data_key = f"security_hotspots_{project_key}_{page_id}"
        parameters = {"project_key": project_key}
        parameters.update(filters)
        
        self.subscribe_to_data(page_id, data_key, "search_hotspots", parameters)
        return data_key


# Global integration service instance
_integration_service_instance = None


def get_mcp_integration_service() -> MCPIntegrationService:
    """Get global MCP integration service instance."""
    global _integration_service_instance
    
    if _integration_service_instance is None:
        _integration_service_instance = MCPIntegrationService()
    
    return _integration_service_instance


def initialize_mcp_integration() -> MCPIntegrationService:
    """Initialize MCP integration service."""
    service = get_mcp_integration_service()
    
    # Start sync if auto-refresh is enabled and MCP is connected
    if (service.sync_config.auto_refresh and 
        service.mcp_client.connection_status == "connected"):
        service.start_sync()
    
    return service
