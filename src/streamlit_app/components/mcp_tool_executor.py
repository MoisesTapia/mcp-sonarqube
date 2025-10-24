"""MCP tool executor component for Streamlit interface."""

import json
from typing import Dict, Any, List, Optional, Union
from datetime import datetime
import streamlit as st

from streamlit_app.services.mcp_client import get_mcp_client, MCPToolResult
from streamlit_app.services.mcp_integration import get_mcp_integration_service
from streamlit_app.utils.error_handler import get_error_handler, ErrorCategory, ErrorSeverity
from streamlit_app.utils.session import SessionManager


class MCPToolExecutor:
    """Component for executing MCP tools from Streamlit interface."""
    
    def __init__(self):
        """Initialize MCP tool executor."""
        self.mcp_client = get_mcp_client()
        self.integration_service = get_mcp_integration_service()
        self.error_handler = get_error_handler()
    
    def render_tool_selector(self, key: str = "mcp_tool_selector") -> Optional[Dict[str, Any]]:
        """Render tool selector interface."""
        st.subheader("🔧 MCP Tool Executor")
        
        # Get available tools
        available_tools = self.mcp_client.get_available_tools()
        
        if not available_tools:
            st.warning("No MCP tools available. Please check MCP server connection.")
            return None
        
        # Tool selection
        tool_names = [tool["name"] for tool in available_tools]
        selected_tool_name = st.selectbox(
            "Select Tool",
            options=tool_names,
            key=f"{key}_tool_select"
        )
        
        # Find selected tool
        selected_tool = next(
            (tool for tool in available_tools if tool["name"] == selected_tool_name),
            None
        )
        
        if not selected_tool:
            return None
        
        # Show tool description
        st.info(f"**Description:** {selected_tool.get('description', 'No description available')}")
        
        return selected_tool
    
    def render_parameter_inputs(self, tool: Dict[str, Any], key: str = "mcp_params") -> Dict[str, Any]:
        """Render parameter input interface for selected tool."""
        parameters = {}
        tool_params = tool.get("parameters", {})
        
        if not tool_params:
            st.info("This tool requires no parameters.")
            return parameters
        
        st.subheader("📝 Parameters")
        
        for param_name, param_config in tool_params.items():
            param_type = param_config.get("type", "string")
            param_required = param_config.get("required", False)
            param_default = param_config.get("default")
            param_optional = param_config.get("optional", False)
            
            # Create label with required indicator
            label = param_name
            if param_required and not param_optional:
                label += " *"
            
            # Render input based on parameter type
            if param_type == "string":
                value = st.text_input(
                    label,
                    value=param_default or "",
                    key=f"{key}_{param_name}",
                    help=f"Type: {param_type}"
                )
                if value:
                    parameters[param_name] = value
            
            elif param_type == "integer":
                value = st.number_input(
                    label,
                    value=param_default or 0,
                    step=1,
                    key=f"{key}_{param_name}",
                    help=f"Type: {param_type}"
                )
                parameters[param_name] = int(value)
            
            elif param_type == "boolean":
                value = st.checkbox(
                    label,
                    value=param_default or False,
                    key=f"{key}_{param_name}",
                    help=f"Type: {param_type}"
                )
                parameters[param_name] = value
            
            elif param_type == "array":
                value = st.text_area(
                    label,
                    value="",
                    key=f"{key}_{param_name}",
                    help="Enter values separated by commas"
                )
                if value:
                    # Split by comma and strip whitespace
                    parameters[param_name] = [item.strip() for item in value.split(",") if item.strip()]
            
            else:
                # Generic text input for unknown types
                value = st.text_input(
                    label,
                    value=param_default or "",
                    key=f"{key}_{param_name}",
                    help=f"Type: {param_type}"
                )
                if value:
                    parameters[param_name] = value
        
        return parameters
    
    def render_execution_interface(self, tool: Dict[str, Any], parameters: Dict[str, Any], 
                                 key: str = "mcp_execute") -> Optional[MCPToolResult]:
        """Render tool execution interface."""
        st.subheader("▶️ Execute Tool")
        
        # Show parameter summary
        if parameters:
            with st.expander("📋 Parameter Summary"):
                st.json(parameters)
        
        # Execution buttons
        col1, col2, col3 = st.columns([1, 1, 2])
        
        with col1:
            execute_button = st.button(
                "🚀 Execute",
                key=f"{key}_execute",
                type="primary"
            )
        
        with col2:
            execute_async_button = st.button(
                "⚡ Execute Async",
                key=f"{key}_execute_async"
            )
        
        with col3:
            if st.button("📋 Copy as JSON", key=f"{key}_copy"):
                tool_call = {
                    "tool": tool["name"],
                    "parameters": parameters
                }
                st.code(json.dumps(tool_call, indent=2))
        
        result = None
        
        # Execute tool synchronously
        if execute_button:
            with st.spinner(f"Executing {tool['name']}..."):
                try:
                    result = self.mcp_client.call_tool_sync(tool["name"], parameters)
                    
                    if result.success:
                        st.success(f"✅ Tool executed successfully in {result.execution_time:.2f}s")
                    else:
                        st.error(f"❌ Tool execution failed: {result.error}")
                        self.error_handler.handle_error(
                            result.error,
                            ErrorCategory.MCP_TOOL,
                            ErrorSeverity.MEDIUM,
                            context={"tool_name": tool["name"], "parameters": parameters}
                        )
                
                except Exception as e:
                    st.error(f"❌ Execution error: {str(e)}")
                    self.error_handler.handle_error(
                        e,
                        ErrorCategory.MCP_TOOL,
                        ErrorSeverity.HIGH,
                        context={"tool_name": tool["name"], "parameters": parameters}
                    )
        
        # Execute tool asynchronously
        if execute_async_button:
            st.info("🔄 Tool execution started in background...")
            try:
                # Store execution request in session state for background processing
                if "async_executions" not in st.session_state:
                    st.session_state.async_executions = []
                
                execution_id = f"{tool['name']}_{datetime.now().timestamp()}"
                st.session_state.async_executions.append({
                    "id": execution_id,
                    "tool_name": tool["name"],
                    "parameters": parameters,
                    "status": "pending",
                    "timestamp": datetime.now().isoformat()
                })
                
                st.success(f"✅ Async execution queued with ID: {execution_id}")
                
            except Exception as e:
                st.error(f"❌ Failed to queue async execution: {str(e)}")
        
        return result
    
    def render_result_display(self, result: MCPToolResult, key: str = "mcp_result") -> None:
        """Render tool execution result."""
        if not result:
            return
        
        st.subheader("📊 Execution Result")
        
        # Result status
        if result.success:
            st.success(f"✅ Success (Execution time: {result.execution_time:.2f}s)")
        else:
            st.error(f"❌ Failed: {result.error}")
            return
        
        # Result data
        if result.data:
            # Show result in tabs
            tab1, tab2, tab3 = st.tabs(["📋 Formatted", "🔍 Raw JSON", "📈 Analysis"])
            
            with tab1:
                self._render_formatted_result(result.data)
            
            with tab2:
                st.json(result.data)
            
            with tab3:
                self._render_result_analysis(result.data)
        
        # Export options
        st.subheader("💾 Export Options")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("📄 Download JSON", key=f"{key}_download_json"):
                json_str = json.dumps(result.data, indent=2)
                st.download_button(
                    "Download",
                    json_str,
                    file_name=f"mcp_result_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                    mime="application/json"
                )
        
        with col2:
            if st.button("📊 Save to Session", key=f"{key}_save_session"):
                SessionManager.cache_data(f"mcp_result_{result.call_id}", result.data)
                st.success("Result saved to session!")
        
        with col3:
            if st.button("🔄 Use as Input", key=f"{key}_use_input"):
                st.session_state[f"mcp_input_data_{key}"] = result.data
                st.success("Result available as input data!")
    
    def _render_formatted_result(self, data: Dict[str, Any]) -> None:
        """Render formatted result based on data structure."""
        if not data:
            st.info("No data returned")
            return
        
        # Handle common data structures
        if isinstance(data, dict):
            if "success" in data and "data" in data:
                # Standard MCP response format
                if data.get("success"):
                    st.success("✅ Operation successful")
                    if data.get("data"):
                        self._render_data_table(data["data"])
                else:
                    st.error(f"❌ Operation failed: {data.get('message', 'Unknown error')}")
            
            elif "projects" in data or "components" in data:
                # Project list data
                projects = data.get("projects") or data.get("components", [])
                if projects:
                    st.write(f"Found {len(projects)} projects:")
                    df_data = []
                    for project in projects:
                        df_data.append({
                            "Key": project.get("key", ""),
                            "Name": project.get("name", ""),
                            "Visibility": project.get("visibility", ""),
                            "Last Analysis": project.get("lastAnalysisDate", "")
                        })
                    st.dataframe(df_data)
            
            elif "issues" in data:
                # Issues data
                issues = data.get("issues", [])
                if issues:
                    st.write(f"Found {len(issues)} issues:")
                    df_data = []
                    for issue in issues:
                        df_data.append({
                            "Key": issue.get("key", ""),
                            "Type": issue.get("type", ""),
                            "Severity": issue.get("severity", ""),
                            "Status": issue.get("status", ""),
                            "Component": issue.get("component", "")
                        })
                    st.dataframe(df_data)
            
            elif "measures" in data:
                # Measures data
                measures = data.get("measures", [])
                if measures:
                    st.write("Project Measures:")
                    df_data = []
                    for measure in measures:
                        df_data.append({
                            "Metric": measure.get("metric", ""),
                            "Value": measure.get("value", ""),
                            "Best Value": measure.get("bestValue", False)
                        })
                    st.dataframe(df_data)
            
            else:
                # Generic dictionary display
                self._render_data_table(data)
        
        elif isinstance(data, list):
            # List data
            if data:
                st.write(f"Found {len(data)} items:")
                if isinstance(data[0], dict):
                    st.dataframe(data)
                else:
                    for i, item in enumerate(data):
                        st.write(f"{i+1}. {item}")
        
        else:
            # Simple value
            st.write(f"Result: {data}")
    
    def _render_data_table(self, data: Union[Dict[str, Any], List[Dict[str, Any]]]) -> None:
        """Render data as a table."""
        if isinstance(data, dict):
            # Convert dict to list of key-value pairs
            table_data = [{"Key": k, "Value": str(v)} for k, v in data.items()]
            st.dataframe(table_data)
        elif isinstance(data, list) and data:
            if isinstance(data[0], dict):
                st.dataframe(data)
            else:
                st.write(data)
        else:
            st.write(str(data))
    
    def _render_result_analysis(self, data: Dict[str, Any]) -> None:
        """Render result analysis and insights."""
        if not data:
            st.info("No data to analyze")
            return
        
        # Basic analysis
        st.write("**Data Analysis:**")
        
        # Count different data types
        if isinstance(data, dict):
            st.write(f"- Dictionary with {len(data)} keys")
            
            # Analyze nested structures
            nested_dicts = sum(1 for v in data.values() if isinstance(v, dict))
            nested_lists = sum(1 for v in data.values() if isinstance(v, list))
            
            if nested_dicts > 0:
                st.write(f"- Contains {nested_dicts} nested objects")
            if nested_lists > 0:
                st.write(f"- Contains {nested_lists} arrays")
            
            # Look for common patterns
            if "total" in data:
                st.write(f"- Total count: {data['total']}")
            if "paging" in data:
                paging = data["paging"]
                st.write(f"- Paginated results: Page {paging.get('pageIndex', 1)} of {paging.get('total', 'unknown')}")
        
        elif isinstance(data, list):
            st.write(f"- Array with {len(data)} items")
            if data and isinstance(data[0], dict):
                keys = set()
                for item in data:
                    keys.update(item.keys())
                st.write(f"- Common fields: {', '.join(sorted(keys))}")
    
    def render_async_execution_monitor(self, key: str = "async_monitor") -> None:
        """Render async execution monitoring interface."""
        if "async_executions" not in st.session_state:
            return
        
        executions = st.session_state.async_executions
        if not executions:
            return
        
        st.subheader("🔄 Async Executions")
        
        for execution in executions:
            with st.expander(f"Execution: {execution['tool_name']} ({execution['status']})"):
                st.write(f"**ID:** {execution['id']}")
                st.write(f"**Tool:** {execution['tool_name']}")
                st.write(f"**Status:** {execution['status']}")
                st.write(f"**Started:** {execution['timestamp']}")
                
                if execution.get("parameters"):
                    st.write("**Parameters:**")
                    st.json(execution["parameters"])
                
                # Action buttons
                col1, col2 = st.columns(2)
                with col1:
                    if st.button(f"Cancel", key=f"{key}_cancel_{execution['id']}"):
                        execution["status"] = "cancelled"
                        st.rerun()
                
                with col2:
                    if st.button(f"Remove", key=f"{key}_remove_{execution['id']}"):
                        st.session_state.async_executions.remove(execution)
                        st.rerun()
    
    def render_complete_interface(self, key: str = "mcp_tool_interface") -> None:
        """Render complete MCP tool execution interface."""
        # Connection status
        connection_info = self.mcp_client.get_connection_info()
        
        if connection_info["status"] == "connected":
            st.success(f"✅ MCP Server Connected")
        else:
            st.error(f"❌ MCP Server: {connection_info['status']}")
            if st.button("🔄 Retry Connection", key="mcp_tool_executor_retry"):
                self.mcp_client.check_health_sync()
                st.rerun()
            return
        
        # Tool selection
        selected_tool = self.render_tool_selector(key)
        if not selected_tool:
            return
        
        # Parameter inputs
        parameters = self.render_parameter_inputs(selected_tool, key)
        
        # Execution interface
        result = self.render_execution_interface(selected_tool, parameters, key)
        
        # Result display
        if result:
            self.render_result_display(result, key)
        
        # Async execution monitor
        self.render_async_execution_monitor(key)
        
        # Tool history
        with st.expander("📜 Recent Tool Calls"):
            history = self.mcp_client.get_tool_history(limit=10)
            if history:
                for call in history:
                    status_icon = "✅" if call.get("success") else "❌"
                    st.write(f"{status_icon} {call['tool_name']} - {call['timestamp']}")
            else:
                st.info("No recent tool calls")


def render_mcp_tool_executor(key: str = "mcp_tool_executor") -> None:
    """Render MCP tool executor component."""
    executor = MCPToolExecutor()
    executor.render_complete_interface(key)
