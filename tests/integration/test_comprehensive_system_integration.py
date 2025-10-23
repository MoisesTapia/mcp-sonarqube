"""Comprehensive system integration tests.

This module tests complete system integration from chat interface to SonarQube API,
verifies data flow consistency across all system components, and tests concurrent
user scenarios and system scalability.
"""

import asyncio
import pytest
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from datetime import datetime, timedelta
from typing import Dict, List, Any
import json

from src.mcp_server.server import SonarQubeMCPServer
from src.sonarqube_client.client import SonarQubeClient
from src.streamlit_app.services.mcp_client import MCPClient, MCPToolResult
from src.streamlit_app.services.sonarqube_service import SonarQubeService
from src.streamlit_app.components.chat_interface import ChatInterface
from src.streamlit_app.services.mcp_integration import MCPIntegrationService
from src.streamlit_app.utils.performance import CacheManager
from src.streamlit_app.utils.performance import get_performance_monitor
from src.streamlit_app.utils.session import SessionManager


class TestCompleteSystemIntegration:
    """Test complete system integration from chat to SonarQube API."""
    
    @pytest.fixture
    def mock_sonarqube_responses(self):
        """Mock comprehensive SonarQube API responses."""
        return {
            "projects": {
                "components": [
                    {
                        "key": "test-project-1",
                        "name": "Test Project 1",
                        "visibility": "public",
                        "lastAnalysisDate": "2025-01-20T10:00:00Z"
                    },
                    {
                        "key": "test-project-2", 
                        "name": "Test Project 2",
                        "visibility": "private",
                        "lastAnalysisDate": "2025-01-21T11:00:00Z"
                    }
                ],
                "paging": {"pageIndex": 1, "pageSize": 100, "total": 2}
            },
            "measures": {
                "component": {
                    "key": "test-project-1",
                    "name": "Test Project 1",
                    "measures": [
                        {"metric": "coverage", "value": "85.5", "bestValue": False},
                        {"metric": "bugs", "value": "3", "bestValue": False},
                        {"metric": "vulnerabilities", "value": "1", "bestValue": False},
                        {"metric": "code_smells", "value": "12", "bestValue": False},
                        {"metric": "reliability_rating", "value": "2.0", "bestValue": False},
                        {"metric": "security_rating", "value": "3.0", "bestValue": False}
                    ]
                }
            },
            "issues": {
                "issues": [
                    {
                        "key": "ISSUE-1",
                        "rule": "java:S1234",
                        "severity": "MAJOR",
                        "component": "test-project-1:src/main/java/Example.java",
                        "project": "test-project-1",
                        "status": "OPEN",
                        "type": "BUG",
                        "message": "Test bug issue",
                        "assignee": None,
                        "author": "test-author",
                        "creationDate": "2025-01-20T10:00:00Z",
                        "updateDate": "2025-01-20T10:00:00Z"
                    },
                    {
                        "key": "ISSUE-2",
                        "rule": "java:S5678",
                        "severity": "CRITICAL",
                        "component": "test-project-1:src/main/java/Security.java",
                        "project": "test-project-1",
                        "status": "CONFIRMED",
                        "type": "VULNERABILITY",
                        "message": "Security vulnerability",
                        "assignee": "security-team",
                        "author": "test-author",
                        "creationDate": "2025-01-19T14:00:00Z",
                        "updateDate": "2025-01-20T09:00:00Z"
                    }
                ],
                "components": [
                    {
                        "key": "test-project-1:src/main/java/Example.java",
                        "name": "Example.java",
                        "path": "src/main/java/Example.java",
                        "qualifier": "FIL"
                    }
                ],
                "rules": [
                    {
                        "key": "java:S1234",
                        "name": "Test Rule",
                        "lang": "java",
                        "type": "BUG"
                    }
                ],
                "users": [
                    {
                        "login": "test-author",
                        "name": "Test Author",
                        "active": True
                    }
                ],
                "paging": {"pageIndex": 1, "pageSize": 100, "total": 2}
            },
            "quality_gate": {
                "projectStatus": {
                    "status": "ERROR",
                    "conditions": [
                        {
                            "status": "ERROR",
                            "metricKey": "coverage",
                            "comparator": "LT",
                            "errorThreshold": "80",
                            "actualValue": "75.5"
                        },
                        {
                            "status": "OK",
                            "metricKey": "bugs",
                            "comparator": "GT",
                            "errorThreshold": "5",
                            "actualValue": "3"
                        }
                    ]
                }
            },
            "hotspots": {
                "hotspots": [
                    {
                        "key": "HOTSPOT-1",
                        "component": "test-project-1:src/main/java/Security.java",
                        "securityCategory": "sql-injection",
                        "vulnerabilityProbability": "HIGH",
                        "status": "TO_REVIEW",
                        "line": 42,
                        "message": "SQL injection vulnerability",
                        "author": "test-author",
                        "creationDate": "2025-01-19T14:00:00Z",
                        "updateDate": "2025-01-20T09:00:00Z"
                    }
                ],
                "components": [
                    {
                        "key": "test-project-1:src/main/java/Security.java",
                        "name": "Security.java",
                        "path": "src/main/java/Security.java",
                        "qualifier": "FIL"
                    }
                ],
                "paging": {"pageIndex": 1, "pageSize": 100, "total": 1}
            }
        }
    
    @pytest.fixture
    def integrated_system_components(self, mock_sonarqube_responses):
        """Create integrated system components with mocked SonarQube responses."""
        # Mock SonarQube client
        mock_sonarqube_client = AsyncMock(spec=SonarQubeClient)
        
        # Configure mock responses based on endpoint
        def mock_get_response(endpoint, params=None):
            if "projects/search" in endpoint:
                return mock_sonarqube_responses["projects"]
            elif "measures/component" in endpoint:
                return mock_sonarqube_responses["measures"]
            elif "issues/search" in endpoint:
                return mock_sonarqube_responses["issues"]
            elif "qualitygates/project_status" in endpoint:
                return mock_sonarqube_responses["quality_gate"]
            elif "hotspots/search" in endpoint:
                return mock_sonarqube_responses["hotspots"]
            else:
                return {}
        
        mock_sonarqube_client.get.side_effect = mock_get_response
        mock_sonarqube_client.post.return_value = {}
        
        # Create cache manager
        cache_manager = CacheManager()
        cache_manager.clear()
        
        # Create MCP server components (without full initialization)
        # We'll test the tools directly instead of the full server
        mcp_server = None  # Skip full server initialization for integration tests
        
        # Create MCP client
        mcp_client = MCPClient()
        
        # Create Streamlit service
        streamlit_service = SonarQubeService()
        streamlit_service.client = mock_sonarqube_client
        
        # Create chat interface
        chat_interface = ChatInterface()
        chat_interface.mcp_client = mcp_client
        
        # Create integration service
        integration_service = MCPIntegrationService(mcp_client)
        
        return {
            "sonarqube_client": mock_sonarqube_client,
            "mcp_server": mcp_server,
            "mcp_client": mcp_client,
            "streamlit_service": streamlit_service,
            "chat_interface": chat_interface,
            "integration_service": integration_service,
            "cache_manager": cache_manager
        }
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_complete_chat_to_api_workflow(self, integrated_system_components):
        """Test complete workflow from chat interface to SonarQube API."""
        components = integrated_system_components
        chat_interface = components["chat_interface"]
        mcp_client = components["mcp_client"]
        
        # Mock MCP client to simulate tool calls
        async def mock_call_tool(tool_name, parameters):
            if tool_name == "list_projects":
                return MCPToolResult(
                    success=True,
                    data=[
                        {"key": "test-project-1", "name": "Test Project 1"},
                        {"key": "test-project-2", "name": "Test Project 2"}
                    ]
                )
            elif tool_name == "get_measures":
                return MCPToolResult(
                    success=True,
                    data={
                        "measures": [
                            {"metric": "coverage", "value": "85.5"},
                            {"metric": "bugs", "value": "3"}
                        ]
                    }
                )
            elif tool_name == "search_issues":
                return MCPToolResult(
                    success=True,
                    data=[
                        {"key": "ISSUE-1", "type": "BUG", "severity": "MAJOR"},
                        {"key": "ISSUE-2", "type": "VULNERABILITY", "severity": "CRITICAL"}
                    ]
                )
            else:
                return MCPToolResult(success=False, error="Unknown tool")
        
        mcp_client.call_tool = mock_call_tool
        
        # Test 1: List projects workflow
        response = await chat_interface._process_user_message("List all projects")
        
        assert response["tool_name"] == "list_projects"
        assert len(response["tool_result"]) == 2
        assert response["tool_result"][0]["key"] == "test-project-1"
        assert "summary" in response
        assert "2 projects" in response["summary"]
        
        # Test 2: Get project metrics workflow
        response = await chat_interface._process_user_message("Get metrics for test-project-1")
        
        assert response["tool_name"] == "get_measures"
        assert "measures" in response["tool_result"]
        assert len(response["tool_result"]["measures"]) == 2
        assert "2 metrics" in response["summary"]
        
        # Test 3: Search issues workflow
        response = await chat_interface._process_user_message("Show issues in test-project-1")
        
        assert response["tool_name"] == "search_issues"
        assert len(response["tool_result"]) == 2
        assert response["tool_result"][0]["type"] == "BUG"
        assert response["tool_result"][1]["type"] == "VULNERABILITY"
        assert "2 issues" in response["summary"]
        
        # Test 4: Error handling workflow
        response = await chat_interface._process_user_message("What's the weather?")
        
        assert "error" in response
        assert "couldn't understand" in response["error"].lower()
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_mcp_server_tool_integration(self, integrated_system_components):
        """Test MCP server tool integration with SonarQube client."""
        components = integrated_system_components
        mcp_server = components["mcp_server"]
        sonarqube_client = components["sonarqube_client"]
        
        # Test projects tool
        from src.mcp_server.tools.projects import ProjectTools
        project_tools = ProjectTools(sonarqube_client, components["cache_manager"])
        
        projects_result = await project_tools.list_projects()
        assert projects_result["total_count"] == 2
        assert len(projects_result["projects"]) == 2
        assert projects_result["projects"][0]["key"] == "test-project-1"
        
        # Test measures tool
        from src.mcp_server.tools.metrics import MetricsTools
        metrics_tools = MetricsTools(sonarqube_client, components["cache_manager"])
        
        measures_result = await metrics_tools.get_measures(
            "test-project-1",
            ["coverage", "bugs", "vulnerabilities"]
        )
        assert measures_result["project_key"] == "test-project-1"
        assert len(measures_result["measures"]) == 6  # All measures from mock
        
        # Test issues tool
        from src.mcp_server.tools.issues import IssueTools
        issue_tools = IssueTools(sonarqube_client, components["cache_manager"])
        
        issues_result = await issue_tools.search_issues(
            project_keys=["test-project-1"],
            severities=["MAJOR", "CRITICAL"]
        )
        assert issues_result["total"] == 2
        assert len(issues_result["issues"]) == 2
        
        # Test quality gates tool
        from src.mcp_server.tools.quality_gates import QualityGateTools
        qg_tools = QualityGateTools(sonarqube_client, components["cache_manager"])
        
        qg_result = await qg_tools.get_project_quality_gate_status("test-project-1")
        assert qg_result["project_key"] == "test-project-1"
        assert qg_result["status"] == "ERROR"
        assert len(qg_result["conditions"]) == 2
        
        # Test security tools
        from src.mcp_server.tools.security import SecurityTools
        security_tools = SecurityTools(sonarqube_client, components["cache_manager"])
        
        hotspots_result = await security_tools.search_hotspots("test-project-1")
        assert hotspots_result["project_key"] == "test-project-1"
        assert hotspots_result["total"] == 1
        assert len(hotspots_result["hotspots"]) == 1
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_streamlit_service_integration(self, integrated_system_components):
        """Test Streamlit service integration with SonarQube client."""
        components = integrated_system_components
        service = components["streamlit_service"]
        
        # Test get projects
        projects = service.get_projects()
        assert len(projects) == 2
        assert projects[0]["key"] == "test-project-1"
        assert projects[1]["key"] == "test-project-2"
        
        # Test get project measures
        measures = service.get_project_measures("test-project-1", ["coverage", "bugs"])
        assert "coverage" in measures
        assert "bugs" in measures
        assert measures["coverage"] == "85.5"
        assert measures["bugs"] == "3"
        
        # Test search issues
        issues = service.search_issues("test-project-1", {"severities": ["MAJOR"]})
        assert len(issues) == 2  # Mock returns all issues
        
        # Test get quality gate status
        qg_status = service.get_quality_gate_status("test-project-1")
        assert qg_status["status"] == "ERROR"
        assert len(qg_status["conditions"]) == 2
        
        # Test get security hotspots
        hotspots = service.get_security_hotspots("test-project-1")
        assert len(hotspots) == 1
        assert hotspots[0]["securityCategory"] == "sql-injection"


