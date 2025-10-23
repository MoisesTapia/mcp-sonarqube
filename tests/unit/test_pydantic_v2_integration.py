"""Integration test for Pydantic V2 compatibility."""

import pytest
import os
from datetime import datetime


def test_sonarqube_models():
    """Test SonarQube models with Pydantic V2."""
    from src.sonarqube_client.models import Project, Issue, Metric
    
    # Test Project model
    project_data = {
        "key": "test-project",
        "name": "Test Project",
        "qualifier": "TRK",
        "visibility": "public",
        "lastAnalysisDate": "2025-10-22T10:00:00Z"
    }
    
    project = Project(**project_data)
    assert project.key == "test-project"
    assert project.name == "Test Project"
    assert isinstance(project.last_analysis_date, datetime)
    
    # Test Metric model
    metric_data = {
        "key": "coverage",
        "value": "85.5",
        "bestValue": False
    }
    
    metric = Metric(**metric_data)
    assert metric.key == "coverage"
    assert metric.value == "85.5"
    assert metric.best_value is False
    
    # Test Issue model
    issue_data = {
        "key": "issue-123",
        "rule": "java:S1234",
        "severity": "MAJOR",
        "component": "project:src/Test.java",
        "project": "test-project",
        "status": "OPEN",
        "message": "Test issue",
        "type": "BUG",
        "creationDate": "2025-10-22T09:00:00Z",
        "updateDate": "2025-10-22T10:00:00Z"
    }
    
    issue = Issue(**issue_data)
    assert issue.key == "issue-123"
    assert issue.severity == "MAJOR"
    assert isinstance(issue.creation_date, datetime)
    assert isinstance(issue.update_date, datetime)


def test_mcp_server_config():
    """Test MCP server configuration with Pydantic V2."""
    # Set required environment variables
    os.environ['SONARQUBE_URL'] = 'https://sonarqube.test.com'
    os.environ['SONARQUBE_TOKEN'] = 'test-token-123'
    
    from src.mcp_server.config import get_settings
    
    settings = get_settings()
    assert settings.sonarqube_url == 'https://sonarqube.test.com'
    assert settings.sonarqube_token == 'test-token-123'
    assert settings.server_host == 'localhost'
    assert settings.server_port == 8000
    assert settings.cache_enabled is True
    
    # Test property methods
    sonarqube_config = settings.sonarqube_config
    assert sonarqube_config.url == 'https://sonarqube.test.com'
    assert sonarqube_config.token == 'test-token-123'
    assert sonarqube_config.timeout == 30
    
    cache_config = settings.cache_config
    assert cache_config.enabled is True
    assert cache_config.ttl == 300


def test_sonarqube_client_import():
    """Test that SonarQube client can be imported and instantiated."""
    from src.sonarqube_client import SonarQubeClient
    
    # Test that we can create a client instance
    client = SonarQubeClient(
        base_url="https://sonarqube.test.com",
        token="test-token"
    )
    
    assert client.base_url == "https://sonarqube.test.com/api"
    assert client.token == "test-token"
    assert client.timeout == 30
    assert client.max_retries == 3


def test_validators_import():
    """Test that validators can be imported and used."""
    from src.sonarqube_client.validators import InputValidator
    
    # Test project key validation
    valid_key = InputValidator.validate_project_key("my-project")
    assert valid_key == "my-project"
    
    # Test metric keys validation
    valid_metrics = InputValidator.validate_metric_keys(["coverage", "bugs"])
    assert valid_metrics == ["coverage", "bugs"]
    
    # Test URL validation
    valid_url = InputValidator.validate_url("sonarqube.example.com")
    assert valid_url == "https://sonarqube.example.com"


if __name__ == "__main__":
    test_sonarqube_models()
    test_mcp_server_config()
    test_sonarqube_client_import()
    test_validators_import()
    print("All Pydantic V2 integration tests passed!")