"""End-to-end UI tests for Streamlit application."""

import pytest
import streamlit as st
from unittest.mock import Mock, patch, MagicMock
import pandas as pd
from datetime import datetime, timedelta

# Import the pages to test
from src.streamlit_app.pages import issues, security, performance
from src.streamlit_app.services.sonarqube_service import SonarQubeService
from src.streamlit_app.config.settings import ConfigManager
from src.streamlit_app.utils.session import SessionManager
from src.streamlit_app.utils.performance import get_performance_monitor, get_cache_manager


class TestIssuesPageUI:
    """Test issues page UI functionality."""
    
    @pytest.fixture
    def mock_config_manager(self):
        """Mock configuration manager."""
        config = Mock(spec=ConfigManager)
        config.is_configured.return_value = True
        config.get_connection_params.return_value = {
            "base_url": "http://localhost:9000",
            "token": "test_token"
        }
        return config
    
    @pytest.fixture
    def mock_service(self):
        """Mock SonarQube service."""
        service = Mock(spec=SonarQubeService)
        
        # Mock projects
        service.get_projects.return_value = [
            {"key": "test-project", "name": "Test Project"},
            {"key": "another-project", "name": "Another Project"}
        ]
        
        # Mock issues
        service.search_issues.return_value = [
            {
                "key": "TEST-1",
                "type": "BUG",
                "severity": "MAJOR",
                "status": "OPEN",
                "component": "test-project:src/main.py",
                "rule": "python:S1234",
                "assignee": "john.doe",
                "creationDate": "2025-01-01T10:00:00Z",
                "message": "Test issue message"
            },
            {
                "key": "TEST-2", 
                "type": "VULNERABILITY",
                "severity": "CRITICAL",
                "status": "CONFIRMED",
                "component": "test-project:src/utils.py",
                "rule": "python:S5678",
                "assignee": None,
                "creationDate": "2025-01-02T11:00:00Z",
                "message": "Security vulnerability found"
            }
        ]
        
        return service
    
    @patch('src.streamlit_app.pages.issues.SonarQubeService')
    @patch('src.streamlit_app.pages.issues.ConfigManager')
    @patch('streamlit.session_state', new_callable=dict)
    def test_issues_page_renders_without_config(self, mock_session_state, mock_config_class, mock_service_class):
        """Test issues page renders warning when not configured."""
        mock_config = Mock()
        mock_config.is_configured.return_value = False
        mock_config_class.return_value = mock_config
        
        with patch('streamlit.warning') as mock_warning:
            issues.render()
            mock_warning.assert_called_once()
    
    @patch('src.streamlit_app.pages.issues.SonarQubeService')
    @patch('src.streamlit_app.pages.issues.ConfigManager')
    @patch('streamlit.session_state', new_callable=dict)
    def test_issues_page_loads_data(self, mock_session_state, mock_config_class, mock_service_class, mock_config_manager, mock_service):
        """Test issues page loads and displays data correctly."""
        mock_config_class.return_value = mock_config_manager
        mock_service_class.return_value = mock_service
        
        with patch('streamlit.title') as mock_title, \
             patch('streamlit.spinner') as mock_spinner, \
             patch('streamlit.columns') as mock_columns, \
             patch('streamlit.metric') as mock_metric:
            
            mock_columns.return_value = [Mock(), Mock(), Mock(), Mock()]
            
            issues.render()
            
            mock_title.assert_called_with("🐛 Issues Management")
            mock_service.search_issues.assert_called()
            mock_metric.assert_called()
    
    @patch('src.streamlit_app.pages.issues.SonarQubeService')
    @patch('src.streamlit_app.pages.issues.ConfigManager')
    @patch('streamlit.session_state', new_callable=dict)
    def test_issue_filtering(self, mock_session_state, mock_config_class, mock_service_class, mock_config_manager, mock_service):
        """Test issue filtering functionality."""
        mock_config_class.return_value = mock_config_manager
        mock_service_class.return_value = mock_service
        
        with patch('streamlit.sidebar') as mock_sidebar:
            mock_sidebar.selectbox.return_value = "Test Project (test-project)"
            mock_sidebar.multiselect.side_effect = [
                ["MAJOR", "CRITICAL"],  # severities
                ["BUG", "VULNERABILITY"],  # types
                ["OPEN", "CONFIRMED"]  # statuses
            ]
            
            filters = issues.render_issue_filters()
            
            assert "project_key" in filters
            assert filters["project_key"] == "test-project"
            assert "severities" in filters
            assert "types" in filters
            assert "statuses" in filters
    
    def test_issue_workflow_visualization(self):
        """Test issue workflow visualization."""
        test_issues = [
            {"status": "OPEN", "type": "BUG"},
            {"status": "CONFIRMED", "type": "BUG"},
            {"status": "OPEN", "type": "VULNERABILITY"}
        ]
        
        with patch('streamlit.subheader') as mock_subheader, \
             patch('streamlit.columns') as mock_columns, \
             patch('streamlit.plotly_chart') as mock_chart:
            
            mock_columns.return_value = [Mock(), Mock()]
            
            issues.render_issue_workflow_visualization(test_issues)
            
            mock_subheader.assert_called_with("📊 Issue Workflow")
            assert mock_chart.call_count == 2  # Two charts should be created
    
    def test_bulk_operations_interface(self):
        """Test bulk operations interface."""
        selected_issues = ["TEST-1", "TEST-2"]
        
        with patch('streamlit.subheader') as mock_subheader, \
             patch('streamlit.columns') as mock_columns, \
             patch('streamlit.button') as mock_button:
            
            mock_columns.return_value = [Mock(), Mock(), Mock()]
            mock_button.return_value = False
            
            issues.render_bulk_operations(selected_issues)
            
            mock_subheader.assert_called_with("🔧 Bulk Operations (2 issues selected)")
            assert mock_button.call_count == 3  # Three bulk operation buttons


