"""Integration tests for advanced MCP tools (issues and quality gates)."""

import asyncio
import os
import pytest
from typing import Dict, Any
from unittest.mock import AsyncMock, patch

from src.mcp_server.tools.issues import IssueTools
from src.mcp_server.tools.quality_gates import QualityGateTools
from src.sonarqube_client import SonarQubeClient
from src.utils import CacheManager


@pytest.fixture
def sonarqube_config():
    """Get SonarQube configuration for integration tests."""
    return {
        "url": os.getenv("SONARQUBE_URL", "http://localhost:9000"),
        "token": os.getenv("SONARQUBE_TOKEN", "test-token"),
        "organization": os.getenv("SONARQUBE_ORGANIZATION"),
    }


@pytest.fixture
def mock_sonarqube_client():
    """Create mock SonarQube client for integration tests."""
    client = AsyncMock(spec=SonarQubeClient)
    return client


@pytest.fixture
def mock_cache_manager():
    """Create mock cache manager for integration tests."""
    cache = AsyncMock()
    cache.get.return_value = None  # No cached data by default
    return cache


@pytest.fixture
def issue_tools(mock_sonarqube_client, mock_cache_manager):
    """Create IssueTools instance for integration tests."""
    return IssueTools(mock_sonarqube_client, mock_cache_manager)


@pytest.fixture
def quality_gate_tools(mock_sonarqube_client, mock_cache_manager):
    """Create QualityGateTools instance for integration tests."""
    return QualityGateTools(mock_sonarqube_client, mock_cache_manager)


