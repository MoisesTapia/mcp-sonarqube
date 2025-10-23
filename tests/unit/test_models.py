"""Unit tests for Pydantic models."""

import pytest
from datetime import datetime
from pydantic import ValidationError

from src.sonarqube_client.models import (
    Project,
    Issue,
    Metric,
    QualityGate,
    QualityGateCondition,
    SecurityHotspot,
    User,
    SystemInfo,
    Component,
    Rule,
    Paging,
    SonarQubeResponse,
    ProjectsResponse,
    IssuesResponse,
    MeasuresResponse,
)


class TestModels:
    """Test cases for Pydantic models."""

    def test_project_model(self):
        """Test Project model."""
        data = {
            "key": "my-project",
            "name": "My Project",
            "qualifier": "TRK",
            "visibility": "public",
            "lastAnalysisDate": "2025-10-22T10:00:00+0000",
            "revision": "abc123",
        }
        
        project = Project(**data)
        assert project.key == "my-project"
        assert project.name == "My Project"
        assert project.qualifier == "TRK"
        assert project.visibility == "public"
        assert isinstance(project.last_analysis_date, datetime)
        assert project.revision == "abc123"

    def test_project_model_minimal(self):
        """Test Project model with minimal data."""
        data = {
            "key": "my-project",
            "name": "My Project",
        }
        
        project = Project(**data)
        assert project.key == "my-project"
        assert project.name == "My Project"
        assert project.qualifier == "TRK"  # Default value
        assert project.visibility == "public"  # Default value
        assert project.last_analysis_date is None

    def test_issue_model(self):
        """Test Issue model."""
        data = {
            "key": "issue-123",
            "rule": "java:S1234",
            "severity": "MAJOR",
            "component": "project:src/main/java/Test.java",
            "project": "my-project",
            "line": 42,
            "status": "OPEN",
            "message": "Test issue message",
            "type": "BUG",
            "creationDate": "2025-10-22T09:00:00+0000",
            "updateDate": "2025-10-22T10:00:00+0000",
            "assignee": "john.doe",
            "tags": ["security", "performance"],
        }
        
        issue = Issue(**data)
        assert issue.key == "issue-123"
        assert issue.rule == "java:S1234"
        assert issue.severity == "MAJOR"
        assert issue.line == 42
        assert issue.assignee == "john.doe"
        assert issue.tags == ["security", "performance"]
        assert isinstance(issue.creation_date, datetime)
        assert isinstance(issue.update_date, datetime)

    def test_metric_model(self):
        """Test Metric model."""
        data = {
            "key": "coverage",
            "value": "85.5",
            "bestValue": False,
        }
        
        metric = Metric(**data)
        assert metric.key == "coverage"
        assert metric.value == "85.5"
        assert metric.best_value is False

    def test_metric_model_numeric_value(self):
        """Test Metric model with numeric value."""
        data = {
            "key": "bugs",
            "value": 3,
        }
        
        metric = Metric(**data)
        assert metric.key == "bugs"
        assert metric.value == 3

    def test_quality_gate_condition_model(self):
        """Test QualityGateCondition model."""
        data = {
            "id": "condition-1",
            "metric": "coverage",
            "op": "LT",
            "error": "80",
            "actualValue": "85.5",
            "status": "OK",
        }
        
        condition = QualityGateCondition(**data)
        assert condition.id == "condition-1"
        assert condition.metric == "coverage"
        assert condition.op == "LT"
        assert condition.error == "80"
        assert condition.actual_value == "85.5"
        assert condition.status == "OK"

    def test_quality_gate_model(self):
        """Test QualityGate model."""
        data = {
            "name": "Sonar way",
            "status": "OK",
            "conditions": [
                {
                    "id": "1",
                    "metric": "coverage",
                    "op": "LT",
                    "error": "80",
                    "actualValue": "85.5",
                    "status": "OK",
                }
            ],
        }
        
        gate = QualityGate(**data)
        assert gate.name == "Sonar way"
        assert gate.status == "OK"
        assert len(gate.conditions) == 1
        assert gate.conditions[0].metric == "coverage"

    def test_security_hotspot_model(self):
        """Test SecurityHotspot model."""
        data = {
            "key": "hotspot-123",
            "component": "project:src/main/java/Security.java",
            "project": "my-project",
            "securityCategory": "sql-injection",
            "vulnerabilityProbability": "HIGH",
            "status": "TO_REVIEW",
            "message": "Potential SQL injection",
            "creationDate": "2025-10-22T11:00:00+0000",
            "updateDate": "2025-10-22T11:30:00+0000",
        }
        
        hotspot = SecurityHotspot(**data)
        assert hotspot.key == "hotspot-123"
        assert hotspot.security_category == "sql-injection"
        assert hotspot.vulnerability_probability == "HIGH"
        assert hotspot.status == "TO_REVIEW"
        assert isinstance(hotspot.creation_date, datetime)
        assert isinstance(hotspot.update_date, datetime)

    def test_user_model(self):
        """Test User model."""
        data = {
            "login": "john.doe",
            "name": "John Doe",
            "email": "john.doe@example.com",
            "active": True,
            "local": True,
            "groups": ["developers", "users"],
        }
        
        user = User(**data)
        assert user.login == "john.doe"
        assert user.name == "John Doe"
        assert user.email == "john.doe@example.com"
        assert user.active is True
        assert user.local is True
        assert user.groups == ["developers", "users"]

    def test_system_info_model(self):
        """Test SystemInfo model."""
        data = {
            "serverId": "server-123",
            "version": "10.2.1",
            "status": "UP",
            "instanceUsageType": "COMMERCIAL",
            "edition": "ENTERPRISE",
        }
        
        info = SystemInfo(**data)
        assert info.server_id == "server-123"
        assert info.version == "10.2.1"
        assert info.status == "UP"
        assert info.instance_usage_type == "COMMERCIAL"
        assert info.edition == "ENTERPRISE"

    def test_component_model(self):
        """Test Component model."""
        data = {
            "key": "project:src/main/java/Test.java",
            "name": "Test.java",
            "qualifier": "FIL",
            "path": "src/main/java/Test.java",
            "language": "java",
        }
        
        component = Component(**data)
        assert component.key == "project:src/main/java/Test.java"
        assert component.name == "Test.java"
        assert component.qualifier == "FIL"
        assert component.path == "src/main/java/Test.java"
        assert component.language == "java"

    def test_rule_model(self):
        """Test Rule model."""
        data = {
            "key": "java:S1234",
            "name": "Test Rule",
            "lang": "java",
            "langName": "Java",
            "type": "BUG",
            "severity": "MAJOR",
            "status": "READY",
            "isTemplate": False,
            "tags": ["security"],
            "sysTags": ["cwe"],
        }
        
        rule = Rule(**data)
        assert rule.key == "java:S1234"
        assert rule.name == "Test Rule"
        assert rule.lang == "java"
        assert rule.lang_name == "Java"
        assert rule.type == "BUG"
        assert rule.severity == "MAJOR"
        assert rule.is_template is False
        assert rule.tags == ["security"]
        assert rule.system_tags == ["cwe"]

    def test_paging_model(self):
        """Test Paging model."""
        data = {
            "pageIndex": 1,
            "pageSize": 100,
            "total": 250,
        }
        
        paging = Paging(**data)
        assert paging.page_index == 1
        assert paging.page_size == 100
        assert paging.total == 250

    def test_sonarqube_response_model(self):
        """Test SonarQubeResponse model."""
        data = {
            "paging": {
                "pageIndex": 1,
                "pageSize": 100,
                "total": 2,
            },
            "data": {"key": "value"},
        }
        
        response = SonarQubeResponse(**data)
        assert response.paging.page_index == 1
        assert response.data == {"key": "value"}
        assert response.errors is None

    def test_projects_response_model(self):
        """Test ProjectsResponse model."""
        data = {
            "paging": {
                "pageIndex": 1,
                "pageSize": 100,
                "total": 1,
            },
            "components": [
                {
                    "key": "my-project",
                    "name": "My Project",
                    "qualifier": "TRK",
                    "visibility": "public",
                }
            ],
        }
        
        response = ProjectsResponse(**data)
        assert len(response.components) == 1
        assert response.components[0].key == "my-project"

    def test_issues_response_model(self):
        """Test IssuesResponse model."""
        data = {
            "issues": [
                {
                    "key": "issue-123",
                    "rule": "java:S1234",
                    "severity": "MAJOR",
                    "component": "project:src/Test.java",
                    "project": "my-project",
                    "status": "OPEN",
                    "message": "Test issue",
                    "type": "BUG",
                    "creationDate": "2025-10-22T09:00:00+0000",
                    "updateDate": "2025-10-22T10:00:00+0000",
                }
            ],
            "components": [
                {
                    "key": "project:src/Test.java",
                    "name": "Test.java",
                    "qualifier": "FIL",
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
                }
            ],
        }
        
        response = IssuesResponse(**data)
        assert len(response.issues) == 1
        assert len(response.components) == 1
        assert len(response.rules) == 1
        assert response.issues[0].key == "issue-123"

    def test_measures_response_model(self):
        """Test MeasuresResponse model."""
        data = {
            "component": {
                "key": "my-project",
                "name": "My Project",
                "qualifier": "TRK",
            },
            "metrics": [
                {
                    "key": "coverage",
                    "value": "85.5",
                },
                {
                    "key": "bugs",
                    "value": 3,
                }
            ],
        }
        
        response = MeasuresResponse(**data)
        assert response.component.key == "my-project"
        assert len(response.metrics) == 2
        assert response.metrics[0].key == "coverage"
        assert response.metrics[1].value == 3

    def test_datetime_parsing(self):
        """Test datetime parsing from ISO strings."""
        # Test with Z suffix
        data = {
            "key": "issue-123",
            "rule": "java:S1234",
            "severity": "MAJOR",
            "component": "project:src/Test.java",
            "project": "my-project",
            "status": "OPEN",
            "message": "Test issue",
            "type": "BUG",
            "creationDate": "2025-10-22T09:00:00Z",
            "updateDate": "2025-10-22T10:00:00+0000",
        }
        
        issue = Issue(**data)
        assert isinstance(issue.creation_date, datetime)
        assert isinstance(issue.update_date, datetime)

    def test_field_aliases(self):
        """Test field aliases work correctly."""
        data = {
            "pageIndex": 1,
            "pageSize": 100,
            "total": 250,
        }
        
        paging = Paging(**data)
        assert paging.page_index == 1
        assert paging.page_size == 100

        # Test that both alias and field name work
        data_alt = {
            "page_index": 2,
            "page_size": 50,
            "total": 250,
        }
        
        paging_alt = Paging(**data_alt)
        assert paging_alt.page_index == 2
        assert paging_alt.page_size == 50

    def test_model_validation_errors(self):
        """Test model validation errors."""
        # Missing required fields
        with pytest.raises(ValidationError):
            Project()  # Missing key and name

        # Invalid field types
        with pytest.raises(ValidationError):
            Project(key=123, name="Test")  # key should be string

        # Invalid datetime format
        with pytest.raises(ValidationError):
            Issue(
                key="issue-123",
                rule="java:S1234",
                severity="MAJOR",
                component="project:src/Test.java",
                project="my-project",
                status="OPEN",
                message="Test issue",
                type="BUG",
                creationDate="invalid-date",
                updateDate="2025-10-22T10:00:00+0000",
            )