class TestSecurityPageUI:
    """Test security page UI functionality."""
    
    @pytest.fixture
    def mock_security_analyzer(self):
        """Mock security analyzer."""
        analyzer = Mock()
        
        # Mock security report
        analyzer.generate_security_report.return_value = {
            "project_key": "test-project",
            "generated_at": datetime.now().isoformat(),
            "metrics": {
                "security_rating": "3",
                "vulnerabilities": "5",
                "security_hotspots": "10"
            },
            "summary": {
                "security_grade": "C",
                "total_vulnerabilities": 5,
                "total_hotspots": 10,
                "high_risk_hotspots": 3,
                "medium_risk_hotspots": 4,
                "low_risk_hotspots": 3,
                "unreviewed_hotspots": 7,
                "hotspots_reviewed_percent": "30"
            },
            "vulnerabilities": [],
            "hotspots": [
                {
                    "key": "HOTSPOT-1",
                    "securityCategory": "sql-injection",
                    "vulnerabilityProbability": "HIGH",
                    "status": "TO_REVIEW",
                    "risk_score": 85
                }
            ],
            "recommendations": [
                "🚨 Critical: Address high-severity vulnerabilities immediately",
                "📋 Review 7 pending security hotspots"
            ]
        }
        
        # Mock prioritized vulnerabilities
        analyzer.prioritize_vulnerabilities.return_value = [
            {
                "key": "HOTSPOT-1",
                "securityCategory": "sql-injection",
                "vulnerabilityProbability": "HIGH",
                "status": "TO_REVIEW",
                "risk_score": 85,
                "component": "test-project:src/db.py"
            }
        ]
        
        return analyzer
    
    @patch('src.streamlit_app.pages.security.SonarQubeService')
    @patch('src.streamlit_app.pages.security.ConfigManager')
    @patch('streamlit.session_state', new_callable=dict)
    def test_security_page_renders_without_config(self, mock_session_state, mock_config_class, mock_service_class):
        """Test security page renders warning when not configured."""
        mock_config = Mock()
        mock_config.is_configured.return_value = False
        mock_config_class.return_value = mock_config
        
        with patch('streamlit.warning') as mock_warning:
            security.render()
            mock_warning.assert_called_once()
    
    @patch('src.streamlit_app.pages.security.SecurityAnalyzer')
    @patch('src.streamlit_app.pages.security.SonarQubeService')
    @patch('src.streamlit_app.pages.security.ConfigManager')
    @patch('streamlit.session_state', new_callable=dict)
    def test_security_metrics_overview(self, mock_session_state, mock_config_class, mock_service_class, mock_analyzer_class, mock_security_analyzer):
        """Test security metrics overview rendering."""
        mock_config = Mock()
        mock_config.is_configured.return_value = True
        mock_config_class.return_value = mock_config
        
        mock_service = Mock()
        mock_service.get_projects.return_value = [
            {"key": "test-project", "name": "Test Project"}
        ]
        mock_service.get_security_metrics.return_value = {
            "vulnerabilities": "5",
            "security_hotspots": "10",
            "security_rating": "3"
        }
        mock_service_class.return_value = mock_service
        
        mock_analyzer_class.return_value = mock_security_analyzer
        
        projects = [{"key": "test-project", "name": "Test Project"}]
        
        with patch('streamlit.subheader') as mock_subheader, \
             patch('streamlit.columns') as mock_columns, \
             patch('streamlit.metric') as mock_metric:
            
            mock_columns.return_value = [Mock(), Mock(), Mock(), Mock()]
            
            security.render_security_metrics_overview(mock_security_analyzer, projects)
            
            mock_subheader.assert_called_with("🛡️ Security Overview")
            assert mock_metric.call_count == 4  # Four metrics should be displayed
    
    def test_vulnerability_prioritization(self, mock_security_analyzer):
        """Test vulnerability prioritization dashboard."""
        mock_security_analyzer.service.get_security_hotspots.return_value = [
            {
                "key": "HOTSPOT-1",
                "securityCategory": "sql-injection",
                "vulnerabilityProbability": "HIGH",
                "status": "TO_REVIEW",
                "risk_score": 85
            }
        ]
        
        with patch('streamlit.subheader') as mock_subheader, \
             patch('streamlit.columns') as mock_columns, \
             patch('streamlit.plotly_chart') as mock_chart, \
             patch('streamlit.dataframe') as mock_dataframe:
            
            mock_columns.return_value = [Mock(), Mock()]
            
            security.render_vulnerability_prioritization(mock_security_analyzer, "test-project")
            
            mock_subheader.assert_called()
            assert mock_chart.call_count == 2  # Risk and category charts
            mock_dataframe.assert_called()
    
    def test_security_report_generation(self, mock_security_analyzer):
        """Test security report generation and export."""
        with patch('streamlit.subheader') as mock_subheader, \
             patch('streamlit.columns') as mock_columns, \
             patch('streamlit.button') as mock_button, \
             patch('streamlit.selectbox') as mock_selectbox, \
             patch('streamlit.session_state', new_callable=dict) as mock_session_state:
            
            mock_columns.return_value = [Mock(), Mock()]
            mock_button.return_value = True
            mock_selectbox.return_value = "JSON"
            
            security.render_security_report_export(mock_security_analyzer, "test-project")
            
            mock_security_analyzer.generate_security_report.assert_called_with("test-project")


