"""Tests for Streamlit SonarQube service."""

import pytest
import asyncio

from unittest.mock import AsyncMock, MagicMock, patch
from src.streamlit_app.services.sonarqube_service import SonarQubeService
from src.streamlit_app.config.settings import ConfigManager
from src.sonarqube_client.exceptions import SonarQubeException


class TestSonarQubeService:
    """Test SonarQube service functionality."""
    
    def setup_method(self):
        """Set up test environment."""
        self.config_manager = MagicMock(spec=ConfigManager)
        self.service = SonarQubeService(self.config_manager)
    
    @pytest.mark.asyncio
    async def test_get_client_success(self):
        """Test successful client creation."""
        self.config_manager.is_configured.return_value = True
        self.config_manager.get_connection_params.return_value = {
            "base_url": "https://sonarqube.example.com",
            "token": "test_token"
        }
        
        with patch("src.streamlit_app.services.sonarqube_service.SonarQubeClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client_class.return_value = mock_client
            
            client = await self.service._get_client()
            
            assert client is not None
            mock_client_class.assert_called_once_with(
                base_url="https://sonarqube.example.com",
                token="test_token"
            )
    
    @pytest.mark.asyncio
    async def test_get_client_not_configured(self):
        """Test client creation when not configured."""
        self.config_manager.is_configured.return_value = False
        
        client = await self.service._get_client()
        
        assert client is None
    
    @pytest.mark.asyncio
    async def test_get_client_exception(self):
        """Test client creation with exception."""
        self.config_manager.is_configured.return_value = True
        self.config_manager.get_connection_params.side_effect = Exception("Config error")
        
        with patch("streamlit.error") as mock_error:
            client = await self.service._get_client()
            
            assert client is None
            mock_error.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_projects_async_success(self):
        """Test successful project retrieval."""
        mock_client = AsyncMock()
        mock_client.get.return_value = {
            "components": [
                {"key": "project1", "name": "Project 1"},
                {"key": "project2", "name": "Project 2"}
            ]
        }
        
        with patch.object(self.service, "_get_client", return_value=mock_client):
            projects = await self.service._get_projects_async()
            
            assert len(projects) == 2
            assert projects[0]["key"] == "project1"
            assert projects[1]["key"] == "project2"
            mock_client.close.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_projects_async_no_client(self):
        """Test project retrieval with no client."""
        with patch.object(self.service, "_get_client", return_value=None):
            projects = await self.service._get_projects_async()
            
            assert projects == []
    
    @pytest.mark.asyncio
    async def test_get_projects_async_exception(self):
        """Test project retrieval with exception."""
        mock_client = AsyncMock()
        mock_client.get.side_effect = SonarQubeException("API error")
        
        with patch.object(self.service, "_get_client", return_value=mock_client), \
             patch("streamlit.error") as mock_error:
            projects = await self.service._get_projects_async()
            
            assert projects == []
            mock_error.assert_called_once()
    
    def test_get_projects_with_cache(self):
        """Test getting projects with cache hit."""
        cached_projects = [{"key": "project1", "name": "Project 1"}]
        
        with patch("src.streamlit_app.services.sonarqube_service.SessionManager") as mock_session:
            mock_session.get_cached_data.return_value = cached_projects
            
            projects = self.service.get_projects(use_cache=True)
            
            assert projects == cached_projects
            mock_session.get_cached_data.assert_called_once_with("cached_projects", ttl_minutes=5)
    
    def test_get_projects_without_cache(self):
        """Test getting projects without cache."""
        expected_projects = [{"key": "project1", "name": "Project 1"}]
        
        with patch.object(self.service, "_run_async", return_value=expected_projects):
            projects = self.service.get_projects(use_cache=False)
            
            assert projects == expected_projects
    
    def test_get_projects_cache_miss(self):
        """Test getting projects with cache miss."""
        expected_projects = [{"key": "project1", "name": "Project 1"}]
        
        with patch("src.streamlit_app.services.sonarqube_service.SessionManager") as mock_session, \
             patch.object(self.service, "_run_async", return_value=expected_projects):
            mock_session.get_cached_data.return_value = None
            
            projects = self.service.get_projects(use_cache=True)
            
            assert projects == expected_projects
            mock_session.cache_data.assert_called_once_with("cached_projects", expected_projects, ttl_minutes=5)
    
    @pytest.mark.asyncio
    async def test_get_project_measures_async_success(self):
        """Test successful project measures retrieval."""
        mock_client = AsyncMock()
        mock_client.get.return_value = {
            "component": {
                "measures": [
                    {"metric": "bugs", "value": "5"},
                    {"metric": "coverage", "value": "85.5"}
                ]
            }
        }
        
        with patch.object(self.service, "_get_client", return_value=mock_client):
            measures = await self.service._get_project_measures_async("project1", ["bugs", "coverage"])
            
            assert measures["bugs"] == "5"
            assert measures["coverage"] == "85.5"
            mock_client.get.assert_called_once_with(
                "/measures/component",
                params={
                    "component": "project1",
                    "metricKeys": "bugs,coverage"
                }
            )
            mock_client.close.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_project_measures_async_no_client(self):
        """Test project measures retrieval with no client."""
        with patch.object(self.service, "_get_client", return_value=None):
            measures = await self.service._get_project_measures_async("project1", ["bugs"])
            
            assert measures == {}
    
    @pytest.mark.asyncio
    async def test_get_project_measures_async_exception(self):
        """Test project measures retrieval with exception."""
        mock_client = AsyncMock()
        mock_client.get.side_effect = SonarQubeException("API error")
        
        with patch.object(self.service, "_get_client", return_value=mock_client), \
             patch("streamlit.error") as mock_error:
            measures = await self.service._get_project_measures_async("project1", ["bugs"])
            
            assert measures == {}
            mock_error.assert_called_once()
    
    def test_get_project_measures(self):
        """Test getting project measures."""
        expected_measures = {"bugs": "5", "coverage": "85.5"}
        
        with patch.object(self.service, "_run_async", return_value=expected_measures):
            measures = self.service.get_project_measures("project1", ["bugs", "coverage"])
            
            assert measures == expected_measures
    
    @pytest.mark.asyncio
    async def test_get_quality_gate_status_async_success(self):
        """Test successful quality gate status retrieval."""
        mock_client = AsyncMock()
        mock_client.get.return_value = {
            "projectStatus": {
                "status": "OK",
                "conditions": []
            }
        }
        
        with patch.object(self.service, "_get_client", return_value=mock_client):
            status = await self.service._get_quality_gate_status_async("project1")
            
            assert status["status"] == "OK"
            mock_client.get.assert_called_once_with(
                "/qualitygates/project_status",
                params={"projectKey": "project1"}
            )
            mock_client.close.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_quality_gate_status_async_no_client(self):
        """Test quality gate status retrieval with no client."""
        with patch.object(self.service, "_get_client", return_value=None):
            status = await self.service._get_quality_gate_status_async("project1")
            
            assert status == {}
    
    def test_get_quality_gate_status(self):
        """Test getting quality gate status."""
        expected_status = {"status": "OK", "conditions": []}
        
        with patch.object(self.service, "_run_async", return_value=expected_status):
            status = self.service.get_quality_gate_status("project1")
            
            assert status == expected_status
    
    @pytest.mark.asyncio
    async def test_get_all_quality_gates_async_success(self):
        """Test successful quality gates retrieval."""
        mock_client = AsyncMock()
        mock_client.get.return_value = {
            "qualitygates": [
                {"id": "1", "name": "Sonar way"},
                {"id": "2", "name": "Custom gate"}
            ]
        }
        
        with patch.object(self.service, "_get_client", return_value=mock_client):
            gates = await self.service._get_all_quality_gates_async()
            
            assert len(gates) == 2
            assert gates[0]["name"] == "Sonar way"
            assert gates[1]["name"] == "Custom gate"
            mock_client.close.assert_called_once()
    
    def test_get_all_quality_gates_with_cache(self):
        """Test getting quality gates with cache hit."""
        cached_gates = [{"id": "1", "name": "Sonar way"}]
        
        with patch("src.streamlit_app.services.sonarqube_service.SessionManager") as mock_session:
            mock_session.get_cached_data.return_value = cached_gates
            
            gates = self.service.get_all_quality_gates(use_cache=True)
            
            assert gates == cached_gates
            mock_session.get_cached_data.assert_called_once_with("cached_quality_gates", ttl_minutes=10)
    
    def test_get_projects_with_quality_gates(self):
        """Test getting projects with quality gate status."""
        project_keys = ["project1", "project2"]
        
        with patch.object(self.service, "get_quality_gate_status") as mock_get_status:
            mock_get_status.side_effect = [
                {"status": "OK"},
                {"status": "ERROR"}
            ]
            
            result = self.service.get_projects_with_quality_gates(project_keys)
            
            assert len(result) == 2
            assert result[0]["project_key"] == "project1"
            assert result[0]["quality_gate"]["status"] == "OK"
            assert result[1]["project_key"] == "project2"
            assert result[1]["quality_gate"]["status"] == "ERROR"
    
    def test_get_dashboard_summary_no_projects(self):
        """Test dashboard summary with no projects."""
        with patch.object(self.service, "get_projects", return_value=[]):
            summary = self.service.get_dashboard_summary()
            
            assert summary["total_projects"] == 0
            assert summary["projects_with_issues"] == 0
            assert summary["quality_gates_passed"] == 0
            assert summary["quality_gates_failed"] == 0
            assert summary["projects"] == []
    
    def test_get_dashboard_summary_with_projects(self):
        """Test dashboard summary with projects."""
        mock_projects = [
            {"key": "project1", "name": "Project 1"},
            {"key": "project2", "name": "Project 2"}
        ]
        
        with patch.object(self.service, "get_projects", return_value=mock_projects), \
             patch.object(self.service, "get_project_measures") as mock_get_measures, \
             patch.object(self.service, "get_quality_gate_status") as mock_get_status:
            
            mock_get_measures.side_effect = [
                {"bugs": "5", "vulnerabilities": "2", "code_smells": "10", "coverage": "85.5"},
                {"bugs": "0", "vulnerabilities": "0", "code_smells": "0", "coverage": "90.0"}
            ]
            
            mock_get_status.side_effect = [
                {"status": "ERROR"},
                {"status": "OK"}
            ]
            
            summary = self.service.get_dashboard_summary()
            
            assert summary["total_projects"] == 2
            assert summary["projects_with_issues"] == 1  # Only project1 has issues
            assert summary["quality_gates_passed"] == 1  # Only project2 passed
            assert summary["quality_gates_failed"] == 1  # Only project1 failed
            assert len(summary["projects"]) == 2
            
            # Check project details
            project1_summary = summary["projects"][0]
            assert project1_summary["key"] == "project1"
            assert project1_summary["bugs"] == 5
            assert project1_summary["quality_gate_status"] == "ERROR"
            
            project2_summary = summary["projects"][1]
            assert project2_summary["key"] == "project2"
            assert project2_summary["bugs"] == 0
            assert project2_summary["quality_gate_status"] == "OK"
    
    def test_run_async(self):
        """Test async coroutine runner."""
        async def test_coro():
            return "test_result"
        
        result = self.service._run_async(test_coro())
        
        assert result == "test_result"