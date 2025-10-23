"""Advanced reporting system with export capabilities."""

import streamlit as st
import pandas as pd
import json
import io
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass, asdict
from pathlib import Path
import base64


@dataclass
class ReportTemplate:
    """Report template configuration."""
    name: str
    description: str
    sections: List[str]
    metrics: List[str]
    chart_types: List[str]
    filters: Dict[str, Any]
    schedule: Optional[str] = None


class ReportGenerator:
    """Advanced report generation with customizable templates."""
    
    DEFAULT_TEMPLATES = {
        'executive_summary': ReportTemplate(
            name='Executive Summary',
            description='High-level overview for management',
            sections=['overview', 'quality_gates', 'key_metrics', 'recommendations'],
            metrics=['total_projects', 'quality_gate_pass_rate', 'total_issues', 'coverage_average'],
            chart_types=['pie', 'bar', 'trend'],
            filters={'status': 'all', 'time_range': '30d'}
        ),
        'technical_report': ReportTemplate(
            name='Technical Report',
            description='Detailed technical analysis for developers',
            sections=['project_details', 'issue_analysis', 'code_quality', 'security', 'technical_debt'],
            metrics=['bugs', 'vulnerabilities', 'code_smells', 'coverage', 'duplicated_lines', 'technical_debt'],
            chart_types=['bar', 'scatter', 'heatmap', 'histogram'],
            filters={'status': 'all', 'time_range': '7d'}
        ),
        'security_report': ReportTemplate(
            name='Security Report',
            description='Security-focused analysis',
            sections=['security_overview', 'vulnerabilities', 'hotspots', 'security_trends'],
            metrics=['vulnerabilities', 'security_rating', 'security_hotspots'],
            chart_types=['pie', 'bar', 'trend'],
            filters={'security_focus': True, 'time_range': '14d'}
        ),
        'quality_gate_report': ReportTemplate(
            name='Quality Gate Report',
            description='Quality gate status and trends',
            sections=['quality_gate_overview', 'failed_projects', 'conditions_analysis', 'trends'],
            metrics=['quality_gate_status', 'quality_gate_conditions'],
            chart_types=['pie', 'heatmap', 'trend'],
            filters={'quality_gate_focus': True, 'time_range': '30d'}
        )
    }
    
    def __init__(self):
        self.templates = self.DEFAULT_TEMPLATES.copy()
    
    def render_report_builder(self) -> Optional[Dict[str, Any]]:
        """Render the report builder interface."""
        st.subheader("📋 Report Builder")
        
        # Template selection
        col1, col2 = st.columns([2, 1])
        
        with col1:
            template_options = {
                key: f"{template.name} - {template.description}"
                for key, template in self.templates.items()
            }
            
            selected_template_key = st.selectbox(
                "Select Report Template",
                options=list(template_options.keys()),
                format_func=lambda x: template_options[x],
                key="report_template_selection"
            )
        
        with col2:
            if st.button("🔧 Customize Template"):
                st.session_state.customize_template = True
        
        selected_template = self.templates[selected_template_key]
        
        # Template customization
        if st.session_state.get('customize_template', False):
            selected_template = self._render_template_customization(selected_template)
        
        # Report configuration
        st.subheader("⚙️ Report Configuration")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            report_title = st.text_input(
                "Report Title",
                value=f"{selected_template.name} - {datetime.now().strftime('%Y-%m-%d')}",
                key="report_title"
            )
        
        with col2:
            time_range = st.selectbox(
                "Time Range",
                options=['7d', '14d', '30d', '90d', 'all'],
                index=2,
                key="report_time_range"
            )
        
        with col3:
            include_charts = st.checkbox(
                "Include Charts",
                value=True,
                key="report_include_charts"
            )
        
        # Additional filters
        with st.expander("🔍 Additional Filters"):
            col1, col2 = st.columns(2)
            
            with col1:
                project_filter = st.multiselect(
                    "Filter Projects",
                    options=[],  # Would be populated with actual project names
                    key="report_project_filter"
                )
            
            with col2:
                quality_gate_filter = st.selectbox(
                    "Quality Gate Status",
                    options=['All', 'Passed', 'Failed', 'Warning'],
                    key="report_qg_filter"
                )
        
        # Generate report button
        if st.button("📊 Generate Report", type="primary"):
            report_config = {
                'template': selected_template,
                'title': report_title,
                'time_range': time_range,
                'include_charts': include_charts,
                'filters': {
                    'projects': project_filter,
                    'quality_gate': quality_gate_filter
                },
                'generated_at': datetime.now()
            }
            return report_config
        
        return None
    
    def _render_template_customization(self, template: ReportTemplate) -> ReportTemplate:
        """Render template customization interface."""
        st.subheader("🔧 Customize Template")
        
        with st.expander("Template Customization", expanded=True):
            col1, col2 = st.columns(2)
            
            with col1:
                # Sections selection
                st.write("**Report Sections**")
                available_sections = [
                    'overview', 'quality_gates', 'key_metrics', 'project_details',
                    'issue_analysis', 'code_quality', 'security', 'technical_debt',
                    'recommendations', 'trends'
                ]
                
                selected_sections = st.multiselect(
                    "Select sections to include",
                    options=available_sections,
                    default=template.sections,
                    key="template_sections"
                )
            
            with col2:
                # Metrics selection
                st.write("**Metrics to Include**")
                available_metrics = [
                    'bugs', 'vulnerabilities', 'code_smells', 'coverage',
                    'duplicated_lines', 'technical_debt', 'ncloc', 'complexity'
                ]
                
                selected_metrics = st.multiselect(
                    "Select metrics to include",
                    options=available_metrics,
                    default=template.metrics,
                    key="template_metrics"
                )
            
            # Chart types
            st.write("**Chart Types**")
            available_charts = ['bar', 'line', 'pie', 'scatter', 'heatmap', 'histogram']
            selected_charts = st.multiselect(
                "Select chart types",
                options=available_charts,
                default=template.chart_types,
                key="template_charts"
            )
            
            # Update template
            template.sections = selected_sections
            template.metrics = selected_metrics
            template.chart_types = selected_charts
        
        return template
    
    def generate_report(
        self,
        config: Dict[str, Any],
        projects_data: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Generate a report based on configuration and data."""
        template = config['template']
        
        report = {
            'title': config['title'],
            'generated_at': config['generated_at'],
            'template_name': template.name,
            'time_range': config['time_range'],
            'summary': {},
            'sections': {},
            'charts': [],
            'data': projects_data
        }
        
        # Generate summary
        report['summary'] = self._generate_summary(projects_data, template.metrics)
        
        # Generate sections
        for section in template.sections:
            report['sections'][section] = self._generate_section(
                section, projects_data, template.metrics
            )
        
        # Generate charts if requested
        if config['include_charts']:
            report['charts'] = self._generate_charts(
                projects_data, template.chart_types, template.metrics
            )
        
        return report
    
    def _generate_summary(
        self,
        projects_data: List[Dict[str, Any]],
        metrics: List[str]
    ) -> Dict[str, Any]:
        """Generate report summary."""
        if not projects_data:
            return {}
        
        df = pd.DataFrame(projects_data)
        
        summary = {
            'total_projects': len(df),
            'projects_analyzed': len(df[df.get('last_analysis', pd.Series()).notna()]) if 'last_analysis' in df.columns else 0,
        }
        
        # Quality gate summary
        if 'quality_gate_status' in df.columns:
            qg_counts = df['quality_gate_status'].value_counts()
            summary['quality_gates'] = {
                'passed': qg_counts.get('OK', 0),
                'failed': qg_counts.get('ERROR', 0),
                'warning': qg_counts.get('WARN', 0),
                'none': qg_counts.get('NONE', 0)
            }
            summary['quality_gate_pass_rate'] = (
                qg_counts.get('OK', 0) / len(df) * 100 if len(df) > 0 else 0
            )
        
        # Metrics summary
        for metric in metrics:
            if metric in df.columns:
                if df[metric].dtype in ['int64', 'float64']:
                    summary[f'{metric}_total'] = df[metric].sum()
                    summary[f'{metric}_average'] = df[metric].mean()
                    summary[f'{metric}_max'] = df[metric].max()
        
        return summary
    
    def _generate_section(
        self,
        section: str,
        projects_data: List[Dict[str, Any]],
        metrics: List[str]
    ) -> Dict[str, Any]:
        """Generate a specific report section."""
        if not projects_data:
            return {}
        
        df = pd.DataFrame(projects_data)
        
        section_data = {
            'title': section.replace('_', ' ').title(),
            'content': {}
        }
        
        if section == 'overview':
            section_data['content'] = {
                'total_projects': len(df),
                'key_metrics': {
                    metric: df[metric].sum() if metric in df.columns and df[metric].dtype in ['int64', 'float64'] else 'N/A'
                    for metric in metrics[:5]  # Top 5 metrics
                }
            }
        
        elif section == 'quality_gates':
            if 'quality_gate_status' in df.columns:
                section_data['content'] = {
                    'status_distribution': df['quality_gate_status'].value_counts().to_dict(),
                    'failed_projects': df[df['quality_gate_status'].isin(['ERROR', 'WARN'])]['name'].tolist()
                }
        
        elif section == 'issue_analysis':
            issue_metrics = [m for m in ['bugs', 'vulnerabilities', 'code_smells'] if m in df.columns]
            if issue_metrics:
                section_data['content'] = {
                    'total_issues': df[issue_metrics].sum().to_dict(),
                    'top_problematic_projects': df.nlargest(5, issue_metrics[0])['name'].tolist() if issue_metrics else []
                }
        
        elif section == 'security':
            security_metrics = [m for m in ['vulnerabilities', 'security_rating'] if m in df.columns]
            if security_metrics:
                section_data['content'] = {
                    'security_summary': df[security_metrics].describe().to_dict() if security_metrics else {},
                    'high_risk_projects': df[df.get('vulnerabilities', 0) > 0]['name'].tolist()
                }
        
        elif section == 'technical_debt':
            if 'technical_debt' in df.columns:
                section_data['content'] = {
                    'total_debt_hours': df['technical_debt'].sum(),
                    'average_debt_hours': df['technical_debt'].mean(),
                    'highest_debt_projects': df.nlargest(5, 'technical_debt')[['name', 'technical_debt']].to_dict('records')
                }
        
        elif section == 'recommendations':
            recommendations = []
            
            # Quality gate recommendations
            if 'quality_gate_status' in df.columns:
                failed_count = len(df[df['quality_gate_status'].isin(['ERROR', 'WARN'])])
                if failed_count > 0:
                    recommendations.append(f"Address {failed_count} projects with failing quality gates")
            
            # Coverage recommendations
            if 'coverage' in df.columns:
                low_coverage = len(df[df['coverage'] < 80])
                if low_coverage > 0:
                    recommendations.append(f"Improve test coverage for {low_coverage} projects below 80%")
            
            # Security recommendations
            if 'vulnerabilities' in df.columns:
                vulnerable_projects = len(df[df['vulnerabilities'] > 0])
                if vulnerable_projects > 0:
                    recommendations.append(f"Address security vulnerabilities in {vulnerable_projects} projects")
            
            section_data['content'] = {'recommendations': recommendations}
        
        return section_data
    
    def _generate_charts(
        self,
        projects_data: List[Dict[str, Any]],
        chart_types: List[str],
        metrics: List[str]
    ) -> List[Dict[str, Any]]:
        """Generate chart configurations for the report."""
        charts = []
        
        if not projects_data:
            return charts
        
        df = pd.DataFrame(projects_data)
        
        # Quality gate pie chart
        if 'pie' in chart_types and 'quality_gate_status' in df.columns:
            charts.append({
                'type': 'pie',
                'title': 'Quality Gate Status Distribution',
                'data': df['quality_gate_status'].value_counts().to_dict()
            })
        
        # Issues bar chart
        if 'bar' in chart_types:
            issue_metrics = [m for m in ['bugs', 'vulnerabilities', 'code_smells'] if m in df.columns]
            if issue_metrics:
                charts.append({
                    'type': 'bar',
                    'title': 'Issues by Type',
                    'data': df[issue_metrics].sum().to_dict()
                })
        
        # Coverage histogram
        if 'histogram' in chart_types and 'coverage' in df.columns:
            charts.append({
                'type': 'histogram',
                'title': 'Test Coverage Distribution',
                'data': df['coverage'].tolist()
            })
        
        return charts


class DataExporter:
    """Data export functionality for multiple formats."""
    
    @staticmethod
    def export_to_csv(data: Union[pd.DataFrame, List[Dict[str, Any]]], filename: str = None) -> bytes:
        """Export data to CSV format."""
        if isinstance(data, list):
            df = pd.DataFrame(data)
        else:
            df = data
        
        output = io.StringIO()
        df.to_csv(output, index=False)
        return output.getvalue().encode('utf-8')
    
    @staticmethod
    def export_to_json(data: Union[pd.DataFrame, List[Dict[str, Any]], Dict[str, Any]], filename: str = None) -> bytes:
        """Export data to JSON format."""
        if isinstance(data, pd.DataFrame):
            json_data = data.to_dict('records')
        elif isinstance(data, list):
            json_data = data
        else:
            json_data = data
        
        return json.dumps(json_data, indent=2, default=str).encode('utf-8')
    
    @staticmethod
    def export_to_excel(data: Union[pd.DataFrame, Dict[str, pd.DataFrame]], filename: str = None) -> bytes:
        """Export data to Excel format."""
        output = io.BytesIO()
        
        if isinstance(data, pd.DataFrame):
            # Single sheet
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                data.to_excel(writer, sheet_name='Data', index=False)
        elif isinstance(data, dict):
            # Multiple sheets
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                for sheet_name, df in data.items():
                    if isinstance(df, pd.DataFrame):
                        df.to_excel(writer, sheet_name=sheet_name, index=False)
        
        output.seek(0)
        return output.getvalue()
    
    @staticmethod
    def create_download_link(data: bytes, filename: str, mime_type: str) -> str:
        """Create a download link for the exported data."""
        b64 = base64.b64encode(data).decode()
        return f'<a href="data:{mime_type};base64,{b64}" download="{filename}">Download {filename}</a>'
    
    @staticmethod
    def render_export_options(
        data: Union[pd.DataFrame, List[Dict[str, Any]], Dict[str, Any]],
        base_filename: str = "sonarqube_export"
    ) -> None:
        """Render export options in Streamlit."""
        st.subheader("📥 Export Data")
        
        col1, col2, col3 = st.columns(3)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        with col1:
            if st.button("📄 Export CSV"):
                csv_data = DataExporter.export_to_csv(data)
                filename = f"{base_filename}_{timestamp}.csv"
                
                st.download_button(
                    label="Download CSV",
                    data=csv_data,
                    file_name=filename,
                    mime="text/csv"
                )
        
        with col2:
            if st.button("📋 Export JSON"):
                json_data = DataExporter.export_to_json(data)
                filename = f"{base_filename}_{timestamp}.json"
                
                st.download_button(
                    label="Download JSON",
                    data=json_data,
                    file_name=filename,
                    mime="application/json"
                )
        
        with col3:
            if st.button("📊 Export Excel"):
                try:
                    excel_data = DataExporter.export_to_excel(data)
                    filename = f"{base_filename}_{timestamp}.xlsx"
                    
                    st.download_button(
                        label="Download Excel",
                        data=excel_data,
                        file_name=filename,
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
                except Exception as e:
                    st.error(f"Excel export failed: {e}")
                    st.info("Install openpyxl for Excel export: pip install openpyxl")


class ScheduledReporting:
    """Scheduled reporting and notification system."""
    
    def __init__(self):
        self.schedules = self._load_schedules()
    
    def _load_schedules(self) -> Dict[str, Any]:
        """Load scheduled reports from session state."""
        return st.session_state.get('scheduled_reports', {})
    
    def _save_schedules(self) -> None:
        """Save scheduled reports to session state."""
        st.session_state.scheduled_reports = self.schedules
    
    def render_schedule_manager(self) -> None:
        """Render the schedule management interface."""
        st.subheader("⏰ Scheduled Reports")
        
        # Add new schedule
        with st.expander("➕ Add New Schedule", expanded=False):
            col1, col2, col3 = st.columns(3)
            
            with col1:
                schedule_name = st.text_input("Schedule Name", key="new_schedule_name")
                report_template = st.selectbox(
                    "Report Template",
                    options=list(ReportGenerator.DEFAULT_TEMPLATES.keys()),
                    format_func=lambda x: ReportGenerator.DEFAULT_TEMPLATES[x].name,
                    key="new_schedule_template"
                )
            
            with col2:
                frequency = st.selectbox(
                    "Frequency",
                    options=['daily', 'weekly', 'monthly'],
                    key="new_schedule_frequency"
                )
                
                time_of_day = st.time_input(
                    "Time of Day",
                    value=datetime.now().time().replace(hour=9, minute=0, second=0, microsecond=0),
                    key="new_schedule_time"
                )
            
            with col3:
                email_recipients = st.text_area(
                    "Email Recipients (one per line)",
                    placeholder="user1@company.com\nuser2@company.com",
                    key="new_schedule_emails"
                )
                
                enabled = st.checkbox("Enabled", value=True, key="new_schedule_enabled")
            
            if st.button("➕ Add Schedule"):
                if schedule_name and email_recipients:
                    schedule_id = f"schedule_{len(self.schedules) + 1}"
                    self.schedules[schedule_id] = {
                        'name': schedule_name,
                        'template': report_template,
                        'frequency': frequency,
                        'time': time_of_day.strftime('%H:%M'),
                        'recipients': [email.strip() for email in email_recipients.split('\n') if email.strip()],
                        'enabled': enabled,
                        'created_at': datetime.now(),
                        'last_run': None,
                        'next_run': self._calculate_next_run(frequency, time_of_day)
                    }
                    self._save_schedules()
                    st.success(f"Schedule '{schedule_name}' added successfully!")
                    st.rerun()
                else:
                    st.error("Please provide schedule name and email recipients")
        
        # Display existing schedules
        if self.schedules:
            st.subheader("📋 Existing Schedules")
            
            for schedule_id, schedule in self.schedules.items():
                with st.expander(f"📅 {schedule['name']} ({schedule['frequency']})", expanded=False):
                    col1, col2, col3, col4 = st.columns(4)
                    
                    with col1:
                        st.write(f"**Template:** {schedule['template']}")
                        st.write(f"**Frequency:** {schedule['frequency']}")
                        st.write(f"**Time:** {schedule['time']}")
                    
                    with col2:
                        st.write(f"**Status:** {'🟢 Enabled' if schedule['enabled'] else '🔴 Disabled'}")
                        st.write(f"**Recipients:** {len(schedule['recipients'])}")
                        if schedule['last_run']:
                            st.write(f"**Last Run:** {schedule['last_run'].strftime('%Y-%m-%d %H:%M')}")
                    
                    with col3:
                        if schedule['next_run']:
                            st.write(f"**Next Run:** {schedule['next_run'].strftime('%Y-%m-%d %H:%M')}")
                        
                        st.write("**Recipients:**")
                        for email in schedule['recipients']:
                            st.write(f"• {email}")
                    
                    with col4:
                        if st.button(f"🗑️ Delete", key=f"delete_{schedule_id}"):
                            del self.schedules[schedule_id]
                            self._save_schedules()
                            st.rerun()
                        
                        if st.button(f"▶️ Run Now", key=f"run_{schedule_id}"):
                            self._run_scheduled_report(schedule_id)
                            st.success("Report generation initiated!")
                        
                        enabled_toggle = st.checkbox(
                            "Enabled",
                            value=schedule['enabled'],
                            key=f"enabled_{schedule_id}"
                        )
                        
                        if enabled_toggle != schedule['enabled']:
                            self.schedules[schedule_id]['enabled'] = enabled_toggle
                            self._save_schedules()
                            st.rerun()
        else:
            st.info("No scheduled reports configured. Add one above to get started.")
    
    def _calculate_next_run(self, frequency: str, time_of_day: datetime.time) -> datetime:
        """Calculate the next run time for a schedule."""
        now = datetime.now()
        today = now.date()
        
        # Combine today's date with the scheduled time
        next_run = datetime.combine(today, time_of_day)
        
        # If the time has already passed today, move to the next occurrence
        if next_run <= now:
            if frequency == 'daily':
                next_run += timedelta(days=1)
            elif frequency == 'weekly':
                next_run += timedelta(weeks=1)
            elif frequency == 'monthly':
                # Simple monthly calculation (same day next month)
                if next_run.month == 12:
                    next_run = next_run.replace(year=next_run.year + 1, month=1)
                else:
                    next_run = next_run.replace(month=next_run.month + 1)
        
        return next_run
    
    def _run_scheduled_report(self, schedule_id: str) -> None:
        """Run a scheduled report."""
        schedule = self.schedules.get(schedule_id)
        if not schedule:
            return
        
        # Update last run time
        self.schedules[schedule_id]['last_run'] = datetime.now()
        
        # Calculate next run time
        time_obj = datetime.strptime(schedule['time'], '%H:%M').time()
        self.schedules[schedule_id]['next_run'] = self._calculate_next_run(
            schedule['frequency'], time_obj
        )
        
        self._save_schedules()
        
        # In a real implementation, this would:
        # 1. Generate the report using the specified template
        # 2. Send emails to recipients
        # 3. Log the execution
        
        st.info(f"Scheduled report '{schedule['name']}' would be generated and sent to {len(schedule['recipients'])} recipients.")
    
    def check_and_run_due_reports(self) -> None:
        """Check for and run any due scheduled reports."""
        now = datetime.now()
        
        for schedule_id, schedule in self.schedules.items():
            if (schedule['enabled'] and 
                schedule['next_run'] and 
                schedule['next_run'] <= now):
                
                self._run_scheduled_report(schedule_id)