"""Tests for MCP prompts."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from src.mcp_server.prompts import PromptManager, AnalyzeProjectQualityPrompt
from src.sonarqube_client import SonarQubeClient


class TestPromptManager:
    """Test cases for PromptManager class."""

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
    def prompt_manager(self, mock_client, mock_cache):
        """Create PromptManager instance with mocked dependencies."""
        return PromptManager(mock_client, mock_cache)

    @pytest.mark.asyncio
    async def test_execute_analyze_project_quality_prompt(self, prompt_manager, mock_client):
        """Test executing analyze_project_quality prompt."""
        # Mock API responses
        project_response = {
            "components": [
                {"key": "my-project", "name": "My Project", "qualifier": "TRK"}
            ]
        }
        
        metrics_response = {
            "component": {
                "measures": [
                    {"metric": "ncloc", "value": "1000"},
                    {"metric": "bugs", "value": "5"},
                    {"metric": "coverage", "value": "85.5"},
                ]
            }
        }
        
        qg_response = {
            "projectStatus": {
                "status": "OK",
                "conditions": []
            }
        }
        
        issues_response = {
            "total": 10,
            "facets": [
                {
                    "property": "severities",
                    "values": [
                        {"val": "MAJOR", "count": 5},
                        {"val": "MINOR", "count": 5}
                    ]
                }
            ]
        }
        
        mock_client.get.side_effect = [
            project_response,
            metrics_response,
            qg_response,
            issues_response
        ]

        result = await prompt_manager.execute_prompt(
            "analyze_project_quality",
            {"project_key": "my-project"}
        )

        assert isinstance(result, str)
        assert "Comprehensive Quality Analysis" in result
        assert "My Project" in result
        assert "Quality Gate" in result

    @pytest.mark.asyncio
    async def test_execute_security_assessment_prompt(self, prompt_manager, mock_client):
        """Test executing security_assessment prompt."""
        # Mock API responses
        project_response = {
            "components": [
                {"key": "my-project", "name": "My Project", "qualifier": "TRK"}
            ]
        }
        
        metrics_response = {
            "component": {
                "measures": [
                    {"metric": "vulnerabilities", "value": "3"},
                    {"metric": "security_hotspots", "value": "5"},
                    {"metric": "security_rating", "value": "2"},
                ]
            }
        }
        
        vulnerabilities_response = {
            "issues": [
                {
                    "key": "vuln-1",
                    "severity": "CRITICAL",
                    "type": "VULNERABILITY",
                    "status": "OPEN",
                    "message": "SQL injection vulnerability",
                    "component": "com.example:project:src/main/java/Example.java",
                    "creationDate": "2025-10-22T10:00:00Z"
                }
            ],
            "components": [],
            "rules": []
        }
        
        hotspots_response = {
            "hotspots": [
                {
                    "key": "hotspot-1",
                    "vulnerabilityProbability": "HIGH",
                    "securityCategory": "sql-injection",
                    "status": "TO_REVIEW",
                    "message": "Review this SQL query",
                    "component": "com.example:project:src/main/java/Example.java",
                    "creationDate": "2025-10-22T10:00:00Z"
                }
            ],
            "components": [],
            "rules": []
        }
        
        mock_client.get.side_effect = [
            project_response,
            metrics_response,
            vulnerabilities_response,
            hotspots_response
        ]

        result = await prompt_manager.execute_prompt(
            "security_assessment",
            {"project_key": "my-project"}
        )

        assert isinstance(result, str)
        assert "Security Assessment Report" in result
        assert "My Project" in result
        assert "MEDIUM RISK" in result or "HIGH RISK" in result or "LOW RISK" in result

    @pytest.mark.asyncio
    async def test_execute_code_review_summary_prompt(self, prompt_manager, mock_client):
        """Test executing code_review_summary prompt."""
        # Mock API responses
        project_response = {
            "components": [
                {"key": "my-project", "name": "My Project", "qualifier": "TRK"}
            ]
        }
        
        new_metrics_response = {
            "component": {
                "measures": [
                    {"metric": "new_lines", "value": "100"},
                    {"metric": "new_bugs", "value": "2"},
                    {"metric": "new_coverage", "value": "75.0"},
                ]
            }
        }
        
        new_issues_response = {
            "issues": [
                {
                    "key": "issue-1",
                    "severity": "MAJOR",
                    "type": "BUG",
                    "status": "OPEN",
                    "message": "Potential null pointer",
                    "component": "com.example:project:src/main/java/Example.java",
                    "creationDate": "2025-10-22T10:00:00Z"
                }
            ],
            "total": 1,
            "components": [],
            "rules": [],
            "facets": []
        }
        
        qg_response = {
            "projectStatus": {
                "status": "OK",
                "conditions": []
            }
        }
        
        coverage_response = {
            "component": {
                "measures": [
                    {"metric": "new_coverage", "value": "75.0"},
                    {"metric": "tests", "value": "50"},
                ]
            }
        }
        
        mock_client.get.side_effect = [
            project_response,
            new_metrics_response,
            new_issues_response,
            qg_response,
            coverage_response
        ]

        result = await prompt_manager.execute_prompt(
            "code_review_summary",
            {"project_key": "my-project"}
        )

        assert isinstance(result, str)
        assert "Code Review Summary" in result
        assert "My Project" in result
        assert "Quality Gate" in result

    @pytest.mark.asyncio
    async def test_execute_unknown_prompt(self, prompt_manager):
        """Test executing unknown prompt."""
        with pytest.raises(RuntimeError, match="Failed to execute prompt"):
            await prompt_manager.execute_prompt("unknown_prompt", {})

    @pytest.mark.asyncio
    async def test_execute_prompt_missing_arguments(self, prompt_manager):
        """Test executing prompt with missing required arguments."""
        with pytest.raises(RuntimeError, match="Failed to execute prompt"):
            await prompt_manager.execute_prompt("analyze_project_quality", {})

    def test_list_prompts(self, prompt_manager):
        """Test listing available prompts."""
        prompts = prompt_manager.list_prompts()
        
        assert len(prompts) == 3
        
        prompt_names = [p["name"] for p in prompts]
        assert "analyze_project_quality" in prompt_names
        assert "security_assessment" in prompt_names
        assert "code_review_summary" in prompt_names
        
        # Check that each prompt has required fields
        for prompt in prompts:
            assert "name" in prompt
            assert "description" in prompt
            assert "arguments" in prompt

    def test_get_prompt_schema(self, prompt_manager):
        """Test getting prompt schema."""
        schema = prompt_manager.get_prompt_schema("analyze_project_quality")
        
        assert schema is not None
        assert schema["name"] == "analyze_project_quality"
        assert "description" in schema
        assert "arguments" in schema
        
        # Check arguments structure
        arguments = schema["arguments"]
        assert len(arguments) >= 1
        
        project_key_arg = next((arg for arg in arguments if arg["name"] == "project_key"), None)
        assert project_key_arg is not None
        assert project_key_arg["required"] is True
        assert project_key_arg["type"] == "string"

    def test_get_unknown_prompt_schema(self, prompt_manager):
        """Test getting schema for unknown prompt."""
        schema = prompt_manager.get_prompt_schema("unknown_prompt")
        assert schema is None

    def test_get_prompt(self, prompt_manager):
        """Test getting prompt instance."""
        prompt = prompt_manager.get_prompt("analyze_project_quality")
        assert prompt is not None
        assert isinstance(prompt, AnalyzeProjectQualityPrompt)
        
        unknown_prompt = prompt_manager.get_prompt("unknown_prompt")
        assert unknown_prompt is None


class TestAnalyzeProjectQualityPrompt:
    """Test cases for AnalyzeProjectQualityPrompt class."""

    @pytest.fixture
    def mock_client(self):
        """Create a mock SonarQube client."""
        client = AsyncMock(spec=SonarQubeClient)
        return client

    @pytest.fixture
    def mock_cache(self):
        """Create a mock cache manager."""
        cache = AsyncMock()
        cache.get.return_value = None
        return cache

    @pytest.fixture
    def quality_prompt(self, mock_client, mock_cache):
        """Create AnalyzeProjectQualityPrompt instance with mocked dependencies."""
        return AnalyzeProjectQualityPrompt(mock_client, mock_cache)

    def test_prompt_metadata(self, quality_prompt):
        """Test prompt metadata."""
        assert quality_prompt.get_name() == "analyze_project_quality"
        assert "comprehensive quality analysis" in quality_prompt.get_description().lower()
        
        arguments = quality_prompt.get_arguments()
        assert len(arguments) >= 1
        
        project_key_arg = next((arg for arg in arguments if arg["name"] == "project_key"), None)
        assert project_key_arg is not None
        assert project_key_arg["required"] is True

    @pytest.mark.asyncio
    async def test_execute_with_minimal_arguments(self, quality_prompt, mock_client):
        """Test executing prompt with minimal arguments."""
        # Mock API responses
        project_response = {
            "components": [
                {"key": "test-project", "name": "Test Project", "qualifier": "TRK"}
            ]
        }
        
        metrics_response = {
            "component": {
                "measures": [
                    {"metric": "ncloc", "value": "1000"},
                    {"metric": "bugs", "value": "0"},
                ]
            }
        }
        
        qg_response = {
            "projectStatus": {
                "status": "OK",
                "conditions": []
            }
        }
        
        issues_response = {
            "total": 0,
            "facets": []
        }
        
        mock_client.get.side_effect = [
            project_response,
            metrics_response,
            qg_response,
            issues_response
        ]

        result = await quality_prompt.execute({"project_key": "test-project"})

        assert isinstance(result, str)
        assert "Test Project" in result
        assert "Quality Gate" in result
        assert "PASSED" in result

    @pytest.mark.asyncio
    async def test_execute_with_history(self, quality_prompt, mock_client):
        """Test executing prompt with history enabled."""
        # Mock API responses (same as above plus history)
        project_response = {
            "components": [
                {"key": "test-project", "name": "Test Project", "qualifier": "TRK"}
            ]
        }
        
        metrics_response = {
            "component": {
                "measures": [
                    {"metric": "bugs", "value": "5"},
                ]
            }
        }
        
        qg_response = {
            "projectStatus": {
                "status": "OK",
                "conditions": []
            }
        }
        
        issues_response = {
            "total": 5,
            "facets": []
        }
        
        history_response = {
            "measures": [
                {
                    "metric": "bugs",
                    "history": [
                        {"date": "2025-10-01", "value": "10"},
                        {"date": "2025-10-22", "value": "5"}
                    ]
                }
            ]
        }
        
        mock_client.get.side_effect = [
            project_response,
            metrics_response,
            qg_response,
            issues_response,
            history_response
        ]

        result = await quality_prompt.execute({
            "project_key": "test-project",
            "include_history": True
        })

        assert isinstance(result, str)
        assert "Historical Trends" in result
        assert "bugs" in result.lower()

    @pytest.mark.asyncio
    async def test_execute_missing_project_key(self, quality_prompt):
        """Test executing prompt without project_key."""
        with pytest.raises(ValueError, match="project_key is required"):
            await quality_prompt.execute({})

    @pytest.mark.asyncio
    async def test_cache_integration(self, quality_prompt, mock_client, mock_cache):
        """Test cache integration."""
        # Test cache hit
        cached_result = "Cached analysis result"
        mock_cache.get.return_value = cached_result

        result = await quality_prompt.execute({"project_key": "test-project"})

        # Should return cached result without API calls
        assert result == cached_result
        mock_client.get.assert_not_called()

        # Test cache miss and set
        mock_cache.get.return_value = None
        
        # Mock minimal API responses
        project_response = {"components": [{"key": "test-project", "name": "Test", "qualifier": "TRK"}]}
        metrics_response = {"component": {"measures": []}}
        qg_response = {"projectStatus": {"status": "OK", "conditions": []}}
        issues_response = {"total": 0, "facets": []}
        
        mock_client.get.side_effect = [project_response, metrics_response, qg_response, issues_response]

        result = await quality_prompt.execute({"project_key": "test-project"})

        # Should make API calls and cache result
        mock_client.get.assert_called()
        mock_cache.set.assert_called_once()

    @pytest.mark.asyncio
    async def test_api_error_handling(self, quality_prompt, mock_client):
        """Test API error handling."""
        mock_client.get.side_effect = Exception("API Error")

        # Should handle API errors gracefully
        result = await quality_prompt.execute({"project_key": "test-project"})

        # Should still return a result (with error handling)
        assert isinstance(result, str)
        assert "test-project" in result