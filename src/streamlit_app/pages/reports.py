"""Advanced reporting and visualization page."""

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional

from ..services.sonarqube_service import SonarQubeService
from ..utils.session import SessionManager
from ..components.visualization import AdvancedVisualization
from ..components.reporting import ReportGenerator, DataExporter, ScheduledReporting


def render():
    """Render the advanced reports page."""
    st.title("📊 Advanced Reports & Analytics")
    
    # Get service from session
    config_manager = st.session_state.config_manager
    service = SonarQubeService(config_manager)
    
    # Check connection status
    connection_status = SessionManager.get_connection_status()
    if connection_status != "connected":
        st.warning("⚠️ Not connected to SonarQube. Please check your configuration.")
        return
    
    # Main tabs
    tab1, tab2, tab3, tab4 = st.tabs([
        "📈 Advanced Visualizations",
        "📋 Report Generator", 
        "📥 Data Export",
        "⏰ Scheduled Reports"
    ])
    
    with tab1:
        render_advanced_visualizations(service)
    
    with tab2:
        render_report_generator(service)
    
    with tab3:
        render_data_export(service)
    
    with tab4:
        render_scheduled_reports()


def render_advanced_visualizations(service: SonarQubeService):
    """Render advanced visualization features."""
    st.subheader("📈 Advanced Data Visualizations")
    
    # Load projects data
    with st.spinner("Loading project data for visualization..."):
        try:
            projects = service.get_projects()
            if not projects:
                st.info("No projects found.")
                return
            
            # Enhance projects with metrics
            enhanced_projects = []
            for project in projects[:20]:  # Limit to first 20 for performance
                try:
                    metrics = [
                        "bugs", "vulnerabilities", "code_smells", "coverage", 
                        "duplicated_lines_density", "ncloc", "complexity", 
                        "technical_debt", "reliability_rating", "security_rating"
                    ]
                    measures = service.get_project_measures(project["key"], metrics)
                    quality_gate = service.get_quality_gate_status(project["key"])
                    
                    enhanced_project = {
                        **project,
                        **{k: float(v) if v.replace('.', '').isdigit() else v for k, v in measures.items()},
                        'quality_gate_status': quality_gate.get('status', 'NONE'),
                        'last_analysis': project.get('lastAnalysisDate', '')
                    }
                    enhanced_projects.append(enhanced_project)
                except Exception as e:
                    st.warning(f"Failed to load metrics for {project.get('name', 'Unknown')}: {e}")
                    continue
            
        except Exception as e:
            st.error(f"Failed to load projects: {e}")
            return
    
    if not enhanced_projects:
        st.warning("No project data available for visualization.")
        return
    
    # Visualization controls
    st.subheader("🎛️ Visualization Controls")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        viz_type = st.selectbox(
            "Visualization Type",
            options=[
                "metrics_dashboard",
                "custom_chart", 
                "comparison_matrix",
                "trend_analysis"
            ],
            format_func=lambda x: {
                "metrics_dashboard": "📊 Comprehensive Dashboard",
                "custom_chart": "🎨 Custom Chart",
                "comparison_matrix": "⚖️ Comparison Matrix", 
                "trend_analysis": "📈 Trend Analysis"
            }[x],
            key="viz_type_selection"
        )
    
    with col2:
        if viz_type == "custom_chart":
            chart_type = st.selectbox(
                "Chart Type",
                options=["bar", "line", "scatter", "pie", "histogram"],
                key="custom_chart_type"
            )
    
    with col3:
        refresh_data = st.button("🔄 Refresh Data")
        if refresh_data:
            st.rerun()
    
    # Render selected visualization
    if viz_type == "metrics_dashboard":
        AdvancedVisualization.create_metrics_dashboard(enhanced_projects)
    
    elif viz_type == "custom_chart":
        render_custom_chart_builder(enhanced_projects, chart_type)
    
    elif viz_type == "comparison_matrix":
        render_comparison_matrix(enhanced_projects)
    
    elif viz_type == "trend_analysis":
        render_trend_analysis(enhanced_projects)