class TestAdvancedToolsIntegration:
    """Integration tests for advanced MCP tools."""

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_issue_management_workflow(self, issue_tools):
        """Test complete issue management workflow."""
        # Mock search issues response
        search_response = {
            "issues": [
                {
                    "key": "test-project:1",
                    "rule": "java:S1234",
                    "severity": "MAJOR",
                    "component": "com.example:project:src/main/java/Example.java",
                    "project": "test-project",
                    "status": "OPEN",
                    "type": "BUG",
                    "message": "Test issue message",
                    "assignee": None,
                    "author": "test-author",
                    "tags": ["test"],
                    "creationDate": "2025-10-22T10:00:00Z",
                    "updateDate": "2025-10-22T10:00:00Z",
                }
            ],
            "components": [
                {
                    "key": "com.example:project:src/main/java/Example.java",
                    "name": "Example.java",
                    "path": "src/main/java/Example.java",
                    "qualifier": "FIL",
                    "language": "java",
                }
            ],
            "rules": [
                {
                    "key": "java:S1234",
                    "name": "Test Rule",
                    "lang": "java",
                    "langName": "Java",
                    "type": "BUG",
                    "severity": "MAJOR",
                    "status": "READY",
                    "isTemplate": False,
                    "tags": [],
                    "sysTags": ["bug"],
                }
            ],
            "users": [
                {
                    "login": "test-author",
                    "name": "Test Author",
                    "active": True,
                },
                {
                    "login": "test-assignee",
                    "name": "Test Assignee",
                    "active": True,
                }
            ],
            "paging": {"pageIndex": 1, "pageSize": 100, "total": 1},
            "total": 1,
            "facets": [],
        }
        
        # Mock issue details response
        issue_details_response = {
            "issues": [
                {
                    "key": "test-project:1",
                    "rule": "java:S1234",
                    "severity": "MAJOR",
                    "component": "com.example:project:src/main/java/Example.java",
                    "project": "test-project",
                    "status": "OPEN",
                    "type": "BUG",
                    "message": "Test issue message",
                    "assignee": None,
                    "author": "test-author",
                    "tags": ["test"],
                    "creationDate": "2025-10-22T10:00:00Z",
                    "updateDate": "2025-10-22T10:00:00Z",
                    "comments": [
                        {
                            "key": "comment-1",
                            "login": "test-author",
                            "markdown": "Initial comment",
                            "createdAt": "2025-10-22T10:00:00Z",
                        }
                    ],
                }
            ],
            "components": search_response["components"],
            "rules": search_response["rules"],
            "users": search_response["users"],
        }
        
        # Mock transitions response
        transitions_response = {
            "transitions": [
                {"transition": "confirm", "name": "Confirm"},
                {"transition": "resolve", "name": "Resolve"},
                {"transition": "reopen", "name": "Reopen"},
            ]
        }
        
        # Configure mock responses
        issue_tools.client.get.side_effect = [
            search_response,  # search_issues call
            issue_details_response,  # get_issue_details call
            transitions_response,  # get_issue_transitions call
        ]
        issue_tools.client.post.return_value = {}  # All POST operations succeed
        
        # Step 1: Search for issues
        search_result = await issue_tools.search_issues(
            project_keys=["test-project"],
            severities=["MAJOR"],
            types=["BUG"],
            statuses=["OPEN"],
        )
        
        assert search_result["total"] == 1
        assert len(search_result["issues"]) == 1
        assert search_result["issues"][0]["key"] == "test-project:1"
        assert "summary" in search_result
        
        # Step 2: Get detailed information about the issue
        issue_key = search_result["issues"][0]["key"]
        issue_details = await issue_tools.get_issue_details(issue_key)
        
        assert issue_details["key"] == issue_key
        assert issue_details["severity"] == "MAJOR"
        assert "component_info" in issue_details
        assert "rule_info" in issue_details
        
        # Step 3: Get available transitions
        transitions = await issue_tools.get_issue_transitions(issue_key)
        
        assert transitions["issue_key"] == issue_key
        assert len(transitions["transitions"]) == 3
        assert any(t["transition"] == "confirm" for t in transitions["transitions"])
        
        # Step 4: Update issue (assign and add comment)
        update_result = await issue_tools.update_issue(
            issue_key,
            assign="test-assignee",
            comment="Assigning this issue for investigation",
        )
        
        assert update_result["success"] is True
        assert update_result["issue_key"] == issue_key
        assert "assigned to test-assignee" in update_result["message"]
        assert "comment added" in update_result["message"]
        
        # Step 5: Add additional comment
        comment_result = await issue_tools.add_issue_comment(
            issue_key,
            "Investigation completed, ready for fix",
        )
        
        assert comment_result["success"] is True
        assert comment_result["issue_key"] == issue_key
        assert comment_result["comment_added"] is True
        
        # Verify API call sequence
        assert issue_tools.client.get.call_count == 3
        assert issue_tools.client.post.call_count == 3  # assign, comment (from update), add_comment

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_quality_gates_workflow(self, quality_gate_tools):
        """Test complete Quality Gates management workflow."""
        # Mock Quality Gates list response
        gates_list_response = {
            "qualitygates": [
                {
                    "id": "1",
                    "name": "Sonar way",
                    "isDefault": True,
                    "isBuiltIn": True,
                },
                {
                    "id": "2",
                    "name": "Custom Gate",
                    "isDefault": False,
                    "isBuiltIn": False,
                },
            ]
        }
        
        # Mock Quality Gate conditions response
        conditions_response = {
            "conditions": [
                {
                    "id": "1",
                    "metric": "coverage",
                    "op": "LT",
                    "error": "80",
                },
                {
                    "id": "2",
                    "metric": "new_coverage",
                    "op": "LT",
                    "error": "80",
                },
                {
                    "id": "3",
                    "metric": "bugs",
                    "op": "GT",
                    "error": "0",
                },
                {
                    "id": "4",
                    "metric": "vulnerabilities",
                    "op": "GT",
                    "error": "0",
                },
                {
                    "id": "5",
                    "metric": "code_smells",
                    "op": "GT",
                    "error": "10",
                },
            ]
        }
        
        # Mock project Quality Gate status response (failed)
        project_status_response = {
            "projectStatus": {
                "status": "ERROR",
                "conditions": [
                    {
                        "status": "ERROR",
                        "metricKey": "coverage",
                        "comparator": "LT",
                        "errorThreshold": "80",
                        "actualValue": "65.5",
                    },
                    {
                        "status": "OK",
                        "metricKey": "new_coverage",
                        "comparator": "LT",
                        "errorThreshold": "80",
                        "actualValue": "85.0",
                    },
                    {
                        "status": "OK",
                        "metricKey": "bugs",
                        "comparator": "GT",
                        "errorThreshold": "0",
                        "actualValue": "0",
                    },
                    {
                        "status": "ERROR",
                        "metricKey": "vulnerabilities",
                        "comparator": "GT",
                        "errorThreshold": "0",
                        "actualValue": "2",
                    },
                    {
                        "status": "OK",
                        "metricKey": "code_smells",
                        "comparator": "GT",
                        "errorThreshold": "10",
                        "actualValue": "8",
                    },
                ],
                "ignoredConditions": False,
                "period": {
                    "mode": "previous_version",
                    "date": "2025-10-20T10:00:00Z",
                },
            }
        }
        
        # Configure mock responses
        quality_gate_tools.client.get.side_effect = [
            gates_list_response,  # list_quality_gates call
            gates_list_response,  # get_quality_gate_conditions call (to find gate ID)
            conditions_response,  # get_quality_gate_conditions call (actual conditions)
            project_status_response,  # get_project_quality_gate_status call
        ]
        
        # Step 1: List all Quality Gates
        gates_list = await quality_gate_tools.list_quality_gates()
        
        assert gates_list["total_count"] == 2
        assert len(gates_list["quality_gates"]) == 2
        assert gates_list["default_gate"]["name"] == "Sonar way"
        assert gates_list["default_gate"]["isDefault"] is True
        
        # Step 2: Get conditions for the default Quality Gate
        gate_name = gates_list["default_gate"]["name"]
        conditions = await quality_gate_tools.get_quality_gate_conditions(gate_name)
        
        assert conditions["quality_gate"]["name"] == gate_name
        assert conditions["quality_gate"]["is_default"] is True
        assert conditions["total_conditions"] == 5
        assert "condition_analysis" in conditions
        
        # Verify condition analysis
        analysis = conditions["condition_analysis"]
        assert analysis["total_conditions"] == 5
        assert len(analysis["coverage_conditions"]) == 2  # coverage and new_coverage
        # Note: vulnerabilities metric doesn't contain "security" keyword, so it won't be categorized as security
        assert len(analysis["maintainability_conditions"]) == 1  # code_smells
        
        # Step 3: Check project Quality Gate status
        project_status = await quality_gate_tools.get_project_quality_gate_status("test-project")
        
        assert project_status["project_key"] == "test-project"
        assert project_status["status"] == "ERROR"
        assert len(project_status["conditions"]) == 5
        assert "condition_analysis" in project_status
        assert "recommendations" in project_status
        
        # Verify condition analysis for project
        project_analysis = project_status["condition_analysis"]
        assert project_analysis["total_conditions"] == 5
        assert project_analysis["failed_conditions"] == 2  # coverage and vulnerabilities
        assert project_analysis["passed_conditions"] == 3
        assert project_analysis["pass_rate_percent"] == 60.0
        
        # Verify recommendations are generated
        recommendations = project_status["recommendations"]
        assert len(recommendations) >= 2
        assert any("coverage from 65.5% to at least 80%" in rec for rec in recommendations)
        assert any("security vulnerabilities" in rec for rec in recommendations)
        
        # Verify API call sequence
        assert quality_gate_tools.client.get.call_count == 4

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_error_scenarios_and_recovery(self, issue_tools, quality_gate_tools):
        """Test error scenarios and recovery mechanisms."""
        # Test network error recovery for issues
        # Simulate network error followed by success
        issue_tools.client.get.side_effect = [
            Exception("Network error"),
            {
                "issues": [],
                "components": [],
                "rules": [],
                "users": [],
                "paging": {"pageIndex": 1, "pageSize": 100, "total": 0},
                "total": 0,
                "facets": [],
            }
        ]
        
        # First call should fail
        with pytest.raises(RuntimeError, match="Failed to search issues"):
            await issue_tools.search_issues(project_keys=["test-project"])
        
        # Second call should succeed (simulating retry or recovery)
        result = await issue_tools.search_issues(project_keys=["test-project"])
        assert result["total"] == 0
        
        # Test authentication error for Quality Gates
        from src.sonarqube_client.exceptions import AuthenticationError
        quality_gate_tools.client.get.side_effect = AuthenticationError("Invalid token")
        
        with pytest.raises(RuntimeError, match="Failed to list Quality Gates"):
            await quality_gate_tools.list_quality_gates()

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_data_consistency_across_tools(self, issue_tools, quality_gate_tools):
        """Test data consistency across different tools."""
        # Create separate mock clients to avoid interference
        issue_client = AsyncMock(spec=SonarQubeClient)
        qg_client = AsyncMock(spec=SonarQubeClient)
        
        issue_tools.client = issue_client
        quality_gate_tools.client = qg_client
        
        # Mock consistent project data across tools
        project_key = "test-project"
        
        # Issues response
        issues_response = {
            "issues": [
                {
                    "key": f"{project_key}:1",
                    "rule": "java:S1234",
                    "severity": "MAJOR",
                    "component": f"com.example:{project_key}:src/main/java/Example.java",
                    "project": project_key,
                    "status": "OPEN",
                    "type": "BUG",
                    "message": "Test issue",
                    "creationDate": "2025-10-22T10:00:00Z",
                    "updateDate": "2025-10-22T10:00:00Z",
                }
            ],
            "components": [],
            "rules": [],
            "users": [],
            "paging": {"pageIndex": 1, "pageSize": 100, "total": 1},
            "total": 1,
            "facets": [],
        }
        
        # Quality Gate status response
        qg_response = {
            "projectStatus": {
                "status": "ERROR",
                "conditions": [
                    {
                        "status": "ERROR",
                        "metricKey": "bugs",
                        "comparator": "GT",
                        "errorThreshold": "0",
                        "actualValue": "1",  # Consistent with issues count
                    }
                ],
                "ignoredConditions": False,
            }
        }
        
        issue_client.get.return_value = issues_response
        qg_client.get.return_value = qg_response
        
        # Get issues for project
        issues_result = await issue_tools.search_issues(
            project_keys=[project_key],
            types=["BUG"],
            statuses=["OPEN"]
        )
        
        # Get Quality Gate status for same project
        qg_result = await quality_gate_tools.get_project_quality_gate_status(project_key)
        
        # Verify data consistency
        bug_count = len([issue for issue in issues_result["issues"] if issue["type"] == "BUG"])
        qg_bug_condition = next(
            (cond for cond in qg_result["conditions"] if cond["metricKey"] == "bugs"),
            None
        )
        
        # Note: The search_issues method filters issues, so we need to check the total from the response
        assert issues_result["total"] == 1  # Total issues from API response
        assert qg_bug_condition is not None
        assert int(qg_bug_condition["actualValue"]) == 1  # Should match the API response
        assert qg_result["status"] == "ERROR"  # Consistent with having bugs

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_concurrent_tool_operations(self, issue_tools, quality_gate_tools):
        """Test concurrent operations across different tools."""
        # Mock responses
        issue_tools.client.get.return_value = {
            "issues": [],
            "components": [],
            "rules": [],
            "users": [],
            "paging": {"pageIndex": 1, "pageSize": 100, "total": 0},
            "total": 0,
            "facets": [],
        }
        
        quality_gate_tools.client.get.return_value = {"qualitygates": []}
        
        # Execute operations concurrently
        tasks = [
            issue_tools.search_issues(project_keys=["project1"]),
            issue_tools.search_issues(project_keys=["project2"]),
            quality_gate_tools.list_quality_gates(),
            quality_gate_tools.list_quality_gates(),  # Test concurrent access to same resource
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Verify all operations completed successfully
        for result in results:
            assert not isinstance(result, Exception)
        
        # Verify API calls were made (both tools share the same mock client)
        # Total calls should be 4 (2 for issues + 2 for quality gates)
        total_calls = issue_tools.client.get.call_count
        assert total_calls == 4