class TestDataFlowConsistency:
    """Test data flow consistency across all system components."""
    
    @pytest.fixture
    def consistent_test_data(self):
        """Create consistent test data for cross-component validation."""
        return {
            "project_key": "consistency-test-project",
            "project_name": "Consistency Test Project",
            "bugs_count": 5,
            "vulnerabilities_count": 2,
            "coverage_value": "78.5",
            "quality_gate_status": "ERROR",
            "issues": [
                {
                    "key": "ISSUE-1",
                    "type": "BUG",
                    "severity": "MAJOR",
                    "project": "consistency-test-project"
                },
                {
                    "key": "ISSUE-2", 
                    "type": "BUG",
                    "severity": "MINOR",
                    "project": "consistency-test-project"
                },
                {
                    "key": "ISSUE-3",
                    "type": "VULNERABILITY",
                    "severity": "HIGH",
                    "project": "consistency-test-project"
                }
            ]
        }
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_cross_component_data_consistency(self, consistent_test_data):
        """Test that data remains consistent across different system components."""
        test_data = consistent_test_data
        
        # Mock SonarQube client with consistent responses
        mock_client = AsyncMock(spec=SonarQubeClient)
        
        # Project response
        mock_client.get.return_value = {
            "components": [{
                "key": test_data["project_key"],
                "name": test_data["project_name"]
            }],
            "paging": {"total": 1}
        }
        
        # Create components with same mock client
        cache_manager = CacheManager()
        cache_manager.clear()
        
        # Test MCP tools consistency
        from src.mcp_server.tools.projects import ProjectTools
        from src.mcp_server.tools.metrics import MetricsTools
        from src.mcp_server.tools.issues import IssueTools
        
        project_tools = ProjectTools(mock_client, cache_manager)
        metrics_tools = MetricsTools(mock_client, cache_manager)
        issue_tools = IssueTools(mock_client, cache_manager)
        
        # Configure different responses for different endpoints
        def mock_get_response(endpoint, params=None):
            if "projects/search" in endpoint:
                return {
                    "components": [{
                        "key": test_data["project_key"],
                        "name": test_data["project_name"]
                    }],
                    "paging": {"total": 1}
                }
            elif "measures/component" in endpoint:
                return {
                    "component": {
                        "key": test_data["project_key"],
                        "measures": [
                            {"metric": "bugs", "value": str(test_data["bugs_count"])},
                            {"metric": "vulnerabilities", "value": str(test_data["vulnerabilities_count"])},
                            {"metric": "coverage", "value": test_data["coverage_value"]}
                        ]
                    }
                }
            elif "issues/search" in endpoint:
                return {
                    "issues": test_data["issues"],
                    "components": [],
                    "rules": [],
                    "users": [],
                    "paging": {"total": len(test_data["issues"])}
                }
            elif "qualitygates/project_status" in endpoint:
                return {
                    "projectStatus": {
                        "status": test_data["quality_gate_status"],
                        "conditions": []
                    }
                }
            return {}
        
        mock_client.get.side_effect = mock_get_response
        
        # Test 1: Project data consistency
        projects_result = await project_tools.list_projects()
        project_data = projects_result["projects"][0]
        assert project_data["key"] == test_data["project_key"]
        assert project_data["name"] == test_data["project_name"]
        
        # Test 2: Metrics data consistency
        measures_result = await metrics_tools.get_measures(
            test_data["project_key"],
            ["bugs", "vulnerabilities", "coverage"]
        )
        assert measures_result["project_key"] == test_data["project_key"]
        
        # Find specific measures
        bugs_measure = next(m for m in measures_result["measures"] if m["metric"] == "bugs")
        vuln_measure = next(m for m in measures_result["measures"] if m["metric"] == "vulnerabilities")
        coverage_measure = next(m for m in measures_result["measures"] if m["metric"] == "coverage")
        
        assert int(bugs_measure["value"]) == test_data["bugs_count"]
        assert int(vuln_measure["value"]) == test_data["vulnerabilities_count"]
        assert coverage_measure["value"] == test_data["coverage_value"]
        
        # Test 3: Issues data consistency
        issues_result = await issue_tools.search_issues(
            project_keys=[test_data["project_key"]]
        )
        assert issues_result["total"] == len(test_data["issues"])
        
        # Count issues by type
        bug_issues = [i for i in issues_result["issues"] if i["type"] == "BUG"]
        vuln_issues = [i for i in issues_result["issues"] if i["type"] == "VULNERABILITY"]
        
        # Verify consistency with metrics
        assert len(bug_issues) == 2  # From test data
        assert len(vuln_issues) == 1  # From test data
        
        # All issues should belong to the same project
        for issue in issues_result["issues"]:
            assert issue["project"] == test_data["project_key"]
    
    @pytest.mark.integration
    def test_cache_consistency_across_components(self):
        """Test that cached data remains consistent across different components."""
        cache_manager = CacheManager()
        cache_manager.clear()
        
        # Test data
        project_key = "cache-test-project"
        project_data = {"key": project_key, "name": "Cache Test Project"}
        measures_data = {"coverage": "85.0", "bugs": "3"}
        
        # Component 1: Cache project data
        cache_key_1 = f"project_details_{project_key}"
        cache_manager.set(cache_key_1, project_data, ttl_minutes=5)
        
        # Component 2: Cache measures data
        cache_key_2 = f"project_measures_{project_key}"
        cache_manager.set(cache_key_2, measures_data, ttl_minutes=5)
        
        # Component 3: Retrieve and verify consistency
        cached_project = cache_manager.get(cache_key_1)
        cached_measures = cache_manager.get(cache_key_2)
        
        assert cached_project is not None
        assert cached_measures is not None
        assert cached_project["key"] == project_key
        assert cached_measures["coverage"] == "85.0"
        
        # Test cache invalidation consistency (manual removal)
        with cache_manager._lock:
            if cache_key_1 in cache_manager.cache:
                del cache_manager.cache[cache_key_1]
        
        assert cache_manager.get(cache_key_1) is None
        assert cache_manager.get(cache_key_2) is not None  # Should still exist
        
        # Test cache expiration consistency
        cache_manager.set("short_lived", {"test": "data"}, ttl_minutes=0.02)  # ~1 second
        time.sleep(1.1)  # Wait for expiration
        
        assert cache_manager.get("short_lived") is None
        assert cache_manager.get(cache_key_2) is not None  # Should still exist
    
    @pytest.mark.integration
    def test_session_state_consistency(self):
        """Test session state consistency across UI components."""
        # Mock session state
        mock_session_state = {}
        
        with patch('streamlit.session_state', mock_session_state):
            # Test user info consistency
            user_info = {
                "name": "Test User",
                "login": "testuser",
                "permissions": {"admin": True}
            }
            SessionManager.set_user_info(user_info)
            
            # Retrieve from different component
            retrieved_user = SessionManager.get_user_info()
            assert retrieved_user["name"] == "Test User"
            assert retrieved_user["permissions"]["admin"] is True
            
            # Test connection status consistency
            system_info = {"status": "UP", "version": "9.9.0"}
            SessionManager.set_connection_status("connected", system_info)
            
            status = SessionManager.get_connection_status()
            assert status == "connected"
            
            # Test filter settings consistency
            filters = {
                "project": "test-project",
                "severities": ["MAJOR", "CRITICAL"]
            }
            SessionManager.set_filter_settings("issues", filters)
            
            retrieved_filters = SessionManager.get_filter_settings("issues")
            assert retrieved_filters["project"] == "test-project"
            assert "MAJOR" in retrieved_filters["severities"]
            
            # Test data caching consistency
            projects_data = [{"key": "proj1"}, {"key": "proj2"}]
            SessionManager.cache_data("projects", projects_data, ttl_minutes=10)
            
            cached_projects = SessionManager.get_cached_data("projects", ttl_minutes=10)
            assert len(cached_projects) == 2
            assert cached_projects[0]["key"] == "proj1"