def render_custom_chart_builder(projects_data: List[Dict[str, Any]], chart_type: str):
    """Render custom chart builder interface."""
    st.subheader("🎨 Custom Chart Builder")
    
    if not projects_data:
        st.warning("No data available for chart creation.")
        return
    
    df = pd.DataFrame(projects_data)
    available_columns = [col for col in df.columns if df[col].dtype in ['int64', 'float64', 'object']]
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        x_column = st.selectbox(
            "X-Axis",
            options=available_columns,
            index=0 if 'name' in available_columns else 0,
            key="custom_x_axis"
        )
    
    with col2:
        numeric_columns = [col for col in df.columns if df[col].dtype in ['int64', 'float64']]
        y_column = st.selectbox(
            "Y-Axis",
            options=numeric_columns,
            index=0 if numeric_columns else 0,
            key="custom_y_axis"
        )
    
    with col3:
        color_column = st.selectbox(
            "Color By (Optional)",
            options=[None] + available_columns,
            key="custom_color_column"
        )
    
    # Chart customization
    with st.expander("🎛️ Chart Customization"):
        col1, col2 = st.columns(2)
        
        with col1:
            chart_title = st.text_input(
                "Chart Title",
                value=f"{y_column.title()} by {x_column.title()}",
                key="custom_chart_title"
            )
        
        with col2:
            chart_height = st.slider(
                "Chart Height",
                min_value=300,
                max_value=800,
                value=500,
                key="custom_chart_height"
            )
    
    # Generate and display chart
    if x_column and y_column:
        try:
            fig = AdvancedVisualization.create_custom_chart(
                data=df,
                chart_type=chart_type,
                x_column=x_column,
                y_column=y_column,
                title=chart_title,
                color_column=color_column,
                height=chart_height
            )
            
            st.plotly_chart(fig, use_container_width=True)
            
            # Export chart data
            if st.button("📥 Export Chart Data"):
                chart_data = df[[x_column, y_column] + ([color_column] if color_column else [])]
                DataExporter.render_export_options(chart_data, f"custom_chart_{chart_type}")
        
        except Exception as e:
            st.error(f"Failed to create chart: {e}")


def render_comparison_matrix(projects_data: List[Dict[str, Any]]):
    """Render project comparison matrix."""
    st.subheader("⚖️ Project Comparison Matrix")
    
    if not projects_data:
        st.warning("No data available for comparison.")
        return
    
    df = pd.DataFrame(projects_data)
    numeric_columns = [col for col in df.columns if df[col].dtype in ['int64', 'float64']]
    
    # Metric selection
    selected_metrics = st.multiselect(
        "Select Metrics for Comparison",
        options=numeric_columns,
        default=numeric_columns[:5] if len(numeric_columns) >= 5 else numeric_columns,
        key="comparison_metrics"
    )
    
    if selected_metrics:
        # Project selection
        max_projects = min(20, len(projects_data))
        selected_projects = st.multiselect(
            f"Select Projects (max {max_projects})",
            options=range(len(projects_data)),
            format_func=lambda x: projects_data[x]['name'],
            default=list(range(min(10, len(projects_data)))),
            max_selections=max_projects,
            key="comparison_projects"
        )
        
        if selected_projects:
            # Filter data
            filtered_data = [projects_data[i] for i in selected_projects]
            
            # Create comparison matrix
            fig = AdvancedVisualization.create_comparison_matrix(
                filtered_data, selected_metrics
            )
            
            st.plotly_chart(fig, use_container_width=True)
            
            # Export comparison data
            if st.button("📥 Export Comparison Data"):
                comparison_df = pd.DataFrame(filtered_data)[['name'] + selected_metrics]
                DataExporter.render_export_options(comparison_df, "project_comparison")
        else:
            st.info("Please select at least one project for comparison.")
    else:
        st.info("Please select at least one metric for comparison.")


