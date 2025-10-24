"""Dashboard page for SonarQube overview."""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
from typing import Dict, Any, List

from streamlit_app.services.sonarqube_service import SonarQubeService
from streamlit_app.utils.session import SessionManager
from streamlit_app.components import create_realtime_component, render_sync_controls


def render():
    """Render the dashboard page."""
    st.title("📊 SonarQube Dashboard")
    
    # Get service from session
    config_manager = st.session_state.config_manager
    service = SonarQubeService(config_manager)
    
    # Check connection status
    connection_status = SessionManager.get_connection_status()
    if connection_status != "connected":
        st.warning("⚠️ Not connected to SonarQube. Please check your configuration.")
        return
    
    # Create real-time data component
    realtime_component = create_realtime_component("dashboard")
    
    # Dashboard controls with MCP integration
    col1, col2, col3, col4 = st.columns([2, 1, 1, 1])
    
    with col1:
        st.subheader("Overview")
    
    with col2:
        if st.button("🔄 Refresh Data", width="stretch"):
            SessionManager.clear_cache()
            st.rerun()
    
    with col3:
        auto_refresh = st.checkbox("Auto-refresh", value=True)
    
    with col4:
        use_mcp = st.checkbox("Use MCP", value=True, help="Use MCP for real-time data")
    
    # Show sync controls in expander
    with st.expander("🔄 Data Synchronization Controls"):
        render_sync_controls("dashboard")
    
    # Load dashboard data - use MCP if enabled, otherwise fallback to direct service
    if use_mcp and "mcp_client" in st.session_state:
        # Use real-time MCP data
        projects_container = st.container()
        projects = realtime_component.sync_and_display_projects(
            container=projects_container,
            auto_refresh=auto_refresh
        )
        
        if projects is None:
            return
        
        # Convert to dashboard format for compatibility
        dashboard_data = {
            "total_projects": len(projects),
            "projects_with_issues": 0,
            "quality_gates_passed": 0,
            "quality_gates_failed": 0,
            "projects": []
        }
        
        # Process projects to get summary data
        for project in projects:
            project_key = project.get("key", "")
            if not project_key:
                continue
            
            # Get metrics for each project using MCP
            metrics_data = realtime_component.sync_and_display_project_metrics(
                project_key, 
                container=st.empty(),  # Hidden container
                auto_refresh=False
            )
            
            qg_data = realtime_component.sync_and_display_quality_gate(
                project_key,
                container=st.empty(),  # Hidden container  
                auto_refresh=False
            )
            
            # Extract values
            bugs = int(metrics_data.get("bugs", 0)) if metrics_data else 0
            vulnerabilities = int(metrics_data.get("vulnerabilities", 0)) if metrics_data else 0
            code_smells = int(metrics_data.get("code_smells", 0)) if metrics_data else 0
            coverage = metrics_data.get("coverage", "0") if metrics_data else "0"
            duplicated_lines = metrics_data.get("duplicated_lines_density", "0") if metrics_data else "0"
            
            qg_status = qg_data.get("status", "NONE") if qg_data else "NONE"
            
            # Update counters
            if bugs > 0 or vulnerabilities > 0 or code_smells > 0:
                dashboard_data["projects_with_issues"] += 1
            
            if qg_status == "OK":
                dashboard_data["quality_gates_passed"] += 1
            elif qg_status in ["ERROR", "WARN"]:
                dashboard_data["quality_gates_failed"] += 1
            
            # Add to projects list
            dashboard_data["projects"].append({
                "key": project_key,
                "name": project.get("name", project_key),
                "last_analysis": project.get("lastAnalysisDate"),
                "quality_gate_status": qg_status,
                "bugs": bugs,
                "vulnerabilities": vulnerabilities,
                "code_smells": code_smells,
                "coverage": coverage,
                "duplicated_lines": duplicated_lines
            })
    else:
        # Fallback to direct service call
        with st.spinner("Loading dashboard data..."):
            try:
                dashboard_data = service.get_dashboard_summary()
            except Exception as e:
                st.error(f"Failed to load dashboard data: {e}")
                return
        
        if not dashboard_data["projects"]:
            st.info("No projects found or no data available.")
            return
    
    # Key metrics row
    st.subheader("📈 Key Metrics")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "Total Projects",
            dashboard_data["total_projects"],
            help="Total number of projects in SonarQube"
        )
    
    with col2:
        st.metric(
            "Projects with Issues",
            dashboard_data["projects_with_issues"],
            delta=f"{dashboard_data['projects_with_issues'] / max(dashboard_data['total_projects'], 1) * 100:.1f}%",
            help="Projects that have bugs, vulnerabilities, or code smells"
        )
    
    with col3:
        st.metric(
            "Quality Gates Passed",
            dashboard_data["quality_gates_passed"],
            delta=f"{dashboard_data['quality_gates_passed'] / max(len(dashboard_data['projects']), 1) * 100:.1f}%",
            delta_color="normal",
            help="Projects that passed their quality gate"
        )
    
    with col4:
        st.metric(
            "Quality Gates Failed",
            dashboard_data["quality_gates_failed"],
            delta=f"{dashboard_data['quality_gates_failed'] / max(len(dashboard_data['projects']), 1) * 100:.1f}%",
            delta_color="inverse",
            help="Projects that failed their quality gate"
        )
    
    st.divider()
    
    # Quality Gate Status Overview
    st.subheader("🚦 Quality Gate Status")
    
    # Create quality gate status chart
    projects_df = pd.DataFrame(dashboard_data["projects"])
    
    if not projects_df.empty:
        col1, col2 = st.columns([1, 1])
        
        with col1:
            # Quality gate status pie chart
            status_counts = projects_df["quality_gate_status"].value_counts()
            
            colors = {
                "OK": "#52c41a",
                "ERROR": "#ff4d4f", 
                "WARN": "#faad14",
                "NONE": "#d9d9d9"
            }
            
            fig_pie = px.pie(
                values=status_counts.values,
                names=status_counts.index,
                title="Quality Gate Status Distribution",
                color=status_counts.index,
                color_discrete_map=colors
            )
            fig_pie.update_traces(textposition='inside', textinfo='percent+label')
            st.plotly_chart(fig_pie, width="stretch")
        
        with col2:
            # Issues overview bar chart
            issues_data = {
                "Bugs": projects_df["bugs"].sum(),
                "Vulnerabilities": projects_df["vulnerabilities"].sum(),
                "Code Smells": projects_df["code_smells"].sum()
            }
            
            fig_bar = px.bar(
                x=list(issues_data.keys()),
                y=list(issues_data.values()),
                title="Total Issues Across All Projects",
                color=list(issues_data.keys()),
                color_discrete_map={
                    "Bugs": "#ff4d4f",
                    "Vulnerabilities": "#fa541c", 
                    "Code Smells": "#faad14"
                }
            )
            fig_bar.update_layout(showlegend=False)
            st.plotly_chart(fig_bar, width="stretch")
    
    # Failed Quality Gates Alert
    failed_projects = projects_df[projects_df["quality_gate_status"].isin(["ERROR", "WARN"])]
    
    if not failed_projects.empty:
        st.subheader("🚨 Quality Gate Alerts")
        
        for _, project in failed_projects.iterrows():
            status_color = "🔴" if project["quality_gate_status"] == "ERROR" else "🟡"
            
            with st.expander(f"{status_color} {project['name']} - {project['quality_gate_status']}", expanded=False):
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.metric("Bugs", project["bugs"])
                    st.metric("Vulnerabilities", project["vulnerabilities"])
                
                with col2:
                    st.metric("Code Smells", project["code_smells"])
                    st.metric("Coverage", f"{project['coverage']}%")
                
                with col3:
                    st.metric("Duplicated Lines", f"{project['duplicated_lines']}%")
                    if project["last_analysis"]:
                        st.write(f"**Last Analysis:** {project['last_analysis'][:10]}")
    
    st.divider()
    
    # Project List with Filtering
    st.subheader("📁 Projects Overview")
    
    # Filters
    col1, col2, col3 = st.columns(3)
    
    with col1:
        status_filter = st.selectbox(
            "Filter by Quality Gate Status",
            options=["All"] + list(projects_df["quality_gate_status"].unique()),
            key="dashboard_status_filter"
        )
    
    with col2:
        issues_filter = st.selectbox(
            "Filter by Issues",
            options=["All", "With Issues", "No Issues"],
            key="dashboard_issues_filter"
        )
    
    with col3:
        sort_by = st.selectbox(
            "Sort by",
            options=["Name", "Bugs", "Vulnerabilities", "Code Smells", "Coverage"],
            key="dashboard_sort_by"
        )
    
    # Apply filters
    filtered_df = projects_df.copy()
    
    if status_filter != "All":
        filtered_df = filtered_df[filtered_df["quality_gate_status"] == status_filter]
    
    if issues_filter == "With Issues":
        filtered_df = filtered_df[
            (filtered_df["bugs"] > 0) | 
            (filtered_df["vulnerabilities"] > 0) | 
            (filtered_df["code_smells"] > 0)
        ]
    elif issues_filter == "No Issues":
        filtered_df = filtered_df[
            (filtered_df["bugs"] == 0) & 
            (filtered_df["vulnerabilities"] == 0) & 
            (filtered_df["code_smells"] == 0)
        ]
    
    # Sort data
    sort_column_map = {
        "Name": "name",
        "Bugs": "bugs",
        "Vulnerabilities": "vulnerabilities", 
        "Code Smells": "code_smells",
        "Coverage": "coverage"
    }
    
    sort_column = sort_column_map[sort_by]
    ascending = sort_by == "Name"  # Only name should be ascending
    filtered_df = filtered_df.sort_values(sort_column, ascending=ascending)
    
    # Display projects table
    if not filtered_df.empty:
        # Format the dataframe for display
        display_df = filtered_df.copy()
        display_df["Quality Gate"] = display_df["quality_gate_status"].apply(_format_quality_gate_status)
        display_df["Coverage"] = display_df["coverage"].apply(lambda x: f"{x}%")
        display_df["Duplicated Lines"] = display_df["duplicated_lines"].apply(lambda x: f"{x}%")
        
        # Select columns for display
        display_columns = [
            "name", "Quality Gate", "bugs", "vulnerabilities", 
            "code_smells", "Coverage", "Duplicated Lines"
        ]
        
        display_df = display_df[display_columns]
        display_df.columns = [
            "Project Name", "Quality Gate", "Bugs", "Vulnerabilities",
            "Code Smells", "Coverage", "Duplicated Lines"
        ]
        
        st.dataframe(
            display_df,
            width="stretch",
            hide_index=True,
            column_config={
                "Quality Gate": st.column_config.TextColumn(
                    "Quality Gate",
                    help="Quality Gate status"
                ),
                "Bugs": st.column_config.NumberColumn(
                    "Bugs",
                    help="Number of bugs",
                    format="%d"
                ),
                "Vulnerabilities": st.column_config.NumberColumn(
                    "Vulnerabilities", 
                    help="Number of vulnerabilities",
                    format="%d"
                ),
                "Code Smells": st.column_config.NumberColumn(
                    "Code Smells",
                    help="Number of code smells",
                    format="%d"
                )
            }
        )
        
        st.caption(f"Showing {len(filtered_df)} of {len(projects_df)} projects")
    else:
        st.info("No projects match the selected filters.")
    
    # Auto-refresh functionality
    if auto_refresh:
        # Check if data is older than 5 minutes
        if not SessionManager.is_connection_recent(max_age_minutes=5):
            st.rerun()


def _format_quality_gate_status(status: str) -> str:
    """Format quality gate status with emoji."""
    status_map = {
        "OK": "✅ PASSED",
        "ERROR": "❌ FAILED", 
        "WARN": "⚠️ WARNING",
        "NONE": "⚪ NONE"
    }
    return status_map.get(status, status)
