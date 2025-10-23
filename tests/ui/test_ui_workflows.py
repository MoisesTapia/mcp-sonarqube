"""End-to-end UI workflow tests."""

import pytest
from unittest.mock import Mock, patch, MagicMock
import pandas as pd
from datetime import datetime, timedelta

from src.streamlit_app.services.sonarqube_service import SonarQubeService
from src.streamlit_app.config.settings import ConfigManager
from src.streamlit_app.utils.session import SessionManager
from src.streamlit_app.pages import issues, security, performance


class TestCompleteUserWorkflows:
    """Test complete user workflows from start to finish."""
    
    @pytest.fixture
    def mock_configured_environment(self):
        """Mock a fully configured environment."""
        config_manager = Mock(spec=ConfigManager)
        config_manager.is_configured.return_value = True
        config_manager.get_connection_params.return_value = {
            "base_url": "http://localhost:9000",
            "token": "test_token"
        }
        
        service = Mock(spec=SonarQubeService)
        service.get_projects.return_value = [
            {"key": "project-1", "name": "Project One"},
            {"key": "project-2", "name": "Project Two"}
        ]
        
        return config_manager, service
    
    def test_user_login_to_issue_management_workflow(self, mock_configured_environment):
        """Test complete workflow from login to managing issues."""
        config_manager, service = mock_configured_environment
        
        # Mock issue data
        service.search_issues.return_value = [
            {
                "key": "ISSUE-1",
                "type": "BUG",
                "severity": "MAJOR",
                "status": "OPEN",
                "component": "project-1:src/main.py",
                "rule": "python:S1234",
                "assignee": None,
                "creationDate": "2025-01-01T10:00:00Z",
                "message": "Potential null pointer dereference"
            },
            {
                "key": "ISSUE-2",
                "type": "VULNERABILITY",
                "severity": "CRITICAL",
                "status": "CONFIRMED",
                "component": "project-1:src/auth.py",
                "rule": "python:S5678",
                "assignee": "john.doe",
                "creationDate": "2025-01-02T11:00:00Z",
                "message": "SQL injection vulnerability"
            }
        ]
        
        with patch('src.streamlit_app.pages.issues.SonarQubeService', return_value=service), \
             patch('src.streamlit_app.pages.issues.ConfigManager', return_value=config_manager), \
             patch('streamlit.session_state', new_callable=dict) as mock_session_state:
            
            # Step 1: User navigates to issues page
            issue_manager = issues.IssueManager(service)
            
            # Step 2: User searches for issues
            search_results = issue_manager.search_issues("project-1")
            assert len(search_results) == 2
            assert search_results[0]["key"] == "ISSUE-1"
            assert search_results[1]["key"] == "ISSUE-2"
            
            # Step 3: User filters issues by severity
            filtered_results = issue_manager.search_issues(
                "project-1", 
                {"severities": ["CRITICAL"]}
            )
            # Service should be called with filters
            service.search_issues.assert_called_with("project-1", {"severities": ["CRITICAL"]})
            
            # Step 4: User assigns an issue
            with patch.object(issue_manager, 'update_issue', return_value=True) as mock_update:
                result = issue_manager.update_issue("ISSUE-1", {"assignee": "jane.doe"})
                assert result is True
                mock_update.assert_called_with("ISSUE-1", {"assignee": "jane.doe"})
            
            # Step 5: User adds a comment
            with patch.object(issue_manager, 'add_comment', return_value=True) as mock_comment:
                result = issue_manager.add_comment("ISSUE-1", "Working on this issue")
                assert result is True
                mock_comment.assert_called_with("ISSUE-1", "Working on this issue")
    
    def test_security_analysis_complete_workflow(self, mock_configured_environment):
        """Test complete security analysis workflow."""
        config_manager, service = mock_configured_environment
        
        # Mock security data
        service.get_security_metrics.return_value = {
            "security_rating": "4",
            "vulnerabilities": "8",
            "security_hotspots": "15",
            "security_hotspots_reviewed": "40"
        }
        
        service.get_security_hotspots.return_value = [
            {
                "key": "HOTSPOT-1",
                "securityCategory": "sql-injection",
                "vulnerabilityProbability": "HIGH",
                "status": "TO_REVIEW",
                "component": "project-1:src/db.py",
                "textRange": {"startLine": 42}
            },
            {
                "key": "HOTSPOT-2",
                "securityCategory": "xss",
                "vulnerabilityProbability": "MEDIUM",
                "status": "IN_REVIEW",
                "component": "project-1:src/web.py",
                "textRange": {"startLine": 128}
            }
        ]
        
        service.search_issues.return_value = [
            {
                "key": "VULN-1",
                "type": "VULNERABILITY",
                "severity": "CRITICAL",
                "status": "OPEN"
            }
        ]
        
        with patch('src.streamlit_app.pages.security.SonarQubeService', return_value=service), \
             patch('src.streamlit_app.pages.security.ConfigManager', return_value=config_manager):
            
            # Step 1: Create security analyzer
            analyzer = security.SecurityAnalyzer(service)
            
            # Step 2: Calculate risk scores
            hotspot = service.get_security_hotspots.return_value[0]
            risk_score = analyzer.calculate_risk_score(hotspot)
            assert risk_score > 50  # High-risk SQL injection should have high score
            
            # Step 3: Prioritize vulnerabilities
            hotspots = service.get_security_hotspots.return_value
            prioritized = analyzer.prioritize_vulnerabilities(hotspots)
            assert len(prioritized) == 2
            assert all("risk_score" in h for h in prioritized)
            
            # Step 4: Generate security report
            report = analyzer.generate_security_report("project-1")
            
            # Verify report structure
            assert report["project_key"] == "project-1"
            assert "generated_at" in report
            assert "metrics" in report
            assert "summary" in report
            assert "recommendations" in report
            
            # Verify summary calculations
            summary = report["summary"]
            assert summary["security_grade"] == "D"  # Rating 4 = D
            assert summary["total_vulnerabilities"] == 1
            assert summary["total_hotspots"] == 2
            
            # Verify recommendations are generated
            assert len(report["recommendations"]) > 0
            assert any("Critical" in rec for rec in report["recommendations"])
    
    def test_performance_monitoring_workflow(self):
        """Test complete performance monitoring workflow."""
        from src.streamlit_app.utils.performance import (
            get_performance_monitor, 
            get_cache_manager,
            performance_timer
        )
        
        # Step 1: Initialize monitoring
        monitor = get_performance_monitor()
        cache = get_cache_manager()
        
        # Clear previous data
        monitor.clear_metrics()
        cache.clear()
        
        # Step 2: Simulate application usage with performance tracking
        @performance_timer("api_call")
        def simulate_api_call():
            import time
            time.sleep(0.05)  # 50ms
            return {"data": "api_response"}
        
        # Step 3: Make several API calls
        for i in range(5):
            result = simulate_api_call()
            assert result["data"] == "api_response"
            
            # Cache some results
            cache.set(f"api_result_{i}", result, 5)
        
        # Step 4: Generate cache hits and misses
        for i in range(3):
            cached_result = cache.get(f"api_result_{i}")  # Hits
            assert cached_result is not None
        
        for i in range(3, 6):
            cached_result = cache.get(f"missing_key_{i}")  # Misses
            assert cached_result is None
        
        # Step 5: Record system metrics
        with patch('psutil.cpu_percent', return_value=75.0), \
             patch('psutil.virtual_memory') as mock_memory, \
             patch('psutil.disk_usage') as mock_disk:
            
            mock_memory.return_value.percent = 85.0
            mock_memory.return_value.available = 2.0 * (1024**3)
            mock_disk.return_value.percent = 60.0
            mock_disk.return_value.free = 40.0 * (1024**3)
            
            system_metrics = monitor.get_system_metrics()
            
            # Record system metrics
            for metric_name, value in system_metrics.items():
                monitor.record_metric(
                    name=metric_name,
                    value=value,
                    unit="percentage" if "usage" in metric_name else "gb"
                )
        
        # Step 6: Verify performance data collection
        api_metrics = monitor.get_metrics("api_call")
        assert len(api_metrics) == 5
        assert all(m.value >= 0.05 for m in api_metrics)  # At least 50ms each
        
        # Step 7: Verify cache statistics
        cache_stats = cache.get_stats()
        assert cache_stats["hits"] == 3
        assert cache_stats["misses"] == 3
        assert cache_stats["hit_ratio"] == 50.0  # 50% hit ratio
        
        # Step 8: Verify alerts were generated for high resource usage
        alerts = monitor.get_recent_alerts()
        alert_metrics = [alert["metric"] for alert in alerts]
        assert "memory_usage" in alert_metrics  # 85% should trigger alert
    
    def test_error_recovery_workflow(self, mock_configured_environment):
        """Test error recovery in UI workflows."""
        config_manager, service = mock_configured_environment
        
        # Step 1: Simulate network error during issue search
        service.search_issues.side_effect = Exception("Network timeout")
        
        with patch('src.streamlit_app.pages.issues.SonarQubeService', return_value=service), \
             patch('src.streamlit_app.pages.issues.ConfigManager', return_value=config_manager), \
             patch('streamlit.error') as mock_error:
            
            issue_manager = issues.IssueManager(service)
            
            # Should handle error gracefully
            results = issue_manager.search_issues("project-1")
            assert results == []  # Should return empty list on error
        
        # Step 2: Simulate recovery - network works again
        service.search_issues.side_effect = None
        service.search_issues.return_value = [
            {"key": "ISSUE-1", "type": "BUG", "severity": "MAJOR"}
        ]
        
        # Should work normally after recovery
        results = issue_manager.search_issues("project-1")
        assert len(results) == 1
        assert results[0]["key"] == "ISSUE-1"
    
    def test_data_consistency_across_pages(self, mock_configured_environment):
        """Test data consistency when navigating between pages."""
        config_manager, service = mock_configured_environment
        
        # Mock consistent project data
        projects_data = [
            {"key": "project-1", "name": "Project One"},
            {"key": "project-2", "name": "Project Two"}
        ]
        service.get_projects.return_value = projects_data
        
        # Mock issues for project-1
        service.search_issues.return_value = [
            {
                "key": "ISSUE-1",
                "type": "VULNERABILITY",
                "severity": "CRITICAL",
                "component": "project-1:src/main.py"
            }
        ]
        
        # Mock security metrics for project-1
        service.get_security_metrics.return_value = {
            "vulnerabilities": "1",
            "security_hotspots": "3",
            "security_rating": "4"
        }
        
        with patch('streamlit.session_state', new_callable=dict) as mock_session_state:
            
            # Step 1: User views issues page
            with patch('src.streamlit_app.pages.issues.SonarQubeService', return_value=service), \
                 patch('src.streamlit_app.pages.issues.ConfigManager', return_value=config_manager):
                
                issue_manager = issues.IssueManager(service)
                issues_data = issue_manager.search_issues("project-1")
                
                # Store in session for consistency
                mock_session_state["current_project"] = "project-1"
                mock_session_state["project_issues"] = issues_data
            
            # Step 2: User navigates to security page
            with patch('src.streamlit_app.pages.security.SonarQubeService', return_value=service), \
                 patch('src.streamlit_app.pages.security.ConfigManager', return_value=config_manager):
                
                analyzer = security.SecurityAnalyzer(service)
                security_metrics = service.get_security_metrics("project-1")
                
                # Verify consistency - vulnerability count should match
                assert security_metrics["vulnerabilities"] == "1"
                assert len(mock_session_state["project_issues"]) == 1
                assert mock_session_state["project_issues"][0]["type"] == "VULNERABILITY"
    
    def test_bulk_operations_workflow(self, mock_configured_environment):
        """Test bulk operations workflow."""
        config_manager, service = mock_configured_environment
        
        # Mock multiple issues
        service.search_issues.return_value = [
            {"key": f"ISSUE-{i}", "type": "BUG", "severity": "MAJOR", "status": "OPEN"}
            for i in range(1, 6)  # 5 issues
        ]
        
        with patch('src.streamlit_app.pages.issues.SonarQubeService', return_value=service), \
             patch('src.streamlit_app.pages.issues.ConfigManager', return_value=config_manager):
            
            issue_manager = issues.IssueManager(service)
            
            # Step 1: User selects multiple issues
            selected_issues = ["ISSUE-1", "ISSUE-2", "ISSUE-3"]
            
            # Step 2: User performs bulk assignment
            with patch.object(issue_manager, 'update_issue', return_value=True) as mock_update:
                success_count = 0
                for issue_key in selected_issues:
                    if issue_manager.update_issue(issue_key, {"assignee": "team.lead"}):
                        success_count += 1
                
                assert success_count == 3
                assert mock_update.call_count == 3
            
            # Step 3: User performs bulk status change
            with patch.object(issue_manager, 'update_issue', return_value=True) as mock_update:
                success_count = 0
                for issue_key in selected_issues:
                    if issue_manager.update_issue(issue_key, {"transition": "confirmed"}):
                        success_count += 1
                
                assert success_count == 3
                assert mock_update.call_count == 3
            
            # Step 4: User adds bulk comments
            with patch.object(issue_manager, 'add_comment', return_value=True) as mock_comment:
                success_count = 0
                for issue_key in selected_issues:
                    if issue_manager.add_comment(issue_key, "Bulk update: assigned to team"):
                        success_count += 1
                
                assert success_count == 3
                assert mock_comment.call_count == 3
    
    def test_performance_optimization_workflow(self):
        """Test performance optimization workflow."""
        from src.streamlit_app.utils.performance import PerformanceOptimizer
        
        # Step 1: Test DataFrame optimization
        large_data = pd.DataFrame({
            'issue_key': [f'ISSUE-{i}' for i in range(2000)],
            'severity': ['MAJOR'] * 2000,
            'status': ['OPEN'] * 2000
        })
        
        optimized_data = PerformanceOptimizer.optimize_dataframe_display(large_data, max_rows=1000)
        assert len(optimized_data) == 1000
        
        # Step 2: Test API call batching
        api_calls = list(range(50))  # 50 API calls to batch
        batches = list(PerformanceOptimizer.batch_api_calls(api_calls, batch_size=10))
        
        assert len(batches) == 5  # 5 batches of 10 each
        assert all(len(batch) == 10 for batch in batches)
        
        # Step 3: Test lazy loading with caching
        call_count = 0
        
        def expensive_operation():
            nonlocal call_count
            call_count += 1
            return {"expensive_data": f"result_{call_count}"}
        
        # First call should execute the operation
        with patch('streamlit.spinner'):
            result1 = PerformanceOptimizer.lazy_load_data(
                expensive_operation, 
                "expensive_cache_key", 
                5
            )
        
        assert call_count == 1
        assert result1["expensive_data"] == "result_1"
        
        # Second call should use cache
        with patch('streamlit.spinner'):
            result2 = PerformanceOptimizer.lazy_load_data(
                expensive_operation, 
                "expensive_cache_key", 
                5
            )
        
        assert call_count == 1  # Should not increment
        assert result2["expensive_data"] == "result_1"  # Same cached result


