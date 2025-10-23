"""Unit tests for input validators."""

import pytest

from src.sonarqube_client.validators import InputValidator
from src.sonarqube_client.exceptions import ValidationError


class TestInputValidator:
    """Test cases for InputValidator."""

    def test_validate_project_key_valid(self):
        """Test valid project key validation."""
        valid_keys = [
            "my-project",
            "my_project",
            "my.project",
            "my:project",
            "project123",
            "PROJECT-123_test.key:value",
        ]
        
        for key in valid_keys:
            result = InputValidator.validate_project_key(key)
            assert result == key

    def test_validate_project_key_invalid(self):
        """Test invalid project key validation."""
        invalid_keys = [
            "",  # Empty
            None,  # None
            123,  # Not string
            "project with spaces",  # Spaces
            "project@invalid",  # Invalid character
            "project#invalid",  # Invalid character
            "a" * 401,  # Too long
        ]
        
        for key in invalid_keys:
            with pytest.raises(ValidationError):
                InputValidator.validate_project_key(key)

    def test_validate_project_key_whitespace(self):
        """Test project key validation with whitespace."""
        result = InputValidator.validate_project_key("  my-project  ")
        assert result == "my-project"

    def test_validate_issue_key_valid(self):
        """Test valid issue key validation."""
        valid_keys = [
            "project-1:123",
            "my_project:456",
            "test.project:789",
        ]
        
        for key in valid_keys:
            result = InputValidator.validate_issue_key(key)
            assert result == key

    def test_validate_issue_key_invalid(self):
        """Test invalid issue key validation."""
        invalid_keys = [
            "",  # Empty
            None,  # None
            123,  # Not string
            "invalid-format",  # Missing colon and number
            "project:",  # Missing number
            ":123",  # Missing project
            "project:abc",  # Non-numeric ID
        ]
        
        for key in invalid_keys:
            with pytest.raises(ValidationError):
                InputValidator.validate_issue_key(key)

    def test_validate_user_login_valid(self):
        """Test valid user login validation."""
        valid_logins = [
            "john.doe",
            "jane_smith",
            "user123",
            "user@example.com",
            "test-user",
        ]
        
        for login in valid_logins:
            result = InputValidator.validate_user_login(login)
            assert result == login

    def test_validate_user_login_invalid(self):
        """Test invalid user login validation."""
        invalid_logins = [
            "",  # Empty
            None,  # None
            123,  # Not string
            "user with spaces",  # Spaces
            "user#invalid",  # Invalid character
            "a" * 256,  # Too long
        ]
        
        for login in invalid_logins:
            with pytest.raises(ValidationError):
                InputValidator.validate_user_login(login)

    def test_validate_metric_keys_valid(self):
        """Test valid metric keys validation."""
        valid_keys = [
            ["coverage", "bugs", "vulnerabilities"],
            ["code_smells"],
            ["ncloc", "complexity"],
        ]
        
        for keys in valid_keys:
            result = InputValidator.validate_metric_keys(keys)
            assert result == keys

    def test_validate_metric_keys_invalid(self):
        """Test invalid metric keys validation."""
        invalid_keys = [
            [],  # Empty list
            None,  # None
            "not-a-list",  # Not a list
            [123, "coverage"],  # Non-string in list
            ["coverage", "invalid@metric"],  # Invalid character
        ]
        
        for keys in invalid_keys:
            with pytest.raises(ValidationError):
                InputValidator.validate_metric_keys(keys)

    def test_validate_severity_valid(self):
        """Test valid severity validation."""
        valid_severities = ["INFO", "MINOR", "MAJOR", "CRITICAL", "BLOCKER"]
        
        for severity in valid_severities:
            result = InputValidator.validate_severity(severity)
            assert result == severity

        # Test case insensitive
        result = InputValidator.validate_severity("major")
        assert result == "MAJOR"

    def test_validate_severity_invalid(self):
        """Test invalid severity validation."""
        invalid_severities = [
            "",  # Empty
            None,  # None
            123,  # Not string
            "INVALID",  # Invalid severity
            "HIGH",  # Not a valid SonarQube severity
        ]
        
        for severity in invalid_severities:
            with pytest.raises(ValidationError):
                InputValidator.validate_severity(severity)

    def test_validate_issue_type_valid(self):
        """Test valid issue type validation."""
        valid_types = ["CODE_SMELL", "BUG", "VULNERABILITY", "SECURITY_HOTSPOT"]
        
        for issue_type in valid_types:
            result = InputValidator.validate_issue_type(issue_type)
            assert result == issue_type

        # Test case insensitive
        result = InputValidator.validate_issue_type("bug")
        assert result == "BUG"

    def test_validate_issue_type_invalid(self):
        """Test invalid issue type validation."""
        invalid_types = [
            "",  # Empty
            None,  # None
            123,  # Not string
            "INVALID",  # Invalid type
            "ERROR",  # Not a valid SonarQube type
        ]
        
        for issue_type in invalid_types:
            with pytest.raises(ValidationError):
                InputValidator.validate_issue_type(issue_type)

    def test_validate_issue_status_valid(self):
        """Test valid issue status validation."""
        valid_statuses = [
            "OPEN", "CONFIRMED", "REOPENED", "RESOLVED", "CLOSED",
            "TO_REVIEW", "IN_REVIEW", "REVIEWED"
        ]
        
        for status in valid_statuses:
            result = InputValidator.validate_issue_status(status)
            assert result == status

        # Test case insensitive
        result = InputValidator.validate_issue_status("open")
        assert result == "OPEN"

    def test_validate_issue_status_invalid(self):
        """Test invalid issue status validation."""
        invalid_statuses = [
            "",  # Empty
            None,  # None
            123,  # Not string
            "INVALID",  # Invalid status
            "PENDING",  # Not a valid SonarQube status
        ]
        
        for status in invalid_statuses:
            with pytest.raises(ValidationError):
                InputValidator.validate_issue_status(status)

    def test_validate_url_valid(self):
        """Test valid URL validation."""
        valid_urls = [
            "https://example.com",
            "http://localhost:9000",
            "example.com",  # Should add https://
            "sonarqube.company.com",
        ]
        
        expected_results = [
            "https://example.com",
            "http://localhost:9000",
            "https://example.com",
            "https://sonarqube.company.com",
        ]
        
        for url, expected in zip(valid_urls, expected_results):
            result = InputValidator.validate_url(url)
            assert result == expected

    def test_validate_url_invalid(self):
        """Test invalid URL validation."""
        invalid_urls = [
            "",  # Empty
            None,  # None
            123,  # Not string
            "not-a-url",  # Invalid format
            "ftp://example.com",  # Valid URL but will be converted
        ]
        
        for url in invalid_urls[:4]:  # Skip the last one as it's actually valid
            with pytest.raises(ValidationError):
                InputValidator.validate_url(url)

    def test_sanitize_search_query(self):
        """Test search query sanitization."""
        test_cases = [
            ("normal query", "normal query"),
            ("query with 'quotes'", "query with quotes"),
            ('query with "double quotes"', "query with double quotes"),
            ("query with -- comment", "query with  comment"),
            ("query with /* comment */", "query with "),
            ("DROP TABLE users", " users"),  # SQL injection attempt
            ("", ""),  # Empty string
            (None, ""),  # None
            ("a" * 1500, "a" * 1000),  # Too long
        ]
        
        for input_query, expected in test_cases:
            result = InputValidator.sanitize_search_query(input_query)
            assert result == expected

    def test_validate_pagination_params_valid(self):
        """Test valid pagination parameters."""
        valid_params = [
            (1, 10),
            (5, 100),
            (1, 500),  # Maximum page size
        ]
        
        for page, page_size in valid_params:
            result_page, result_page_size = InputValidator.validate_pagination_params(page, page_size)
            assert result_page == page
            assert result_page_size == page_size

    def test_validate_pagination_params_invalid(self):
        """Test invalid pagination parameters."""
        invalid_params = [
            (0, 10),  # Page < 1
            (-1, 10),  # Negative page
            (1, 0),  # Page size < 1
            (1, -10),  # Negative page size
            (1, 501),  # Page size too large
            ("1", 10),  # Non-integer page
            (1, "10"),  # Non-integer page size
        ]
        
        for page, page_size in invalid_params:
            with pytest.raises(ValidationError):
                InputValidator.validate_pagination_params(page, page_size)

    def test_validate_api_parameters(self):
        """Test API parameters validation."""
        valid_params = {
            "projectKeys": ["project-1", "project-2"],
            "severities": ["MAJOR", "CRITICAL"],
            "types": ["BUG", "VULNERABILITY"],
            "statuses": ["OPEN", "CONFIRMED"],
            "p": 1,
            "ps": 50,
            "q": "search query",
            "other": "value",
        }
        
        result = InputValidator.validate_api_parameters(valid_params)
        
        assert "projectKeys" in result
        assert "severities" in result
        assert "types" in result
        assert "statuses" in result
        assert "p" in result
        assert "ps" in result
        assert "q" in result
        assert "other" in result

    def test_validate_api_parameters_invalid(self):
        """Test invalid API parameters."""
        with pytest.raises(ValidationError):
            InputValidator.validate_api_parameters("not-a-dict")

        with pytest.raises(ValidationError):
            InputValidator.validate_api_parameters({123: "value"})  # Non-string key