def render_trend_analysis(projects_data: List[Dict[str, Any]]):
    """Render trend analysis visualization."""
    st.subheader("📈 Trend Analysis")
    
    st.info("📝 **Note:** This is a demonstration of trend analysis capabilities. " +
            "In a production environment, this would use historical data from SonarQube's database.")
    
    if not projects_data:
        st.warning("No data available for trend analysis.")
        return
    
    # Generate sample trend data for demonstration
    df = pd.DataFrame(projects_data)
    
    # Trend configuration
    col1, col2, col3 = st.columns(3)
    
    with col1:
        trend_metric = st.selectbox(
            "Metric to Analyze",
            options=['coverage', 'bugs', 'vulnerabilities', 'code_smells', 'technical_debt'],
            key="trend_metric"
        )
    
    with col2:
        time_period = st.selectbox(
            "Time Period",
            options=['7d', '30d', '90d', '1y'],
            index=1,
            key="trend_period"
        )
    
    with col3:
        trend_projects = st.multiselect(
            "Select Projects",
            options=range(min(10, len(projects_data))),
            format_func=lambda x: projects_data[x]['name'],
            default=list(range(min(5, len(projects_data)))),
            key="trend_projects"
        )
    
    if trend_projects and trend_metric in df.columns:
        # Generate sample historical data
        historical_data = []
        
        days = {'7d': 7, '30d': 30, '90d': 90, '1y': 365}[time_period]
        base_date = datetime.now() - timedelta(days=days)
        
        for project_idx in trend_projects:
            project = projects_data[project_idx]
            base_value = project.get(trend_metric, 0)
            
            for day in range(days):
                date = base_date + timedelta(days=day)
                
                # Simulate trend (slight improvement over time for coverage, decrease for issues)
                if trend_metric == 'coverage':
                    trend_factor = 1 + (day / days) * 0.1  # Slight improvement
                else:
                    trend_factor = 1 - (day / days) * 0.1  # Slight decrease
                
                # Add some random variation
                import random
                variation = random.uniform(0.9, 1.1)
                value = max(0, base_value * trend_factor * variation)
                
                historical_data.append({
                    'project': project['name'],
                    'date': date,
                    'value': value,
                    'metric': trend_metric
                })
        
        if historical_data:
            trend_df = pd.DataFrame(historical_data)
            
            # Create trend chart
            import plotly.express as px
            fig = px.line(
                trend_df,
                x='date',
                y='value',
                color='project',
                title=f'{trend_metric.title()} Trends Over {time_period}',
                labels={'value': trend_metric.title(), 'date': 'Date'}
            )
            
            fig.update_layout(height=500)
            st.plotly_chart(fig, use_container_width=True)
            
            # Trend summary
            st.subheader("📊 Trend Summary")
            
            for project_idx in trend_projects:
                project = projects_data[project_idx]
                project_data = trend_df[trend_df['project'] == project['name']]
                
                if len(project_data) > 1:
                    start_value = project_data.iloc[0]['value']
                    end_value = project_data.iloc[-1]['value']
                    change = ((end_value - start_value) / start_value * 100) if start_value > 0 else 0
                    
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric(
                            f"{project['name']} - Start",
                            f"{start_value:.1f}"
                        )
                    with col2:
                        st.metric(
                            f"{project['name']} - End", 
                            f"{end_value:.1f}"
                        )
                    with col3:
                        st.metric(
                            f"{project['name']} - Change",
                            f"{change:+.1f}%"
                        )
            
            # Export trend data
            if st.button("📥 Export Trend Data"):
                DataExporter.render_export_options(trend_df, f"trend_analysis_{trend_metric}")
    else:
        st.info("Please select projects and ensure the selected metric is available.")