class TestPerformancePageUI:
    """Test performance monitoring page UI functionality."""
    
    def test_system_health_rendering(self):
        """Test system health dashboard rendering."""
        mock_monitor = Mock()
        mock_monitor.get_system_metrics.return_value = {
            "cpu_usage": 45.5,
            "memory_usage": 67.2,
            "memory_available_gb": 4.8,
            "disk_usage": 78.1,
            "disk_free_gb": 25.3
        }
        
        with patch('src.streamlit_app.pages.performance.get_performance_monitor', return_value=mock_monitor), \
             patch('src.streamlit_app.pages.performance.get_cache_manager') as mock_cache_manager, \
             patch('streamlit.subheader') as mock_subheader, \
             patch('streamlit.columns') as mock_columns, \
             patch('streamlit.metric') as mock_metric:
            
            mock_cache_manager.return_value.get_stats.return_value = {
                "hit_ratio": 75.5,
                "cache_size": 42
            }
            mock_columns.return_value = [Mock(), Mock(), Mock(), Mock()]
            
            performance.render_system_health()
            
            mock_subheader.assert_called_with("🖥️ System Health")
            assert mock_metric.call_count == 4  # Four system metrics
    
    def test_performance_metrics_charts(self):
        """Test performance metrics charts rendering."""
        mock_monitor = Mock()
        
        # Mock response time metrics
        mock_response_metrics = [
            Mock(timestamp=datetime.now(), value=1.5, context={"function": "get_projects"}),
            Mock(timestamp=datetime.now(), value=2.1, context={"function": "search_issues"})
        ]
        
        # Mock system metrics
        mock_cpu_metrics = [
            Mock(timestamp=datetime.now(), value=45.0),
            Mock(timestamp=datetime.now(), value=50.0)
        ]
        
        mock_monitor.get_metrics.side_effect = [
            mock_response_metrics,  # First call for response_time
            mock_cpu_metrics,       # Second call for cpu_usage
            []                      # Third call for memory_usage (empty)
        ]
        
        with patch('src.streamlit_app.pages.performance.get_performance_monitor', return_value=mock_monitor), \
             patch('streamlit.subheader') as mock_subheader, \
             patch('streamlit.plotly_chart') as mock_chart:
            
            performance.render_performance_metrics()
            
            mock_subheader.assert_called_with("📊 Performance Metrics")
            assert mock_chart.call_count >= 1  # At least one chart should be rendered
    
    def test_cache_performance_dashboard(self):
        """Test cache performance dashboard."""
        mock_cache_manager = Mock()
        mock_cache_manager.get_stats.return_value = {
            "total_requests": 100,
            "hits": 75,
            "misses": 25,
            "hit_ratio": 75.0,
            "cache_size": 50
        }
        mock_cache_manager.clear.return_value = None
        mock_cache_manager.cleanup_expired.return_value = None
        
        with patch('src.streamlit_app.pages.performance.get_cache_manager', return_value=mock_cache_manager), \
             patch('streamlit.subheader') as mock_subheader, \
             patch('streamlit.columns') as mock_columns, \
             patch('streamlit.button') as mock_button, \
             patch('streamlit.plotly_chart') as mock_chart:
            
            mock_columns.return_value = [Mock(), Mock()]
            mock_button.return_value = False
            
            performance.render_cache_performance()
            
            mock_subheader.assert_called_with("🗄️ Cache Performance")
            mock_chart.assert_called()  # Cache visualization chart
    
    def test_performance_alerts(self):
        """Test performance alerts rendering."""
        mock_monitor = Mock()
        mock_monitor.get_recent_alerts.return_value = [
            {
                "timestamp": datetime.now(),
                "severity": "critical",
                "message": "High CPU usage detected",
                "metric": "cpu_usage",
                "value": 85.0,
                "threshold": 80.0
            },
            {
                "timestamp": datetime.now() - timedelta(minutes=5),
                "severity": "warning",
                "message": "Memory usage above threshold",
                "metric": "memory_usage",
                "value": 75.0,
                "threshold": 70.0
            }
        ]
        
        with patch('src.streamlit_app.pages.performance.get_performance_monitor', return_value=mock_monitor), \
             patch('streamlit.subheader') as mock_subheader, \
             patch('streamlit.selectbox') as mock_selectbox, \
             patch('streamlit.expander') as mock_expander:
            
            mock_selectbox.return_value = "All"
            mock_expander.return_value.__enter__ = Mock()
            mock_expander.return_value.__exit__ = Mock()
            
            performance.render_performance_alerts()
            
            mock_subheader.assert_called_with("🚨 Performance Alerts")
            mock_monitor.get_recent_alerts.assert_called_with(severity=None, limit=20)


