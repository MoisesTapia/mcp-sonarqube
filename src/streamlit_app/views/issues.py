"""Issues page - Interactive issue management interface."""

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import plotly.express as px
import plotly.graph_objects as go

from streamlit_app.services.sonarqube_service import SonarQubeService
from streamlit_app.config.settings import ConfigManager
from streamlit_app.utils.session import SessionManager


class IssueManager:
    """Manager for issue operations."""
    
    def __init__(self, service: SonarQubeService):
        self.service = service
    
    async def search_issues_async(self, project_key: str = None, filters: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """Search issues with filters."""
        client = await self.service._get_client()
        if not client:
            return []
        
        try:
            params = {"ps": 500}  # Page size
            
            if project_key:
                params["componentKeys"] = project_key
            
            if filters:
                if filters.get("severities"):
                    params["severities"] = ",".join(filters["severities"])
                if filters.get("types"):
                    params["types"] = ",".join(filters["types"])
                if filters.get("statuses"):
                    params["statuses"] = ",".join(filters["statuses"])
                if filters.get("assignees"):
                    params["assignees"] = ",".join(filters["assignees"])
                if filters.get("rules"):
                    params["rules"] = ",".join(filters["rules"])
            
            response = await client.get("/issues/search", params=params)
            return response.get("issues", [])
        except Exception as e:
            st.error(f"Failed to search issues: {e}")
            return []
        finally:
            await client.close()
    
    def search_issues(self, project_key: str = None, filters: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """Search issues synchronously."""
        return self.service._run_async(self.search_issues_async(project_key, filters))
    
    async def update_issue_async(self, issue_key: str, updates: Dict[str, Any]) -> bool:
        """Update issue properties."""
        client = await self.service._get_client()
        if not client:
            return False
        
        try:
            params = {"issue": issue_key}
            params.update(updates)
            
            await client.post("/issues/assign" if "assignee" in updates else "/issues/do_transition", data=params)
            return True
        except Exception as e:
            st.error(f"Failed to update issue {issue_key}: {e}")
            return False
        finally:
            await client.close()
    
    def update_issue(self, issue_key: str, updates: Dict[str, Any]) -> bool:
        """Update issue synchronously."""
        return self.service._run_async(self.update_issue_async(issue_key, updates))
    
    async def add_comment_async(self, issue_key: str, comment: str) -> bool:
        """Add comment to issue."""
        client = await self.service._get_client()
        if not client:
            return False
        
        try:
            params = {"issue": issue_key, "text": comment}
            await client.post("/issues/add_comment", data=params)
            return True
        except Exception as e:
            st.error(f"Failed to add comment to issue {issue_key}: {e}")
            return False
        finally:
            await client.close()
    
    def add_comment(self, issue_key: str, comment: str) -> bool:
        """Add comment synchronously."""
        return self.service._run_async(self.add_comment_async(issue_key, comment))


def render_issue_filters() -> Dict[str, Any]:
    """Render issue filters sidebar."""
    st.sidebar.header("🔍 Filters")
    
    filters = {}
    
    # Project selection
    service = SonarQubeService(ConfigManager())
    projects = service.get_projects()
    project_options = ["All Projects"] + [f"{p['name']} ({p['key']})" for p in projects]
    selected_project = st.sidebar.selectbox("Project", project_options)
    
    if selected_project != "All Projects":
        project_key = selected_project.split("(")[-1].rstrip(")")
        filters["project_key"] = project_key
    
    # Severity filter
    severities = st.sidebar.multiselect(
        "Severity",
        ["BLOCKER", "CRITICAL", "MAJOR", "MINOR", "INFO"],
        default=["BLOCKER", "CRITICAL", "MAJOR"]
    )
    if severities:
        filters["severities"] = severities
    
    # Type filter
    types = st.sidebar.multiselect(
        "Type",
        ["BUG", "VULNERABILITY", "CODE_SMELL"],
        default=["BUG", "VULNERABILITY"]
    )
    if types:
        filters["types"] = types
    
    # Status filter
    statuses = st.sidebar.multiselect(
        "Status",
        ["OPEN", "CONFIRMED", "REOPENED", "RESOLVED", "CLOSED"],
        default=["OPEN", "CONFIRMED", "REOPENED"]
    )
    if statuses:
        filters["statuses"] = statuses
    
    return filters


def render_issue_workflow_visualization(issues: List[Dict[str, Any]]):
    """Render issue workflow visualization."""
    st.subheader("📊 Issue Workflow")
    
    if not issues:
        st.info("No issues to display workflow for.")
        return
    
    # Create workflow data
    workflow_data = {}
    for issue in issues:
        status = issue.get("status", "UNKNOWN")
        issue_type = issue.get("type", "UNKNOWN")
        key = f"{issue_type} - {status}"
        workflow_data[key] = workflow_data.get(key, 0) + 1
    
    # Create workflow chart
    if workflow_data:
        col1, col2 = st.columns(2)
        
        with col1:
            # Status distribution
            status_counts = {}
            for issue in issues:
                status = issue.get("status", "UNKNOWN")
                status_counts[status] = status_counts.get(status, 0) + 1
            
            fig_status = px.pie(
                values=list(status_counts.values()),
                names=list(status_counts.keys()),
                title="Issues by Status"
            )
            st.plotly_chart(fig_status, use_container_width=True)
        
        with col2:
            # Type distribution
            type_counts = {}
            for issue in issues:
                issue_type = issue.get("type", "UNKNOWN")
                type_counts[issue_type] = type_counts.get(issue_type, 0) + 1
            
            fig_type = px.pie(
                values=list(type_counts.values()),
                names=list(type_counts.keys()),
                title="Issues by Type"
            )
            st.plotly_chart(fig_type, use_container_width=True)


def render_bulk_operations(selected_issues: List[str]):
    """Render bulk operations interface."""
    if not selected_issues:
        return
    
    st.subheader(f"🔧 Bulk Operations ({len(selected_issues)} issues selected)")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("Assign Selected", type="secondary"):
            assignee = st.text_input("Assignee", key="bulk_assignee")
            if assignee:
                service = SonarQubeService(ConfigManager())
                issue_manager = IssueManager(service)
                
                success_count = 0
                for issue_key in selected_issues:
                    if issue_manager.update_issue(issue_key, {"assignee": assignee}):
                        success_count += 1
                
                st.success(f"Successfully assigned {success_count}/{len(selected_issues)} issues")
                st.rerun()
    
    with col2:
        if st.button("Change Status", type="secondary"):
            new_status = st.selectbox(
                "New Status",
                ["OPEN", "CONFIRMED", "RESOLVED", "CLOSED"],
                key="bulk_status"
            )
            if new_status:
                service = SonarQubeService(ConfigManager())
                issue_manager = IssueManager(service)
                
                success_count = 0
                for issue_key in selected_issues:
                    if issue_manager.update_issue(issue_key, {"transition": new_status.lower()}):
                        success_count += 1
                
                st.success(f"Successfully updated {success_count}/{len(selected_issues)} issues")
                st.rerun()
    
    with col3:
        if st.button("Add Comment", type="secondary"):
            comment = st.text_area("Comment", key="bulk_comment")
            if comment:
                service = SonarQubeService(ConfigManager())
                issue_manager = IssueManager(service)
                
                success_count = 0
                for issue_key in selected_issues:
                    if issue_manager.add_comment(issue_key, comment):
                        success_count += 1
                
                st.success(f"Successfully commented on {success_count}/{len(selected_issues)} issues")
                st.rerun()


def render_issue_table(issues: List[Dict[str, Any]]) -> List[str]:
    """Render interactive issue table with selection."""
    if not issues:
        st.info("No issues found with current filters.")
        return []
    
    # Convert to DataFrame for better display
    df_data = []
    for issue in issues:
        df_data.append({
            "Key": issue.get("key", ""),
            "Type": issue.get("type", ""),
            "Severity": issue.get("severity", ""),
            "Status": issue.get("status", ""),
            "Component": issue.get("component", "").split(":")[-1] if issue.get("component") else "",
            "Rule": issue.get("rule", ""),
            "Assignee": issue.get("assignee", "Unassigned"),
            "Created": issue.get("creationDate", "")[:10] if issue.get("creationDate") else "",
            "Message": issue.get("message", "")[:100] + "..." if len(issue.get("message", "")) > 100 else issue.get("message", "")
        })
    
    df = pd.DataFrame(df_data)
    
    # Add selection column
    df.insert(0, "Select", False)
    
    # Display editable dataframe
    edited_df = st.data_editor(
        df,
        column_config={
            "Select": st.column_config.CheckboxColumn(
                "Select",
                help="Select issues for bulk operations",
                default=False,
            ),
            "Key": st.column_config.TextColumn(
                "Issue Key",
                help="Unique issue identifier",
                width="small",
            ),
            "Type": st.column_config.SelectboxColumn(
                "Type",
                help="Issue type",
                options=["BUG", "VULNERABILITY", "CODE_SMELL"],
                width="small",
            ),
            "Severity": st.column_config.SelectboxColumn(
                "Severity",
                help="Issue severity",
                options=["BLOCKER", "CRITICAL", "MAJOR", "MINOR", "INFO"],
                width="small",
            ),
            "Status": st.column_config.SelectboxColumn(
                "Status",
                help="Issue status",
                options=["OPEN", "CONFIRMED", "REOPENED", "RESOLVED", "CLOSED"],
                width="small",
            ),
            "Assignee": st.column_config.TextColumn(
                "Assignee",
                help="Assigned user",
                width="small",
            ),
            "Message": st.column_config.TextColumn(
                "Description",
                help="Issue description",
                width="large",
            ),
        },
        hide_index=True,
        use_container_width=True,
    )
    
    # Get selected issues
    selected_issues = edited_df[edited_df["Select"]]["Key"].tolist()
    
    return selected_issues


def render_inline_commenting():
    """Render inline commenting system."""
    if "selected_issue_for_comment" in st.session_state:
        issue_key = st.session_state.selected_issue_for_comment
        
        st.subheader(f"💬 Add Comment to {issue_key}")
        
        comment = st.text_area(
            "Comment",
            placeholder="Enter your comment here...",
            height=100,
            key=f"comment_{issue_key}"
        )
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Add Comment", type="primary"):
                if comment.strip():
                    service = SonarQubeService(ConfigManager())
                    issue_manager = IssueManager(service)
                    
                    if issue_manager.add_comment(issue_key, comment):
                        st.success("Comment added successfully!")
                        del st.session_state.selected_issue_for_comment
                        st.rerun()
                    else:
                        st.error("Failed to add comment")
                else:
                    st.warning("Please enter a comment")
        
        with col2:
            if st.button("Cancel"):
                del st.session_state.selected_issue_for_comment
                st.rerun()


def render():
    """Render the issues page."""
    st.title("🐛 Issues Management")
    
    # Check configuration
    config_manager = ConfigManager()
    if not config_manager.is_configured():
        st.warning("Please configure SonarQube connection in the Configuration page first.")
        return
    
    # Initialize services
    service = SonarQubeService(config_manager)
    issue_manager = IssueManager(service)
    
    # Render filters
    filters = render_issue_filters()
    
    # Load issues
    with st.spinner("Loading issues..."):
        project_key = filters.get("project_key")
        filter_params = {k: v for k, v in filters.items() if k != "project_key"}
        issues = issue_manager.search_issues(project_key, filter_params)
    
    # Display metrics
    if issues:
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total Issues", len(issues))
        with col2:
            open_issues = len([i for i in issues if i.get("status") in ["OPEN", "CONFIRMED", "REOPENED"]])
            st.metric("Open Issues", open_issues)
        with col3:
            critical_issues = len([i for i in issues if i.get("severity") in ["BLOCKER", "CRITICAL"]])
            st.metric("Critical Issues", critical_issues)
        with col4:
            unassigned_issues = len([i for i in issues if not i.get("assignee")])
            st.metric("Unassigned", unassigned_issues)
    
    # Render workflow visualization
    render_issue_workflow_visualization(issues)
    
    # Render issue table
    st.subheader("📋 Issues")
    selected_issues = render_issue_table(issues)
    
    # Render bulk operations
    if selected_issues:
        render_bulk_operations(selected_issues)
    
    # Render inline commenting
    render_inline_commenting()
    
    # Add comment button for individual issues
    if issues and not selected_issues:
        st.subheader("💬 Quick Actions")
        issue_keys = [issue["key"] for issue in issues[:10]]  # Show first 10 for performance
        selected_issue = st.selectbox("Select issue to comment on:", [""] + issue_keys)
        
        if selected_issue:
            if st.button("Add Comment to Issue"):
                st.session_state.selected_issue_for_comment = selected_issue
                st.rerun()