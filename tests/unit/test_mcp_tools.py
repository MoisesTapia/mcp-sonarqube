"""Unit tests for MCP tools."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from src.mcp_server.tools.projects import ProjectTools
from src.mcp_server.tools.measures import MeasureTools
from src.sonarqube_client import ValidationError
from tests.fixtures.sonarqube_responses import SonarQubeFixtures


class TestProjectTools:
    """Test cases for ProjectTools."""

    @pytest.fixture
    def mock_client(self):
        """Create mock SonarQube client."""
        client = AsyncMock()
        return client

    @pytest.fixture
    def mock_cache(self):
        """Create mock cache manager."""
        cache = AsyncMock()
        cache.get.return_value = None  # Default to cache miss
        return cache

    @pytest.fixture
    def project_tools(self, mock_client, mock_cache):
        """Create ProjectTools instance with mocks."""
        return ProjectTools(mock_client, mock_cache)

    @pytest.mark.asyncio
    async def test_list_projects_success(self, project_tools, mock_client):
        """Test successful project listing."""
        # Setup mock response
        mock_client.get.return_value = SonarQubeFixtures.project_list()
        
        # Call method
        result = await project_tools.list_projects()
        
        # Verify results
        assert "projects" in result
        assert "paging" in result
        assert "total" in result
        assert len(result["projects"]) == 2
        assert result["total"] == 2
        
        # Verify API call
        mock_client.get.assert_called_once_with(
            "/projects/search",
            params={"p": 1, "ps": 100}
        )

    @pytest.mark.asyncio
    async def test_list_projects_with_search(self, project_tools, mock_client):
        """Test project listing with search parameter."""
        mock_client.get.return_value = SonarQubeFixtures.project_list()
        
        result = await project_tools.list_projects(search="test", page=2, page_size=50)
        
        # Verify API call with search parameters
        mock_client.get.assert_called_once_with(
            "/projects/search",
            params={"p": 2, "ps": 50, "q": "test"}
        )

    @pytest.mark.asyncio
    async def test_list_projects_cached(self, project_tools, mock_client, mock_cache):
        """Test project listing with cache hit."""
        # Setup cache to return data
        cached_data = {"projects": [], "paging": {}, "total": 0}
        mock_cache.get.return_value = cached_data
        
        result = await project_tools.list_projects()
        
        # Should return cached data without API call
        assert result == cached_data
        mock_client.get.assert_not_called()
        mock_cache.get.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_project_details_success(self, project_tools, mock_client):
        """Test successful project details retrieval."""
        # Setup mock responses
        mock_client.get.side_effect = [
            SonarQubeFixtures.project_list(),  # Project search
            SonarQubeFixtures.project_measures(),  # Metrics
            SonarQubeFixtures.quality_gate_status(),  # Quality Gate
        ]
        
        result = await project_tools.get_project_details("project-1")
        
        # Verify result structure
        assert "key" in result
        assert "name" in result
        assert "metrics" in result
        assert "quality_gate" in result
        
        # Verify API calls
        assert mock_client.get.call_count == 3

    @pytest.mark.asyncio
    async def test_get_project_details_not_found(self, project_tools, mock_client):
        """Test project details when project not found."""
        # Setup mock to return empty projects list
        mock_client.get.return_value = {"components": []}
        
        with pytest.raises(RuntimeError, match="Project not found"):
            await project_tools.get_project_details("nonexistent-project")

    @pytest.mark.asyncio
    async def test_create_project_success(self, project_tools, mock_client, mock_cache):
        """Test successful project creation."""
        mock_client.post.return_value = {
            "project": {"key": "new-project", "name": "New Project"}
        }
        
        result = await project_tools.create_project("New Project", "new-project")
        
        # Verify result
        assert result["key"] == "new-project"
        assert result["name"] == "New Project"
        
        # Verify API call
        mock_client.post.assert_called_once_with(
            "/projects/create",
            data={
                "name": "New Project",
                "project": "new-project",
                "visibility": "private",
            }
        )
        
        # Verify cache invalidation
        mock_cache.invalidate_pattern.assert_called_once_with("projects", "*")

    @pytest.mark.asyncio
    async def test_create_project_invalid_key(self, project_tools, mock_client):
        """Test project creation with invalid key."""
        with pytest.raises(RuntimeError):
            await project_tools.create_project("Test", "invalid key with spaces")

    @pytest.mark.asyncio
    async def test_delete_project_success(self, project_tools, mock_client, mock_cache):
        """Test successful project deletion."""
        # Mock get_project_details to return a project (exists)
        project_tools.get_project_details = AsyncMock(return_value={"key": "test-project"})
        
        result = await project_tools.delete_project("test-project")
        
        # Verify result
        assert result["success"] is True
        assert "test-project" in result["message"]
        
        # Verify API call
        mock_client.post.assert_called_once_with(
            "/projects/delete",
            data={"project": "test-project"}
        )

    @pytest.mark.asyncio
    async def test_delete_project_not_found(self, project_tools, mock_client):
        """Test project deletion when project doesn't exist."""
        # Mock get_project_details to raise error (not found)
        project_tools.get_project_details = AsyncMock(
            side_effect=RuntimeError("Project not found")
        )
        
        with pytest.raises(RuntimeError, match="Project not found"):
            await project_tools.delete_project("nonexistent-project")

    @pytest.mark.asyncio
    async def test_get_project_branches_success(self, project_tools, mock_client):
        """Test successful project branches retrieval."""
        mock_client.get.return_value = {
            "branches": [
                {"name": "main", "isMain": True},
                {"name": "develop", "isMain": False},
            ]
        }
        
        result = await project_tools.get_project_branches("test-project")
        
        # Verify result
        assert result["project_key"] == "test-project"
        assert len(result["branches"]) == 2
        
        # Verify API call
        mock_client.get.assert_called_once_with(
            "/project_branches/list",
            params={"project": "test-project"}
        )


