"""Advanced visualization components for SonarQube data."""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Union
import json


class AdvancedVisualization:
    """Advanced visualization components for SonarQube metrics."""
    
    @staticmethod
    def create_metrics_dashboard(projects_data: List[Dict[str, Any]]) -> None:
        """Create comprehensive metrics dashboard with multiple chart types."""
        if not projects_data:
            st.warning("No project data available for visualization")
            return
        
        df = pd.DataFrame(projects_data)
        
        # Metrics overview section
        st.subheader("📊 Metrics Overview Dashboard")
        
        # Create tabs for different visualization types
        tab1, tab2, tab3, tab4 = st.tabs([
            "📈 Trends", "🎯 Quality Gates", "🔍 Issue Analysis", "📏 Size & Complexity"
        ])
        
        with tab1:
            AdvancedVisualization._render_trends_charts(df)
        
        with tab2:
            AdvancedVisualization._render_quality_gate_analysis(df)
        
        with tab3:
            AdvancedVisualization._render_issue_analysis(df)
        
        with tab4:
            AdvancedVisualization._render_size_complexity_analysis(df)
    
    @staticmethod
    def _render_trends_charts(df: pd.DataFrame) -> None:
        """Render trend analysis charts."""
        col1, col2 = st.columns(2)
        
        with col1:
            # Coverage trend
            if 'coverage' in df.columns:
                fig_coverage = px.line(
                    df.sort_values('last_analysis') if 'last_analysis' in df.columns else df,
                    x='name',
                    y='coverage',
                    title='Test Coverage Trends',
                    markers=True,
                    line_shape='spline'
                )
                fig_coverage.update_layout(xaxis_tickangle=-45)
                fig_coverage.add_hline(y=80, line_dash="dash", line_color="green", 
                                     annotation_text="Target: 80%")
                st.plotly_chart(fig_coverage, width="stretch")
        
        with col2:
            # Technical debt trend
            if 'technical_debt' in df.columns:
                fig_debt = px.bar(
                    df.sort_values('technical_debt', ascending=False).head(10),
                    x='name',
                    y='technical_debt',
                    title='Technical Debt by Project (Top 10)',
                    color='technical_debt',
                    color_continuous_scale='Reds'
                )
                fig_debt.update_layout(xaxis_tickangle=-45)
                st.plotly_chart(fig_debt, width="stretch")
        
        # Historical trends simulation (in real implementation, this would use historical data)
        st.subheader("📈 Historical Trends Simulation")
        
        # Generate sample historical data for demonstration
        historical_data = AdvancedVisualization._generate_historical_data(df)
        
        if historical_data:
            fig_historical = px.line(
                historical_data,
                x='date',
                y='value',
                color='metric',
                title='Historical Metrics Trends (Last 30 Days)',
                facet_col='project',
                facet_col_wrap=2
            )
            fig_historical.update_layout(height=600)
            st.plotly_chart(fig_historical, width="stretch")
    
    @staticmethod
    def _render_quality_gate_analysis(df: pd.DataFrame) -> None:
        """Render Quality Gate analysis with detailed breakdowns."""
        if 'quality_gate_status' not in df.columns:
            st.warning("Quality Gate data not available")
            return
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Quality Gate status distribution
            status_counts = df['quality_gate_status'].value_counts()
            
            colors = {
                'OK': '#52c41a',
                'ERROR': '#ff4d4f',
                'WARN': '#faad14',
                'NONE': '#d9d9d9'
            }
            
            fig_qg = px.pie(
                values=status_counts.values,
                names=status_counts.index,
                title='Quality Gate Status Distribution',
                color=status_counts.index,
                color_discrete_map=colors
            )
            fig_qg.update_traces(textposition='inside', textinfo='percent+label')
            st.plotly_chart(fig_qg, width="stretch")
        
        with col2:
            # Quality Gate failure reasons analysis
            failed_projects = df[df['quality_gate_status'].isin(['ERROR', 'WARN'])]
            
            if not failed_projects.empty:
                # Analyze common failure patterns
                failure_reasons = []
                for _, project in failed_projects.iterrows():
                    if project.get('bugs', 0) > 0:
                        failure_reasons.append('High Bug Count')
                    if project.get('vulnerabilities', 0) > 0:
                        failure_reasons.append('Security Issues')
                    if project.get('coverage', 0) < 80:
                        failure_reasons.append('Low Coverage')
                    if project.get('duplicated_lines', 0) > 3:
                        failure_reasons.append('Code Duplication')
                
                if failure_reasons:
                    reason_counts = pd.Series(failure_reasons).value_counts()
                    
                    fig_reasons = px.bar(
                        x=reason_counts.index,
                        y=reason_counts.values,
                        title='Common Quality Gate Failure Reasons',
                        color=reason_counts.values,
                        color_continuous_scale='Reds'
                    )
                    fig_reasons.update_layout(xaxis_tickangle=-45)
                    st.plotly_chart(fig_reasons, width="stretch")
            else:
                st.success("🎉 All projects are passing their Quality Gates!")
        
        # Quality Gate conditions heatmap
        st.subheader("🔥 Quality Gate Conditions Heatmap")
        
        # Create a heatmap showing which projects fail which conditions
        conditions_data = []
        for _, project in df.iterrows():
            conditions_data.append({
                'Project': project['name'],
                'Bugs': 'FAIL' if project.get('bugs', 0) > 0 else 'PASS',
                'Vulnerabilities': 'FAIL' if project.get('vulnerabilities', 0) > 0 else 'PASS',
                'Coverage': 'FAIL' if project.get('coverage', 0) < 80 else 'PASS',
                'Duplication': 'FAIL' if project.get('duplicated_lines', 0) > 3 else 'PASS'
            })
        
        if conditions_data:
            conditions_df = pd.DataFrame(conditions_data)
            
            # Convert to numeric for heatmap
            conditions_numeric = conditions_df.copy()
            for col in ['Bugs', 'Vulnerabilities', 'Coverage', 'Duplication']:
                conditions_numeric[col] = conditions_numeric[col].map({'PASS': 1, 'FAIL': 0})
            
            fig_heatmap = px.imshow(
                conditions_numeric.set_index('Project')[['Bugs', 'Vulnerabilities', 'Coverage', 'Duplication']],
                title='Quality Gate Conditions Status (Green=Pass, Red=Fail)',
                color_continuous_scale=['red', 'green'],
                aspect='auto'
            )
            fig_heatmap.update_layout(height=max(400, len(conditions_df) * 20))
            st.plotly_chart(fig_heatmap, width="stretch")
    
    @staticmethod
    def _render_issue_analysis(df: pd.DataFrame) -> None:
        """Render detailed issue analysis charts."""
        issue_columns = ['bugs', 'vulnerabilities', 'code_smells']
        available_columns = [col for col in issue_columns if col in df.columns]
        
        if not available_columns:
            st.warning("Issue data not available")
            return
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Issues by severity stacked bar chart
            issues_data = df[['name'] + available_columns].copy()
            issues_melted = issues_data.melt(
                id_vars=['name'],
                value_vars=available_columns,
                var_name='Issue Type',
                value_name='Count'
            )
            
            fig_issues = px.bar(
                issues_melted,
                x='name',
                y='Count',
                color='Issue Type',
                title='Issues by Project and Type',
                color_discrete_map={
                    'bugs': '#ff4d4f',
                    'vulnerabilities': '#fa541c',
                    'code_smells': '#faad14'
                }
            )
            fig_issues.update_layout(xaxis_tickangle=-45)
            st.plotly_chart(fig_issues, width="stretch")
        
        with col2:
            # Issue density analysis (issues per KLOC)
            if 'ncloc' in df.columns:
                df_density = df.copy()
                df_density['total_issues'] = df_density[available_columns].sum(axis=1)
                df_density['issue_density'] = (df_density['total_issues'] / 
                                             (df_density['ncloc'] / 1000)).fillna(0)
                
                fig_density = px.scatter(
                    df_density,
                    x='ncloc',
                    y='total_issues',
                    size='issue_density',
                    color='issue_density',
                    hover_name='name',
                    title='Issue Density vs Project Size',
                    labels={'ncloc': 'Lines of Code', 'total_issues': 'Total Issues'},
                    color_continuous_scale='Reds'
                )
                st.plotly_chart(fig_density, width="stretch")
        
        # Top problematic projects
        st.subheader("🚨 Most Problematic Projects")
        
        if available_columns:
            df_problems = df.copy()
            df_problems['total_issues'] = df_problems[available_columns].sum(axis=1)
            top_problems = df_problems.nlargest(10, 'total_issues')
            
            if not top_problems.empty:
                fig_top_problems = px.bar(
                    top_problems,
                    x='name',
                    y=available_columns,
                    title='Top 10 Projects by Issue Count',
                    color_discrete_map={
                        'bugs': '#ff4d4f',
                        'vulnerabilities': '#fa541c',
                        'code_smells': '#faad14'
                    }
                )
                fig_top_problems.update_layout(xaxis_tickangle=-45)
                st.plotly_chart(fig_top_problems, width="stretch")
    
    @staticmethod
    def _render_size_complexity_analysis(df: pd.DataFrame) -> None:
        """Render size and complexity analysis."""
        size_columns = ['ncloc', 'complexity', 'cognitive_complexity']
        available_columns = [col for col in size_columns if col in df.columns]
        
        if not available_columns:
            st.warning("Size and complexity data not available")
            return
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Project size distribution
            if 'ncloc' in df.columns:
                fig_size = px.histogram(
                    df,
                    x='ncloc',
                    nbins=20,
                    title='Project Size Distribution (Lines of Code)',
                    labels={'ncloc': 'Lines of Code', 'count': 'Number of Projects'}
                )
                st.plotly_chart(fig_size, width="stretch")
        
        with col2:
            # Complexity vs Size correlation
            if 'ncloc' in df.columns and 'complexity' in df.columns:
                fig_complexity = px.scatter(
                    df,
                    x='ncloc',
                    y='complexity',
                    hover_name='name',
                    title='Complexity vs Project Size',
                    labels={'ncloc': 'Lines of Code', 'complexity': 'Cyclomatic Complexity'},
                    trendline='ols'
                )
                st.plotly_chart(fig_complexity, width="stretch")
        
        # Technical debt ratio analysis
        if 'technical_debt' in df.columns and 'ncloc' in df.columns:
            st.subheader("💰 Technical Debt Analysis")
            
            df_debt = df.copy()
            df_debt['debt_ratio'] = (df_debt['technical_debt'] / 
                                   (df_debt['ncloc'] / 1000)).fillna(0)
            
            fig_debt_ratio = px.bar(
                df_debt.sort_values('debt_ratio', ascending=False).head(15),
                x='name',
                y='debt_ratio',
                title='Technical Debt Ratio (Hours per KLOC) - Top 15',
                color='debt_ratio',
                color_continuous_scale='Reds'
            )
            fig_debt_ratio.update_layout(xaxis_tickangle=-45)
            st.plotly_chart(fig_debt_ratio, width="stretch")
    
    @staticmethod
    def _generate_historical_data(df: pd.DataFrame) -> Optional[pd.DataFrame]:
        """Generate sample historical data for demonstration."""
        if df.empty:
            return None
        
        # Generate 30 days of historical data for top 3 projects
        top_projects = df.head(3)
        historical_data = []
        
        base_date = datetime.now() - timedelta(days=30)
        
        for _, project in top_projects.iterrows():
            for day in range(30):
                date = base_date + timedelta(days=day)
                
                # Simulate some variation in metrics
                import random
                
                # Coverage trend (slight improvement over time)
                base_coverage = project.get('coverage', 70)
                coverage_trend = base_coverage + (day * 0.1) + random.uniform(-2, 2)
                coverage_trend = max(0, min(100, coverage_trend))
                
                # Bug count trend (slight decrease over time)
                base_bugs = project.get('bugs', 10)
                bugs_trend = max(0, base_bugs - (day * 0.1) + random.uniform(-1, 1))
                
                historical_data.extend([
                    {
                        'project': project['name'],
                        'date': date,
                        'metric': 'Coverage',
                        'value': coverage_trend
                    },
                    {
                        'project': project['name'],
                        'date': date,
                        'metric': 'Bugs',
                        'value': bugs_trend
                    }
                ])
        
        return pd.DataFrame(historical_data) if historical_data else None
    
    @staticmethod
    def create_custom_chart(
        data: Union[pd.DataFrame, List[Dict[str, Any]]],
        chart_type: str,
        x_column: str,
        y_column: str,
        title: str,
        color_column: Optional[str] = None,
        **kwargs
    ) -> go.Figure:
        """Create a custom chart with specified parameters."""
        if isinstance(data, list):
            df = pd.DataFrame(data)
        else:
            df = data
        
        if df.empty:
            # Return empty figure
            fig = go.Figure()
            fig.add_annotation(
                text="No data available",
                xref="paper", yref="paper",
                x=0.5, y=0.5, xanchor='center', yanchor='middle',
                showarrow=False, font=dict(size=16)
            )
            return fig
        
        # Create chart based on type
        if chart_type == 'bar':
            fig = px.bar(df, x=x_column, y=y_column, color=color_column, title=title, **kwargs)
        elif chart_type == 'line':
            fig = px.line(df, x=x_column, y=y_column, color=color_column, title=title, **kwargs)
        elif chart_type == 'scatter':
            fig = px.scatter(df, x=x_column, y=y_column, color=color_column, title=title, **kwargs)
        elif chart_type == 'pie':
            fig = px.pie(df, values=y_column, names=x_column, title=title, **kwargs)
        elif chart_type == 'histogram':
            fig = px.histogram(df, x=x_column, title=title, **kwargs)
        else:
            # Default to bar chart
            fig = px.bar(df, x=x_column, y=y_column, color=color_column, title=title, **kwargs)
        
        return fig
    
    @staticmethod
    def create_comparison_matrix(
        projects_data: List[Dict[str, Any]],
        metrics: List[str]
    ) -> go.Figure:
        """Create a comparison matrix heatmap for multiple projects and metrics."""
        if not projects_data or not metrics:
            fig = go.Figure()
            fig.add_annotation(
                text="No data available for comparison",
                xref="paper", yref="paper",
                x=0.5, y=0.5, xanchor='center', yanchor='middle',
                showarrow=False, font=dict(size=16)
            )
            return fig
        
        df = pd.DataFrame(projects_data)
        
        # Filter available metrics
        available_metrics = [m for m in metrics if m in df.columns]
        
        if not available_metrics:
            fig = go.Figure()
            fig.add_annotation(
                text="Selected metrics not available in data",
                xref="paper", yref="paper",
                x=0.5, y=0.5, xanchor='center', yanchor='middle',
                showarrow=False, font=dict(size=16)
            )
            return fig
        
        # Normalize metrics for comparison (0-1 scale)
        comparison_data = df[['name'] + available_metrics].copy()
        
        for metric in available_metrics:
            if comparison_data[metric].dtype in ['int64', 'float64']:
                max_val = comparison_data[metric].max()
                if max_val > 0:
                    comparison_data[f'{metric}_normalized'] = comparison_data[metric] / max_val
                else:
                    comparison_data[f'{metric}_normalized'] = 0
        
        # Create heatmap
        normalized_columns = [f'{m}_normalized' for m in available_metrics]
        
        fig = px.imshow(
            comparison_data[normalized_columns].T,
            x=comparison_data['name'],
            y=available_metrics,
            title='Project Metrics Comparison Matrix (Normalized)',
            color_continuous_scale='RdYlGn',
            aspect='auto'
        )
        
        fig.update_layout(
            xaxis_title='Projects',
            yaxis_title='Metrics',
            height=max(400, len(available_metrics) * 50)
        )
        
        return fig
