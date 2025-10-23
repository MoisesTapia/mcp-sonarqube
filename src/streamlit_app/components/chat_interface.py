"""Interactive chat interface for MCP tool execution."""

import json
import re
from typing import Dict, Any, List, Optional, Tuple, Union
from datetime import datetime
import uuid

import streamlit as st
import asyncio
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from streamlit_app.services.mcp_client import MCPClient


class ChatInterface:
    """Interactive chat interface for MCP tool execution."""
    
    def __init__(self):
        """Initialize the chat interface."""
        self.mcp_client = None
        self.conversation_history = []
        self.available_tools = []
        
    def initialize_session_state(self):
        """Initialize Streamlit session state for chat."""
        if "chat_messages" not in st.session_state:
            st.session_state.chat_messages = []
        if "mcp_connected" not in st.session_state:
            st.session_state.mcp_connected = False
        if "available_tools" not in st.session_state:
            st.session_state.available_tools = []
        if "chat_session_id" not in st.session_state:
            st.session_state.chat_session_id = str(uuid.uuid4())
        if "conversation_started" not in st.session_state:
            st.session_state.conversation_started = datetime.now()
        if "recent_projects" not in st.session_state:
            st.session_state.recent_projects = []
    
    async def connect_to_mcp(self) -> bool:
        """Connect to the MCP server."""
        try:
            from streamlit_app.services.mcp_client import get_mcp_client
            
            self.mcp_client = get_mcp_client()
            
            # Check health and get available tools
            is_healthy = await self.mcp_client.check_health()
            if is_healthy:
                self.available_tools = self.mcp_client.get_available_tools()
                st.session_state.available_tools = [tool["name"] for tool in self.available_tools]
                st.session_state.mcp_connected = True
                return True
            else:
                st.error("MCP server health check failed")
                return False
                
        except Exception as e:
            st.error(f"Failed to connect to MCP server: {str(e)}")
            return False
    
    def render_chat_interface(self):
        """Render the main chat interface."""
        self.initialize_session_state()
        
        st.title("💬 SonarQube Chat Assistant")
        st.markdown("Ask questions about your SonarQube projects using natural language!")
        
        # Session information
        col1, col2, col3 = st.columns(3)
        with col1:
            st.caption(f"🆔 Session: {st.session_state.chat_session_id[:8]}...")
        with col2:
            st.caption(f"🕒 Started: {st.session_state.conversation_started.strftime('%H:%M:%S')}")
        with col3:
            st.caption(f"💬 Messages: {len(st.session_state.chat_messages)}")
        
        # Connection status
        if not st.session_state.mcp_connected:
            st.warning("🔌 MCP Server not connected")
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button("🔌 Connect to MCP Server", type="primary"):
                    with st.spinner("Connecting to MCP server..."):
                        if asyncio.run(self.connect_to_mcp()):
                            st.success("Connected to MCP server!")
                            st.rerun()
            
            with col2:
                if st.button("🔄 Retry Connection", key="chat_interface_retry"):
                    with st.spinner("Retrying connection..."):
                        if asyncio.run(self.connect_to_mcp()):
                            st.success("Connected to MCP server!")
                            st.rerun()
                        else:
                            st.error("Connection failed. Please check your configuration.")
            
            st.info("💡 Make sure your SonarQube server is running and properly configured.")
            return
        
        # Connection success indicator
        st.success("✅ Connected to MCP Server")
        
        # Show available tools in sidebar or expander
        with st.expander("🛠️ Available Tools", expanded=False):
            if st.session_state.available_tools:
                st.write("**Available MCP Tools:**")
                for tool in st.session_state.available_tools:
                    st.code(f"• {tool}")
            else:
                st.info("No tools available")
        
        # Welcome message for new conversations
        if not st.session_state.chat_messages:
            self._render_welcome_message()
        
        # Chat messages container
        chat_container = st.container()
        
        # Display chat history
        with chat_container:
            for message in st.session_state.chat_messages:
                self._render_message(message)
        
        # Enhanced chat input with context-aware suggestions
        self._render_chat_input_with_suggestions()

    
    def _render_welcome_message(self):
        """Render welcome message for new conversations."""
        with st.chat_message("assistant"):
            st.markdown("""
            👋 **Welcome to SonarQube Chat Assistant!**
            
            I can help you interact with your SonarQube projects using natural language. Here's what I can do:
            
            🔍 **Project Discovery**
            - List all your projects
            - Get detailed project information
            
            📊 **Quality Analysis**
            - Show code quality metrics
            - Check Quality Gate status
            - Analyze test coverage and technical debt
            
            🐛 **Issue Management**
            - Find and filter code issues
            - Show bug reports and code smells
            - Track issue resolution
            
            🔒 **Security Analysis**
            - Identify security hotspots
            - Analyze vulnerability risks
            - Review security categories
            
            💡 **Getting Started:**
            - Try asking "List all projects" to see what's available
            - Use natural language like "How is the quality of my-project?"
            - Check the suggestions panel for more examples
            
            What would you like to know about your SonarQube projects?
            """)
            
            st.caption(f"🕒 {datetime.now().strftime('%H:%M:%S')}")
    
    def _render_message(self, message: Dict[str, Any]):
        """Render a single chat message."""
        with st.chat_message(message["role"]):
            if message["role"] == "user":
                st.write(message["content"])
            else:
                # Assistant message might contain structured data
                if isinstance(message["content"], dict):
                    self._render_structured_response(message["content"])
                else:
                    st.write(message["content"])
            
            # Show timestamp
            st.caption(f"🕒 {message['timestamp'].strftime('%H:%M:%S')}")
    
    def _render_structured_response(self, response: Dict[str, Any]):
        """Render structured response from MCP tools with rich visualizations."""
        if "tool_result" in response:
            tool_name = response.get("tool_name", "Unknown Tool")
            
            # Tool header with icon and execution info
            tool_icons = {
                "list_projects": "📁",
                "get_project_details": "📊",
                "get_measures": "📈",
                "search_issues": "🐛",
                "get_quality_gate_status": "🚦",
                "search_hotspots": "🔒",
                "health_check": "💚",
                "get_cache_info": "🗄️"
            }
            
            icon = tool_icons.get(tool_name, "🔧")
            
            # Create expandable section for tool result
            with st.expander(f"{icon} {tool_name.replace('_', ' ').title()}", expanded=True):
                # Show execution metadata if available
                if "execution_time" in response:
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.caption(f"⏱️ Execution: {response['execution_time']:.2f}s")
                    with col2:
                        st.caption(f"🔧 Tool: {tool_name}")
                    with col3:
                        st.caption(f"✅ Status: Success")
                
                result = response["tool_result"]
                
                # Enhanced rendering based on tool type
                if tool_name == "list_projects":
                    self._render_projects_list(result)
                elif tool_name == "get_project_details":
                    self._render_project_details(result)
                elif tool_name == "get_measures":
                    self._render_metrics_visualization(result)
                elif tool_name == "search_issues":
                    self._render_issues_analysis(result)
                elif tool_name == "get_quality_gate_status":
                    self._render_quality_gate_status(result)
                elif tool_name == "search_hotspots":
                    self._render_security_analysis(result)
                elif tool_name == "health_check":
                    self._render_health_check(result)
                elif tool_name == "get_cache_info":
                    self._render_cache_info(result)
                else:
                    # Generic JSON rendering with syntax highlighting
                    st.json(result)
                
                # Add quick actions based on result type
                self._render_quick_actions(tool_name, result)
        
        if "error" in response:
            st.error(f"❌ Error: {response['error']}")
            
            # Suggest troubleshooting steps
            error_msg = response['error'].lower()
            if "connection" in error_msg or "timeout" in error_msg:
                st.info("💡 **Troubleshooting:** Check your SonarQube server connection and try again.")
            elif "authentication" in error_msg or "unauthorized" in error_msg:
                st.info("💡 **Troubleshooting:** Verify your SonarQube token and permissions.")
            elif "not found" in error_msg:
                st.info("💡 **Troubleshooting:** Check if the project key exists and is accessible.")
        
        if "summary" in response:
            st.success(f"📋 {response['summary']}")
    
    def _render_health_check(self, result: Any):
        """Render health check results."""
        if isinstance(result, dict):
            status = result.get("status", "unknown")
            
            if status == "healthy":
                st.success("✅ SonarQube server is healthy and accessible")
            else:
                st.warning(f"⚠️ Health check status: {status}")
            
            # Show additional health info
            if "sonarqube_version" in result:
                st.info(f"🏷️ SonarQube Version: {result['sonarqube_version']}")
            
            if "response_time" in result:
                st.info(f"⏱️ Response Time: {result['response_time']:.2f}s")
            
            # Show detailed health metrics
            with st.expander("🔍 Detailed Health Information"):
                st.json(result)
        else:
            st.json(result)
    
    def _render_cache_info(self, result: Any):
        """Render cache information with statistics."""
        if isinstance(result, dict):
            # Cache statistics
            col1, col2, col3 = st.columns(3)
            
            with col1:
                hit_rate = result.get("hit_rate", 0)
                st.metric("Cache Hit Rate", f"{hit_rate:.1f}%")
            
            with col2:
                total_requests = result.get("total_requests", 0)
                st.metric("Total Requests", total_requests)
            
            with col3:
                cache_size = result.get("cache_size", 0)
                st.metric("Cache Entries", cache_size)
            
            # Cache performance chart
            if "cache_stats" in result:
                cache_stats = result["cache_stats"]
                
                # Create hit/miss chart
                fig = px.pie(
                    values=[cache_stats.get("hits", 0), cache_stats.get("misses", 0)],
                    names=["Hits", "Misses"],
                    title="Cache Performance",
                    color_discrete_map={"Hits": "green", "Misses": "red"}
                )
                st.plotly_chart(fig, use_container_width=True)
            
            # Detailed cache info
            with st.expander("🗄️ Detailed Cache Information"):
                st.json(result)
        else:
            st.json(result)
    
    def _render_quick_actions(self, tool_name: str, result: Any):
        """Render quick action buttons based on the tool result."""
        st.markdown("---")
        st.write("**🚀 Quick Actions:**")
        
        col1, col2, col3 = st.columns(3)
        
        if tool_name == "list_projects" and isinstance(result, list) and result:
            with col1:
                if st.button("📊 Get Metrics for First Project", key=f"quick_metrics_{tool_name}"):
                    project_key = result[0].get("key", "")
                    if project_key:
                        self._execute_suggestion(f"Get metrics for {project_key}")
            
            with col2:
                if st.button("🐛 Find Issues in First Project", key=f"quick_issues_{tool_name}"):
                    project_key = result[0].get("key", "")
                    if project_key:
                        self._execute_suggestion(f"Show issues in {project_key}")
            
            with col3:
                if st.button("🚦 Check Quality Gate", key=f"quick_qg_{tool_name}"):
                    project_key = result[0].get("key", "")
                    if project_key:
                        self._execute_suggestion(f"Check quality gate for {project_key}")
        
        elif tool_name == "get_project_details" and isinstance(result, dict):
            project_key = result.get("key", "")
            if project_key:
                with col1:
                    if st.button("📈 View Metrics", key=f"quick_metrics_{tool_name}"):
                        self._execute_suggestion(f"Get metrics for {project_key}")
                
                with col2:
                    if st.button("🐛 Find Issues", key=f"quick_issues_{tool_name}"):
                        self._execute_suggestion(f"Show issues in {project_key}")
                
                with col3:
                    if st.button("🔒 Security Analysis", key=f"quick_security_{tool_name}"):
                        self._execute_suggestion(f"Find security issues in {project_key}")
        
        elif tool_name == "get_measures" and isinstance(result, dict):
            # Extract project key from measures result if available
            project_key = result.get("component", {}).get("key", "")
            if project_key:
                with col1:
                    if st.button("🐛 View Issues", key=f"quick_issues_{tool_name}"):
                        self._execute_suggestion(f"Show issues in {project_key}")
                
                with col2:
                    if st.button("🚦 Quality Gate", key=f"quick_qg_{tool_name}"):
                        self._execute_suggestion(f"Check quality gate for {project_key}")
                
                with col3:
                    if st.button("🔒 Security Check", key=f"quick_security_{tool_name}"):
                        self._execute_suggestion(f"Find security issues in {project_key}")
        
        elif tool_name == "search_issues" and isinstance(result, list) and result:
            with col1:
                if st.button("🔒 Check Security", key=f"quick_security_{tool_name}"):
                    # Try to extract project key from first issue
                    first_issue = result[0]
                    component = first_issue.get("component", "")
                    if ":" in component:
                        project_key = component.split(":")[0]
                        self._execute_suggestion(f"Find security issues in {project_key}")
            
            with col2:
                if st.button("📊 View Metrics", key=f"quick_metrics_{tool_name}"):
                    first_issue = result[0]
                    component = first_issue.get("component", "")
                    if ":" in component:
                        project_key = component.split(":")[0]
                        self._execute_suggestion(f"Get metrics for {project_key}")
            
            with col3:
                if st.button("🚦 Quality Gate", key=f"quick_qg_{tool_name}"):
                    first_issue = result[0]
                    component = first_issue.get("component", "")
                    if ":" in component:
                        project_key = component.split(":")[0]
                        self._execute_suggestion(f"Check quality gate for {project_key}")
        
        # Generic actions available for all tools
        if tool_name != "list_projects":
            st.markdown("**🔄 General Actions:**")
            col1, col2, col3 = st.columns(3)
            
            with col1:
                if st.button("📁 List All Projects", key=f"quick_list_{tool_name}"):
                    self._execute_suggestion("List all projects")
            
            with col2:
                if st.button("🔄 Refresh Data", key=f"quick_refresh_{tool_name}"):
                    # Re-execute the same tool with same parameters
                    last_user_msg = None
                    for msg in reversed(st.session_state.chat_messages):
                        if msg["role"] == "user":
                            last_user_msg = msg["content"]
                            break
                    if last_user_msg:
                        self._execute_suggestion(last_user_msg)
            
            with col3:
                if st.button("💡 Get Suggestions", key=f"quick_suggest_{tool_name}"):
                    st.info("Check the suggestions panel on the right for more ideas!")
    
    def _render_projects_list(self, result: Any):
        """Render projects list with enhanced visualization."""
        if isinstance(result, list) and result:
            df = pd.DataFrame(result)
            
            # Summary metrics
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total Projects", len(result))
            with col2:
                public_count = sum(1 for p in result if p.get("visibility") == "public")
                st.metric("Public Projects", public_count)
            with col3:
                private_count = len(result) - public_count
                st.metric("Private Projects", private_count)
            
            # Interactive table
            st.dataframe(
                df,
                use_container_width=True,
                column_config={
                    "key": st.column_config.TextColumn("Project Key", width="medium"),
                    "name": st.column_config.TextColumn("Name", width="large"),
                    "visibility": st.column_config.TextColumn("Visibility", width="small"),
                    "lastAnalysisDate": st.column_config.DatetimeColumn("Last Analysis", width="medium")
                }
            )
            
            # Visibility distribution chart
            if "visibility" in df.columns:
                visibility_counts = df["visibility"].value_counts()
                fig = px.pie(
                    values=visibility_counts.values,
                    names=visibility_counts.index,
                    title="Project Visibility Distribution"
                )
                st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No projects found")
    
    def _render_project_details(self, result: Any):
        """Render detailed project information."""
        if isinstance(result, dict):
            # Key project information
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Project Key", result.get("key", "N/A"))
            with col2:
                st.metric("Project Name", result.get("name", "N/A"))
            with col3:
                st.metric("Visibility", result.get("visibility", "N/A"))
            
            # Analysis information
            if "lastAnalysisDate" in result:
                st.info(f"🕒 Last Analysis: {result['lastAnalysisDate']}")
            
            # Additional details in expandable sections
            with st.expander("📊 Complete Project Information", expanded=True):
                st.json(result)
        else:
            st.json(result)
    
    def _render_metrics_visualization(self, result: Any):
        """Render metrics with advanced visualizations."""
        if isinstance(result, dict) and "measures" in result:
            measures = result["measures"]
            
            # Convert to DataFrame for easier manipulation
            metrics_data = []
            for measure in measures:
                metrics_data.append({
                    "metric": measure.get("metric", "Unknown"),
                    "value": measure.get("value", "0"),
                    "best_value": measure.get("bestValue", False)
                })
            
            df = pd.DataFrame(metrics_data)
            
            # Key metrics display
            key_metrics = ["coverage", "bugs", "vulnerabilities", "code_smells", "duplicated_lines_density"]
            available_key_metrics = [m for m in key_metrics if m in df["metric"].values]
            
            if available_key_metrics:
                st.subheader("🎯 Key Quality Metrics")
                cols = st.columns(len(available_key_metrics))
                
                for i, metric in enumerate(available_key_metrics):
                    metric_row = df[df["metric"] == metric].iloc[0]
                    value = metric_row["value"]
                    
                    with cols[i]:
                        # Format value based on metric type
                        if metric == "coverage":
                            formatted_value = f"{value}%"
                            delta_color = "normal" if float(value) >= 80 else "inverse"
                        elif metric in ["bugs", "vulnerabilities", "code_smells"]:
                            formatted_value = str(value)
                            delta_color = "normal" if int(value) == 0 else "inverse"
                        elif metric == "duplicated_lines_density":
                            formatted_value = f"{value}%"
                            delta_color = "normal" if float(value) <= 3 else "inverse"
                        else:
                            formatted_value = str(value)
                            delta_color = "normal"
                        
                        st.metric(
                            metric.replace("_", " ").title(),
                            formatted_value,
                            delta_color=delta_color
                        )
            
            # Rating metrics visualization
            rating_metrics = df[df["metric"].str.contains("rating", na=False)]
            if not rating_metrics.empty:
                st.subheader("⭐ Quality Ratings")
                
                fig = go.Figure()
                
                for _, row in rating_metrics.iterrows():
                    metric_name = row["metric"].replace("_rating", "").title()
                    value = float(row["value"])
                    
                    # Color coding for ratings (1=best, 5=worst)
                    color = ["green", "yellow", "orange", "red", "darkred"][int(value) - 1]
                    
                    fig.add_trace(go.Bar(
                        x=[metric_name],
                        y=[6 - value],  # Invert for better visualization
                        name=metric_name,
                        marker_color=color,
                        text=f"Rating: {int(value)}",
                        textposition="auto"
                    ))
                
                fig.update_layout(
                    title="Quality Ratings (Lower is Better)",
                    yaxis_title="Quality Score",
                    showlegend=False,
                    height=400
                )
                
                st.plotly_chart(fig, use_container_width=True)
            
            # All metrics table
            with st.expander("📈 All Metrics Details", expanded=False):
                st.dataframe(df, use_container_width=True)
        else:
            st.json(result)
    
    def _render_issues_analysis(self, result: Any):
        """Render issues with analysis and visualizations."""
        if isinstance(result, list) and result:
            df = pd.DataFrame(result)
            
            # Summary statistics
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Total Issues", len(result))
            with col2:
                if "severity" in df.columns:
                    critical_count = len(df[df["severity"] == "CRITICAL"])
                    st.metric("Critical Issues", critical_count)
            with col3:
                if "type" in df.columns:
                    bug_count = len(df[df["type"] == "BUG"])
                    st.metric("Bugs", bug_count)
            with col4:
                if "status" in df.columns:
                    open_count = len(df[df["status"] == "OPEN"])
                    st.metric("Open Issues", open_count)
            
            # Severity distribution
            if "severity" in df.columns:
                severity_counts = df["severity"].value_counts()
                fig = px.bar(
                    x=severity_counts.index,
                    y=severity_counts.values,
                    title="Issues by Severity",
                    color=severity_counts.index,
                    color_discrete_map={
                        "CRITICAL": "red",
                        "MAJOR": "orange", 
                        "MINOR": "yellow",
                        "INFO": "blue"
                    }
                )
                st.plotly_chart(fig, use_container_width=True)
            
            # Issues table
            st.dataframe(
                df,
                use_container_width=True,
                column_config={
                    "key": st.column_config.TextColumn("Issue Key", width="small"),
                    "rule": st.column_config.TextColumn("Rule", width="medium"),
                    "severity": st.column_config.TextColumn("Severity", width="small"),
                    "status": st.column_config.TextColumn("Status", width="small"),
                    "component": st.column_config.TextColumn("Component", width="large")
                }
            )
        else:
            st.info("No issues found")
    
    def _render_quality_gate_status(self, result: Any):
        """Render Quality Gate status with visual indicators."""
        if isinstance(result, dict):
            status = result.get("status", "UNKNOWN")
            
            # Status indicator
            if status == "PASSED":
                st.success(f"✅ Quality Gate: {status}")
            elif status == "FAILED":
                st.error(f"❌ Quality Gate: {status}")
            else:
                st.warning(f"⚠️ Quality Gate: {status}")
            
            # Conditions breakdown
            if "conditions" in result:
                conditions = result["conditions"]
                st.subheader("📋 Quality Gate Conditions")
                
                passed_conditions = []
                failed_conditions = []
                
                for condition in conditions:
                    condition_status = condition.get("status", "UNKNOWN")
                    metric_key = condition.get("metricKey", "Unknown")
                    actual_value = condition.get("actualValue", "N/A")
                    error_threshold = condition.get("errorThreshold", "N/A")
                    
                    condition_data = {
                        "Metric": metric_key,
                        "Actual": actual_value,
                        "Threshold": error_threshold,
                        "Status": condition_status
                    }
                    
                    if condition_status == "OK":
                        passed_conditions.append(condition_data)
                    else:
                        failed_conditions.append(condition_data)
                
                # Show failed conditions first
                if failed_conditions:
                    st.error("❌ Failed Conditions")
                    st.dataframe(pd.DataFrame(failed_conditions), use_container_width=True)
                
                if passed_conditions:
                    st.success("✅ Passed Conditions")
                    st.dataframe(pd.DataFrame(passed_conditions), use_container_width=True)
            
            # Full details
            with st.expander("🔍 Complete Quality Gate Details", expanded=False):
                st.json(result)
        else:
            st.json(result)
    
    def _render_security_analysis(self, result: Any):
        """Render security hotspots with risk analysis."""
        if isinstance(result, list) and result:
            df = pd.DataFrame(result)
            
            # Security summary
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total Hotspots", len(result))
            with col2:
                if "vulnerabilityProbability" in df.columns:
                    high_risk = len(df[df["vulnerabilityProbability"] == "HIGH"])
                    st.metric("High Risk", high_risk)
            with col3:
                if "status" in df.columns:
                    to_review = len(df[df["status"] == "TO_REVIEW"])
                    st.metric("To Review", to_review)
            
            # Risk distribution
            if "vulnerabilityProbability" in df.columns:
                risk_counts = df["vulnerabilityProbability"].value_counts()
                fig = px.pie(
                    values=risk_counts.values,
                    names=risk_counts.index,
                    title="Security Risk Distribution",
                    color_discrete_map={
                        "HIGH": "red",
                        "MEDIUM": "orange",
                        "LOW": "green"
                    }
                )
                st.plotly_chart(fig, use_container_width=True)
            
            # Security categories
            if "securityCategory" in df.columns:
                category_counts = df["securityCategory"].value_counts()
                fig = px.bar(
                    x=category_counts.values,
                    y=category_counts.index,
                    orientation="h",
                    title="Security Categories",
                    labels={"x": "Count", "y": "Category"}
                )
                st.plotly_chart(fig, use_container_width=True)
            
            # Hotspots table
            st.dataframe(
                df,
                use_container_width=True,
                column_config={
                    "key": st.column_config.TextColumn("Hotspot Key", width="small"),
                    "securityCategory": st.column_config.TextColumn("Category", width="medium"),
                    "vulnerabilityProbability": st.column_config.TextColumn("Risk", width="small"),
                    "status": st.column_config.TextColumn("Status", width="small"),
                    "component": st.column_config.TextColumn("Component", width="large")
                }
            )
        else:
            st.info("No security hotspots found")
    
    async def _process_user_message(self, message: str) -> Dict[str, Any]:
        """Process user message and execute appropriate MCP tools."""
        try:
            # Parse the message to identify intent and extract parameters
            intent, params = self._parse_user_intent(message)
            
            if not intent:
                return {
                    "error": "I couldn't understand your request. Try asking about projects, issues, or metrics.",
                    "summary": "Please be more specific about what you'd like to know."
                }
            
            # Execute the appropriate tool
            tool_result = await self._execute_tool(intent, params)
            
            return {
                "tool_name": intent,
                "tool_result": tool_result,
                "summary": self._generate_summary(intent, tool_result)
            }
            
        except Exception as e:
            return {
                "error": str(e),
                "summary": "An error occurred while processing your request."
            }
    
    def _parse_user_intent(self, message: str) -> Tuple[Optional[str], Dict[str, Any]]:
        """Parse user message to identify intent and extract parameters with enhanced NLP."""
        message_lower = message.lower()
        params = {}
        
        # Enhanced project key extraction patterns
        project_patterns = [
            r"(?:details|info|metrics|issues|quality|security|vulnerabilities|hotspots)\s+(?:for|of|in)\s+([a-zA-Z0-9_.-]+)",
            r"(?:for|of|about|in)\s+([a-zA-Z0-9_.-]+)(?:\s|$)",
            r"(?:project|key)[:\s]+([a-zA-Z0-9_.-]+)",
            r"([a-zA-Z0-9_.-]+)\s+(?:project)(?:\s|$)",
            r"(?:are\s+there|exist)\s+in\s+([a-zA-Z0-9_.-]+)",
            r"secure\s+in\s+([a-zA-Z0-9_.-]+)"
        ]
        
        def extract_project_key(text: str) -> Optional[str]:
            for pattern in project_patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    return match.group(1)
            return None
        
        # Enhanced intent patterns with synonyms and variations
        intent_patterns = {
            "list_projects": [
                r"(?:list|show|get|display|find)\s+(?:all\s+)?projects",
                r"what\s+projects\s+(?:do\s+)?(?:i\s+have|are\s+available)",
                r"show\s+me\s+(?:all\s+)?projects",
                r"projects\s+list",
                r"(?:all|available)\s+projects"
            ],
            "get_project_details": [
                r"(?:project\s+)?(?:details|info|information)\s+(?:for|of|about)",
                r"(?:tell\s+me\s+about|describe|show\s+details\s+of)",
                r"what\s+(?:is|about)\s+(?:project\s+)?",
                r"(?:details|info)\s+(?:for|of|about)",
                r"describe\s+(?:project\s+)?"
            ],
            "get_measures": [
                r"(?:metrics|measures|stats|statistics)\s+(?:for|of)",
                r"(?:code\s+)?quality\s+(?:metrics|measures|of)",
                r"(?:show|get|display)\s+(?:metrics|measures)",
                r"how\s+(?:good|bad)\s+is\s+(?:the\s+)?(?:code|quality)",
                r"coverage\s+(?:for|of)",
                r"technical\s+debt",
                r"(?:test\s+)?coverage",
                r"code\s+quality",
                r"maintainability"
            ],
            "search_issues": [
                r"(?:issues|bugs|problems|defects)\s+(?:in|for|of)",
                r"(?:show|find|get|list)\s+(?:issues|bugs|problems)",
                r"what\s+(?:issues|bugs|problems)\s+(?:are\s+there|exist)",
                r"code\s+(?:issues|problems|smells)",
                r"(?:bugs|problems)\s+(?:are\s+there|exist)\s+in",
                r"find\s+(?:all\s+)?(?:issues|bugs|problems)",
                r"code\s+smells"
            ],
            "get_quality_gate_status": [
                r"quality\s+gate\s+(?:status|result)",
                r"(?:did|has)\s+(?:the\s+)?(?:project\s+)?.*?(?:pass|fail)",
                r"gate\s+(?:status|result|check)",
                r"quality\s+(?:check|validation|gate)",
                r"check\s+quality\s+gate",
                r"(?:pass|fail)(?:ed)?\s+(?:quality\s+)?gate"
            ],
            "search_hotspots": [
                r"(?:security\s+)?(?:hotspots|vulnerabilities|issues)",
                r"security\s+(?:problems|issues|risks)",
                r"(?:find|show|get)\s+(?:security\s+)?(?:hotspots|vulnerabilities)",
                r"(?:is\s+(?:the\s+)?(?:code|project)\s+)?secure",
                r"(?:code|project)\s+secure\s+in",
                r"security\s+analysis",
                r"vulnerability\s+(?:scan|analysis)"
            ]
        }
        
        # Try to match intent patterns
        for intent, patterns in intent_patterns.items():
            for pattern in patterns:
                if re.search(pattern, message_lower):
                    # Extract project key if needed
                    project_key = extract_project_key(message)
                    if project_key and intent != "list_projects":
                        params["project_key"] = project_key
                    
                    # Extract additional parameters based on intent
                    if intent == "search_issues":
                        # Extract severity filter
                        severity_match = re.search(r"(?:severity|priority)[:\s]+(major|minor|critical|blocker|info)", message_lower)
                        if severity_match:
                            params["severities"] = [severity_match.group(1).upper()]
                        
                        # Extract type filter
                        type_match = re.search(r"(?:type|kind)[:\s]+(bug|vulnerability|code_smell)", message_lower)
                        if type_match:
                            params["types"] = [type_match.group(1).upper()]
                    
                    elif intent == "get_measures":
                        # Extract specific metrics
                        metric_keywords = {
                            "coverage": ["coverage", "test coverage"],
                            "bugs": ["bugs", "bug count"],
                            "vulnerabilities": ["vulnerabilities", "security"],
                            "code_smells": ["code smells", "maintainability"],
                            "duplicated_lines_density": ["duplication", "duplicated"],
                            "complexity": ["complexity", "cyclomatic"]
                        }
                        
                        requested_metrics = []
                        for metric_key, keywords in metric_keywords.items():
                            if any(keyword in message_lower for keyword in keywords):
                                requested_metrics.append(metric_key)
                        
                        if requested_metrics:
                            params["metric_keys"] = requested_metrics
                    
                    return intent, params
        
        # Fallback: try to extract project key for generic queries
        project_key = extract_project_key(message)
        if project_key:
            # If we have a project key but no clear intent, default to project details
            return "get_project_details", {"project_key": project_key}
        
        return None, {}
    
    async def _execute_tool(self, tool_name: str, params: Dict[str, Any]) -> Any:
        """Execute the specified MCP tool with parameters."""
        if not self.mcp_client:
            raise Exception("MCP client not connected")
        
        # Call the appropriate tool
        result = await self.mcp_client.call_tool(tool_name, params)
        
        if result.success:
            return result.data
        else:
            raise Exception(result.error or "Tool execution failed")
    
    def _generate_summary(self, tool_name: str, result: Any) -> str:
        """Generate a human-readable summary of the tool result."""
        if tool_name == "list_projects":
            if isinstance(result, list):
                return f"Found {len(result)} projects in your SonarQube instance."
            return "Retrieved project list."
        
        elif tool_name == "get_project_details":
            if isinstance(result, dict) and "name" in result:
                return f"Retrieved details for project: {result['name']}"
            return "Retrieved project details."
        
        elif tool_name == "get_measures":
            if isinstance(result, dict) and "measures" in result:
                return f"Retrieved {len(result['measures'])} metrics for the project."
            return "Retrieved project metrics."
        
        elif tool_name == "search_issues":
            if isinstance(result, list):
                return f"Found {len(result)} issues in the project."
            return "Retrieved project issues."
        
        elif tool_name == "get_quality_gate_status":
            if isinstance(result, dict) and "status" in result:
                status = result["status"]
                return f"Quality Gate status: {status}"
            return "Retrieved Quality Gate status."
        
        elif tool_name == "search_hotspots":
            if isinstance(result, list):
                return f"Found {len(result)} security hotspots in the project."
            return "Retrieved security hotspots."
        
        return "Tool executed successfully."
    
    def render_conversation_export(self):
        """Render enhanced conversation export and management functionality."""
        if st.session_state.chat_messages:
            st.subheader("💾 Conversation Management")
            
            # Enhanced conversation statistics
            total_messages = len(st.session_state.chat_messages)
            user_messages = len([m for m in st.session_state.chat_messages if m["role"] == "user"])
            assistant_messages = total_messages - user_messages
            
            # Calculate conversation duration
            if st.session_state.chat_messages:
                first_msg = st.session_state.chat_messages[0]
                last_msg = st.session_state.chat_messages[-1]
                duration = last_msg["timestamp"] - first_msg["timestamp"]
                duration_str = str(duration).split('.')[0]  # Remove microseconds
            else:
                duration_str = "0:00:00"
            
            # Count tool executions
            tool_executions = len([m for m in st.session_state.chat_messages 
                                 if m["role"] == "assistant" and isinstance(m.get("content"), dict) 
                                 and "tool_result" in m.get("content", {})])
            
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Total Messages", total_messages)
            with col2:
                st.metric("Your Messages", user_messages)
            with col3:
                st.metric("Tool Executions", tool_executions)
            with col4:
                st.metric("Duration", duration_str)
            
            # Export options with enhanced formats
            st.subheader("📤 Export Options")
            
            col1, col2 = st.columns(2)
            
            with col1:
                # JSON export with metadata
                conversation_data = {
                    "session_id": st.session_state.chat_session_id,
                    "export_timestamp": datetime.now().isoformat(),
                    "conversation_started": st.session_state.conversation_started.isoformat(),
                    "duration": duration_str,
                    "statistics": {
                        "total_messages": total_messages,
                        "user_messages": user_messages,
                        "assistant_messages": assistant_messages,
                        "tool_executions": tool_executions
                    },
                    "messages": [
                        {
                            "message_id": msg.get("message_id", f"msg_{i}"),
                            "role": msg["role"],
                            "content": msg["content"],
                            "timestamp": msg["timestamp"].isoformat() if isinstance(msg["timestamp"], datetime) else str(msg["timestamp"]),
                            "has_tool_result": isinstance(msg.get("content"), dict) and "tool_result" in msg.get("content", {})
                        }
                        for i, msg in enumerate(st.session_state.chat_messages)
                    ]
                }
                
                st.download_button(
                    label="📄 Export as JSON",
                    data=json.dumps(conversation_data, indent=2, default=str),
                    file_name=f"sonarqube_chat_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                    mime="application/json",
                    help="Export conversation in JSON format with metadata for analysis or backup"
                )
                
                # HTML export for sharing
                html_content = self._generate_html_export()
                st.download_button(
                    label="🌐 Export as HTML",
                    data=html_content,
                    file_name=f"sonarqube_chat_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html",
                    mime="text/html",
                    help="Export conversation as a styled HTML page for sharing"
                )
            
            with col2:
                # Markdown export
                markdown_content = self._generate_markdown_export()
                st.download_button(
                    label="📝 Export as Markdown",
                    data=markdown_content,
                    file_name=f"sonarqube_chat_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md",
                    mime="text/markdown",
                    help="Export conversation in readable Markdown format"
                )
                
                # CSV export (for analysis)
                csv_content = self._generate_csv_export()
                st.download_button(
                    label="📊 Export as CSV",
                    data=csv_content,
                    file_name=f"sonarqube_chat_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    mime="text/csv",
                    help="Export conversation data for analysis in spreadsheet applications"
                )
            
            # Advanced conversation management
            st.subheader("🔧 Conversation Actions")
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                if st.button("🗑️ Clear Conversation", help="Remove all messages from current conversation"):
                    if st.session_state.get("confirm_clear", False):
                        st.session_state.chat_messages = []
                        st.session_state.confirm_clear = False
                        st.success("Conversation cleared!")
                        st.rerun()
                    else:
                        st.session_state.confirm_clear = True
                        st.warning("Click again to confirm clearing the conversation")
                        st.rerun()
            
            with col2:
                if st.button("💾 Save to Session", help="Save conversation to browser session"):
                    session_key = f"saved_conversation_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                    conversation_backup = {
                        "messages": st.session_state.chat_messages.copy(),
                        "session_id": st.session_state.chat_session_id,
                        "saved_at": datetime.now().isoformat(),
                        "statistics": {
                            "total_messages": total_messages,
                            "duration": duration_str
                        }
                    }
                    st.session_state[session_key] = conversation_backup
                    st.success(f"Conversation saved!")
            
            with col3:
                # Show saved conversations with preview
                saved_conversations = [key for key in st.session_state.keys() if key.startswith("saved_conversation_")]
                if saved_conversations:
                    selected_conversation = st.selectbox(
                        "Load Saved Conversation",
                        options=[""] + saved_conversations,
                        format_func=lambda x: self._format_saved_conversation_name(x) if x else "Select..."
                    )
                    
                    if selected_conversation:
                        # Show preview
                        saved_data = st.session_state[selected_conversation]
                        if isinstance(saved_data, dict):
                            st.caption(f"💬 {saved_data.get('statistics', {}).get('total_messages', 0)} messages")
                            st.caption(f"📅 {saved_data.get('saved_at', 'Unknown date')[:16]}")
                        
                        if st.button("📂 Load", help="Load selected conversation"):
                            if isinstance(saved_data, dict):
                                st.session_state.chat_messages = saved_data.get("messages", [])
                            else:
                                st.session_state.chat_messages = saved_data  # Legacy format
                            st.success("Conversation loaded!")
                            st.rerun()
            
            # Enhanced conversation search and analysis
            st.subheader("🔍 Search & Analysis")
            
            col1, col2 = st.columns(2)
            
            with col1:
                search_term = st.text_input("Search in messages:", placeholder="Enter search term...")
                
                if search_term:
                    matching_messages = []
                    for i, message in enumerate(st.session_state.chat_messages):
                        content = str(message.get("content", ""))
                        if search_term.lower() in content.lower():
                            matching_messages.append((i, message))
                    
                    if matching_messages:
                        st.success(f"Found {len(matching_messages)} matching messages:")
                        for i, (msg_index, message) in enumerate(matching_messages):
                            with st.expander(f"Match {i+1} - {message['role'].title()} (Message #{msg_index+1})"):
                                if isinstance(message["content"], dict):
                                    st.json(message["content"])
                                else:
                                    st.write(message["content"])
                                st.caption(f"Timestamp: {message['timestamp']}")
                    else:
                        st.info("No matching messages found.")
            
            with col2:
                # Conversation insights
                st.write("**📊 Conversation Insights**")
                
                # Most used tools
                tool_usage = {}
                for message in st.session_state.chat_messages:
                    if (message["role"] == "assistant" and 
                        isinstance(message.get("content"), dict) and 
                        "tool_name" in message.get("content", {})):
                        tool_name = message["content"]["tool_name"]
                        tool_usage[tool_name] = tool_usage.get(tool_name, 0) + 1
                
                if tool_usage:
                    st.write("**Most Used Tools:**")
                    for tool, count in sorted(tool_usage.items(), key=lambda x: x[1], reverse=True)[:3]:
                        st.write(f"• {tool}: {count} times")
                
                # Message frequency over time
                if len(st.session_state.chat_messages) > 5:
                    st.write("**Activity Pattern:**")
                    timestamps = [msg["timestamp"] for msg in st.session_state.chat_messages]
                    time_diffs = [(timestamps[i] - timestamps[i-1]).total_seconds() 
                                for i in range(1, len(timestamps))]
                    avg_interval = sum(time_diffs) / len(time_diffs) if time_diffs else 0
                    st.write(f"• Average response time: {avg_interval:.1f}s")
        else:
            st.info("No conversation to export. Start chatting to see export options!")
    
    def _format_saved_conversation_name(self, key: str) -> str:
        """Format saved conversation name for display."""
        if not key:
            return "Select..."
        
        # Extract timestamp from key
        timestamp_part = key.replace("saved_conversation_", "")
        try:
            # Parse timestamp and format nicely
            dt = datetime.strptime(timestamp_part, "%Y%m%d_%H%M%S")
            return f"Conversation from {dt.strftime('%Y-%m-%d %H:%M')}"
        except ValueError:
            return key.replace("saved_conversation_", "Conversation ")
    
    def _generate_html_export(self) -> str:
        """Generate HTML format export of the conversation."""
        html_lines = [
            "<!DOCTYPE html>",
            "<html>",
            "<head>",
            "<meta charset='UTF-8'>",
            "<title>SonarQube Chat Conversation</title>",
            "<style>",
            "body { font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }",
            ".header { background: #f0f2f6; padding: 20px; border-radius: 10px; margin-bottom: 20px; }",
            ".message { margin: 10px 0; padding: 15px; border-radius: 10px; }",
            ".user { background: #e3f2fd; margin-left: 50px; }",
            ".assistant { background: #f5f5f5; margin-right: 50px; }",
            ".timestamp { font-size: 0.8em; color: #666; margin-top: 5px; }",
            ".tool-result { background: #fff3e0; border-left: 4px solid #ff9800; padding: 10px; margin: 10px 0; }",
            "pre { background: #f8f8f8; padding: 10px; border-radius: 5px; overflow-x: auto; }",
            "</style>",
            "</head>",
            "<body>",
            "<div class='header'>",
            f"<h1>🔍 SonarQube Chat Conversation</h1>",
            f"<p><strong>Export Date:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>",
            f"<p><strong>Total Messages:</strong> {len(st.session_state.chat_messages)}</p>",
            f"<p><strong>Session ID:</strong> {st.session_state.chat_session_id}</p>",
            "</div>"
        ]
        
        for i, message in enumerate(st.session_state.chat_messages, 1):
            role = message["role"]
            content = message.get("content", "")
            timestamp = message.get("timestamp", "")
            
            html_lines.append(f"<div class='message {role}'>")
            html_lines.append(f"<strong>{role.title()}:</strong><br>")
            
            if isinstance(content, dict):
                if "tool_result" in content:
                    html_lines.append(f"<div class='tool-result'>")
                    html_lines.append(f"<strong>Tool:</strong> {content.get('tool_name', 'Unknown')}<br>")
                    html_lines.append(f"<strong>Result:</strong><br>")
                    html_lines.append(f"<pre>{json.dumps(content['tool_result'], indent=2)}</pre>")
                    html_lines.append(f"</div>")
                else:
                    html_lines.append(f"<pre>{json.dumps(content, indent=2)}</pre>")
            else:
                html_lines.append(str(content).replace('\n', '<br>'))
            
            html_lines.append(f"<div class='timestamp'>🕒 {timestamp}</div>")
            html_lines.append("</div>")
        
        html_lines.extend([
            "</body>",
            "</html>"
        ])
        
        return "\n".join(html_lines)
    
    def _generate_markdown_export(self) -> str:
        """Generate Markdown format export of the conversation."""
        markdown_lines = [
            f"# SonarQube Chat Conversation",
            f"",
            f"**Export Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"**Total Messages:** {len(st.session_state.chat_messages)}",
            f"",
            f"---",
            f""
        ]
        
        for i, message in enumerate(st.session_state.chat_messages, 1):
            role = message["role"].title()
            content = str(message.get("content", ""))
            timestamp = message.get("timestamp", "")
            
            markdown_lines.extend([
                f"## Message {i} - {role}",
                f"",
                f"**Time:** {timestamp}",
                f"",
                content,
                f"",
                f"---",
                f""
            ])
        
        return "\n".join(markdown_lines)
    
    def _generate_csv_export(self) -> str:
        """Generate CSV format export of the conversation."""
        import io
        import csv
        
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Header
        writer.writerow(["Message_ID", "Role", "Content", "Timestamp", "Content_Length", "Has_Tool_Result"])
        
        # Data rows
        for i, message in enumerate(st.session_state.chat_messages, 1):
            content = str(message.get("content", ""))
            has_tool_result = "Yes" if isinstance(message.get("content"), dict) and "tool_result" in message.get("content", {}) else "No"
            
            writer.writerow([
                i,
                message["role"],
                content[:500] + "..." if len(content) > 500 else content,  # Truncate long content
                message.get("timestamp", ""),
                len(content),
                has_tool_result
            ])
        
        return output.getvalue()
    
    def render_command_suggestions(self):
        """Render intelligent command suggestions based on context and conversation history."""
        st.subheader("💡 Smart Suggestions")
        
        # Get recent projects from session state if available
        recent_projects = self._get_recent_projects()
        
        # Analyze conversation history for context-aware suggestions
        context_suggestions = self._generate_context_suggestions()
        
        # Base suggestions
        base_suggestions = [
            {
                "text": "List all projects",
                "description": "Show all available SonarQube projects",
                "category": "Discovery",
                "priority": 1
            },
            {
                "text": "Show me project overview",
                "description": "Get a general overview of projects and metrics",
                "category": "Overview",
                "priority": 1
            }
        ]
        
        # Project-specific suggestions if we have recent projects
        project_suggestions = []
        if recent_projects:
            for project in recent_projects[:3]:  # Limit to 3 recent projects
                project_key = project.get("key", "unknown")
                project_name = project.get("name", project_key)
                
                project_suggestions.extend([
                    {
                        "text": f"Get metrics for {project_key}",
                        "description": f"View quality metrics for {project_name}",
                        "category": "Metrics",
                        "priority": 2
                    },
                    {
                        "text": f"Show issues in {project_key}",
                        "description": f"List code issues in {project_name}",
                        "category": "Issues",
                        "priority": 2
                    },
                    {
                        "text": f"Check quality gate for {project_key}",
                        "description": f"View Quality Gate status for {project_name}",
                        "category": "Quality",
                        "priority": 2
                    },
                    {
                        "text": f"Find security issues in {project_key}",
                        "description": f"Analyze security hotspots in {project_name}",
                        "category": "Security",
                        "priority": 2
                    }
                ])
        
        # Generic project suggestions if no recent projects
        if not recent_projects:
            project_suggestions = [
                {
                    "text": "Get metrics for my-project",
                    "description": "Replace 'my-project' with your project key",
                    "category": "Metrics",
                    "priority": 3
                },
                {
                    "text": "Show issues in my-project",
                    "description": "Replace 'my-project' with your project key",
                    "category": "Issues",
                    "priority": 3
                },
                {
                    "text": "Check quality gate for my-project",
                    "description": "Replace 'my-project' with your project key",
                    "category": "Quality",
                    "priority": 3
                },
                {
                    "text": "Find security vulnerabilities in my-project",
                    "description": "Replace 'my-project' with your project key",
                    "category": "Security",
                    "priority": 3
                }
            ]
        
        # Advanced suggestions
        advanced_suggestions = [
            {
                "text": "Show me projects with failed quality gates",
                "description": "Find projects that need attention",
                "category": "Analysis",
                "priority": 4
            },
            {
                "text": "What are the most critical issues?",
                "description": "Find high-priority issues across projects",
                "category": "Analysis",
                "priority": 4
            },
            {
                "text": "Show coverage trends",
                "description": "Analyze test coverage over time",
                "category": "Trends",
                "priority": 4
            },
            {
                "text": "Compare project quality metrics",
                "description": "Side-by-side comparison of multiple projects",
                "category": "Analysis",
                "priority": 4
            }
        ]
        
        # Combine all suggestions and add context-aware ones
        all_suggestions = base_suggestions + project_suggestions + advanced_suggestions + context_suggestions
        
        # Sort by priority and group by category
        all_suggestions.sort(key=lambda x: x.get("priority", 5))
        categories = {}
        for suggestion in all_suggestions:
            category = suggestion["category"]
            if category not in categories:
                categories[category] = []
            categories[category].append(suggestion)
        
        # Show top priority suggestions first
        priority_suggestions = [s for s in all_suggestions if s.get("priority", 5) <= 2]
        if priority_suggestions:
            st.subheader("🎯 Recommended for You")
            cols = st.columns(min(3, len(priority_suggestions)))
            for i, suggestion in enumerate(priority_suggestions[:3]):
                with cols[i]:
                    if st.button(
                        f"🚀 {suggestion['text'][:30]}{'...' if len(suggestion['text']) > 30 else ''}",
                        key=f"priority_{i}",
                        help=suggestion['description'],
                        use_container_width=True
                    ):
                        self._execute_suggestion(suggestion['text'])
        
        # Render suggestions by category
        for category, suggestions in categories.items():
            with st.expander(f"📂 {category}", expanded=(category in ["Discovery", "Overview"])):
                for suggestion in suggestions:
                    col1, col2 = st.columns([3, 1])
                    
                    with col1:
                        st.write(f"**{suggestion['text']}**")
                        st.caption(suggestion['description'])
                    
                    with col2:
                        if st.button("Try", key=f"suggestion_{suggestion['text']}", help="Click to use this suggestion"):
                            self._execute_suggestion(suggestion['text'])
        
        # Natural language examples with interactive buttons
        st.subheader("🗣️ Natural Language Examples")
        
        example_queries = [
            "How is the code quality of my-project?",
            "Are there any critical bugs in the backend service?",
            "What's the test coverage for the frontend?",
            "Show me security issues that need attention",
            "Did the latest build pass the quality gate?",
            "Which projects have the most technical debt?"
        ]
        
        st.markdown("**Try these natural language queries:**")
        
        for i, query in enumerate(example_queries):
            col1, col2 = st.columns([4, 1])
            with col1:
                st.markdown(f"*{query}*")
            with col2:
                if st.button("Ask", key=f"example_{i}", help=f"Ask: {query}"):
                    self._execute_suggestion(query)
    
    def _generate_context_suggestions(self) -> List[Dict[str, Any]]:
        """Generate context-aware suggestions based on conversation history."""
        suggestions = []
        
        if not st.session_state.chat_messages:
            return suggestions
        
        # Analyze recent messages for patterns
        recent_messages = st.session_state.chat_messages[-5:]  # Last 5 messages
        mentioned_projects = set()
        mentioned_tools = set()
        
        for message in recent_messages:
            content = str(message.get("content", "")).lower()
            
            # Extract mentioned projects
            import re
            project_matches = re.findall(r'\b([a-zA-Z0-9_.-]+(?:-[a-zA-Z0-9_.-]+)*)\b', content)
            for match in project_matches:
                if len(match) > 3 and '-' in match:  # Likely a project key
                    mentioned_projects.add(match)
            
            # Track tool usage patterns
            if isinstance(message.get("content"), dict) and "tool_name" in message.get("content", {}):
                mentioned_tools.add(message["content"]["tool_name"])
        
        # Generate follow-up suggestions based on context
        for project in list(mentioned_projects)[:2]:  # Limit to 2 projects
            if "get_measures" not in mentioned_tools:
                suggestions.append({
                    "text": f"Show detailed metrics for {project}",
                    "description": f"Deep dive into quality metrics for {project}",
                    "category": "Follow-up",
                    "priority": 1
                })
            
            if "search_issues" not in mentioned_tools:
                suggestions.append({
                    "text": f"Find critical issues in {project}",
                    "description": f"Look for high-priority issues in {project}",
                    "category": "Follow-up",
                    "priority": 1
                })
        
        # Suggest complementary actions
        if "list_projects" in mentioned_tools and "get_measures" not in mentioned_tools:
            suggestions.append({
                "text": "Compare quality metrics across projects",
                "description": "Analyze quality differences between projects",
                "category": "Follow-up",
                "priority": 1
            })
        
        if "search_issues" in mentioned_tools and "search_hotspots" not in mentioned_tools:
            suggestions.append({
                "text": "Also check security vulnerabilities",
                "description": "Complete the analysis with security review",
                "category": "Follow-up",
                "priority": 1
            })
        
        return suggestions
    
    def _execute_suggestion(self, suggestion_text: str):
        """Execute a suggestion by adding it to chat messages."""
        user_message = {
            "role": "user",
            "content": suggestion_text,
            "timestamp": datetime.now(),
            "message_id": str(uuid.uuid4())
        }
        st.session_state.chat_messages.append(user_message)
        st.rerun()
    
    def _get_recent_projects(self) -> List[Dict[str, Any]]:
        """Get recently accessed projects from session state or tool history."""
        # Check if we have recent project data in session state
        if "recent_projects" in st.session_state:
            return st.session_state.recent_projects
        
        # Try to extract from tool history
        if hasattr(self, 'mcp_client') and self.mcp_client:
            history = self.mcp_client.get_tool_history(limit=20)
            projects = []
            
            for call in history:
                if call.get("tool_name") == "list_projects" and call.get("success"):
                    result = call.get("result", [])
                    if isinstance(result, list):
                        projects.extend(result[:5])  # Take first 5 projects
                        break
            
            return projects
        
        return []
    
    def _render_chat_input_with_suggestions(self):
        """Render enhanced chat input with auto-suggestions and context awareness."""
        # Dynamic placeholder based on conversation context
        placeholder_messages = [
            "Ask about your SonarQube projects...",
            "Try: 'List all projects'",
            "Try: 'Show metrics for my-project'",
            "Try: 'Find issues in my-app'",
            "Try: 'Check quality gate status'"
        ]
        
        # Add context-aware placeholders
        if st.session_state.chat_messages:
            last_message = st.session_state.chat_messages[-1]
            if last_message["role"] == "assistant" and isinstance(last_message.get("content"), dict):
                tool_name = last_message["content"].get("tool_name", "")
                if tool_name == "list_projects":
                    placeholder_messages.insert(0, "Try: 'Get metrics for [project-key]'")
                elif tool_name == "get_measures":
                    placeholder_messages.insert(0, "Try: 'Show issues in this project'")
                elif tool_name == "search_issues":
                    placeholder_messages.insert(0, "Try: 'Check security vulnerabilities'")
        
        import random
        placeholder = random.choice(placeholder_messages)
        
        # Chat input with enhanced features
        col1, col2 = st.columns([4, 1])
        
        with col1:
            user_input = st.chat_input(placeholder, key="main_chat_input")
        
        with col2:
            # Voice input simulation (placeholder for future enhancement)
            if st.button("🎤", help="Voice input (coming soon)", disabled=True):
                st.info("Voice input feature coming soon!")
        
        # Process user input
        if user_input:
            self._process_chat_input(user_input)
        
        # Show typing indicators and suggestions
        self._render_typing_suggestions()
    
    def _process_chat_input(self, user_input: str):
        """Process user input and generate response."""
        # Add user message to history
        user_message = {
            "role": "user",
            "content": user_input,
            "timestamp": datetime.now(),
            "message_id": str(uuid.uuid4())
        }
        st.session_state.chat_messages.append(user_message)
        
        # Process the message
        with st.spinner("🤔 Processing your request..."):
            response = asyncio.run(self._process_user_message(user_input))
            
            # Add assistant response to history
            assistant_message = {
                "role": "assistant",
                "content": response,
                "timestamp": datetime.now(),
                "message_id": str(uuid.uuid4())
            }
            st.session_state.chat_messages.append(assistant_message)
        
        st.rerun()
    
    def _render_typing_suggestions(self):
        """Render real-time typing suggestions and command hints."""
        # This would be enhanced with JavaScript for real-time suggestions
        # For now, show static helpful hints
        
        if not st.session_state.chat_messages:
            st.markdown("""
            <div style="background: #f0f2f6; padding: 10px; border-radius: 5px; margin-top: 10px;">
                <small>
                💡 <strong>Quick tips:</strong><br>
                • Type "list projects" to see all available projects<br>
                • Use project keys like "my-project" in your questions<br>
                • Ask about "metrics", "issues", "quality gates", or "security"<br>
                • Try natural language: "How is the quality of my-project?"
                </small>
            </div>
            """, unsafe_allow_html=True)
        
        # Show recent project keys for easy reference
        recent_projects = self._get_recent_projects()
        if recent_projects:
            project_keys = [p.get("key", "") for p in recent_projects[:5] if p.get("key")]
            if project_keys:
                st.markdown(f"""
                <div style="background: #e8f5e8; padding: 8px; border-radius: 5px; margin-top: 5px;">
                    <small>
                    🔑 <strong>Available project keys:</strong> {', '.join(project_keys)}
                    </small>
                </div>
                """, unsafe_allow_html=True)