class TestUIComponentIntegration:
    """Test integration between different UI components."""
    
    def test_filter_state_persistence(self):
        """Test that filter states persist across page refreshes."""
        with patch('streamlit.session_state', new_callable=dict) as mock_session_state:
            
            # Step 1: User sets filters on issues page
            SessionManager.set_filter_settings("issues", {
                "severities": ["CRITICAL", "MAJOR"],
                "types": ["BUG", "VULNERABILITY"],
                "project": "project-1"
            })
            
            # Step 2: User navigates away and back
            retrieved_filters = SessionManager.get_filter_settings("issues")
            
            assert retrieved_filters["severities"] == ["CRITICAL", "MAJOR"]
            assert retrieved_filters["types"] == ["BUG", "VULNERABILITY"]
            assert retrieved_filters["project"] == "project-1"
    
    def test_cross_page_data_sharing(self):
        """Test data sharing between different pages."""
        with patch('streamlit.session_state', new_callable=dict) as mock_session_state:
            
            # Step 1: Issues page caches project data
            SessionManager.cache_data("cached_projects", [
                {"key": "project-1", "name": "Project One"},
                {"key": "project-2", "name": "Project Two"}
            ], ttl_minutes=5)
            
            # Step 2: Security page retrieves cached project data
            cached_projects = SessionManager.get_cached_data("cached_projects", ttl_minutes=5)
            
            assert cached_projects is not None
            assert len(cached_projects) == 2
            assert cached_projects[0]["key"] == "project-1"
    
    def test_real_time_updates(self):
        """Test real-time updates across UI components."""
        from src.streamlit_app.utils.performance import get_performance_monitor
        
        monitor = get_performance_monitor()
        monitor.clear_metrics()
        
        # Step 1: Record performance metrics from different components
        monitor.record_metric("issues_load_time", 1.2, "seconds", {"page": "issues"})
        monitor.record_metric("security_load_time", 0.8, "seconds", {"page": "security"})
        monitor.record_metric("cpu_usage", 75.0, "percentage", {"source": "system"})
        
        # Step 2: Performance page should see all metrics
        all_metrics = monitor.get_metrics()
        assert len(all_metrics) == 3
        
        # Step 3: Filter metrics by context
        page_metrics = [m for m in all_metrics if m.context and m.context.get("page")]
        system_metrics = [m for m in all_metrics if m.context and m.context.get("source") == "system"]
        
        assert len(page_metrics) == 2
        assert len(system_metrics) == 1


if __name__ == "__main__":
    pytest.main([__file__])