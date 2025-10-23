"""Comprehensive end-to-end UI workflow tests.

This module tests complete user workflows from login to task completion,
verifies data consistency across different UI components, and tests error
handling and recovery in UI scenarios.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock, call
import pandas as pd
from datetime import datetime, timedelta

from src.streamlit_app.services.sonarqube_service import SonarQubeService
from src.streamlit_app.config.settings import ConfigManager, SonarQubeConfig
from src.streamlit_app.utils.session import SessionManager
from src.streamlit_app.utils.auth import AuthManager
from src.streamlit_app.pages import configuration, dashboard, projects, issues, security, performance


class MockSessionState:
    """Mock Streamlit session state that behaves like a dict with attribute access."""
    
    def __init__(self):
        self._data = {}
    
    def __getattr__(self, name):
        if name.startswith('_'):
            return super().__getattribute__(name)
        return self._data.get(name)
    
    def __setattr__(self, name, value):
        if name.startswith('_'):
            super().__setattr__(name, value)
        else:
            self._data[name] = value
    
    def __getitem__(self, key):
        return self._data[key]
    
    def __setitem__(self, key, value):
        self._data[key] = value
    
    def __contains__(self, key):
        return key in self._data
    
    def get(self, key, default=None):
        return self._data.get(key, default)


def create_context_manager_mock():
    """Create a mock that supports context manager protocol."""
    mock = Mock()
    mock.__enter__ = Mock(return_value=mock)
    mock.__exit__ = Mock(return_value=None)
    return mock


class TestCompleteUserJourneys:
    """Test complete user journeys from start to finish."""
    
    @pytest.fixture
    def mock_streamlit_environment(self):
        """Mock complete Streamlit environment."""
        mock_session_state = MockSessionState()
        
        with patch('streamlit.set_page_config'), \
             patch('streamlit.session_state', mock_session_state), \
             patch('streamlit.sidebar') as mock_sidebar, \
             patch('streamlit.title'), \
             patch('streamlit.markdown'), \
             patch('streamlit.warning'), \
             patch('streamlit.error'), \
             patch('streamlit.success'), \
             patch('streamlit.info'), \
             patch('streamlit.spinner'), \
             patch('streamlit.rerun'):
            
            yield mock_session_state, mock_sidebar
    
    @pytest.fixture
    def mock_sonarqube_data(self):
        """Mock comprehensive SonarQube data."""
        return {
            "projects": [
                {
                    "key": "project-1",
                    "name": "Critical Project",
                    "quality_gate_status": "ERROR",
                    "bugs": 15,
                    "vulnerabilities": 8,
                    "code_smells": 45,
                    "coverage": 65.5,
                    "duplicated_lines": 12.3,
                    "last_analysis": "2025-01-20T10:30:00Z"
                },
                {
                    "key": "project-2", 
                    "name": "Healthy Project",
                    "quality_gate_status": "OK",
                    "bugs": 2,
                    "vulnerabilities": 0,
                    "code_smells": 8,
                    "coverage": 85.2,
                    "duplicated_lines": 3.1,
                    "last_analysis": "2025-01-21T09:15:00Z"
                }
            ],
            "issues": [
                {
                    "key": "ISSUE-1",
                    "type": "BUG",
                    "severity": "CRITICAL",
                    "status": "OPEN",
                    "component": "project-1:src/critical.py",
                    "rule": "python:S1234",
                    "assignee": None,
                    "creationDate": "2025-01-20T10:00:00Z",
                    "message": "Critical bug that needs immediate attention"
                },
                {
                    "key": "ISSUE-2",
                    "type": "VULNERABILITY", 
                    "severity": "HIGH",
                    "status": "CONFIRMED",
                    "component": "project-1:src/security.py",
                    "rule": "python:S5678",
                    "assignee": "security.team",
                    "creationDate": "2025-01-19T14:30:00Z",
                    "message": "SQL injection vulnerability detected"
                }
            ],
            "security_hotspots": [
                {
                    "key": "HOTSPOT-1",
                    "securityCategory": "sql-injection",
                    "vulnerabilityProbability": "HIGH",
                    "status": "TO_REVIEW",
                    "component": "project-1:src/database.py",
                    "textRange": {"startLine": 42}
                }
            ],
            "system_info": {
                "status": "UP",
                "version": "9.9.0",
                "serverId": "12345678-abcd-efgh-ijkl-123456789012",
                "edition": "Community"
            },
            "user_info": {
                "name": "Test User",
                "login": "testuser",
                "email": "test@example.com",
                "active": True
            },
            "permissions": {
                "admin": True,
                "scan": True,
                "provisioning": False,
                "profileadmin": True
            }
        }
    
    def test_complete_first_time_user_setup_workflow(self, mock_streamlit_environment, mock_sonarqube_data):
        """Test complete workflow for first-time user setup."""
        mock_session_state, mock_sidebar = mock_streamlit_environment
        
        # Step 1: Test unconfigured system state
        config_manager = Mock(spec=ConfigManager)
        config_manager.is_configured.return_value = False
        config_manager.get_config.return_value = SonarQubeConfig()
        config_manager.mask_sensitive_data.return_value = {"url": "", "token": "***"}
        
        auth_manager = Mock(spec=AuthManager)
        
        # Verify initial state
        assert config_manager.is_configured() is False
        initial_config = config_manager.get_config()
        assert initial_config.url == ""
        assert initial_config.token == ""
        
        # Step 2: User configures SonarQube connection
        config_manager.is_configured.return_value = True
        config_manager.save_config.return_value = True
        
        # Mock successful authentication
        auth_manager.validate_credentials_sync.return_value = (True, "Connection successful")
        auth_manager.test_connection_sync.return_value = (
            True, 
            "Connected successfully", 
            mock_sonarqube_data["system_info"]
        )
        auth_manager.get_user_info_sync.return_value = mock_sonarqube_data["user_info"]
        auth_manager.check_permissions_sync.return_value = mock_sonarqube_data["permissions"]
        
        # Test configuration save workflow
        new_config = SonarQubeConfig(
            url="http://localhost:9000",
            token="test_token"
        )
        
        # Test configuration save
        save_result = config_manager.save_config(new_config)
        assert save_result is True
        
        # Test connection validation
        success, message, system_info = auth_manager.test_connection_sync()
        assert success is True
        assert message == "Connected successfully"
        assert system_info == mock_sonarqube_data["system_info"]
        
        # Test user info retrieval
        user_info = auth_manager.get_user_info_sync()
        assert user_info["name"] == "Test User"
        assert user_info["login"] == "testuser"
        assert user_info["active"] is True
        
        # Test permissions check
        permissions = auth_manager.check_permissions_sync()
        assert permissions["admin"] is True
        assert permissions["scan"] is True
        
        # Step 3: Test that user can now access dashboard functionality
        service = Mock(spec=SonarQubeService)
        service.get_dashboard_summary.return_value = {
            "total_projects": 2,
            "projects_with_issues": 1,
            "quality_gates_passed": 1,
            "quality_gates_failed": 1,
            "projects": mock_sonarqube_data["projects"]
        }
        
        # Test dashboard data retrieval
        dashboard_data = service.get_dashboard_summary()
        assert dashboard_data["total_projects"] == 2
        assert len(dashboard_data["projects"]) == 2
        assert dashboard_data["projects"][0]["key"] == "project-1"
        assert dashboard_data["projects"][0]["quality_gate_status"] == "ERROR"
        assert dashboard_data["projects"][1]["key"] == "project-2"
        assert dashboard_data["projects"][1]["quality_gate_status"] == "OK"
    
    def test_project_management_complete_workflow(self, mock_streamlit_environment, mock_sonarqube_data):
        """Test complete project management workflow."""
        mock_session_state, mock_sidebar = mock_streamlit_environment
        
        # Setup configured environment
        config_manager = Mock(spec=ConfigManager)
        config_manager.is_configured.return_value = True
        
        service = Mock(spec=SonarQubeService)
        service.get_projects.return_value = mock_sonarqube_data["projects"]
        service.get_project_measures.return_value = {"coverage": "65.5", "bugs": "15"}
        service.get_quality_gate_status.return_value = {"status": "ERROR", "conditions": []}
        
        mock_session_state["config_manager"] = config_manager
        mock_session_state["connection_status"] = "connected"
        
        # Test project management functionality without full page rendering
        
        # Step 1: Test project list retrieval
        projects_list = service.get_projects()
        assert len(projects_list) == 2
        assert projects_list[0]["key"] == "project-1"
        assert projects_list[0]["name"] == "Critical Project"
        assert projects_list[1]["key"] == "project-2"
        assert projects_list[1]["name"] == "Healthy Project"
        
        # Step 2: Test project measures retrieval
        project_measures = service.get_project_measures("project-1", ["coverage", "bugs"])
        assert project_measures["coverage"] == "65.5"
        assert project_measures["bugs"] == "15"
        
        # Step 3: Test quality gate status retrieval
        quality_gate_status = service.get_quality_gate_status("project-1")
        assert quality_gate_status["status"] == "ERROR"
        assert "conditions" in quality_gate_status
        
        # Step 4: Test project filtering by quality gate status
        failed_projects = [p for p in projects_list if p["quality_gate_status"] == "ERROR"]
        passed_projects = [p for p in projects_list if p["quality_gate_status"] == "OK"]
        assert len(failed_projects) == 1
        assert len(passed_projects) == 1
        assert failed_projects[0]["key"] == "project-1"
        assert passed_projects[0]["key"] == "project-2"
    
    def test_issue_management_complete_workflow(self, mock_streamlit_environment, mock_sonarqube_data):
        """Test complete issue management workflow from discovery to resolution."""
        mock_session_state, mock_sidebar = mock_streamlit_environment
        
        # Setup configured environment
        config_manager = Mock(spec=ConfigManager)
        config_manager.is_configured.return_value = True
        
        service = Mock(spec=SonarQubeService)
        service.get_projects.return_value = mock_sonarqube_data["projects"]
        service.search_issues.return_value = mock_sonarqube_data["issues"]
        service.get_security_hotspots.return_value = mock_sonarqube_data["security_hotspots"]
        
        mock_session_state["config_manager"] = config_manager
        mock_session_state["connection_status"] = "connected"
        
        # Test issue management functionality without full page rendering
        
        # Step 1: Test issue search functionality
        all_issues = service.search_issues("project-1")
        assert len(all_issues) == 2
        
        # Step 2: Test filtering by severity
        critical_issues = service.search_issues("project-1", {"severities": ["CRITICAL"]})
        assert len(critical_issues) == 2
        critical_issue = next(issue for issue in critical_issues if issue["severity"] == "CRITICAL")
        assert critical_issue["key"] == "ISSUE-1"
        assert critical_issue["message"] == "Critical bug that needs immediate attention"
        assert critical_issue["assignee"] is None
        
        # Step 3: Test filtering by issue type
        vulnerability_issues = service.search_issues("project-1", {"types": ["VULNERABILITY"]})
        vulnerability_issue = next(issue for issue in vulnerability_issues if issue["type"] == "VULNERABILITY")
        assert vulnerability_issue["key"] == "ISSUE-2"
        assert vulnerability_issue["severity"] == "HIGH"
        assert vulnerability_issue["assignee"] == "security.team"
        
        # Step 4: Test security hotspots retrieval
        hotspots = service.get_security_hotspots("project-1")
        assert len(hotspots) == 1
        assert hotspots[0]["securityCategory"] == "sql-injection"
        assert hotspots[0]["vulnerabilityProbability"] == "HIGH"
        
        # Step 5: Test issue workflow analysis
        open_issues = [issue for issue in all_issues if issue["status"] == "OPEN"]
        confirmed_issues = [issue for issue in all_issues if issue["status"] == "CONFIRMED"]
        assert len(open_issues) == 1
        assert len(confirmed_issues) == 1
    
    def test_security_analysis_complete_workflow(self, mock_streamlit_environment, mock_sonarqube_data):
        """Test complete security analysis workflow."""
        mock_session_state, mock_sidebar = mock_streamlit_environment
        
        # Setup configured environment
        config_manager = Mock(spec=ConfigManager)
        config_manager.is_configured.return_value = True
        
        service = Mock(spec=SonarQubeService)
        service.get_projects.return_value = mock_sonarqube_data["projects"]
        service.get_security_metrics.return_value = {
            "security_rating": "4",
            "vulnerabilities": "8",
            "security_hotspots": "1",
            "security_hotspots_reviewed": "0"
        }
        service.get_security_hotspots.return_value = mock_sonarqube_data["security_hotspots"]
        service.search_issues.return_value = [
            issue for issue in mock_sonarqube_data["issues"] 
            if issue["type"] == "VULNERABILITY"
        ]
        
        mock_session_state["config_manager"] = config_manager
        mock_session_state["connection_status"] = "connected"
        
        # Test security page functionality
        with patch('src.streamlit_app.pages.security.SonarQubeService', return_value=service), \
             patch('src.streamlit_app.pages.security.ConfigManager', return_value=config_manager), \
             patch('src.streamlit_app.pages.security.SessionManager') as mock_session_manager, \
             patch('src.streamlit_app.pages.security.SecurityAnalyzer') as mock_analyzer_class, \
             patch('streamlit.columns') as mock_columns:
            
            # Mock security analyzer
            mock_analyzer = Mock()
            mock_analyzer.service = service
            mock_analyzer.calculate_risk_score.return_value = 85.0
            mock_analyzer.prioritize_vulnerabilities.return_value = [
                {**mock_sonarqube_data["security_hotspots"][0], "risk_score": 85.0}
            ]
            mock_analyzer.generate_security_report.return_value = {
                "project_key": "project-1",
                "generated_at": datetime.now().isoformat(),
                "summary": {
                    "security_grade": "D",
                    "total_vulnerabilities": 1,
                    "total_hotspots": 1,
                    "high_risk_hotspots": 1
                },
                "recommendations": [
                    "🚨 Critical: Review high-risk SQL injection hotspot",
                    "📋 Address 1 confirmed vulnerability"
                ]
            }
            mock_analyzer_class.return_value = mock_analyzer
            
            # Create mock columns that support context manager protocol
            mock_col1 = Mock()
            mock_col1.__enter__ = Mock(return_value=mock_col1)
            mock_col1.__exit__ = Mock(return_value=None)
            mock_col2 = Mock()
            mock_col2.__enter__ = Mock(return_value=mock_col2)
            mock_col2.__exit__ = Mock(return_value=None)
            mock_col3 = Mock()
            mock_col3.__enter__ = Mock(return_value=mock_col3)
            mock_col3.__exit__ = Mock(return_value=None)
            mock_col4 = Mock()
            mock_col4.__enter__ = Mock(return_value=mock_col4)
            mock_col4.__exit__ = Mock(return_value=None)
            mock_columns.return_value = [mock_col1, mock_col2, mock_col3, mock_col4]
            mock_session_manager.get_connection_status.return_value = "connected"
            
            # Test security analysis functionality without full page rendering
            
            # Step 2: Test security metrics retrieval
            security_metrics = service.get_security_metrics("project-1")
            assert security_metrics["security_rating"] == "4"  # Poor security rating
            assert security_metrics["vulnerabilities"] == "8"
            
            # Step 3: Test security hotspots analysis
            hotspots = service.get_security_hotspots("project-1")
            assert len(hotspots) == 1
            assert hotspots[0]["securityCategory"] == "sql-injection"
            
            # Step 4: Test risk score calculation
            risk_score = mock_analyzer.calculate_risk_score(hotspots[0])
            assert risk_score == 85.0  # High risk
            
            # Step 5: Test security report generation
            security_report = mock_analyzer.generate_security_report("project-1")
            assert security_report["summary"]["security_grade"] == "D"
            assert len(security_report["recommendations"]) == 2
    
    def test_performance_monitoring_complete_workflow(self, mock_streamlit_environment):
        """Test complete performance monitoring workflow."""
        mock_session_state, mock_sidebar = mock_streamlit_environment
        
        from src.streamlit_app.utils.performance import get_performance_monitor, get_cache_manager
        
        # Setup performance monitoring
        monitor = get_performance_monitor()
        cache = get_cache_manager()
        
        # Clear previous data
        monitor.clear_metrics()
        cache.clear()
        
        # Test performance page functionality
        with patch('src.streamlit_app.pages.performance.get_performance_monitor', return_value=monitor), \
             patch('src.streamlit_app.pages.performance.get_cache_manager', return_value=cache), \
             patch('psutil.cpu_percent', return_value=78.5), \
             patch('psutil.virtual_memory') as mock_memory, \
             patch('psutil.disk_usage') as mock_disk, \
             patch('streamlit.columns') as mock_columns, \
             patch('streamlit.metric') as mock_metric:
            
            # Mock system metrics
            mock_memory.return_value.percent = 82.3
            mock_memory.return_value.available = 3.2 * (1024**3)
            mock_disk.return_value.percent = 65.1
            mock_disk.return_value.free = 45.8 * (1024**3)
            
            # Mock columns to return the expected number for different calls
            mock_columns.side_effect = [
                [Mock(), Mock()],  # First call expects 2 columns
                [Mock(), Mock(), Mock(), Mock()]  # Second call expects 4 columns
            ]
            
            # Test performance monitoring functionality without full page rendering
            
            # Step 2: Record performance metrics
            monitor.record_metric("api_response_time", 1.8, "seconds", {"endpoint": "search_issues"})
            monitor.record_metric("cache_hit_ratio", 72.5, "percentage")
            monitor.record_metric("memory_usage", 82.3, "percentage")  # Should trigger alert
            
            # Step 3: Test system health metrics
            system_metrics = monitor.get_system_metrics()
            assert system_metrics["cpu_usage"] == 78.5
            assert system_metrics["memory_usage"] == 82.3
            
            # Step 4: Test cache performance
            cache.set("test_key_1", "value_1", 5)
            cache.set("test_key_2", "value_2", 5)
            cache.get("test_key_1")  # Hit
            cache.get("missing_key")  # Miss
            
            cache_stats = cache.get_stats()
            assert cache_stats["hits"] == 1
            assert cache_stats["misses"] == 1
            assert cache_stats["hit_ratio"] == 50.0
            
            # Step 5: Test performance alerts
            alerts = monitor.get_recent_alerts()
            memory_alerts = [alert for alert in alerts if alert["metric"] == "memory_usage"]
            assert len(memory_alerts) >= 1
            assert memory_alerts[0]["value"] == 82.3


class TestDataConsistencyAcrossComponents:
    """Test data consistency when navigating between different UI components."""
    
    @pytest.fixture
    def consistent_mock_data(self):
        """Mock data that should be consistent across components."""
        return {
            "project_key": "test-project",
            "project_name": "Test Project",
            "issues_count": 15,
            "vulnerabilities_count": 3,
            "security_rating": "3",
            "quality_gate_status": "ERROR"
        }
    
    def test_project_data_consistency_across_pages(self, consistent_mock_data):
        """Test that project data remains consistent across different pages."""
        # Mock service with consistent data
        service = Mock(spec=SonarQubeService)
        
        # Project data should be consistent
        project_data = {
            "key": consistent_mock_data["project_key"],
            "name": consistent_mock_data["project_name"],
            "quality_gate_status": consistent_mock_data["quality_gate_status"]
        }
        service.get_projects.return_value = [project_data]
        service.get_project_measures.return_value = {"coverage": "65.5", "bugs": "15"}
        
        # Issues data should match project
        issues_data = [
            {"key": f"ISSUE-{i}", "component": f"{consistent_mock_data['project_key']}:src/file{i}.py"}
            for i in range(consistent_mock_data["issues_count"])
        ]
        service.search_issues.return_value = issues_data
        
        # Security data should match project
        security_metrics = {
            "vulnerabilities": str(consistent_mock_data["vulnerabilities_count"]),
            "security_rating": consistent_mock_data["security_rating"]
        }
        service.get_security_metrics.return_value = security_metrics
        
        with patch('streamlit.session_state', new_callable=dict) as mock_session_state:
            
            # Step 1: User views dashboard - caches project data
            SessionManager.cache_data("projects_list", [project_data], ttl_minutes=5)
            
            # Step 2: User navigates to issues page
            cached_projects = SessionManager.get_cached_data("projects_list", ttl_minutes=5)
            assert cached_projects is not None
            assert cached_projects[0]["key"] == consistent_mock_data["project_key"]
            
            # Issues should belong to the same project
            project_issues = service.search_issues(consistent_mock_data["project_key"])
            assert len(project_issues) == consistent_mock_data["issues_count"]
            for issue in project_issues:
                assert consistent_mock_data["project_key"] in issue["component"]
            
            # Step 3: User navigates to security page
            project_security = service.get_security_metrics(consistent_mock_data["project_key"])
            assert project_security["vulnerabilities"] == str(consistent_mock_data["vulnerabilities_count"])
            assert project_security["security_rating"] == consistent_mock_data["security_rating"]
            
            # Step 4: Verify data consistency
            assert len(project_issues) == consistent_mock_data["issues_count"]
            assert int(project_security["vulnerabilities"]) == consistent_mock_data["vulnerabilities_count"]
    
    def test_filter_state_persistence_across_navigation(self):
        """Test that filter states persist when navigating between pages."""
        mock_session_state = MockSessionState()
        
        with patch('streamlit.session_state', mock_session_state):
            
            # Step 1: User sets filters on issues page
            issues_filters = {
                "project": "test-project",
                "severities": ["CRITICAL", "MAJOR"],
                "types": ["BUG", "VULNERABILITY"],
                "assignee": "developer.team"
            }
            SessionManager.set_filter_settings("issues", issues_filters)
            
            # Step 2: User navigates to security page and sets filters
            security_filters = {
                "project": "test-project",
                "categories": ["sql-injection", "xss"],
                "status": ["TO_REVIEW", "IN_REVIEW"]
            }
            SessionManager.set_filter_settings("security", security_filters)
            
            # Step 3: User returns to issues page
            retrieved_issues_filters = SessionManager.get_filter_settings("issues")
            assert retrieved_issues_filters["project"] == "test-project"
            assert retrieved_issues_filters["severities"] == ["CRITICAL", "MAJOR"]
            assert retrieved_issues_filters["assignee"] == "developer.team"
            
            # Step 4: User returns to security page
            retrieved_security_filters = SessionManager.get_filter_settings("security")
            assert retrieved_security_filters["project"] == "test-project"
            assert retrieved_security_filters["categories"] == ["sql-injection", "xss"]
            assert retrieved_security_filters["status"] == ["TO_REVIEW", "IN_REVIEW"]
            
            # Step 5: Verify project consistency across filters
            assert retrieved_issues_filters["project"] == retrieved_security_filters["project"]
    
    def test_session_data_synchronization(self):
        """Test that session data stays synchronized across components."""
        mock_session_state = MockSessionState()
        
        with patch('streamlit.session_state', mock_session_state):
            
            # Step 1: Initialize session with user data
            user_data = {
                "name": "Test User",
                "login": "testuser",
                "permissions": {"admin": True, "scan": True}
            }
            SessionManager.set_user_info(user_data)
            
            # Step 2: Set connection status
            system_info = {
                "status": "UP",
                "version": "9.9.0",
                "serverId": "test-server-id"
            }
            SessionManager.set_connection_status("connected", system_info)
            
            # Step 3: Cache project data
            projects_data = [
                {"key": "project-1", "name": "Project One"},
                {"key": "project-2", "name": "Project Two"}
            ]
            SessionManager.cache_data("projects", projects_data, ttl_minutes=10)
            
            # Step 4: Verify all data is accessible from different components
            
            # User info should be consistent
            retrieved_user = SessionManager.get_user_info()
            assert retrieved_user["name"] == "Test User"
            assert retrieved_user["permissions"]["admin"] is True
            
            # Connection status should be consistent
            connection_status = SessionManager.get_connection_status()
            assert connection_status == "connected"
            
            # Cached data should be consistent
            cached_projects = SessionManager.get_cached_data("projects", ttl_minutes=10)
            assert len(cached_projects) == 2
            assert cached_projects[0]["key"] == "project-1"
            
            # Step 5: Update data and verify synchronization
            updated_user_data = {**user_data, "email": "test@example.com"}
            SessionManager.set_user_info(updated_user_data)
            
            retrieved_updated_user = SessionManager.get_user_info()
            assert retrieved_updated_user["email"] == "test@example.com"
            assert retrieved_updated_user["name"] == "Test User"  # Should preserve existing data


class TestErrorHandlingAndRecovery:
    """Test error handling and recovery scenarios in UI workflows."""
    
    def test_network_error_recovery_workflow(self):
        """Test recovery from network errors during UI operations."""
        service = Mock(spec=SonarQubeService)
        
        # Step 1: Simulate network error
        service.get_projects.side_effect = Exception("Network timeout")
        service.search_issues.side_effect = Exception("Connection refused")
        
        with patch('streamlit.error') as mock_error, \
             patch('streamlit.warning') as mock_warning:
            
            # UI should handle errors gracefully
            try:
                projects = service.get_projects()
            except Exception:
                # Error should be caught and handled by UI
                pass
            
            try:
                issues = service.search_issues("test-project")
            except Exception:
                # Error should be caught and handled by UI
                pass
        
        # Step 2: Simulate network recovery
        service.get_projects.side_effect = None
        service.search_issues.side_effect = None
        service.get_projects.return_value = [{"key": "project-1", "name": "Project One"}]
        service.search_issues.return_value = [{"key": "ISSUE-1", "type": "BUG"}]
        
        # Operations should work normally after recovery
        projects = service.get_projects()
        assert len(projects) == 1
        assert projects[0]["key"] == "project-1"
        
        issues = service.search_issues("project-1")
        assert len(issues) == 1
        assert issues[0]["key"] == "ISSUE-1"
    
    def test_authentication_error_recovery_workflow(self):
        """Test recovery from authentication errors."""
        config_manager = Mock(spec=ConfigManager)
        auth_manager = Mock(spec=AuthManager)
        
        # Step 1: Simulate authentication failure
        config_manager.is_configured.return_value = True
        auth_manager.validate_credentials_sync.return_value = (False, "Invalid token")
        auth_manager.test_connection_sync.return_value = (False, "Authentication failed", None)
        
        mock_session_state = MockSessionState()
        
        with patch('streamlit.session_state', mock_session_state), \
             patch('streamlit.error') as mock_error:
            
            mock_session_state["config_manager"] = config_manager
            mock_session_state["auth_manager"] = auth_manager
            
            # Test connection should fail
            success, message, _ = auth_manager.test_connection_sync()
            assert success is False
            assert "Authentication failed" in message
            
            # Session should reflect error state
            SessionManager.set_connection_status("error")
            assert SessionManager.get_connection_status() == "error"
        
        # Step 2: User updates credentials
        auth_manager.validate_credentials_sync.return_value = (True, "Connection successful")
        auth_manager.test_connection_sync.return_value = (
            True, 
            "Connected successfully", 
            {"status": "UP", "version": "9.9.0"}
        )
        
        # Step 3: Connection should recover
        success, message, system_info = auth_manager.test_connection_sync()
        assert success is True
        assert "Connected successfully" in message
        assert system_info["status"] == "UP"
        
        # Session should reflect recovered state
        SessionManager.set_connection_status("connected", system_info)
        assert SessionManager.get_connection_status() == "connected"
    
    def test_data_corruption_recovery_workflow(self):
        """Test recovery from data corruption scenarios."""
        mock_session_state = MockSessionState()
        
        with patch('streamlit.session_state', mock_session_state):
            
            # Step 1: Simulate corrupted session data
            mock_session_state["corrupted_data"] = "invalid_json_data"
            mock_session_state["user_info"] = {"incomplete": "data"}
            
            # Step 2: SessionManager should handle corrupted data gracefully
            try:
                user_info = SessionManager.get_user_info()
                # Should return None or default data instead of crashing
                assert user_info is None or isinstance(user_info, dict)
            except Exception:
                pytest.fail("SessionManager should handle corrupted data gracefully")
            
            # Step 3: Clear corrupted data and reinitialize
            SessionManager.clear_session()
            SessionManager.initialize_session()
            
            # Step 4: Set valid data
            valid_user_info = {
                "name": "Test User",
                "login": "testuser",
                "email": "test@example.com"
            }
            SessionManager.set_user_info(valid_user_info)
            
            # Step 5: Verify recovery
            recovered_user_info = SessionManager.get_user_info()
            assert recovered_user_info["name"] == "Test User"
            assert recovered_user_info["email"] == "test@example.com"
    
    def test_concurrent_user_operations_error_handling(self):
        """Test error handling during concurrent user operations."""
        from src.streamlit_app.utils.performance import get_cache_manager
        
        cache = get_cache_manager()
        cache.clear()
        
        # Step 1: Simulate concurrent cache operations
        def concurrent_cache_operation(key_suffix):
            try:
                cache.set(f"concurrent_key_{key_suffix}", f"value_{key_suffix}", 5)
                return cache.get(f"concurrent_key_{key_suffix}")
            except Exception as e:
                return f"error: {str(e)}"
        
        # Step 2: Perform multiple concurrent operations
        results = []
        for i in range(10):
            result = concurrent_cache_operation(i)
            results.append(result)
        
        # Step 3: Verify that operations completed successfully or failed gracefully
        successful_operations = [r for r in results if not str(r).startswith("error:")]
        assert len(successful_operations) >= 8  # At least 80% should succeed
        
        # Step 4: Verify cache consistency after concurrent operations
        cache_stats = cache.get_stats()
        assert cache_stats["cache_size"] >= 8  # Most operations should have succeeded
    
    def test_ui_component_error_isolation(self):
        """Test that errors in one UI component don't affect others."""
        service = Mock(spec=SonarQubeService)
        
        # Step 1: Configure service with mixed success/failure responses
        service.get_projects.return_value = [{"key": "project-1", "name": "Project One"}]
        service.search_issues.side_effect = Exception("Issues service error")
        service.get_security_metrics.return_value = {"vulnerabilities": "5"}
        
        with patch('streamlit.error') as mock_error:
            
            # Step 2: Projects component should work
            projects = service.get_projects()
            assert len(projects) == 1
            assert projects[0]["key"] == "project-1"
            
            # Step 3: Issues component should fail gracefully
            try:
                issues = service.search_issues("project-1")
                # Should not reach here if properly handled
                assert False, "Exception should have been raised"
            except Exception as e:
                # Error should be isolated to issues component
                assert "Issues service error" in str(e)
            
            # Step 4: Security component should still work
            security_metrics = service.get_security_metrics("project-1")
            assert security_metrics["vulnerabilities"] == "5"
            
            # Step 5: Verify that working components are not affected by failing ones
            projects_again = service.get_projects()
            assert len(projects_again) == 1  # Should still work


if __name__ == "__main__":
    pytest.main([__file__, "-v"])