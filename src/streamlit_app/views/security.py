"""Security page - Security analysis dashboard."""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import json
import io

from streamlit_app.services.sonarqube_service import SonarQubeService
from streamlit_app.config.settings import ConfigManager
from streamlit_app.utils.session import SessionManager


class SecurityAnalyzer:
    """Security analysis and reporting manager."""
    
    def __init__(self, service: SonarQubeService):
        self.service = service
    
    def calculate_risk_score(self, hotspot: Dict[str, Any]) -> int:
        """Calculate risk score for a security hotspot."""
        score = 0
        
        # Vulnerability probability scoring
        prob_scores = {
            "HIGH": 30,
            "MEDIUM": 20,
            "LOW": 10
        }
        score += prob_scores.get(hotspot.get("vulnerabilityProbability", "LOW"), 10)
        
        # Security category scoring
        category_scores = {
            "sql-injection": 25,
            "command-injection": 25,
            "path-traversal-injection": 20,
            "ldap-injection": 20,
            "xpath-injection": 20,
            "rce": 25,
            "dos": 15,
            "ssrf": 20,
            "csrf": 15,
            "xss": 15,
            "log-injection": 10,
            "http-response-splitting": 15,
            "open-redirect": 10,
            "xxe": 20,
            "object-injection": 20,
            "weak-cryptography": 15,
            "auth": 20,
            "insecure-conf": 10,
            "file-manipulation": 15,
            "others": 5
        }
        score += category_scores.get(hotspot.get("securityCategory", "others"), 5)
        
        # Status penalty (unreviewed is higher risk)
        if hotspot.get("status") == "TO_REVIEW":
            score += 15
        elif hotspot.get("status") == "IN_REVIEW":
            score += 10
        
        return min(score, 100)  # Cap at 100
    
    def prioritize_vulnerabilities(self, hotspots: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Prioritize vulnerabilities by risk score."""
        for hotspot in hotspots:
            hotspot["risk_score"] = self.calculate_risk_score(hotspot)
        
        return sorted(hotspots, key=lambda x: x["risk_score"], reverse=True)
    
    def generate_security_report(self, project_key: str) -> Dict[str, Any]:
        """Generate comprehensive security report."""
        # Get security metrics
        metrics = self.service.get_security_metrics(project_key)
        
        # Get security hotspots
        hotspots = self.service.get_security_hotspots(project_key)
        prioritized_hotspots = self.prioritize_vulnerabilities(hotspots)
        
        # Get vulnerabilities (issues of type VULNERABILITY)
        vulnerabilities = self.service.search_issues(
            project_key, 
            {"types": ["VULNERABILITY"]}
        )
        
        # Calculate summary statistics
        total_hotspots = len(hotspots)
        high_risk_hotspots = len([h for h in prioritized_hotspots if h["risk_score"] >= 70])
        medium_risk_hotspots = len([h for h in prioritized_hotspots if 40 <= h["risk_score"] < 70])
        low_risk_hotspots = len([h for h in prioritized_hotspots if h["risk_score"] < 40])
        
        unreviewed_hotspots = len([h for h in hotspots if h.get("status") == "TO_REVIEW"])
        
        # Security rating interpretation
        security_rating = metrics.get("security_rating", "5")
        rating_labels = {"1": "A", "2": "B", "3": "C", "4": "D", "5": "E"}
        security_grade = rating_labels.get(security_rating, "E")
        
        return {
            "project_key": project_key,
            "generated_at": datetime.now().isoformat(),
            "metrics": metrics,
            "summary": {
                "security_grade": security_grade,
                "total_vulnerabilities": len(vulnerabilities),
                "total_hotspots": total_hotspots,
                "high_risk_hotspots": high_risk_hotspots,
                "medium_risk_hotspots": medium_risk_hotspots,
                "low_risk_hotspots": low_risk_hotspots,
                "unreviewed_hotspots": unreviewed_hotspots,
                "hotspots_reviewed_percent": metrics.get("security_hotspots_reviewed", "0")
            },
            "vulnerabilities": vulnerabilities[:50],  # Limit for performance
            "hotspots": prioritized_hotspots[:50],  # Limit for performance
            "recommendations": self._generate_recommendations(metrics, prioritized_hotspots)
        }
    
    def _generate_recommendations(self, metrics: Dict[str, Any], hotspots: List[Dict[str, Any]]) -> List[str]:
        """Generate security recommendations."""
        recommendations = []
        
        # Security rating recommendations
        security_rating = int(metrics.get("security_rating", "5"))
        if security_rating >= 4:
            recommendations.append("🚨 Critical: Address high-severity vulnerabilities immediately")
        elif security_rating >= 3:
            recommendations.append("⚠️ Warning: Review and fix medium-severity vulnerabilities")
        
        # Hotspot review recommendations
        unreviewed_count = len([h for h in hotspots if h.get("status") == "TO_REVIEW"])
        if unreviewed_count > 10:
            recommendations.append(f"📋 Review {unreviewed_count} pending security hotspots")
        
        # High-risk hotspot recommendations
        high_risk_count = len([h for h in hotspots if h.get("risk_score", 0) >= 70])
        if high_risk_count > 0:
            recommendations.append(f"🔥 Prioritize {high_risk_count} high-risk security hotspots")
        
        # Category-specific recommendations
        categories = {}
        for hotspot in hotspots:
            category = hotspot.get("securityCategory", "others")
            categories[category] = categories.get(category, 0) + 1
        
        top_categories = sorted(categories.items(), key=lambda x: x[1], reverse=True)[:3]
        for category, count in top_categories:
            if count >= 3:
                recommendations.append(f"🎯 Focus on {category} vulnerabilities ({count} instances)")
        
        if not recommendations:
            recommendations.append("✅ Security posture looks good! Continue regular reviews.")
        
        return recommendations


def render_security_metrics_overview(analyzer: SecurityAnalyzer, projects: List[Dict[str, Any]]):
    """Render security metrics overview."""
    st.subheader("🛡️ Security Overview")
    
    if not projects:
        st.info("No projects available for security analysis.")
        return
    
    # Calculate aggregate metrics
    total_vulnerabilities = 0
    total_hotspots = 0
    projects_with_issues = 0
    security_ratings = []
    
    for project in projects[:10]:  # Limit for performance
        project_key = project["key"]
        
        # Get security metrics
        metrics = analyzer.service.get_security_metrics(project_key)
        vulnerabilities = int(metrics.get("vulnerabilities", "0"))
        hotspots = int(metrics.get("security_hotspots", "0"))
        rating = int(metrics.get("security_rating", "5"))
        
        total_vulnerabilities += vulnerabilities
        total_hotspots += hotspots
        security_ratings.append(rating)
        
        if vulnerabilities > 0 or hotspots > 0:
            projects_with_issues += 1
    
    # Display metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Vulnerabilities", total_vulnerabilities)
    
    with col2:
        st.metric("Security Hotspots", total_hotspots)
    
    with col3:
        st.metric("Projects with Issues", projects_with_issues)
    
    with col4:
        avg_rating = sum(security_ratings) / len(security_ratings) if security_ratings else 5
        rating_labels = {1: "A", 2: "B", 3: "C", 4: "D", 5: "E"}
        avg_grade = rating_labels.get(round(avg_rating), "E")
        st.metric("Avg Security Grade", avg_grade)


def render_vulnerability_prioritization(analyzer: SecurityAnalyzer, project_key: str):
    """Render vulnerability prioritization dashboard."""
    st.subheader("🎯 Vulnerability Prioritization")
    
    # Get and prioritize hotspots
    hotspots = analyzer.service.get_security_hotspots(project_key)
    prioritized_hotspots = analyzer.prioritize_vulnerabilities(hotspots)
    
    if not prioritized_hotspots:
        st.info("No security hotspots found for this project.")
        return
    
    # Risk distribution chart
    risk_categories = {"High (70-100)": 0, "Medium (40-69)": 0, "Low (0-39)": 0}
    for hotspot in prioritized_hotspots:
        score = hotspot["risk_score"]
        if score >= 70:
            risk_categories["High (70-100)"] += 1
        elif score >= 40:
            risk_categories["Medium (40-69)"] += 1
        else:
            risk_categories["Low (0-39)"] += 1
    
    col1, col2 = st.columns(2)
    
    with col1:
        fig_risk = px.pie(
            values=list(risk_categories.values()),
            names=list(risk_categories.keys()),
            title="Risk Distribution",
            color_discrete_map={
                "High (70-100)": "#ff4444",
                "Medium (40-69)": "#ffaa00",
                "Low (0-39)": "#44ff44"
            }
        )
        st.plotly_chart(fig_risk, use_container_width=True)
    
    with col2:
        # Category distribution
        categories = {}
        for hotspot in prioritized_hotspots:
            category = hotspot.get("securityCategory", "others")
            categories[category] = categories.get(category, 0) + 1
        
        fig_category = px.bar(
            x=list(categories.keys()),
            y=list(categories.values()),
            title="Vulnerabilities by Category"
        )
        fig_category.update_layout(xaxis_tickangle=45)
        st.plotly_chart(fig_category, use_container_width=True)
    
    # Top priority hotspots table
    st.subheader("🔥 Top Priority Hotspots")
    
    if prioritized_hotspots:
        df_data = []
        for hotspot in prioritized_hotspots[:20]:  # Show top 20
            df_data.append({
                "Risk Score": hotspot["risk_score"],
                "Key": hotspot.get("key", ""),
                "Category": hotspot.get("securityCategory", ""),
                "Probability": hotspot.get("vulnerabilityProbability", ""),
                "Status": hotspot.get("status", ""),
                "Component": hotspot.get("component", "").split(":")[-1] if hotspot.get("component") else "",
                "Line": hotspot.get("textRange", {}).get("startLine", "") if hotspot.get("textRange") else ""
            })
        
        df = pd.DataFrame(df_data)
        
        # Color code by risk score
        def color_risk_score(val):
            if val >= 70:
                return 'background-color: #ffebee'
            elif val >= 40:
                return 'background-color: #fff3e0'
            else:
                return 'background-color: #e8f5e8'
        
        styled_df = df.style.applymap(color_risk_score, subset=['Risk Score'])
        st.dataframe(styled_df, use_container_width=True)


def render_security_trends(analyzer: SecurityAnalyzer, project_key: str):
    """Render security trends analysis."""
    st.subheader("📈 Security Trends")
    
    # For demo purposes, we'll create mock trend data
    # In a real implementation, this would fetch historical data
    dates = pd.date_range(start=datetime.now() - timedelta(days=30), end=datetime.now(), freq='D')
    
    # Mock trend data
    vulnerabilities_trend = [max(0, 15 - i//3 + (i % 7)) for i in range(len(dates))]
    hotspots_trend = [max(0, 25 - i//2 + (i % 5)) for i in range(len(dates))]
    
    trend_df = pd.DataFrame({
        'Date': dates,
        'Vulnerabilities': vulnerabilities_trend,
        'Security Hotspots': hotspots_trend
    })
    
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=trend_df['Date'],
        y=trend_df['Vulnerabilities'],
        mode='lines+markers',
        name='Vulnerabilities',
        line=dict(color='red')
    ))
    fig.add_trace(go.Scatter(
        x=trend_df['Date'],
        y=trend_df['Security Hotspots'],
        mode='lines+markers',
        name='Security Hotspots',
        line=dict(color='orange')
    ))
    
    fig.update_layout(
        title="Security Issues Trend (Last 30 Days)",
        xaxis_title="Date",
        yaxis_title="Count",
        hovermode='x unified'
    )
    
    st.plotly_chart(fig, use_container_width=True)


def render_security_alerts():
    """Render security alert system."""
    st.subheader("🚨 Security Alerts")
    
    # Alert preferences
    with st.expander("Alert Preferences"):
        col1, col2 = st.columns(2)
        
        with col1:
            st.checkbox("High-risk vulnerabilities", value=True, key="alert_high_risk")
            st.checkbox("New security hotspots", value=True, key="alert_new_hotspots")
            st.checkbox("Security rating degradation", value=True, key="alert_rating_drop")
        
        with col2:
            st.selectbox("Alert frequency", ["Immediate", "Daily", "Weekly"], key="alert_frequency")
            st.text_input("Email notifications", placeholder="email@example.com", key="alert_email")
            st.selectbox("Severity threshold", ["High", "Medium", "Low"], key="alert_threshold")
    
    # Mock active alerts
    alerts = [
        {
            "severity": "High",
            "message": "New SQL injection vulnerability detected in user-service",
            "timestamp": datetime.now() - timedelta(hours=2),
            "project": "user-service"
        },
        {
            "severity": "Medium", 
            "message": "Security rating dropped from B to C in payment-api",
            "timestamp": datetime.now() - timedelta(hours=6),
            "project": "payment-api"
        },
        {
            "severity": "Low",
            "message": "5 new security hotspots require review in web-frontend",
            "timestamp": datetime.now() - timedelta(days=1),
            "project": "web-frontend"
        }
    ]
    
    for alert in alerts:
        severity_colors = {"High": "🔴", "Medium": "🟡", "Low": "🟢"}
        st.info(f"{severity_colors[alert['severity']]} **{alert['severity']}** - {alert['message']} ({alert['timestamp'].strftime('%Y-%m-%d %H:%M')})")


def render_security_report_export(analyzer: SecurityAnalyzer, project_key: str):
    """Render security report generation and export."""
    st.subheader("📄 Security Reports")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("Generate Security Report", type="primary"):
            with st.spinner("Generating security report..."):
                report = analyzer.generate_security_report(project_key)
                st.session_state.security_report = report
                st.success("Security report generated successfully!")
    
    with col2:
        report_format = st.selectbox("Export Format", ["JSON", "CSV", "PDF Summary"])
    
    # Display report if generated
    if "security_report" in st.session_state:
        report = st.session_state.security_report
        
        # Report summary
        st.subheader("📊 Report Summary")
        summary = report["summary"]
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Security Grade", summary["security_grade"])
        with col2:
            st.metric("Vulnerabilities", summary["total_vulnerabilities"])
        with col3:
            st.metric("High Risk Hotspots", summary["high_risk_hotspots"])
        with col4:
            st.metric("Review Progress", f"{summary['hotspots_reviewed_percent']}%")
        
        # Recommendations
        st.subheader("💡 Recommendations")
        for rec in report["recommendations"]:
            st.write(f"• {rec}")
        
        # Export functionality
        if st.button("Download Report"):
            if report_format == "JSON":
                report_json = json.dumps(report, indent=2, default=str)
                st.download_button(
                    label="Download JSON Report",
                    data=report_json,
                    file_name=f"security_report_{project_key}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                    mime="application/json"
                )
            elif report_format == "CSV":
                # Convert hotspots to CSV
                if report["hotspots"]:
                    df = pd.DataFrame(report["hotspots"])
                    csv = df.to_csv(index=False)
                    st.download_button(
                        label="Download CSV Report",
                        data=csv,
                        file_name=f"security_hotspots_{project_key}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                        mime="text/csv"
                    )


def render():
    """Render the security page."""
    st.title("🔒 Security Analysis Dashboard")
    
    # Check configuration
    config_manager = ConfigManager()
    if not config_manager.is_configured():
        st.warning("Please configure SonarQube connection in the Configuration page first.")
        return
    
    # Initialize services
    service = SonarQubeService(config_manager)
    analyzer = SecurityAnalyzer(service)
    
    # Get projects for selection
    projects = service.get_projects()
    
    # Project selection
    if projects:
        project_options = [f"{p['name']} ({p['key']})" for p in projects]
        selected_project = st.selectbox("Select Project", project_options)
        project_key = selected_project.split("(")[-1].rstrip(")")
    else:
        st.error("No projects found. Please check your SonarQube configuration.")
        return
    
    # Render security overview
    render_security_metrics_overview(analyzer, projects)
    
    # Tabs for different views
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "🎯 Prioritization", 
        "📈 Trends", 
        "🚨 Alerts", 
        "📄 Reports",
        "🔍 Details"
    ])
    
    with tab1:
        render_vulnerability_prioritization(analyzer, project_key)
    
    with tab2:
        render_security_trends(analyzer, project_key)
    
    with tab3:
        render_security_alerts()
    
    with tab4:
        render_security_report_export(analyzer, project_key)
    
    with tab5:
        # Detailed security metrics
        st.subheader("🔍 Detailed Security Metrics")
        metrics = service.get_security_metrics(project_key)
        
        if metrics:
            col1, col2 = st.columns(2)
            
            with col1:
                st.metric("Security Rating", metrics.get("security_rating", "N/A"))
                st.metric("Vulnerabilities", metrics.get("vulnerabilities", "0"))
                st.metric("Security Hotspots", metrics.get("security_hotspots", "0"))
            
            with col2:
                st.metric("Security Review Rating", metrics.get("security_review_rating", "N/A"))
                st.metric("Hotspots Reviewed", f"{metrics.get('security_hotspots_reviewed', '0')}%")
        else:
            st.info("No security metrics available for this project.")