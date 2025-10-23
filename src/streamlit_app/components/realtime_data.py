"""Real-time data synchronization components for Streamlit."""

from typing import Dict, Any, List, Optional, Callable
from datetime import datetime, timedelta
import streamlit as st

from streamlit_app.services.mcp_integration import get_mcp_integration_service, SyncedData
from streamlit_app.utils.error_handler import get_error_handler, ErrorCategory
from streamlit_app.utils.session import SessionManager


class RealtimeDataComponent:
    """Component for real-time data synchronization and display."""
    
    def __init__(self, page_id: str):
        """Initialize real-time data component."""
        self.page_id = page_id
        self.integration_service = get_mcp_integration_service()
        self.error_handler = get_error_handler()
    
    def sync_and_display_projects(self, 
                                 container: st.container = None,
                                 search: str = None,
                                 organization: str = None,
                                 auto_refresh: bool = True,
                                 refresh_interval: int = 30) -> Optional[List[Dict[str, Any]]]:
        """Sync and display projects data with real-time updates."""
        if container is None:
            container = st.container()
        
        # Subscribe to projects data
        data_key = self.integration_service.sync_projects_data(
            self.page_id, search=search, organization=organization
        )
        
        with container:
            # Show sync status
            self._render_sync_status(data_key, auto_refresh)
            
            # Get synced data
            projects_data = self.integration_service.get_data_value(data_key)
            
            if self.integration_service.has_data_error(data_key):
                error_msg = self.integration_service.get_data_error(data_key)
                st.error(f"❌ Failed to load projects: {error_msg}")
                return None
            
            if projects_data is None:
                st.info("🔄 Loading projects...")
                return None
            
            # Extract projects from response
            if isinstance(projects_data, dict):
                projects = projects_data.get("components", []) or projects_data.get("projects", [])
            else:
                projects = projects_data if isinstance(projects_data, list) else []
            
            if not projects:
                st.info("No projects found")
                return []
            
            # Display projects
            st.success(f"✅ Found {len(projects)} projects")
            
            # Create projects table
            project_rows = []
            for project in projects:
                project_rows.append({
                    "Key": project.get("key", ""),
                    "Name": project.get("name", ""),
                    "Visibility": project.get("visibility", ""),
                    "Last Analysis": project.get("lastAnalysisDate", "Never")
                })
            
            if project_rows:
                st.dataframe(project_rows, use_container_width=True)
            
            return projects
    
    def sync_and_display_project_metrics(self,
                                       project_key: str,
                                       metrics: List[str] = None,
                                       container: st.container = None,
                                       auto_refresh: bool = True) -> Optional[Dict[str, Any]]:
        """Sync and display project metrics with real-time updates."""
        if container is None:
            container = st.container()
        
        if metrics is None:
            metrics = ["bugs", "vulnerabilities", "code_smells", "coverage", "duplicated_lines_density"]
        
        # Subscribe to project measures
        data_key = self.integration_service.sync_project_measures(
            self.page_id, project_key, metrics
        )
        
        with container:
            # Show sync status
            self._render_sync_status(data_key, auto_refresh, f"Metrics for {project_key}")
            
            # Get synced data
            measures_data = self.integration_service.get_data_value(data_key)
            
            if self.integration_service.has_data_error(data_key):
                error_msg = self.integration_service.get_data_error(data_key)
                st.error(f"❌ Failed to load metrics: {error_msg}")
                return None
            
            if measures_data is None:
                st.info("🔄 Loading metrics...")
                return None
            
            # Extract measures from response
            if isinstance(measures_data, dict) and "component" in measures_data:
                measures = measures_data["component"].get("measures", [])
            else:
                measures = measures_data if isinstance(measures_data, list) else []
            
            # Convert to dict for easier access
            metrics_dict = {}
            for measure in measures:
                metrics_dict[measure.get("metric", "")] = measure.get("value", "0")
            
            if not metrics_dict:
                st.info("No metrics available")
                return {}
            
            # Display metrics in columns
            cols = st.columns(len(metrics_dict))
            for i, (metric, value) in enumerate(metrics_dict.items()):
                with cols[i]:
                    # Format metric name
                    display_name = metric.replace("_", " ").title()
                    
                    # Determine metric color based on type
                    if metric in ["bugs", "vulnerabilities", "code_smells"]:
                        color = "red" if int(value) > 0 else "green"
                    elif metric == "coverage":
                        coverage_val = float(value) if value else 0
                        color = "green" if coverage_val >= 80 else "orange" if coverage_val >= 60 else "red"
                    else:
                        color = "blue"
                    
                    st.metric(
                        label=display_name,
                        value=value,
                        delta=None
                    )
            
            return metrics_dict
    
    def sync_and_display_quality_gate(self,
                                    project_key: str,
                                    container: st.container = None,
                                    auto_refresh: bool = True) -> Optional[Dict[str, Any]]:
        """Sync and display quality gate status with real-time updates."""
        if container is None:
            container = st.container()
        
        # Subscribe to quality gate status
        data_key = self.integration_service.sync_quality_gate_status(self.page_id, project_key)
        
        with container:
            # Show sync status
            self._render_sync_status(data_key, auto_refresh, f"Quality Gate for {project_key}")
            
            # Get synced data
            qg_data = self.integration_service.get_data_value(data_key)
            
            if self.integration_service.has_data_error(data_key):
                error_msg = self.integration_service.get_data_error(data_key)
                st.error(f"❌ Failed to load quality gate: {error_msg}")
                return None
            
            if qg_data is None:
                st.info("🔄 Loading quality gate status...")
                return None
            
            # Extract quality gate status
            if isinstance(qg_data, dict) and "projectStatus" in qg_data:
                qg_status = qg_data["projectStatus"]
            else:
                qg_status = qg_data
            
            if not qg_status:
                st.info("No quality gate information available")
                return {}
            
            # Display quality gate status
            status = qg_status.get("status", "NONE")
            
            if status == "OK":
                st.success(f"✅ Quality Gate: PASSED")
            elif status == "ERROR":
                st.error(f"❌ Quality Gate: FAILED")
            elif status == "WARN":
                st.warning(f"⚠️ Quality Gate: WARNING")
            else:
                st.info(f"ℹ️ Quality Gate: {status}")
            
            # Show conditions if available
            conditions = qg_status.get("conditions", [])
            if conditions:
                st.subheader("Quality Gate Conditions")
                for condition in conditions:
                    metric_key = condition.get("metricKey", "")
                    status = condition.get("status", "")
                    actual_value = condition.get("actualValue", "")
                    error_threshold = condition.get("errorThreshold", "")
                    
                    if status == "OK":
                        st.success(f"✅ {metric_key}: {actual_value}")
                    elif status == "ERROR":
                        st.error(f"❌ {metric_key}: {actual_value} (threshold: {error_threshold})")
                    else:
                        st.warning(f"⚠️ {metric_key}: {actual_value}")
            
            return qg_status
    
    def sync_and_display_issues(self,
                              project_keys: List[str] = None,
                              severities: List[str] = None,
                              types: List[str] = None,
                              container: st.container = None,
                              auto_refresh: bool = True,
                              limit: int = 50) -> Optional[List[Dict[str, Any]]]:
        """Sync and display issues with real-time updates."""
        if container is None:
            container = st.container()
        
        # Subscribe to issues data
        filters = {}
        if severities:
            filters["severities"] = severities
        if types:
            filters["types"] = types
        
        data_key = self.integration_service.sync_issues_data(
            self.page_id, project_keys=project_keys, **filters
        )
        
        with container:
            # Show sync status
            self._render_sync_status(data_key, auto_refresh, "Issues")
            
            # Get synced data
            issues_data = self.integration_service.get_data_value(data_key)
            
            if self.integration_service.has_data_error(data_key):
                error_msg = self.integration_service.get_data_error(data_key)
                st.error(f"❌ Failed to load issues: {error_msg}")
                return None
            
            if issues_data is None:
                st.info("🔄 Loading issues...")
                return None
            
            # Extract issues from response
            if isinstance(issues_data, dict):
                issues = issues_data.get("issues", [])
                total = issues_data.get("total", len(issues))
            else:
                issues = issues_data if isinstance(issues_data, list) else []
                total = len(issues)
            
            if not issues:
                st.info("No issues found")
                return []
            
            # Display issues summary
            st.success(f"✅ Found {total} issues (showing {min(len(issues), limit)})")
            
            # Group issues by severity
            severity_counts = {}
            type_counts = {}
            
            for issue in issues[:limit]:
                severity = issue.get("severity", "UNKNOWN")
                issue_type = issue.get("type", "UNKNOWN")
                
                severity_counts[severity] = severity_counts.get(severity, 0) + 1
                type_counts[issue_type] = type_counts.get(issue_type, 0) + 1
            
            # Display summary metrics
            col1, col2 = st.columns(2)
            
            with col1:
                st.subheader("By Severity")
                for severity, count in sorted(severity_counts.items()):
                    if severity == "BLOCKER":
                        st.error(f"🚨 {severity}: {count}")
                    elif severity == "CRITICAL":
                        st.error(f"🔴 {severity}: {count}")
                    elif severity == "MAJOR":
                        st.warning(f"🟠 {severity}: {count}")
                    elif severity == "MINOR":
                        st.info(f"🟡 {severity}: {count}")
                    else:
                        st.write(f"⚪ {severity}: {count}")
            
            with col2:
                st.subheader("By Type")
                for issue_type, count in sorted(type_counts.items()):
                    if issue_type == "BUG":
                        st.error(f"🐛 {issue_type}: {count}")
                    elif issue_type == "VULNERABILITY":
                        st.error(f"🔒 {issue_type}: {count}")
                    elif issue_type == "CODE_SMELL":
                        st.warning(f"👃 {issue_type}: {count}")
                    else:
                        st.write(f"📋 {issue_type}: {count}")
            
            # Display issues table
            if st.checkbox("Show detailed issues", key=f"{self.page_id}_show_issues"):
                issue_rows = []
                for issue in issues[:limit]:
                    issue_rows.append({
                        "Key": issue.get("key", ""),
                        "Type": issue.get("type", ""),
                        "Severity": issue.get("severity", ""),
                        "Status": issue.get("status", ""),
                        "Component": issue.get("component", ""),
                        "Message": issue.get("message", "")[:100] + "..." if len(issue.get("message", "")) > 100 else issue.get("message", "")
                    })
                
                if issue_rows:
                    st.dataframe(issue_rows, use_container_width=True)
            
            return issues[:limit]
    
    def _render_sync_status(self, data_key: str, auto_refresh: bool, title: str = "Data") -> None:
        """Render synchronization status indicator."""
        synced_data = self.integration_service.get_synced_data(data_key)
        
        if not synced_data:
            return
        
        # Create status indicator
        col1, col2, col3 = st.columns([3, 1, 1])
        
        with col1:
            if synced_data.error:
                st.error(f"❌ {title} sync error")
            elif synced_data.data is None:
                st.info(f"🔄 Loading {title.lower()}...")
            else:
                age = (datetime.now() - synced_data.last_updated).total_seconds()
                if age < 60:
                    st.success(f"✅ {title} (updated {int(age)}s ago)")
                else:
                    st.warning(f"⚠️ {title} (updated {int(age/60)}m ago)")
        
        with col2:
            if st.button("🔄", key=f"refresh_{data_key}", help="Refresh data"):
                self.integration_service.refresh_data(data_key)
                st.rerun()
        
        with col3:
            if auto_refresh:
                st.success("🔄 Auto")
            else:
                st.info("⏸️ Manual")
    
    def cleanup(self) -> None:
        """Clean up subscriptions for this page."""
        self.integration_service.unsubscribe_from_data(self.page_id)