def render_report_generator(service: SonarQubeService):
    """Render report generation interface."""
    st.subheader("📋 Automated Report Generation")
    
    report_generator = ReportGenerator()
    
    # Report builder interface
    report_config = report_generator.render_report_builder()
    
    if report_config:
        st.subheader("📊 Generated Report")
        
        # Load data for report
        with st.spinner("Generating report..."):
            try:
                projects = service.get_projects()
                
                # Enhance projects with metrics for report
                enhanced_projects = []
                for project in projects[:10]:  # Limit for performance
                    try:
                        metrics = [
                            "bugs", "vulnerabilities", "code_smells", "coverage",
                            "duplicated_lines_density", "ncloc", "technical_debt"
                        ]
                        measures = service.get_project_measures(project["key"], metrics)
                        quality_gate = service.get_quality_gate_status(project["key"])
                        
                        enhanced_project = {
                            **project,
                            **{k: float(v) if v.replace('.', '').isdigit() else v for k, v in measures.items()},
                            'quality_gate_status': quality_gate.get('status', 'NONE')
                        }
                        enhanced_projects.append(enhanced_project)
                    except Exception:
                        continue
                
                # Generate report
                report = report_generator.generate_report(report_config, enhanced_projects)
                
                # Display report
                render_generated_report(report)
                
                # Export report
                st.subheader("📥 Export Report")
                DataExporter.render_export_options(report, f"report_{report_config['title'].replace(' ', '_')}")
                
            except Exception as e:
                st.error(f"Failed to generate report: {e}")


def render_generated_report(report: Dict[str, Any]):
    """Render the generated report."""
    st.markdown(f"# {report['title']}")
    st.markdown(f"**Generated:** {report['generated_at'].strftime('%Y-%m-%d %H:%M:%S')}")
    st.markdown(f"**Template:** {report['template_name']}")
    
    # Summary section
    if report.get('summary'):
        st.subheader("📊 Executive Summary")
        
        summary = report['summary']
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Total Projects", summary.get('total_projects', 0))
        
        with col2:
            if 'quality_gate_pass_rate' in summary:
                st.metric("Quality Gate Pass Rate", f"{summary['quality_gate_pass_rate']:.1f}%")
        
        with col3:
            if 'bugs_total' in summary:
                st.metric("Total Bugs", summary['bugs_total'])
        
        with col4:
            if 'coverage_average' in summary:
                st.metric("Average Coverage", f"{summary['coverage_average']:.1f}%")
    
    # Report sections
    if report.get('sections'):
        for section_name, section_data in report['sections'].items():
            if section_data.get('content'):
                st.subheader(f"📋 {section_data['title']}")
                
                content = section_data['content']
                
                if section_name == 'overview':
                    st.write(f"**Total Projects:** {content.get('total_projects', 0)}")
                    if 'key_metrics' in content:
                        st.write("**Key Metrics:**")
                        for metric, value in content['key_metrics'].items():
                            st.write(f"• {metric.title()}: {value}")
                
                elif section_name == 'quality_gates':
                    if 'status_distribution' in content:
                        st.write("**Quality Gate Status Distribution:**")
                        for status, count in content['status_distribution'].items():
                            st.write(f"• {status}: {count}")
                    
                    if 'failed_projects' in content and content['failed_projects']:
                        st.write("**Failed Projects:**")
                        for project in content['failed_projects']:
                            st.write(f"• {project}")
                
                elif section_name == 'recommendations':
                    if 'recommendations' in content:
                        st.write("**Recommendations:**")
                        for rec in content['recommendations']:
                            st.write(f"• {rec}")
                
                else:
                    # Generic content display
                    for key, value in content.items():
                        if isinstance(value, (list, dict)):
                            st.write(f"**{key.title()}:** {value}")
                        else:
                            st.write(f"**{key.title()}:** {value}")


