"""Projects page for detailed project exploration."""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
from typing import Dict, Any, List, Optional

from streamlit_app.services.sonarqube_service import SonarQubeService
from streamlit_app.utils.session import SessionManager


def render():
    """Render the projects page."""
    st.title("📁 Project Explorer")
    
    # Get service from session
    config_manager = st.session_state.config_manager
    service = SonarQubeService(config_manager)
    
    # Check connection status
    connection_status = SessionManager.get_connection_status()
    if connection_status != "connected":
        st.warning("⚠️ Not connected to SonarQube. Please check your configuration.")
        return
    
    # Load projects
    with st.spinner("Loading projects..."):
        try:
            projects = service.get_projects()
        except Exception as e:
            st.error(f"Failed to load projects: {e}")
            return
    
    if not projects:
        st.info("No projects found.")
        return
    
    # Navigation breadcrumbs
    _render_breadcrumbs()
    
    # Project search and filtering
    selected_projects = _render_project_filters(projects)
    
    if not selected_projects:
        st.info("No projects match the current filters.")
        return
    
    # Main content area
    tab1, tab2, tab3 = st.tabs(["📊 Project Details", "⚖️ Compare Projects", "🔖 Bookmarks"])
    
    with tab1:
        _render_project_details(service, selected_projects)
    
    with tab2:
        _render_project_comparison(service, selected_projects)
    
    with tab3:
        _render_bookmarks(selected_projects)


def _render_breadcrumbs():
    """Render navigation breadcrumbs."""
    # Get current navigation state
    page_state = SessionManager.get_page_state("projects")
    selected_project = page_state.get("selected_project")
    
    # Breadcrumb navigation
    breadcrumbs = ["🏠 Dashboard", "📁 Projects"]
    
    if selected_project:
        breadcrumbs.append(f"📊 {selected_project}")
    
    st.markdown(" > ".join(breadcrumbs))