class TestMeasureTools:
    """Test cases for MeasureTools."""

    @pytest.fixture
    def mock_client(self):
        """Create mock SonarQube client."""
        client = AsyncMock()
        return client

    @pytest.fixture
    def mock_cache(self):
        """Create mock cache manager."""
        cache = AsyncMock()
        cache.get.return_value = None  # Default to cache miss
        return cache

    @pytest.fixture
    def measure_tools(self, mock_client, mock_cache):
        """Create MeasureTools instance with mocks."""
        return MeasureTools(mock_client, mock_cache)

    @pytest.mark.asyncio
    async def test_get_measures_success(self, measure_tools, mock_client):
        """Test successful measures retrieval."""
        mock_client.get.return_value = SonarQubeFixtures.project_measures()
        
        result = await measure_tools.get_measures("project-1")
        
        # Verify result structure
        assert "project_key" in result
        assert "metrics" in result
        assert result["project_key"] == "project-1"
        
        # Verify metrics are properly formatted
        metrics = result["metrics"]
        assert "coverage" in metrics
        assert "bugs" in metrics
        assert metrics["coverage"]["value"] == "85.5"
        
        # Verify API call
        mock_client.get.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_measures_custom_metrics(self, measure_tools, mock_client):
        """Test measures retrieval with custom metrics."""
        mock_client.get.return_value = SonarQubeFixtures.project_measures()
        
        custom_metrics = ["coverage", "bugs"]
        result = await measure_tools.get_measures("project-1", custom_metrics)
        
        # Verify API call includes custom metrics
        call_args = mock_client.get.call_args
        assert "metricKeys" in call_args[1]["params"]
        assert "coverage,bugs" == call_args[1]["params"]["metricKeys"]

    @pytest.mark.asyncio
    async def test_get_quality_gate_status_success(self, measure_tools, mock_client):
        """Test successful Quality Gate status retrieval."""
        mock_client.get.return_value = SonarQubeFixtures.quality_gate_status()
        
        result = await measure_tools.get_quality_gate_status("project-1")
        
        # Verify result structure
        assert "project_key" in result
        assert "status" in result
        assert "conditions" in result
        assert result["project_key"] == "project-1"
        assert result["status"] == "OK"
        
        # Verify API call
        mock_client.get.assert_called_once_with(
            "/qualitygates/project_status",
            params={"projectKey": "project-1"}
        )

    @pytest.mark.asyncio
    async def test_get_project_history_success(self, measure_tools, mock_client):
        """Test successful project history retrieval."""
        mock_response = {
            "measures": [
                {
                    "metric": "coverage",
                    "history": [
                        {"date": "2025-10-20", "value": "80.0"},
                        {"date": "2025-10-21", "value": "85.5"},
                    ]
                }
            ],
            "paging": {"pageIndex": 1, "pageSize": 1000, "total": 1}
        }
        mock_client.get.return_value = mock_response
        
        result = await measure_tools.get_project_history("project-1")
        
        # Verify result structure
        assert "project_key" in result
        assert "metrics_history" in result
        assert result["project_key"] == "project-1"
        
        # Verify history data
        history = result["metrics_history"]
        assert "coverage" in history
        assert len(history["coverage"]) == 2
        assert history["coverage"][0]["value"] == "80.0"

    @pytest.mark.asyncio
    async def test_get_project_history_with_date_range(self, measure_tools, mock_client):
        """Test project history with date range."""
        mock_client.get.return_value = {"measures": [], "paging": {}}
        
        await measure_tools.get_project_history(
            "project-1",
            from_date="2025-10-01",
            to_date="2025-10-31"
        )
        
        # Verify API call includes date parameters
        call_args = mock_client.get.call_args
        params = call_args[1]["params"]
        assert params["from"] == "2025-10-01"
        assert params["to"] == "2025-10-31"

    @pytest.mark.asyncio
    async def test_get_metrics_definitions_success(self, measure_tools, mock_client):
        """Test successful metrics definitions retrieval."""
        mock_response = {
            "metrics": [
                {
                    "key": "coverage",
                    "name": "Coverage",
                    "description": "Test coverage percentage",
                    "type": "PERCENT",
                    "domain": "Coverage",
                }
            ]
        }
        mock_client.get.return_value = mock_response
        
        result = await measure_tools.get_metrics_definitions()
        
        # Verify result structure
        assert "metrics" in result
        assert "total_metrics" in result
        assert result["total_metrics"] == 1
        
        # Verify metric definition
        coverage_def = result["metrics"]["coverage"]
        assert coverage_def["name"] == "Coverage"
        assert coverage_def["type"] == "PERCENT"

    @pytest.mark.asyncio
    async def test_analyze_project_quality_success(self, measure_tools, mock_client):
        """Test successful project quality analysis."""
        # Mock the get_measures and get_quality_gate_status methods
        measure_tools.get_measures = AsyncMock(return_value={
            "project_key": "project-1",
            "project_name": "Test Project",
            "last_analysis": "2025-10-22T10:00:00Z",
            "metrics": {
                "coverage": {"value": "85.5"},
                "bugs": {"value": "3"},
                "vulnerabilities": {"value": "0"},
                "sqale_index": {"value": "120"},  # 2 hours
                "duplicated_lines_density": {"value": "2.5"},
            }
        })
        
        measure_tools.get_quality_gate_status = AsyncMock(return_value={
            "status": "OK"
        })
        
        result = await measure_tools.analyze_project_quality("project-1")
        
        # Verify result structure
        assert "project_key" in result
        assert "overall_status" in result
        assert "quality_summary" in result
        assert "recommendations" in result
        assert "risk_factors" in result
        assert "overall_risk" in result
        
        # Verify analysis results
        assert result["project_key"] == "project-1"
        assert result["overall_status"] == "OK"
        assert result["overall_risk"] == "low"  # Good metrics should result in low risk
        
        # Verify quality summary
        quality_summary = result["quality_summary"]
        assert "coverage" in quality_summary
        assert quality_summary["coverage"]["status"] == "good"  # 85.5% > 80%

    @pytest.mark.asyncio
    async def test_analyze_project_quality_poor_metrics(self, measure_tools, mock_client):
        """Test project quality analysis with poor metrics."""
        # Mock poor metrics
        measure_tools.get_measures = AsyncMock(return_value={
            "project_key": "project-1",
            "project_name": "Test Project",
            "last_analysis": "2025-10-22T10:00:00Z",
            "metrics": {
                "coverage": {"value": "45.0"},  # Poor coverage
                "bugs": {"value": "15"},  # Many bugs
                "vulnerabilities": {"value": "3"},  # Vulnerabilities present
                "sqale_index": {"value": "14400"},  # 240 hours = 30 days
                "duplicated_lines_density": {"value": "15.0"},  # High duplication
            }
        })
        
        measure_tools.get_quality_gate_status = AsyncMock(return_value={
            "status": "ERROR"
        })
        
        result = await measure_tools.analyze_project_quality("project-1")
        
        # Verify poor quality is detected
        assert result["overall_status"] == "ERROR"
        assert result["overall_risk"] == "high"  # Poor metrics should result in high risk
        
        # Should have recommendations and risk factors
        assert len(result["recommendations"]) > 0
        assert len(result["risk_factors"]) > 0
        
        # Verify specific quality assessments
        quality_summary = result["quality_summary"]
        assert quality_summary["coverage"]["status"] == "poor"  # 45% < 60%
        assert quality_summary["bugs"]["status"] == "poor"  # 15 > 10
        assert quality_summary["vulnerabilities"]["status"] == "poor"  # > 0

    @pytest.mark.asyncio
    async def test_invalid_project_key(self, measure_tools, mock_client):
        """Test tools with invalid project key."""
        with pytest.raises(RuntimeError):
            await measure_tools.get_measures("invalid key with spaces")

    @pytest.mark.asyncio
    async def test_invalid_metric_keys(self, measure_tools, mock_client):
        """Test get_measures with invalid metric keys."""
        with pytest.raises(RuntimeError):
            await measure_tools.get_measures("project-1", ["invalid@metric"])

    @pytest.mark.asyncio
    async def test_client_error_handling(self, measure_tools, mock_client):
        """Test error handling when client raises exception."""
        mock_client.get.side_effect = Exception("API Error")
        
        with pytest.raises(RuntimeError, match="Failed to get project measures"):
            await measure_tools.get_measures("project-1")

    @pytest.mark.asyncio
    async def test_cache_integration(self, measure_tools, mock_client, mock_cache):
        """Test cache integration in tools."""
        # Setup cache to return data
        cached_data = {"project_key": "project-1", "metrics": {}}
        mock_cache.get.return_value = cached_data
        
        result = await measure_tools.get_measures("project-1")
        
        # Should return cached data without API call
        assert result == cached_data
        mock_client.get.assert_not_called()
        mock_cache.get.assert_called_once()
        
        # Test cache miss and set
        mock_cache.get.return_value = None
        mock_client.get.return_value = SonarQubeFixtures.project_measures()
        
        result = await measure_tools.get_measures("project-1")
        
        # Should make API call and cache result
        mock_client.get.assert_called_once()
        mock_cache.set.assert_called_once()