"""Tests for Quality Gates management tools."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from src.mcp_server.tools.quality_gates import QualityGateTools
from src.sonarqube_client import SonarQubeClient


class TestQualityGateTools:
    """Test cases for QualityGateTools class."""

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
    def quality_gate_tools(self, mock_client, mock_cache):
        """Create QualityGateTools instance with mocked dependencies."""
        return QualityGateTools(mock_client, mock_cache)

    @pytest.mark.asyncio
    async def test_list_quality_gates_success(self, quality_gate_tools, mock_client):
        """Test successful Quality Gates listing."""
        # Mock API response
        mock_response = {
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
        mock_client.get.return_value = mock_response

        result = await quality_gate_tools.list_quality_gates()

        assert result["total_count"] == 2
        assert len(result["quality_gates"]) == 2
        assert result["quality_gates"][0]["name"] == "Sonar way"
        assert result["quality_gates"][0]["isDefault"] is True
        assert result["default_gate"]["name"] == "Sonar way"
        mock_client.get.assert_called_once_with("/qualitygates/list")

    @pytest.mark.asyncio
    async def test_list_quality_gates_cached(self, quality_gate_tools, mock_client, mock_cache):
        """Test Quality Gates listing with cache hit."""
        cached_data = {
            "quality_gates": [],
            "total_count": 0,
            "default_gate": None,
        }
        mock_cache.get.return_value = cached_data

        result = await quality_gate_tools.list_quality_gates()

        # Should return cached data without API call
        assert result == cached_data
        mock_client.get.assert_not_called()
        mock_cache.get.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_quality_gate_conditions_success(self, quality_gate_tools, mock_client):
        """Test successful Quality Gate conditions retrieval."""
        # Mock list response to find gate ID
        list_response = {
            "qualitygates": [
                {
                    "id": "1",
                    "name": "Sonar way",
                    "isDefault": True,
                    "isBuiltIn": True,
                }
            ]
        }
        
        # Mock conditions response
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
                    "metric": "bugs",
                    "op": "GT",
                    "error": "0",
                },
                {
                    "id": "3",
                    "metric": "vulnerabilities",
                    "op": "GT",
                    "error": "0",
                },
            ]
        }
        
        mock_client.get.side_effect = [list_response, conditions_response]

        result = await quality_gate_tools.get_quality_gate_conditions("Sonar way")

        assert result["quality_gate"]["name"] == "Sonar way"
        assert result["quality_gate"]["id"] == "1"
        assert result["quality_gate"]["is_default"] is True
        assert result["total_conditions"] == 3
        assert len(result["conditions"]) == 3
        assert "condition_analysis" in result

        # Verify API calls
        assert mock_client.get.call_count == 2
        mock_client.get.assert_any_call("/qualitygates/list")
        mock_client.get.assert_any_call("/qualitygates/show", params={"id": "1"})

    @pytest.mark.asyncio
    async def test_get_quality_gate_conditions_not_found(self, quality_gate_tools, mock_client):
        """Test Quality Gate conditions when gate not found."""
        list_response = {"qualitygates": []}
        mock_client.get.return_value = list_response

        with pytest.raises(RuntimeError, match="Quality Gate not found"):
            await quality_gate_tools.get_quality_gate_conditions("Nonexistent Gate")

    @pytest.mark.asyncio
    async def test_get_project_quality_gate_status_success(self, quality_gate_tools, mock_client):
        """Test successful project Quality Gate status retrieval."""
        # Mock API response
        mock_response = {
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
                        "metricKey": "bugs",
                        "comparator": "GT",
                        "errorThreshold": "0",
                        "actualValue": "0",
                    },
                ],
                "ignoredConditions": False,
                "period": {
                    "mode": "previous_version",
                    "date": "2025-10-20T10:00:00Z",
                },
            }
        }
        mock_client.get.return_value = mock_response

        result = await quality_gate_tools.get_project_quality_gate_status("test-project")

        assert result["project_key"] == "test-project"
        assert result["status"] == "ERROR"
        assert len(result["conditions"]) == 2
        assert result["ignored_conditions"] is False
        assert "condition_analysis" in result
        assert "recommendations" in result

        # Verify condition analysis
        analysis = result["condition_analysis"]
        assert analysis["total_conditions"] == 2
        assert analysis["failed_conditions"] == 1
        assert analysis["passed_conditions"] == 1
        assert analysis["pass_rate_percent"] == 50.0

        # Verify recommendations are generated for failed status
        assert len(result["recommendations"]) > 0

        # Verify API call
        mock_client.get.assert_called_once_with(
            "/qualitygates/project_status", params={"projectKey": "test-project"}
        )

    @pytest.mark.asyncio
    async def test_get_project_quality_gate_status_passed(self, quality_gate_tools, mock_client):
        """Test project Quality Gate status when all conditions pass."""
        mock_response = {
            "projectStatus": {
                "status": "OK",
                "conditions": [
                    {
                        "status": "OK",
                        "metricKey": "coverage",
                        "comparator": "LT",
                        "errorThreshold": "80",
                        "actualValue": "85.0",
                    }
                ],
                "ignoredConditions": False,
            }
        }
        mock_client.get.return_value = mock_response

        result = await quality_gate_tools.get_project_quality_gate_status("test-project")

        assert result["status"] == "OK"
        assert "recommendations" not in result  # No recommendations for passing gates

        # Verify condition analysis
        analysis = result["condition_analysis"]
        assert analysis["failed_conditions"] == 0
        assert analysis["passed_conditions"] == 1
        assert analysis["pass_rate_percent"] == 100.0

    @pytest.mark.asyncio
    async def test_cache_integration(self, quality_gate_tools, mock_client, mock_cache):
        """Test cache integration in Quality Gate tools."""
        # Test cache hit for list_quality_gates
        cached_data = {"quality_gates": [], "total_count": 0}
        mock_cache.get.return_value = cached_data

        result = await quality_gate_tools.list_quality_gates()

        # Should return cached data without API call
        assert result == cached_data
        mock_client.get.assert_not_called()

        # Test cache miss and set
        mock_cache.get.return_value = None
        mock_response = {"qualitygates": []}
        mock_client.get.return_value = mock_response

        result = await quality_gate_tools.list_quality_gates()

        # Should make API call and cache result
        mock_client.get.assert_called_once()
        mock_cache.set.assert_called_once()

    def test_analyze_conditions(self, quality_gate_tools):
        """Test condition analysis functionality."""
        conditions = [
            {
                "metric": "coverage",
                "op": "LT",
                "error": "80",
            },
            {
                "metric": "new_coverage",
                "op": "LT",
                "error": "80",
            },
            {
                "metric": "security_rating",
                "op": "GT",
                "error": "1",
            },
            {
                "metric": "maintainability_rating",
                "op": "GT",
                "error": "1",
            },
        ]

        analysis = quality_gate_tools._analyze_conditions(conditions)

        assert analysis["total_conditions"] == 4
        assert analysis["by_metric"]["coverage"] == 1
        assert analysis["by_metric"]["new_coverage"] == 1
        assert analysis["by_operator"]["LT"] == 2
        assert analysis["by_operator"]["GT"] == 2
        assert len(analysis["coverage_conditions"]) == 2
        assert len(analysis["security_conditions"]) == 1
        assert len(analysis["maintainability_conditions"]) == 1

    def test_analyze_project_conditions(self, quality_gate_tools):
        """Test project-specific condition analysis."""
        conditions = [
            {
                "status": "OK",
                "metricKey": "coverage",
                "comparator": "LT",
                "errorThreshold": "80",
                "actualValue": "85.0",
            },
            {
                "status": "ERROR",
                "metricKey": "bugs",
                "comparator": "GT",
                "errorThreshold": "0",
                "actualValue": "5",
            },
            {
                "status": "WARN",
                "metricKey": "code_smells",
                "comparator": "GT",
                "errorThreshold": "10",
                "actualValue": "12",
            },
        ]

        analysis = quality_gate_tools._analyze_project_conditions(conditions)

        assert analysis["total_conditions"] == 3
        assert analysis["passed_conditions"] == 1
        assert analysis["failed_conditions"] == 1
        assert analysis["warning_conditions"] == 1
        assert analysis["pass_rate_percent"] == pytest.approx(33.33, rel=1e-2)
        assert len(analysis["failed_condition_details"]) == 1

        # Check failed condition details
        failed_detail = analysis["failed_condition_details"][0]
        assert failed_detail["metric"] == "bugs"
        assert failed_detail["actual_value"] == "5"
        assert failed_detail["threshold"] == "0"

    def test_generate_quality_gate_recommendations(self, quality_gate_tools):
        """Test Quality Gate recommendations generation."""
        conditions = [
            {
                "status": "ERROR",
                "metricKey": "coverage",
                "comparator": "LT",
                "errorThreshold": "80",
                "actualValue": "65.5",
            },
            {
                "status": "ERROR",
                "metricKey": "new_coverage",
                "comparator": "LT",
                "errorThreshold": "80",
                "actualValue": "70.0",
            },
            {
                "status": "ERROR",
                "metricKey": "bugs",
                "comparator": "GT",
                "errorThreshold": "0",
                "actualValue": "3",
            },
            {
                "status": "ERROR",
                "metricKey": "vulnerabilities",
                "comparator": "GT",
                "errorThreshold": "0",
                "actualValue": "1",
            },
            {
                "status": "ERROR",
                "metricKey": "code_smells",
                "comparator": "GT",
                "errorThreshold": "10",
                "actualValue": "25",
            },
            {
                "status": "ERROR",
                "metricKey": "duplicated_lines_density",
                "comparator": "GT",
                "errorThreshold": "3.0",
                "actualValue": "8.5",
            },
        ]

        recommendations = quality_gate_tools._generate_quality_gate_recommendations(conditions)

        assert len(recommendations) == 6
        assert any("coverage from 65.5% to at least 80%" in rec for rec in recommendations)
        assert any("new code has at least 80% test coverage" in rec for rec in recommendations)
        assert any("Fix existing bugs" in rec for rec in recommendations)
        assert any("Address security vulnerabilities" in rec for rec in recommendations)
        assert any("Resolve code smells" in rec for rec in recommendations)
        assert any("Reduce code duplication from 8.5% to under 3.0%" in rec for rec in recommendations)

    def test_generate_quality_gate_recommendations_unknown_metric(self, quality_gate_tools):
        """Test recommendations for unknown metrics."""
        conditions = [
            {
                "status": "ERROR",
                "metricKey": "unknown_metric",
                "comparator": "LT",
                "errorThreshold": "100",
                "actualValue": "50",
            }
        ]

        recommendations = quality_gate_tools._generate_quality_gate_recommendations(conditions)

        assert len(recommendations) == 1
        assert "unknown_metric: current value 50, required LT 100" in recommendations[0]

    @pytest.mark.asyncio
    async def test_invalid_project_key(self, quality_gate_tools):
        """Test validation of invalid project key."""
        with pytest.raises(RuntimeError, match="Failed to get Quality Gate status"):
            await quality_gate_tools.get_project_quality_gate_status("invalid key with spaces")

    @pytest.mark.asyncio
    async def test_empty_quality_gate_name(self, quality_gate_tools):
        """Test validation of empty Quality Gate name."""
        with pytest.raises(RuntimeError, match="Quality Gate name cannot be empty"):
            await quality_gate_tools.get_quality_gate_conditions("")

        with pytest.raises(RuntimeError, match="Quality Gate name cannot be empty"):
            await quality_gate_tools.get_quality_gate_conditions("   ")

    @pytest.mark.asyncio
    async def test_client_error_handling(self, quality_gate_tools, mock_client):
        """Test error handling when client raises exception."""
        mock_client.get.side_effect = Exception("API Error")

        with pytest.raises(RuntimeError, match="Failed to list Quality Gates"):
            await quality_gate_tools.list_quality_gates()

        with pytest.raises(RuntimeError, match="Failed to get Quality Gate conditions"):
            await quality_gate_tools.get_quality_gate_conditions("Test Gate")

        with pytest.raises(RuntimeError, match="Failed to get Quality Gate status"):
            await quality_gate_tools.get_project_quality_gate_status("test-project")

    @pytest.mark.asyncio
    async def test_cache_ttl_configuration(self, quality_gate_tools, mock_client, mock_cache):
        """Test that Quality Gates use longer TTL for caching."""
        mock_response = {"qualitygates": []}
        mock_client.get.return_value = mock_response

        await quality_gate_tools.list_quality_gates()

        # Verify cache.set was called with longer TTL (1800 seconds)
        mock_cache.set.assert_called_once()
        call_args = mock_cache.set.call_args
        # The TTL should be passed as ttl parameter
        assert call_args[1]["ttl"] == 1800

    @pytest.mark.asyncio
    async def test_conditions_with_analysis(self, quality_gate_tools, mock_client):
        """Test that conditions include analysis when present."""
        list_response = {
            "qualitygates": [
                {"id": "1", "name": "Test Gate", "isDefault": False, "isBuiltIn": False}
            ]
        }
        conditions_response = {
            "conditions": [
                {"metric": "coverage", "op": "LT", "error": "80"},
                {"metric": "bugs", "op": "GT", "error": "0"},
            ]
        }
        mock_client.get.side_effect = [list_response, conditions_response]

        result = await quality_gate_tools.get_quality_gate_conditions("Test Gate")

        # Verify analysis is included
        assert "condition_analysis" in result
        analysis = result["condition_analysis"]
        assert analysis["total_conditions"] == 2
        assert "by_metric" in analysis
        assert "by_operator" in analysis

    @pytest.mark.asyncio
    async def test_project_status_without_conditions(self, quality_gate_tools, mock_client):
        """Test project Quality Gate status without conditions."""
        mock_response = {
            "projectStatus": {
                "status": "NONE",
                "conditions": [],
                "ignoredConditions": False,
            }
        }
        mock_client.get.return_value = mock_response

        result = await quality_gate_tools.get_project_quality_gate_status("test-project")

        assert result["status"] == "NONE"
        assert len(result["conditions"]) == 0
        # Should not have condition_analysis for empty conditions
        assert "condition_analysis" not in result
        # Should not have recommendations for NONE status
        assert "recommendations" not in result