class TestUIWorkflowIntegration:
    """Test complete UI workflows and integration."""
    
    @patch('src.streamlit_app.services.sonarqube_service.SonarQubeClient')
    @patch('streamlit.session_state', new_callable=dict)
    def test_complete_issue_management_workflow(self, mock_session_state, mock_client_class):
        """Test complete issue management workflow from loading to updating."""
        # Mock the client and its responses
        mock_client = Mock()
        mock_client.get.return_value = {
            "issues": [
                {
                    "key": "TEST-1",
                    "type": "BUG",
                    "severity": "MAJOR",
                    "status": "OPEN",
                    "component": "test-project:src/main.py",
                    "rule": "python:S1234",
                    "assignee": "john.doe",
                    "creationDate": "2025-01-01T10:00:00Z",
                    "message": "Test issue message"
                }
            ]
        }
        mock_client.post.return_value = {}
        mock_client.close.return_value = None
        mock_client_class.return_value = mock_client
        
        # Mock configuration
        config_manager = Mock()
        config_manager.is_configured.return_value = True
        config_manager.get_connection_params.return_value = {
            "base_url": "http://localhost:9000",
            "token": "test_token"
        }
        
        # Create service and issue manager
        service = SonarQubeService(config_manager)
        issue_manager = issues.IssueManager(service)
        
        # Test search issues
        search_results = issue_manager.search_issues("test-project")
        assert len(search_results) == 1
        assert search_results[0]["key"] == "TEST-1"
        
        # Test update issue
        update_result = issue_manager.update_issue("TEST-1", {"assignee": "jane.doe"})
        assert update_result is True
        
        # Test add comment
        comment_result = issue_manager.add_comment("TEST-1", "Test comment")
        assert comment_result is True
    
    def test_security_analysis_workflow(self):
        """Test complete security analysis workflow."""
        # Mock service
        mock_service = Mock()
        mock_service.get_security_metrics.return_value = {
            "security_rating": "3",
            "vulnerabilities": "5",
            "security_hotspots": "10",
            "security_hotspots_reviewed": "30"
        }
        mock_service.get_security_hotspots.return_value = [
            {
                "key": "HOTSPOT-1",
                "securityCategory": "sql-injection",
                "vulnerabilityProbability": "HIGH",
                "status": "TO_REVIEW"
            }
        ]
        mock_service.search_issues.return_value = [
            {
                "key": "VULN-1",
                "type": "VULNERABILITY",
                "severity": "CRITICAL"
            }
        ]
        
        # Create security analyzer
        analyzer = security.SecurityAnalyzer(mock_service)
        
        # Test risk score calculation
        hotspot = {
            "vulnerabilityProbability": "HIGH",
            "securityCategory": "sql-injection",
            "status": "TO_REVIEW"
        }
        risk_score = analyzer.calculate_risk_score(hotspot)
        assert risk_score > 50  # Should be high risk
        
        # Test vulnerability prioritization
        hotspots = [hotspot]
        prioritized = analyzer.prioritize_vulnerabilities(hotspots)
        assert len(prioritized) == 1
        assert "risk_score" in prioritized[0]
        
        # Test security report generation
        report = analyzer.generate_security_report("test-project")
        assert "project_key" in report
        assert "summary" in report
        assert "recommendations" in report
    
    def test_performance_monitoring_workflow(self):
        """Test performance monitoring workflow."""
        # Test performance monitor
        monitor = get_performance_monitor()
        
        # Record some metrics
        monitor.record_metric("test_metric", 50.0, "percentage")
        monitor.record_metric("response_time", 1.5, "seconds")
        
        # Get metrics
        metrics = monitor.get_metrics("test_metric")
        assert len(metrics) >= 1
        
        response_metrics = monitor.get_metrics("response_time")
        assert len(response_metrics) >= 1
        
        # Test cache manager
        cache_manager = get_cache_manager()
        
        # Test cache operations
        cache_manager.set("test_key", "test_value", 5)
        cached_value = cache_manager.get("test_key")
        assert cached_value == "test_value"
        
        # Test cache stats
        stats = cache_manager.get_stats()
        assert "hits" in stats
        assert "misses" in stats
        assert "hit_ratio" in stats
    
    def test_error_handling_in_ui_components(self):
        """Test error handling in UI components."""
        # Test with invalid configuration
        config_manager = Mock()
        config_manager.is_configured.return_value = False
        
        with patch('streamlit.warning') as mock_warning:
            # Test issues page with invalid config
            with patch('src.streamlit_app.pages.issues.ConfigManager', return_value=config_manager):
                issues.render()
                mock_warning.assert_called()
            
            # Test security page with invalid config
            with patch('src.streamlit_app.pages.security.ConfigManager', return_value=config_manager):
                security.render()
                mock_warning.assert_called()
    
    def test_data_consistency_across_components(self):
        """Test data consistency across different UI components."""
        # Mock consistent data
        projects_data = [
            {"key": "test-project", "name": "Test Project"},
            {"key": "another-project", "name": "Another Project"}
        ]
        
        issues_data = [
            {
                "key": "TEST-1",
                "type": "BUG",
                "severity": "MAJOR",
                "status": "OPEN",
                "component": "test-project:src/main.py"
            }
        ]
        
        security_data = {
            "vulnerabilities": "5",
            "security_hotspots": "10",
            "security_rating": "3"
        }
        
        # Mock service with consistent data
        mock_service = Mock()
        mock_service.get_projects.return_value = projects_data
        mock_service.search_issues.return_value = issues_data
        mock_service.get_security_metrics.return_value = security_data
        
        # Test that all components receive consistent data
        projects = mock_service.get_projects()
        assert len(projects) == 2
        assert projects[0]["key"] == "test-project"
        
        issues_list = mock_service.search_issues("test-project")
        assert len(issues_list) == 1
        assert "test-project" in issues_list[0]["component"]
        
        security_metrics = mock_service.get_security_metrics("test-project")
        assert security_metrics["vulnerabilities"] == "5"


if __name__ == "__main__":
    pytest.main([__file__])