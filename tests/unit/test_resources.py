"""Tests for MCP resources."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from src.mcp_server.resources import ResourceManager, ResourceURI, ProjectResource
from src.sonarqube_client import SonarQubeClient


class TestResourceURI:
    """Test cases for ResourceURI class."""

    def test_valid_uri_parsing(self):
        """Test parsing of valid resource URIs."""
        uri = ResourceURI("sonarqube://projects/my-project?include_branches=true")
        
        assert uri.parsed.scheme == "sonarqube"
        assert uri.resource_type == "projects"
        assert uri.resource_id == "my-project"
        assert uri.sub_resource is None
        assert uri.query_params["include_branches"] == "true"

    def test_complex_uri_parsing(self):
        """Test parsing of complex resource URIs."""
        uri = ResourceURI("sonarqube://metrics/my-project?groups=reliability,security&include_history=true")
        
        assert uri.resource_type == "metrics"
        assert uri.resource_id == "my-project"
        assert uri.query_params["groups"] == "reliability,security"
        assert uri.query_params["include_history"] == "true"

    def test_invalid_scheme(self):
        """Test handling of invalid URI scheme."""
        with pytest.raises(ValueError, match="Invalid scheme"):
            ResourceURI("http://projects/my-project")

    def test_uri_without_resource_id(self):
        """Test URI without resource ID."""
        uri = ResourceURI("sonarqube://projects")
        
        assert uri.resource_type == "projects"
        assert uri.resource_id is None
        assert uri.sub_resource is None

    def test_uri_with_sub_resource(self):
        """Test URI with sub-resource."""
        uri = ResourceURI("sonarqube://projects/my-project/branches")
        
        assert uri.resource_type == "projects"
        assert uri.resource_id == "my-project"
        assert uri.sub_resource == "branches"


class TestResourceManager:
    """Test cases for ResourceManager class."""

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
    def resource_manager(self, mock_client, mock_cache):
        """Create ResourceManager instance with mocked dependencies."""
        return ResourceManager(mock_client, mock_cache)

    @pytest.mark.asyncio
    async def test_get_project_resource(self, resource_manager, mock_client):
        """Test getting project resource."""
        # Mock API response
        mock_response = {
            "components": [
                {
                    "key": "my-project",
                    "name": "My Project",
                    "qualifier": "TRK",
                    "visibility": "public",
                }
            ]
        }
        mock_client.get.return_value = mock_response

        # Mock metrics response
        metrics_response = {
            "component": {
                "measures": [
                    {"metric": "ncloc", "value": "1000"},
                    {"metric": "bugs", "value": "5"},
                ]
            }
        }
        mock_client.get.side_effect = [mock_response, metrics_response]

        result = await resource_manager.get_resource("sonarqube://projects/my-project")

        assert result["resource_type"] == "project_details"
        assert result["project"]["key"] == "my-project"
        assert result["project"]["name"] == "My Project"
        assert "metrics" in result["project"]

    @pytest.mark.asyncio
    async def test_get_projects_list_resource(self, resource_manager, mock_client):
        """Test getting projects list resource."""
        # Mock API response
        mock_response = {
            "components": [
                {
                    "key": "project1",
                    "name": "Project 1",
                    "qualifier": "TRK",
                },
                {
                    "key": "project2", 
                    "name": "Project 2",
                    "qualifier": "TRK",
                }
            ],
            "paging": {"total": 2, "pageIndex": 1, "pageSize": 100}
        }
        mock_client.get.return_value = mock_response

        result = await resource_manager.get_resource("sonarqube://projects")

        assert result["resource_type"] == "projects_list"
        assert len(result["projects"]) == 2
        assert result["total_count"] == 2

    @pytest.mark.asyncio
    async def test_get_metrics_resource(self, resource_manager, mock_client):
        """Test getting metrics resource."""
        # Mock metrics response
        metrics_response = {
            "component": {
                "measures": [
                    {"metric": "ncloc", "value": "1000"},
                    {"metric": "bugs", "value": "5"},
                    {"metric": "coverage", "value": "85.5"},
                ]
            }
        }
        
        # Mock Quality Gate response
        qg_response = {
            "projectStatus": {
                "status": "OK",
                "conditions": []
            }
        }
        
        mock_client.get.side_effect = [metrics_response, qg_response]

        result = await resource_manager.get_resource("sonarqube://metrics/my-project")

        assert result["resource_type"] == "project_metrics"
        assert result["project_key"] == "my-project"
        assert "metrics" in result
        assert "quality_gate" in result

    @pytest.mark.asyncio
    async def test_invalid_resource_type(self, resource_manager):
        """Test handling of invalid resource type."""
        with pytest.raises(RuntimeError, match="No handler found"):
            await resource_manager.get_resource("sonarqube://invalid/resource")

    @pytest.mark.asyncio
    async def test_invalid_uri_scheme(self, resource_manager):
        """Test handling of invalid URI scheme."""
        with pytest.raises(RuntimeError, match="Failed to get resource"):
            await resource_manager.get_resource("http://projects/my-project")

    def test_list_supported_resources(self, resource_manager):
        """Test listing supported resources."""
        resources = resource_manager.list_supported_resources()
        
        assert len(resources) >= 4  # projects, metrics, issues, quality_gates
        
        # Check that each resource has required fields
        for resource in resources:
            assert "type" in resource
            assert "description" in resource
            assert "uri_patterns" in resource
            assert "examples" in resource

    def test_validate_uri_valid(self, resource_manager):
        """Test URI validation with valid URI."""
        result = resource_manager.validate_uri("sonarqube://projects/my-project")
        
        assert result["valid"] is True
        assert result["handler_found"] is True
        assert result["parsed"]["resource_type"] == "projects"
        assert result["parsed"]["resource_id"] == "my-project"

    def test_validate_uri_invalid(self, resource_manager):
        """Test URI validation with invalid URI."""
        result = resource_manager.validate_uri("http://invalid/uri")
        
        assert result["valid"] is False
        assert result["handler_found"] is False
        assert "error" in result


class TestProjectResource:
    """Test cases for ProjectResource class."""

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
    def project_resource(self, mock_client, mock_cache):
        """Create ProjectResource instance with mocked dependencies."""
        return ProjectResource(mock_client, mock_cache)

    def test_supports_uri(self, project_resource):
        """Test URI support checking."""
        projects_uri = ResourceURI("sonarqube://projects/my-project")
        metrics_uri = ResourceURI("sonarqube://metrics/my-project")
        
        assert project_resource.supports_uri(projects_uri) is True
        assert project_resource.supports_uri(metrics_uri) is False

    @pytest.mark.asyncio
    async def test_get_project_details_with_branches(self, project_resource, mock_client):
        """Test getting project details with branches."""
        # Mock project response
        project_response = {
            "components": [
                {
                    "key": "my-project",
                    "name": "My Project",
                    "qualifier": "TRK",
                }
            ]
        }
        
        # Mock metrics response
        metrics_response = {
            "component": {
                "measures": [
                    {"metric": "ncloc", "value": "1000"},
                ]
            }
        }
        
        # Mock branches response
        branches_response = {
            "branches": [
                {"name": "main", "isMain": True, "type": "LONG"},
                {"name": "feature-1", "isMain": False, "type": "SHORT"},
            ]
        }
        
        # Mock Quality Gate response (called by _enrich_project_data when detailed=True)
        qg_response = {
            "projectStatus": {
                "status": "OK",
                "conditions": []
            }
        }
        
        # Set up the mock to return responses in the correct order:
        # 1. projects/search, 2. measures/component, 3. qualitygates/project_status, 4. project_branches/list
        mock_client.get.side_effect = [project_response, metrics_response, qg_response, branches_response]

        uri = ResourceURI("sonarqube://projects/my-project?include_branches=true")
        result = await project_resource.get_resource(uri)

        assert result["resource_type"] == "project_details"
        assert result["project"]["key"] == "my-project"
        assert "branches" in result["project"]
        assert len(result["project"]["branches"]) == 2

    @pytest.mark.asyncio
    async def test_get_projects_list_with_filters(self, project_resource, mock_client):
        """Test getting projects list with filters."""
        mock_response = {
            "components": [
                {
                    "key": "test-project",
                    "name": "Test Project",
                    "qualifier": "TRK",
                }
            ],
            "paging": {"total": 1, "pageIndex": 1, "pageSize": 100}
        }
        mock_client.get.return_value = mock_response

        uri = ResourceURI("sonarqube://projects?search=test&visibility=public")
        result = await project_resource.get_resource(uri)

        assert result["resource_type"] == "projects_list"
        assert result["filters"]["search"] == "test"
        assert result["filters"]["visibility"] == "public"

    @pytest.mark.asyncio
    async def test_project_not_found(self, project_resource, mock_client):
        """Test handling when project is not found."""
        mock_response = {"components": []}
        mock_client.get.return_value = mock_response

        uri = ResourceURI("sonarqube://projects/nonexistent")
        
        with pytest.raises(RuntimeError, match="Project not found"):
            await project_resource.get_resource(uri)

    @pytest.mark.asyncio
    async def test_cache_integration(self, project_resource, mock_client, mock_cache):
        """Test cache integration."""
        # Test cache hit
        cached_data = {"resource_type": "project_details", "project": {"key": "cached-project"}}
        mock_cache.get.return_value = cached_data

        uri = ResourceURI("sonarqube://projects/my-project")
        result = await project_resource.get_resource(uri)

        # Should return cached data without API call
        assert result == cached_data
        mock_client.get.assert_not_called()

        # Test cache miss and set
        mock_cache.get.return_value = None
        mock_response = {
            "components": [
                {"key": "my-project", "name": "My Project", "qualifier": "TRK"}
            ]
        }
        metrics_response = {
            "component": {"measures": []}
        }
        mock_client.get.side_effect = [mock_response, metrics_response]

        result = await project_resource.get_resource(uri)

        # Should make API call and cache result
        mock_client.get.assert_called()
        mock_cache.set.assert_called_once()

    @pytest.mark.asyncio
    async def test_api_error_handling(self, project_resource, mock_client):
        """Test API error handling."""
        mock_client.get.side_effect = Exception("API Error")

        uri = ResourceURI("sonarqube://projects/my-project")
        
        with pytest.raises(RuntimeError, match="Failed to get project resource"):
            await project_resource.get_resource(uri)