def _render_project_filters(projects: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Render project search and filtering controls."""
    st.subheader("🔍 Search & Filter")
    
    col1, col2, col3 = st.columns([2, 1, 1])
    
    with col1:
        search_term = st.text_input(
            "Search projects",
            placeholder="Enter project name or key...",
            key="project_search"
        )
    
    with col2:
        visibility_filter = st.selectbox(
            "Visibility",
            options=["All", "public", "private"],
            key="visibility_filter"
        )
    
    with col3:
        sort_by = st.selectbox(
            "Sort by",
            options=["Name", "Key", "Last Analysis"],
            key="project_sort"
        )
    
    # Apply filters
    filtered_projects = projects.copy()
    
    # Search filter
    if search_term:
        filtered_projects = [
            p for p in filtered_projects
            if search_term.lower() in p.get("name", "").lower() or 
               search_term.lower() in p.get("key", "").lower()
        ]
    
    # Visibility filter
    if visibility_filter != "All":
        filtered_projects = [
            p for p in filtered_projects
            if p.get("visibility", "public") == visibility_filter
        ]
    
    # Sort projects
    if sort_by == "Name":
        filtered_projects.sort(key=lambda x: x.get("name", "").lower())
    elif sort_by == "Key":
        filtered_projects.sort(key=lambda x: x.get("key", "").lower())
    elif sort_by == "Last Analysis":
        filtered_projects.sort(
            key=lambda x: x.get("lastAnalysisDate", ""),
            reverse=True
        )
    
    st.caption(f"Found {len(filtered_projects)} of {len(projects)} projects")
    
    return filtered_projects


def _render_project_details(service: SonarQubeService, projects: List[Dict[str, Any]]):
    """Render detailed project view."""
    if not projects:
        return
    
    # Project selection
    project_options = {p["key"]: f"{p['name']} ({p['key']})" for p in projects}
    
    # Get previously selected project or default to first
    page_state = SessionManager.get_page_state("projects")
    default_project = page_state.get("selected_project", projects[0]["key"])
    
    if default_project not in project_options:
        default_project = projects[0]["key"]
    
    selected_project_key = st.selectbox(
        "Select project for detailed view:",
        options=list(project_options.keys()),
        format_func=lambda x: project_options[x],
        index=list(project_options.keys()).index(default_project),
        key="selected_project_detail"
    )
    
    # Save selected project to session
    SessionManager.set_page_state("projects", {"selected_project": selected_project_key})
    
    # Get selected project data
    selected_project = next(p for p in projects if p["key"] == selected_project_key)
    
    # Project header
    col1, col2, col3 = st.columns([2, 1, 1])
    
    with col1:
        st.subheader(f"📊 {selected_project['name']}")
        st.code(selected_project["key"])
    
    with col2:
        visibility_icon = "🔒" if selected_project.get("visibility") == "private" else "🌐"
        st.metric("Visibility", f"{visibility_icon} {selected_project.get('visibility', 'public').title()}")
    
    with col3:
        last_analysis = selected_project.get("lastAnalysisDate")
        if last_analysis:
            st.metric("Last Analysis", last_analysis[:10])
        else:
            st.metric("Last Analysis", "Never")
    
    # Load comprehensive metrics
    with st.spinner("Loading project metrics..."):
        metrics = [
            "bugs", "vulnerabilities", "code_smells", "coverage", "duplicated_lines_density",
            "ncloc", "complexity", "cognitive_complexity", "technical_debt", "reliability_rating",
            "security_rating", "maintainability_rating", "sqale_rating"
        ]
        measures = service.get_project_measures(selected_project_key, metrics)
        quality_gate = service.get_quality_gate_status(selected_project_key)
    
    # Quality Gate Status
    st.subheader("🚦 Quality Gate Status")
    
    gate_status = quality_gate.get("status", "NONE")
    status_colors = {
        "OK": "success",
        "ERROR": "error", 
        "WARN": "warning",
        "NONE": "info"
    }
    
    status_icons = {
        "OK": "✅",
        "ERROR": "❌",
        "WARN": "⚠️", 
        "NONE": "⚪"
    }
    
    st.markdown(f"**Status:** {status_icons.get(gate_status, '❓')} {gate_status}")
    
    # Quality Gate conditions
    conditions = quality_gate.get("conditions", [])
    if conditions:
        st.subheader("📋 Quality Gate Conditions")
        
        for condition in conditions:
            col1, col2, col3, col4 = st.columns([2, 1, 1, 1])
            
            with col1:
                st.write(f"**{condition.get('metricKey', 'Unknown')}**")
            
            with col2:
                operator = condition.get("comparator", "")
                threshold = condition.get("errorThreshold", condition.get("warningThreshold", ""))
                st.write(f"{operator} {threshold}")
            
            with col3:
                actual_value = condition.get("actualValue", "N/A")
                st.write(f"**{actual_value}**")
            
            with col4:
                cond_status = condition.get("status", "OK")
                cond_icon = status_icons.get(cond_status, "❓")
                st.write(f"{cond_icon} {cond_status}")
    
    # Metrics Overview
    st.subheader("📈 Metrics Overview")
    
    # Reliability metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "Bugs",
            measures.get("bugs", "0"),
            help="Number of bug issues"
        )
        
        reliability_rating = measures.get("reliability_rating", "1")
        rating_labels = {"1": "A", "2": "B", "3": "C", "4": "D", "5": "E"}
        st.metric(
            "Reliability Rating",
            rating_labels.get(reliability_rating, reliability_rating),
            help="Reliability rating based on bugs"
        )
    
    with col2:
        st.metric(
            "Vulnerabilities",
            measures.get("vulnerabilities", "0"),
            help="Number of vulnerability issues"
        )
        
        security_rating = measures.get("security_rating", "1")
        st.metric(
            "Security Rating",
            rating_labels.get(security_rating, security_rating),
            help="Security rating based on vulnerabilities"
        )
    
    with col3:
        st.metric(
            "Code Smells",
            measures.get("code_smells", "0"),
            help="Number of maintainability issues"
        )
        
        maintainability_rating = measures.get("maintainability_rating", "1")
        st.metric(
            "Maintainability Rating",
            rating_labels.get(maintainability_rating, maintainability_rating),
            help="Maintainability rating based on technical debt"
        )
    
    with col4:
        coverage = measures.get("coverage", "0")
        st.metric(
            "Coverage",
            f"{coverage}%",
            help="Test coverage percentage"
        )
        
        duplicated_lines = measures.get("duplicated_lines_density", "0")
        st.metric(
            "Duplicated Lines",
            f"{duplicated_lines}%",
            help="Percentage of duplicated lines"
        )
    
    # Size and Complexity metrics
    st.subheader("📏 Size & Complexity")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        ncloc = measures.get("ncloc", "0")
        st.metric("Lines of Code", f"{int(ncloc):,}" if ncloc.isdigit() else ncloc)
    
    with col2:
        complexity = measures.get("complexity", "0")
        st.metric("Cyclomatic Complexity", complexity)
    
    with col3:
        cognitive_complexity = measures.get("cognitive_complexity", "0")
        st.metric("Cognitive Complexity", cognitive_complexity)
    
    with col4:
        technical_debt = measures.get("technical_debt", "0")
        if technical_debt.isdigit():
            hours = int(technical_debt)
            if hours >= 60:
                debt_display = f"{hours // 60}d {hours % 60}h"
            else:
                debt_display = f"{hours}h"
        else:
            debt_display = technical_debt
        st.metric("Technical Debt", debt_display)


def _render_project_comparison(service: SonarQubeService, projects: List[Dict[str, Any]]):
    """Render project comparison functionality."""
    st.subheader("⚖️ Compare Projects")
    
    if len(projects) < 2:
        st.info("Select at least 2 projects to enable comparison.")
        return
    
    # Project selection for comparison
    project_options = {p["key"]: f"{p['name']} ({p['key']})" for p in projects}
    
    selected_projects = st.multiselect(
        "Select projects to compare (max 5):",
        options=list(project_options.keys()),
        format_func=lambda x: project_options[x],
        max_selections=5,
        key="comparison_projects"
    )
    
    if len(selected_projects) < 2:
        st.info("Please select at least 2 projects for comparison.")
        return
    
    # Load metrics for selected projects
    with st.spinner("Loading comparison data..."):
        comparison_data = []
        
        for project_key in selected_projects:
            project = next(p for p in projects if p["key"] == project_key)
            
            metrics = ["bugs", "vulnerabilities", "code_smells", "coverage", "ncloc", "technical_debt"]
            measures = service.get_project_measures(project_key, metrics)
            quality_gate = service.get_quality_gate_status(project_key)
            
            comparison_data.append({
                "Project": project["name"],
                "Key": project_key,
                "Bugs": int(measures.get("bugs", "0")),
                "Vulnerabilities": int(measures.get("vulnerabilities", "0")),
                "Code Smells": int(measures.get("code_smells", "0")),
                "Coverage": float(measures.get("coverage", "0")),
                "Lines of Code": int(measures.get("ncloc", "0")),
                "Technical Debt (hours)": int(measures.get("technical_debt", "0")),
                "Quality Gate": quality_gate.get("status", "NONE")
            })
    
    if not comparison_data:
        st.error("Failed to load comparison data.")
        return
    
    # Comparison table
    comparison_df = pd.DataFrame(comparison_data)
    
    st.subheader("📊 Comparison Table")
    st.dataframe(
        comparison_df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Coverage": st.column_config.NumberColumn(
                "Coverage (%)",
                format="%.1f%%"
            ),
            "Lines of Code": st.column_config.NumberColumn(
                "Lines of Code",
                format="%d"
            ),
            "Technical Debt (hours)": st.column_config.NumberColumn(
                "Technical Debt (hours)",
                format="%d"
            )
        }
    )
    
    # Comparison charts
    st.subheader("📈 Visual Comparison")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Issues comparison
        fig_issues = px.bar(
            comparison_df,
            x="Project",
            y=["Bugs", "Vulnerabilities", "Code Smells"],
            title="Issues Comparison",
            barmode="group"
        )
        fig_issues.update_layout(xaxis_tickangle=-45)
        st.plotly_chart(fig_issues, use_container_width=True)
    
    with col2:
        # Coverage and size comparison
        fig_metrics = go.Figure()
        
        fig_metrics.add_trace(go.Bar(
            name="Coverage (%)",
            x=comparison_df["Project"],
            y=comparison_df["Coverage"],
            yaxis="y",
            offsetgroup=1
        ))
        
        fig_metrics.add_trace(go.Bar(
            name="Lines of Code (thousands)",
            x=comparison_df["Project"],
            y=comparison_df["Lines of Code"] / 1000,
            yaxis="y2",
            offsetgroup=2
        ))
        
        fig_metrics.update_layout(
            title="Coverage vs Size",
            xaxis=dict(tickangle=-45),
            yaxis=dict(title="Coverage (%)", side="left"),
            yaxis2=dict(title="Lines of Code (thousands)", side="right", overlaying="y"),
            barmode="group"
        )
        
        st.plotly_chart(fig_metrics, use_container_width=True)


def _render_bookmarks(projects: List[Dict[str, Any]]):
    """Render project bookmarks functionality."""
    st.subheader("🔖 Project Bookmarks")
    
    # Get bookmarked projects from session
    page_state = SessionManager.get_page_state("projects")
    bookmarked_projects = page_state.get("bookmarks", [])
    
    # Bookmark management
    col1, col2 = st.columns([2, 1])
    
    with col1:
        project_options = {p["key"]: f"{p['name']} ({p['key']})" for p in projects}
        
        project_to_bookmark = st.selectbox(
            "Select project to bookmark:",
            options=list(project_options.keys()),
            format_func=lambda x: project_options[x],
            key="bookmark_selection"
        )
    
    with col2:
        st.write("")  # Spacing
        st.write("")  # Spacing
        
        if st.button("➕ Add Bookmark", use_container_width=True):
            if project_to_bookmark not in bookmarked_projects:
                bookmarked_projects.append(project_to_bookmark)
                SessionManager.set_page_state("projects", {
                    **page_state,
                    "bookmarks": bookmarked_projects
                })
                st.success(f"Added {project_options[project_to_bookmark]} to bookmarks")
                st.rerun()
            else:
                st.warning("Project is already bookmarked")
    
    # Display bookmarked projects
    if bookmarked_projects:
        st.subheader("📌 Your Bookmarks")
        
        for i, project_key in enumerate(bookmarked_projects):
            project = next((p for p in projects if p["key"] == project_key), None)
            
            if project:
                col1, col2, col3 = st.columns([3, 1, 1])
                
                with col1:
                    st.write(f"**{project['name']}**")
                    st.caption(project["key"])
                
                with col2:
                    if st.button("👁️ View", key=f"view_bookmark_{i}"):
                        SessionManager.set_page_state("projects", {
                            **page_state,
                            "selected_project": project_key
                        })
                        st.rerun()
                
                with col3:
                    if st.button("🗑️ Remove", key=f"remove_bookmark_{i}"):
                        bookmarked_projects.remove(project_key)
                        SessionManager.set_page_state("projects", {
                            **page_state,
                            "bookmarks": bookmarked_projects
                        })
                        st.rerun()
            else:
                # Project no longer exists, remove from bookmarks
                bookmarked_projects.remove(project_key)
                SessionManager.set_page_state("projects", {
                    **page_state,
                    "bookmarks": bookmarked_projects
                })
    else:
        st.info("No bookmarked projects. Add some projects to your bookmarks for quick access.")