class TestConcurrentUserScenarios:
    """Test concurrent user scenarios and system scalability."""
    
    @pytest.fixture
    def scalability_test_setup(self):
        """Set up components for scalability testing."""
        # Create shared cache manager
        cache_manager = CacheManager()
        cache_manager.clear()
        
        # Create mock SonarQube client
        mock_client = AsyncMock(spec=SonarQubeClient)
        mock_client.get.return_value = {
            "components": [{"key": "test-project", "name": "Test Project"}],
            "paging": {"total": 1}
        }
        
        # Create performance monitor
        performance_monitor = get_performance_monitor()
        performance_monitor.clear_metrics()
        
        return {
            "cache_manager": cache_manager,
            "mock_client": mock_client,
            "performance_monitor": performance_monitor
        }
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_concurrent_mcp_tool_calls(self, scalability_test_setup):
        """Test concurrent MCP tool calls for scalability."""
        setup = scalability_test_setup
        mock_client = setup["mock_client"]
        cache_manager = setup["cache_manager"]
        
        from src.mcp_server.tools.projects import ProjectTools
        project_tools = ProjectTools(mock_client, cache_manager)
        
        # Configure mock to simulate realistic response times
        async def mock_get_with_delay(endpoint, params=None):
            await asyncio.sleep(0.1)  # Simulate network delay
            return {
                "components": [{"key": f"project-{hash(endpoint) % 100}", "name": "Test Project"}],
                "paging": {"total": 1}
            }
        
        mock_client.get.side_effect = mock_get_with_delay
        
        # Test concurrent tool calls
        concurrent_calls = 20
        start_time = time.time()
        
        tasks = [
            project_tools.list_projects(search=f"search-{i}")
            for i in range(concurrent_calls)
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # Verify results
        successful_results = [r for r in results if not isinstance(r, Exception)]
        assert len(successful_results) == concurrent_calls
        
        # Verify performance (should be faster than sequential execution)
        expected_sequential_time = concurrent_calls * 0.1
        assert total_time < expected_sequential_time * 0.8  # At least 20% faster
        
        # Verify all calls were made
        assert mock_client.get.call_count == concurrent_calls
    
    @pytest.mark.integration
    def test_concurrent_cache_operations(self, scalability_test_setup):
        """Test concurrent cache operations for thread safety."""
        setup = scalability_test_setup
        cache_manager = setup["cache_manager"]
        
        # Test concurrent cache writes
        def cache_write_worker(worker_id):
            results = []
            for i in range(10):
                key = f"worker_{worker_id}_item_{i}"
                value = {"worker": worker_id, "item": i, "timestamp": time.time()}
                cache_manager.set(key, value, ttl=60)
                results.append(key)
            return results
        
        # Test concurrent cache reads
        def cache_read_worker(keys_to_read):
            results = []
            for key in keys_to_read:
                value = cache_manager.get(key)
                results.append((key, value is not None))
            return results
        
        # Execute concurrent writes
        num_workers = 5
        with ThreadPoolExecutor(max_workers=num_workers) as executor:
            write_futures = [
                executor.submit(cache_write_worker, worker_id)
                for worker_id in range(num_workers)
            ]
            
            all_keys = []
            for future in as_completed(write_futures):
                keys = future.result()
                all_keys.extend(keys)
        
        # Verify all writes succeeded
        assert len(all_keys) == num_workers * 10
        
        # Execute concurrent reads
        keys_per_reader = len(all_keys) // num_workers
        with ThreadPoolExecutor(max_workers=num_workers) as executor:
            read_futures = [
                executor.submit(
                    cache_read_worker,
                    all_keys[i * keys_per_reader:(i + 1) * keys_per_reader]
                )
                for i in range(num_workers)
            ]
            
            read_results = []
            for future in as_completed(read_futures):
                results = future.result()
                read_results.extend(results)
        
        # Verify all reads found the data
        successful_reads = [r for r in read_results if r[1]]
        assert len(successful_reads) >= len(read_results) * 0.9  # At least 90% success rate
    
    @pytest.mark.integration
    def test_concurrent_session_operations(self):
        """Test concurrent session operations for thread safety."""
        # Mock multiple session states
        session_states = {}
        
        def session_worker(session_id):
            # Simulate different session state for each worker
            mock_session_state = {}
            session_states[session_id] = mock_session_state
            
            with patch('streamlit.session_state', mock_session_state):
                # Perform session operations
                user_info = {
                    "name": f"User {session_id}",
                    "login": f"user{session_id}",
                    "session_id": session_id
                }
                SessionManager.set_user_info(user_info)
                
                # Cache some data
                projects_data = [{"key": f"project-{session_id}-{i}"} for i in range(3)]
                SessionManager.cache_data("projects", projects_data, ttl_minutes=10)
                
                # Set filters
                filters = {"project": f"project-{session_id}", "severity": ["MAJOR"]}
                SessionManager.set_filter_settings("issues", filters)
                
                # Retrieve and verify
                retrieved_user = SessionManager.get_user_info()
                cached_projects = SessionManager.get_cached_data("projects", ttl_minutes=10)
                retrieved_filters = SessionManager.get_filter_settings("issues")
                
                return {
                    "session_id": session_id,
                    "user_name": retrieved_user["name"] if retrieved_user else None,
                    "projects_count": len(cached_projects) if cached_projects else 0,
                    "filter_project": retrieved_filters.get("project") if retrieved_filters else None
                }
        
        # Execute concurrent session operations
        num_sessions = 10
        with ThreadPoolExecutor(max_workers=num_sessions) as executor:
            futures = [
                executor.submit(session_worker, session_id)
                for session_id in range(num_sessions)
            ]
            
            results = []
            for future in as_completed(futures):
                result = future.result()
                results.append(result)
        
        # Verify session isolation
        assert len(results) == num_sessions
        
        for result in results:
            session_id = result["session_id"]
            assert result["user_name"] == f"User {session_id}"
            assert result["projects_count"] == 3
            assert result["filter_project"] == f"project-{session_id}"
        
        # Verify no cross-session contamination
        session_ids = [r["session_id"] for r in results]
        user_names = [r["user_name"] for r in results]
        filter_projects = [r["filter_project"] for r in results]
        
        assert len(set(session_ids)) == num_sessions
        assert len(set(user_names)) == num_sessions
        assert len(set(filter_projects)) == num_sessions
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_system_performance_under_load(self, scalability_test_setup):
        """Test system performance under concurrent load."""
        setup = scalability_test_setup
        mock_client = setup["mock_client"]
        cache_manager = setup["cache_manager"]
        performance_monitor = setup["performance_monitor"]
        
        # Create multiple tool instances
        from src.mcp_server.tools.projects import ProjectTools
        from src.mcp_server.tools.metrics import MetricsTools
        from src.mcp_server.tools.issues import IssueTools
        
        project_tools = ProjectTools(mock_client, cache_manager)
        metrics_tools = MetricsTools(mock_client, cache_manager)
        issue_tools = IssueTools(mock_client, cache_manager)
        
        # Configure mock responses with realistic delays
        async def mock_get_with_metrics(endpoint, params=None):
            start_time = time.time()
            await asyncio.sleep(0.05)  # Simulate API delay
            
            # Record performance metric
            duration = time.time() - start_time
            performance_monitor.record_metric(
                "api_response_time",
                duration,
                "seconds",
                {"endpoint": endpoint.split('/')[-1]}
            )
            
            if "projects" in endpoint:
                return {"components": [{"key": "test-project"}], "paging": {"total": 1}}
            elif "measures" in endpoint:
                return {"component": {"measures": [{"metric": "coverage", "value": "80"}]}}
            elif "issues" in endpoint:
                return {"issues": [{"key": "ISSUE-1"}], "paging": {"total": 1}}
            return {}
        
        mock_client.get.side_effect = mock_get_with_metrics
        
        # Create mixed workload
        async def mixed_workload_worker(worker_id):
            tasks = []
            
            # Projects calls
            for i in range(3):
                tasks.append(project_tools.list_projects(search=f"worker-{worker_id}-{i}"))
            
            # Metrics calls
            for i in range(2):
                tasks.append(metrics_tools.get_measures(f"project-{worker_id}-{i}", ["coverage"]))
            
            # Issues calls
            for i in range(2):
                tasks.append(issue_tools.search_issues(project_keys=[f"project-{worker_id}-{i}"]))
            
            start_time = time.time()
            results = await asyncio.gather(*tasks, return_exceptions=True)
            duration = time.time() - start_time
            
            successful_results = [r for r in results if not isinstance(r, Exception)]
            
            return {
                "worker_id": worker_id,
                "total_calls": len(tasks),
                "successful_calls": len(successful_results),
                "duration": duration,
                "success_rate": len(successful_results) / len(tasks)
            }
        
        # Execute concurrent mixed workload
        num_workers = 8
        start_time = time.time()
        
        tasks = [mixed_workload_worker(i) for i in range(num_workers)]
        worker_results = await asyncio.gather(*tasks)
        
        total_duration = time.time() - start_time
        
        # Analyze results
        total_calls = sum(r["total_calls"] for r in worker_results)
        total_successful = sum(r["successful_calls"] for r in worker_results)
        overall_success_rate = total_successful / total_calls
        
        # Performance assertions
        assert overall_success_rate >= 0.95  # At least 95% success rate
        assert total_duration < 2.0  # Should complete within 2 seconds
        
        # Verify performance metrics were recorded
        system_metrics = performance_monitor.get_system_metrics()
        assert "api_response_time" in [m["name"] for m in system_metrics]
        
        # Verify cache effectiveness
        cache_stats = cache_manager.get_stats()
        assert cache_stats["cache_size"] > 0  # Some data should be cached
        
        # Test cache hit ratio under load
        # Make repeated calls to same data
        repeated_tasks = [
            project_tools.list_projects(search="repeated-search")
            for _ in range(10)
        ]
        
        await asyncio.gather(*repeated_tasks)
        
        # Cache should improve performance for repeated calls
        updated_cache_stats = cache_manager.get_stats()
        if updated_cache_stats["total_requests"] > 0:
            assert updated_cache_stats["hit_ratio"] > 0  # Some cache hits expected
    
    @pytest.mark.integration
    def test_error_handling_under_concurrent_load(self):
        """Test error handling and recovery under concurrent load."""
        cache_manager = CacheManager()
        cache_manager.clear()
        
        # Create mock client that fails intermittently
        mock_client = AsyncMock(spec=SonarQubeClient)
        
        call_count = 0
        async def failing_mock_get(endpoint, params=None):
            nonlocal call_count
            call_count += 1
            
            # Fail every 3rd call
            if call_count % 3 == 0:
                raise ConnectionError("Simulated network error")
            
            await asyncio.sleep(0.01)  # Small delay
            return {"components": [{"key": "test"}], "paging": {"total": 1}}
        
        mock_client.get.side_effect = failing_mock_get
        
        from src.mcp_server.tools.projects import ProjectTools
        project_tools = ProjectTools(mock_client, cache_manager)
        
        async def error_prone_worker(worker_id):
            results = {"success": 0, "errors": 0}
            
            for i in range(5):
                try:
                    await project_tools.list_projects(search=f"worker-{worker_id}-{i}")
                    results["success"] += 1
                except Exception:
                    results["errors"] += 1
            
            return results
        
        # Execute concurrent error-prone operations
        async def run_concurrent_error_test():
            num_workers = 6
            tasks = [error_prone_worker(i) for i in range(num_workers)]
            worker_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            total_success = sum(r["success"] for r in worker_results if isinstance(r, dict))
            total_errors = sum(r["errors"] for r in worker_results if isinstance(r, dict))
            
            return total_success, total_errors
        
        # Run the test
        total_success, total_errors = asyncio.run(run_concurrent_error_test())
        
        # Verify error handling
        assert total_success > 0  # Some calls should succeed
        assert total_errors > 0  # Some calls should fail (as designed)
        
        # Verify system didn't crash
        total_operations = total_success + total_errors
        assert total_operations == 6 * 5  # All operations completed (success or error)
        
        # Verify error rate matches expectation (roughly 1/3 should fail)
        error_rate = total_errors / total_operations
        assert 0.2 <= error_rate <= 0.4  # Allow some variance due to concurrency


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-m", "integration"])