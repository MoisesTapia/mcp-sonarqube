"""Unit tests for SonarQube client."""

import pytest
import httpx

from src.sonarqube_client import (
    SonarQubeClient,
    AuthenticationError,
    AuthorizationError,
    NetworkError,
    APIError,
    RateLimitError,
    ServerError,
    ValidationError,
)
from tests.fixtures.sonarqube_responses import SonarQubeFixtures


class TestSonarQubeClient:
    """Test cases for SonarQube client."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        return SonarQubeClient(
            base_url="https://sonarqube.example.com",
            token="test-token",
            timeout=10,
            max_retries=2,
        )

    @pytest.fixture
    def client_with_org(self):
        """Create test client with organization."""
        return SonarQubeClient(
            base_url="https://sonarqube.example.com",
            token="test-token",
            organization="test-org",
            timeout=10,
            max_retries=2,
        )

    def test_url_normalization(self):
        """Test URL normalization."""
        # Test with protocol
        client = SonarQubeClient("https://example.com", "token")
        assert client.base_url == "https://example.com/api"

        # Test without protocol
        client = SonarQubeClient("example.com", "token")
        assert client.base_url == "https://example.com/api"

        # Test with existing /api
        client = SonarQubeClient("https://example.com/api", "token")
        assert client.base_url == "https://example.com/api"

        # Test with trailing slash
        client = SonarQubeClient("https://example.com/", "token")
        assert client.base_url == "https://example.com/api"

    def test_invalid_url(self):
        """Test invalid URL handling."""
        with pytest.raises(ValidationError):
            SonarQubeClient("", "token")

        with pytest.raises(ValidationError):
            SonarQubeClient("invalid-url", "token")

    @pytest.mark.asyncio
    async def test_validate_connection_success(self, client, httpx_mock):
        """Test successful connection validation."""
        httpx_mock.add_response(
            method="GET",
            url="https://sonarqube.example.com/api/system/status",
            json=SonarQubeFixtures.system_status(),
            status_code=200,
        )

        result = await client.validate_connection()
        assert result is True

    @pytest.mark.asyncio
    async def test_validate_connection_failure(self, client, httpx_mock):
        """Test failed connection validation."""
        httpx_mock.add_response(
            method="GET",
            url="https://sonarqube.example.com/api/system/status",
            json={"status": "DOWN"},
            status_code=200,
        )

        result = await client.validate_connection()
        assert result is False

    @pytest.mark.asyncio
    async def test_authenticate_success(self, client, httpx_mock):
        """Test successful authentication."""
        httpx_mock.add_response(
            method="GET",
            url="https://sonarqube.example.com/api/authentication/validate",
            json=SonarQubeFixtures.authentication_validate(),
            status_code=200,
        )

        result = await client.authenticate()
        assert result is True

    @pytest.mark.asyncio
    async def test_authenticate_failure(self, client, httpx_mock):
        """Test failed authentication."""
        httpx_mock.add_response(
            method="GET",
            url="https://sonarqube.example.com/api/authentication/validate",
            json=SonarQubeFixtures.authentication_error(),
            status_code=401,
        )

        result = await client.authenticate()
        assert result is False

    @pytest.mark.asyncio
    async def test_get_request_success(self, client, httpx_mock):
        """Test successful GET request."""
        httpx_mock.add_response(
            method="GET",
            url="https://sonarqube.example.com/api/projects/search",
            json=SonarQubeFixtures.project_list(),
            status_code=200,
        )

        result = await client.get("/projects/search")
        assert "components" in result
        assert len(result["components"]) == 2

    @pytest.mark.asyncio
    async def test_authentication_error(self, client, httpx_mock):
        """Test authentication error handling."""
        httpx_mock.add_response(
            method="GET",
            url="https://sonarqube.example.com/api/projects/search",
            json=SonarQubeFixtures.authentication_error(),
            status_code=401,
        )

        with pytest.raises(AuthenticationError):
            await client.get("/projects/search")

    @pytest.mark.asyncio
    async def test_server_error(self, client, httpx_mock):
        """Test server error handling."""
        httpx_mock.add_response(
            method="GET",
            url="https://sonarqube.example.com/api/projects/search",
            json=SonarQubeFixtures.server_error(),
            status_code=500,
        )

        with pytest.raises(ServerError):
            await client.get("/projects/search")

    @pytest.mark.asyncio
    async def test_context_manager(self):
        """Test client as async context manager."""
        async with SonarQubeClient("https://example.com", "token") as client:
            assert client._client is not None

    @pytest.mark.asyncio
    async def test_close_method(self, client):
        """Test explicit close method."""
        await client.close()
        assert client._client is not None