"""Tests for security analysis tools."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from src.mcp_server.tools.security import SecurityTools
from src.sonarqube_client import SonarQubeClient


class TestSecurityTools:
    """Test cases for SecurityTools class."""

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
    def security_tools(self, mock_client, mock_cache):
        """Create SecurityTools instance with mocked dependencies."""
        return SecurityTools(mock_client, mock_cache)

    @pytest.mark.asyncio
    async def test_search_hotspots_success(self, security_tools, mock_client):
        """Test successful hotspot search."""
        # Mock API response
        mock_response = {
            "hotspots": [
                {
                    "key": "hotspot1",
                    "component": "com.example:project:src/main/java/Example.java",
                    "securityCategory": "sql-injection",
                    "vulnerabilityProbability": "HIGH",
                    "status": "TO_REVIEW",
                }
            ],
            "components": [],
            "rules": [],
            "paging": {"total": 1, "pageIndex": 1, "pageSize": 100},
        }
        mock_client.get.return_value = mock_response

        result = await security_tools.search_hotspots("test-project")

        assert result["total"] == 1
        assert len(result["hotspots"]) == 1
        assert result["hotspots"][0]["key"] == "hotspot1"
        assert "security_analysis" in result
        mock_client.get.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_hotspot_details_success(self, security_tools, mock_client):
        """Test successful hotspot details retrieval."""
        # Mock API response
        mock_response = {
            "key": "hotspot1",
            "component": "com.example:project:src/main/java/Example.java",
            "securityCategory": "sql-injection",
            "vulnerabilityProbability": "HIGH",
            "status": "TO_REVIEW",
            "rule": "java:S2077",
        }
        mock_client.get.return_value = mock_response

        result = await security_tools.get_hotspot_details("hotspot1")

        assert result["key"] == "hotspot1"
        assert result["securityCategory"] == "sql-injection"
        assert "risk_assessment" in result
        assert "remediation_recommendations" in result
        mock_client.get.assert_called_once()

    @pytest.mark.asyncio
    async def test_generate_security_assessment_success(self, security_tools, mock_client):
        """Test successful security assessment generation."""
        # Mock hotspots search response
        hotspots_response = {
            "hotspots": [
                {
                    "key": "hotspot1",
                    "vulnerabilityProbability": "HIGH",
                    "status": "TO_REVIEW",
                    "securityCategory": "sql-injection",
                },
                {
                    "key": "hotspot2",
                    "vulnerabilityProbability": "MEDIUM",
                    "status": "REVIEWED",
                    "securityCategory": "xss",
                },
            ],
            "security_analysis": {
                "total_count": 2,
                "by_vulnerability_probability": {"HIGH": 1, "MEDIUM": 1},
            },
        }

        # Mock security metrics response
        metrics_response = {
            "component": {
                "measures": [
                    {"metric": "security_hotspots", "value": "2"},
                    {"metric": "security_rating", "value": "3"},
                    {"metric": "vulnerabilities", "value": "1"},
                ]
            }
        }

        # Setup mock to return different responses for different calls
        mock_client.get.side_effect = [metrics_response]

        # Mock the search_hotspots method
        security_tools.search_hotspots = AsyncMock(return_value=hotspots_response)

        result = await security_tools.generate_security_assessment("test-project")

        assert result["project_key"] == "test-project"
        assert "summary" in result
        assert "risk_score" in result
        assert "recommendations" in result
        assert result["summary"]["total_hotspots"] == 2
        assert result["summary"]["high_risk_hotspots"] == 1

    @pytest.mark.asyncio
    async def test_update_hotspot_status_success(self, security_tools, mock_client):
        """Test successful hotspot status update."""
        mock_client.post.return_value = {}

        result = await security_tools.update_hotspot_status(
            "hotspot1", "REVIEWED", "FIXED", "Fixed SQL injection vulnerability"
        )

        assert result["success"] is True
        assert result["hotspot_key"] == "hotspot1"
        assert result["new_status"] == "REVIEWED"
        assert result["resolution"] == "FIXED"
        mock_client.post.assert_called_once()

    @pytest.mark.asyncio
    async def test_invalid_hotspot_status(self, security_tools):
        """Test validation of invalid hotspot status."""
        with pytest.raises(RuntimeError, match="Invalid hotspot status"):
            await security_tools.update_hotspot_status("hotspot1", "INVALID_STATUS")

    @pytest.mark.asyncio
    async def test_invalid_hotspot_resolution(self, security_tools):
        """Test validation of invalid hotspot resolution."""
        with pytest.raises(RuntimeError, match="Invalid hotspot resolution"):
            await security_tools.update_hotspot_status(
                "hotspot1", "REVIEWED", "INVALID_RESOLUTION"
            )

    def test_analyze_hotspots(self, security_tools):
        """Test hotspot analysis functionality."""
        hotspots = [
            {
                "vulnerabilityProbability": "HIGH",
                "status": "TO_REVIEW",
                "securityCategory": "sql-injection",
                "component": "file1.java",
            },
            {
                "vulnerabilityProbability": "MEDIUM",
                "status": "REVIEWED",
                "securityCategory": "xss",
                "component": "file2.java",
            },
        ]

        analysis = security_tools._analyze_hotspots(hotspots)

        assert analysis["total_count"] == 2
        assert analysis["by_vulnerability_probability"]["HIGH"] == 1
        assert analysis["by_vulnerability_probability"]["MEDIUM"] == 1
        assert analysis["by_status"]["TO_REVIEW"] == 1
        assert analysis["by_status"]["REVIEWED"] == 1
        assert analysis["unreviewed_count"] == 1
        assert analysis["high_risk_count"] == 1

    def test_assess_hotspot_risk(self, security_tools):
        """Test hotspot risk assessment."""
        hotspot = {
            "vulnerabilityProbability": "HIGH",
            "securityCategory": "sql-injection",
            "status": "TO_REVIEW",
        }

        risk_assessment = security_tools._assess_hotspot_risk(hotspot)

        assert risk_assessment["risk_level"] in ["CRITICAL", "HIGH", "MEDIUM", "LOW"]
        assert risk_assessment["vulnerability_probability"] == "HIGH"
        assert risk_assessment["security_category"] == "SQL Injection"
        assert isinstance(risk_assessment["risk_score"], int)
        assert 0 <= risk_assessment["risk_score"] <= 10

    def test_generate_remediation_recommendations(self, security_tools):
        """Test remediation recommendations generation."""
        hotspot = {
            "securityCategory": "sql-injection",
            "vulnerabilityProbability": "HIGH",
        }

        recommendations = security_tools._generate_remediation_recommendations(hotspot)

        assert isinstance(recommendations, list)
        assert len(recommendations) > 0
        assert any("parameterized queries" in rec.lower() for rec in recommendations)

    def test_calculate_project_risk_score(self, security_tools):
        """Test project risk score calculation."""
        summary = {
            "total_hotspots": 5,
            "high_risk_hotspots": 2,
            "medium_risk_hotspots": 2,
            "unreviewed_hotspots": 3,
        }
        security_metrics = {
            "security_rating": 3,
            "vulnerabilities": 1,
        }

        risk_score = security_tools._calculate_project_risk_score(summary, security_metrics)

        assert isinstance(risk_score, float)
        assert 0 <= risk_score <= 100

    def test_generate_security_recommendations(self, security_tools):
        """Test security recommendations generation."""
        summary = {
            "total_hotspots": 10,
            "high_risk_hotspots": 3,
            "unreviewed_hotspots": 5,
        }
        security_metrics = {"security_rating": 4}
        hotspots = [
            {"securityCategory": "sql-injection"},
            {"securityCategory": "sql-injection"},
            {"securityCategory": "xss"},
        ]

        recommendations = security_tools._generate_security_recommendations(
            summary, security_metrics, hotspots
        )

        assert isinstance(recommendations, list)
        assert len(recommendations) > 0
        assert any("high-risk" in rec.lower() for rec in recommendations)
        assert any("unreviewed" in rec.lower() for rec in recommendations)