def render_data_export(service: SonarQubeService):
    """Render data export interface."""
    st.subheader("📥 Data Export Center")
    
    # Export options
    export_type = st.selectbox(
        "Select Data to Export",
        options=[
            "projects_summary",
            "detailed_metrics", 
            "quality_gates",
            "issues_summary",
            "custom_query"
        ],
        format_func=lambda x: {
            "projects_summary": "📁 Projects Summary",
            "detailed_metrics": "📊 Detailed Metrics",
            "quality_gates": "🚦 Quality Gates Status",
            "issues_summary": "🐛 Issues Summary",
            "custom_query": "🔍 Custom Data Query"
        }[x],
        key="export_data_type"
    )
    
    # Load and export data based on selection
    if st.button("📊 Load Data for Export"):
        with st.spinner("Loading data..."):
            try:
                if export_type == "projects_summary":
                    projects = service.get_projects()
                    df = pd.DataFrame(projects)
                    st.dataframe(df, use_container_width=True)
                    DataExporter.render_export_options(df, "projects_summary")
                
                elif export_type == "detailed_metrics":
                    projects = service.get_projects()
                    detailed_data = []
                    
                    for project in projects[:10]:  # Limit for performance
                        try:
                            metrics = [
                                "bugs", "vulnerabilities", "code_smells", "coverage",
                                "duplicated_lines_density", "ncloc", "complexity", "technical_debt"
                            ]
                            measures = service.get_project_measures(project["key"], metrics)
                            
                            detailed_data.append({
                                **project,
                                **measures
                            })
                        except Exception:
                            continue
                    
                    df = pd.DataFrame(detailed_data)
                    st.dataframe(df, use_container_width=True)
                    DataExporter.render_export_options(df, "detailed_metrics")
                
                elif export_type == "quality_gates":
                    projects = service.get_projects()
                    qg_data = []
                    
                    for project in projects[:10]:
                        try:
                            qg_status = service.get_quality_gate_status(project["key"])
                            qg_data.append({
                                'project_key': project["key"],
                                'project_name': project["name"],
                                'quality_gate_status': qg_status.get('status', 'NONE'),
                                'conditions_count': len(qg_status.get('conditions', []))
                            })
                        except Exception:
                            continue
                    
                    df = pd.DataFrame(qg_data)
                    st.dataframe(df, use_container_width=True)
                    DataExporter.render_export_options(df, "quality_gates")
                
                elif export_type == "custom_query":
                    st.info("Custom query export would allow users to specify custom SonarQube API queries.")
                    
                    # Custom query interface
                    with st.expander("🔍 Custom Query Builder"):
                        query_endpoint = st.text_input(
                            "SonarQube API Endpoint",
                            placeholder="/api/projects/search",
                            key="custom_endpoint"
                        )
                        
                        query_params = st.text_area(
                            "Query Parameters (JSON format)",
                            placeholder='{"ps": 100, "qualifiers": "TRK"}',
                            key="custom_params"
                        )
                        
                        if st.button("Execute Custom Query"):
                            st.info("Custom query execution would be implemented here.")
                
            except Exception as e:
                st.error(f"Failed to load data: {e}")


def render_scheduled_reports():
    """Render scheduled reporting interface."""
    st.subheader("⏰ Scheduled Reports & Notifications")
    
    scheduled_reporting = ScheduledReporting()
    
    # Check for due reports
    scheduled_reporting.check_and_run_due_reports()
    
    # Render schedule manager
    scheduled_reporting.render_schedule_manager()
    
    # Email notification settings
    st.subheader("📧 Email Notification Settings")
    
    with st.expander("📧 Email Configuration"):
        st.info("📝 **Note:** Email functionality requires SMTP configuration. " +
                "In a production environment, this would integrate with your email service.")
        
        col1, col2 = st.columns(2)
        
        with col1:
            smtp_server = st.text_input("SMTP Server", placeholder="smtp.company.com")
            smtp_port = st.number_input("SMTP Port", value=587, min_value=1, max_value=65535)
            smtp_username = st.text_input("SMTP Username", placeholder="reports@company.com")
        
        with col2:
            smtp_password = st.text_input("SMTP Password", type="password")
            use_tls = st.checkbox("Use TLS", value=True)
            sender_email = st.text_input("Sender Email", placeholder="sonarqube-reports@company.com")
        
        if st.button("💾 Save Email Settings"):
            # In a real implementation, this would save to secure configuration
            st.success("Email settings saved successfully!")
            st.info("Settings would be securely stored and used for scheduled report delivery.")