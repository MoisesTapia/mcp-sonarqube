"""Tests for issue management tools."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from src.mcp_server.tools.issues import IssueTools
from src.sonarqube_client import SonarQubeClient


class TestIssueTools:
    """Test cases for IssueTools class."""

    @pytest.fixture
    def mock_client(self):
        """Create a mock SonarQube client."""
        client = AsyncMock(spec=SonarQubeClient)
        return client

    @pytest.fixture
    def mock_cache(self):
        """Create a mock cache manager."""
        cache = AsyncMock()
        cache.get.return_value = None  # No cached data by default
        return cache

    @pytest.fixture
    def issue_tools(self, mock_client, mock_cache):
        """Create IssueTools instance with mocked dependencies."""
        return IssueTools(mock_client, mock_cache)

    @pytest.mark.asyncio
    async def test_search_issues_success(self, issue_tools, mock_client):
        """Test successful issue search."""
        # Mock API response
        mock_response = {
            "issues": [
                {
                    "key": "test-project:1",
                    "rule": "java:S1234",
                    "severity": "MAJOR",
                    "component": "com.example:project:src/main/java/Example.java",
                    "status": "OPEN",
                    "type": "BUG",
                    "assignee": "user1",
                    "creationDate": "2025-10-22T10:00:00Z",
                },
                {
                    "key": "test-project:2",
                    "rule": "java:S5678",
                    "severity": "MINOR",
                    "component": "com.example:project:src/main/java/Test.java",
                    "status": "RESOLVED",
                    "type": "CODE_SMELL",
                    "assignee": "user2",
                    "creationDate": "2025-10-21T15:30:00Z",
                }
            ],
            "components": [],
            "rules": [],
            "users": [],
            "paging": {"pageIndex": 1, "pageSize": 100, "total": 2},
            "total": 2,
            "facets": [],
        }
        mock_client.get.return_value = mock_response

        result = await issue_tools.search_issues(project_keys=["test-project"])

        assert result["total"] == 2
        assert len(result["issues"]) == 2
        assert result["issues"][0]["key"] == "test-project:1"
        assert result["issues"][0]["severity"] == "MAJOR"
        assert "summary" in result
        mock_client.get.assert_called_once()

    @pytest.mark.asyncio
    async def test_search_issues_with_filters(self, issue_tools, mock_client):
        """Test issue search with comprehensive filters."""
        mock_response = {
            "issues": [],
            "components": [],
            "rules": [],
            "users": [],
            "paging": {"pageIndex": 1, "pageSize": 50, "total": 0},
            "total": 0,
            "facets": [],
        }
        mock_client.get.return_value = mock_response

        result = await issue_tools.search_issues(
            project_keys=["project1", "project2"],
            severities=["MAJOR", "CRITICAL"],
            types=["BUG", "VULNERABILITY"],
            statuses=["OPEN", "CONFIRMED"],
            assignees=["user1"],
            created_after="2025-10-01",
            created_before="2025-10-31",
            page=1,
            page_size=50,
        )

        # Verify API call parameters
        call_args = mock_client.get.call_args
        params = call_args[1]["params"]
        assert params["projectKeys"] == "project1,project2"
        assert params["severities"] == "MAJOR,CRITICAL"
        assert params["types"] == "BUG,VULNERABILITY"
        assert params["statuses"] == "OPEN,CONFIRMED"
        assert params["assignees"] == "user1"
        assert params["createdAfter"] == "2025-10-01"
        assert params["createdBefore"] == "2025-10-31"
        assert params["p"] == 1
        assert params["ps"] == 50

    @pytest.mark.asyncio
    async def test_get_issue_details_success(self, issue_tools, mock_client):
        """Test successful issue details retrieval."""
        # Mock API response
        mock_response = {
            "issues": [
                {
                    "key": "test-project:1",
                    "rule": "java:S1234",
                    "severity": "MAJOR",
                    "component": "com.example:project:src/main/java/Example.java",
                    "status": "OPEN",
                    "type": "BUG",
                    "assignee": "user1",
                    "author": "author1",
                    "creationDate": "2025-10-22T10:00:00Z",
                    "comments": [
                        {
                            "key": "comment-1",
                            "login": "user1",
                            "markdown": "This is a comment",
                            "createdAt": "2025-10-22T11:00:00Z",
                        }
                    ],
                }
            ],
            "components": [
                {
                    "key": "com.example:project:src/main/java/Example.java",
                    "name": "Example.java",
                    "path": "src/main/java/Example.java",
                }
            ],
            "rules": [
                {
                    "key": "java:S1234",
                    "name": "Test Rule",
                    "lang": "java",
                }
            ],
            "users": [
                {"login": "user1", "name": "User One"},
                {"login": "author1", "name": "Author One"},
            ],
        }
        mock_client.get.return_value = mock_response

        result = await issue_tools.get_issue_details("test-project:1")

        assert result["key"] == "test-project:1"
        assert result["severity"] == "MAJOR"
        assert "component_info" in result
        assert "rule_info" in result
        assert "assignee_info" in result
        assert "author_info" in result
        mock_client.get.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_issue_details_not_found(self, issue_tools, mock_client):
        """Test issue details when issue not found."""
        mock_response = {"issues": [], "components": [], "rules": [], "users": []}
        mock_client.get.return_value = mock_response

        with pytest.raises(RuntimeError, match="Issue not found"):
            await issue_tools.get_issue_details("test-project:999")

    @pytest.mark.asyncio
    async def test_update_issue_success(self, issue_tools, mock_client, mock_cache):
        """Test successful issue update."""
        mock_client.post.return_value = {}

        result = await issue_tools.update_issue(
            "test-project:1",
            assign="user1",
            transition="confirm",
            comment="Confirmed this issue",
            severity="CRITICAL",
            type="BUG",
        )

        assert result["success"] is True
        assert result["issue_key"] == "test-project:1"
        assert "assigned to user1" in result["message"]
        assert "transitioned to confirm" in result["message"]
        assert "comment added" in result["message"]
        assert "severity set to CRITICAL" in result["message"]
        assert "type set to BUG" in result["message"]

        # Verify API calls were made
        assert mock_client.post.call_count == 5  # assign, transition, comment, severity, type

        # Verify cache invalidation
        mock_cache.delete.assert_called_once()
        mock_cache.invalidate_pattern.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_issue_assign_only(self, issue_tools, mock_client):
        """Test issue update with assignment only."""
        mock_client.post.return_value = {}

        result = await issue_tools.update_issue("test-project:1", assign="user1")

        assert result["success"] is True
        assert len(result["updates_made"]) == 1
        assert "assigned to user1" in result["updates_made"]

        # Verify only assignment API call was made
        mock_client.post.assert_called_once_with(
            "/issues/assign", data={"issue": "test-project:1", "assignee": "user1"}
        )

    @pytest.mark.asyncio
    async def test_add_issue_comment_success(self, issue_tools, mock_client, mock_cache):
        """Test successful issue comment addition."""
        mock_client.post.return_value = {}

        result = await issue_tools.add_issue_comment("test-project:1", "This is a test comment")

        assert result["success"] is True
        assert result["issue_key"] == "test-project:1"
        assert result["comment_added"] is True

        # Verify API call
        mock_client.post.assert_called_once_with(
            "/issues/add_comment",
            data={"issue": "test-project:1", "text": "This is a test comment"},
        )

        # Verify cache invalidation
        mock_cache.delete.assert_called_once()

    @pytest.mark.asyncio
    async def test_add_issue_comment_empty_text(self, issue_tools):
        """Test issue comment addition with empty text."""
        with pytest.raises(RuntimeError, match="Comment text cannot be empty"):
            await issue_tools.add_issue_comment("test-project:1", "")

        with pytest.raises(RuntimeError, match="Comment text cannot be empty"):
            await issue_tools.add_issue_comment("test-project:1", "   ")

    @pytest.mark.asyncio
    async def test_get_issue_transitions_success(self, issue_tools, mock_client):
        """Test successful issue transitions retrieval."""
        mock_response = {
            "transitions": [
                {"transition": "confirm", "name": "Confirm"},
                {"transition": "resolve", "name": "Resolve"},
                {"transition": "reopen", "name": "Reopen"},
            ]
        }
        mock_client.get.return_value = mock_response

        result = await issue_tools.get_issue_transitions("test-project:1")

        assert result["issue_key"] == "test-project:1"
        assert len(result["transitions"]) == 3
        assert result["transitions"][0]["transition"] == "confirm"

        # Verify API call
        mock_client.get.assert_called_once_with(
            "/issues/transitions", params={"issue": "test-project:1"}
        )

    @pytest.mark.asyncio
    async def test_invalid_severity(self, issue_tools):
        """Test validation of invalid severity."""
        with pytest.raises(RuntimeError, match="Failed to update issue"):
            await issue_tools.update_issue("test-project:1", severity="INVALID_SEVERITY")

    @pytest.mark.asyncio
    async def test_invalid_issue_type(self, issue_tools):
        """Test validation of invalid issue type."""
        with pytest.raises(RuntimeError, match="Failed to update issue"):
            await issue_tools.update_issue("test-project:1", type="INVALID_TYPE")

    @pytest.mark.asyncio
    async def test_invalid_issue_status(self, issue_tools):
        """Test validation of invalid issue status."""
        with pytest.raises(RuntimeError, match="Failed to search issues"):
            await issue_tools.search_issues(statuses=["INVALID_STATUS"])

    @pytest.mark.asyncio
    async def test_cache_integration(self, issue_tools, mock_client, mock_cache):
        """Test cache integration in issue tools."""
        # Test cache hit
        cached_data = {"issues": [], "total": 0}
        mock_cache.get.return_value = cached_data

        result = await issue_tools.search_issues(project_keys=["test-project"])

        # Should return cached data without API call
        assert result == cached_data
        mock_client.get.assert_not_called()
        mock_cache.get.assert_called_once()

        # Test cache miss and set
        mock_cache.get.return_value = None
        mock_response = {
            "issues": [],
            "components": [],
            "rules": [],
            "users": [],
            "paging": {"total": 0},
            "total": 0,
            "facets": [],
        }
        mock_client.get.return_value = mock_response

        result = await issue_tools.search_issues(project_keys=["test-project"])

        # Should make API call and cache result
        mock_client.get.assert_called_once()
        mock_cache.set.assert_called_once()

    def test_generate_issue_summary(self, issue_tools):
        """Test issue summary generation."""
        issues = [
            {
                "severity": "MAJOR",
                "type": "BUG",
                "status": "OPEN",
                "assignee": "user1",
            },
            {
                "severity": "MINOR",
                "type": "CODE_SMELL",
                "status": "RESOLVED",
                "assignee": "user2",
            },
            {
                "severity": "MAJOR",
                "type": "VULNERABILITY",
                "status": "OPEN",
                # No assignee (unassigned)
            },
        ]

        summary = issue_tools._generate_issue_summary(issues)

        assert summary["total_count"] == 3
        assert summary["by_severity"]["MAJOR"] == 2
        assert summary["by_severity"]["MINOR"] == 1
        assert summary["by_type"]["BUG"] == 1
        assert summary["by_type"]["CODE_SMELL"] == 1
        assert summary["by_type"]["VULNERABILITY"] == 1
        assert summary["by_status"]["OPEN"] == 2
        assert summary["by_status"]["RESOLVED"] == 1
        assert summary["by_assignee"]["user1"] == 1
        assert summary["by_assignee"]["user2"] == 1
        assert summary["by_assignee"]["UNASSIGNED"] == 1

    def test_generate_issue_summary_empty(self, issue_tools):
        """Test issue summary generation with empty list."""
        summary = issue_tools._generate_issue_summary([])
        assert summary == {}

    @pytest.mark.asyncio
    async def test_pagination_validation(self, issue_tools, mock_client):
        """Test pagination parameter validation."""
        mock_response = {
            "issues": [],
            "components": [],
            "rules": [],
            "users": [],
            "paging": {"pageIndex": 1, "pageSize": 100, "total": 0},
            "total": 0,
            "facets": [],
        }
        mock_client.get.return_value = mock_response

        # Test valid pagination
        await issue_tools.search_issues(page=1, page_size=100)

        # Test page size limit validation should be handled by InputValidator
        # The actual validation happens in the InputValidator.validate_pagination_params method

    @pytest.mark.asyncio
    async def test_client_error_handling(self, issue_tools, mock_client):
        """Test error handling when client raises exception."""
        mock_client.get.side_effect = Exception("API Error")

        with pytest.raises(RuntimeError, match="Failed to search issues"):
            await issue_tools.search_issues(project_keys=["test-project"])

        # Test error in issue details
        with pytest.raises(RuntimeError, match="Failed to get issue details"):
            await issue_tools.get_issue_details("issue-1")

        # Test error in transitions
        with pytest.raises(RuntimeError, match="Failed to get issue transitions"):
            await issue_tools.get_issue_transitions("issue-1")

    @pytest.mark.asyncio
    async def test_update_issue_error_handling(self, issue_tools, mock_client):
        """Test error handling in issue updates."""
        mock_client.post.side_effect = Exception("API Error")

        with pytest.raises(RuntimeError, match="Failed to update issue"):
            await issue_tools.update_issue("test-project:1", assign="user1")

        with pytest.raises(RuntimeError, match="Failed to add comment"):
            await issue_tools.add_issue_comment("test-project:1", "test comment")