def create_realtime_component(page_id: str) -> RealtimeDataComponent:
    """Create a real-time data component for a specific page."""
    return RealtimeDataComponent(page_id)


def render_sync_controls(page_id: str, container: st.container = None) -> None:
    """Render synchronization controls for a page."""
    if container is None:
        container = st.container()
    
    integration_service = get_mcp_integration_service()
    
    with container:
        st.subheader("🔄 Data Synchronization")
        
        # Sync status
        sync_status = integration_service.get_sync_status()
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if sync_status["status"] == "running":
                st.success("✅ Auto-sync: ON")
            else:
                st.error("❌ Auto-sync: OFF")
        
        with col2:
            if sync_status["last_sync"]:
                last_sync = datetime.fromisoformat(sync_status["last_sync"])
                age = (datetime.now() - last_sync).total_seconds()
                st.info(f"🕐 Last sync: {int(age)}s ago")
            else:
                st.info("🕐 Never synced")
        
        with col3:
            st.info(f"📊 {sync_status['subscriptions_count']} subscriptions")
        
        # Control buttons
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            if st.button("▶️ Start Sync", key=f"{page_id}_start_sync"):
                integration_service.start_sync()
                st.success("Sync started!")
                st.rerun()
        
        with col2:
            if st.button("⏸️ Stop Sync", key=f"{page_id}_stop_sync"):
                integration_service.stop_sync()
                st.success("Sync stopped!")
                st.rerun()
        
        with col3:
            if st.button("🔄 Refresh All", key=f"{page_id}_refresh_all"):
                integration_service.refresh_all_data()
                st.success("Refreshing all data...")
                st.rerun()
        
        with col4:
            if st.button("🧹 Clear Cache", key=f"{page_id}_clear_cache"):
                integration_service.unsubscribe_from_data(page_id)
                st.success("Cache cleared!")
                st.rerun()
        
        # Sync configuration
        with st.expander("⚙️ Sync Configuration"):
            current_interval = sync_status.get("sync_interval", 30)
            new_interval = st.slider(
                "Sync Interval (seconds)",
                min_value=10,
                max_value=300,
                value=current_interval,
                key=f"{page_id}_sync_interval"
            )
            
            auto_refresh = st.checkbox(
                "Auto Refresh",
                value=sync_status.get("auto_refresh", True),
                key=f"{page_id}_auto_refresh"
            )
            
            if st.button("💾 Save Config", key=f"{page_id}_save_config"):
                integration_service.configure_sync(
                    sync_interval=new_interval,
                    auto_refresh=auto_refresh
                )
                st.success("Configuration saved!")
                st.rerun()
        
        # Error display
        errors = sync_status.get("errors", [])
        if errors:
            with st.expander(f"⚠️ Sync Errors ({len(errors)})"):
                for error in errors[-5:]:  # Show last 5 errors
                    st.error(f"{error['timestamp']}: {error['error']}")
                
                if st.button("🧹 Clear Errors", key=f"{page_id}_clear_errors"):
                    integration_service.clear_sync_errors()
                    st.rerun()