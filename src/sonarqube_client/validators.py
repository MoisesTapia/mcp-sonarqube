"""Input validation and sanitization utilities."""

import re
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

from .exceptions import ValidationError


class InputValidator:
    """Utility class for input validation and sanitization."""

    # Regex patterns for validation
    PROJECT_KEY_PATTERN = re.compile(r"^[a-zA-Z0-9_\-.:]+$")
    ISSUE_KEY_PATTERN = re.compile(r"^[a-zA-Z0-9_\-]+:[0-9]+$")
    USER_LOGIN_PATTERN = re.compile(r"^[a-zA-Z0-9_\-@.]+$")
    METRIC_KEY_PATTERN = re.compile(r"^[a-zA-Z0-9_\-]+$")

    # Valid values for enums
    VALID_SEVERITIES = {"INFO", "MINOR", "MAJOR", "CRITICAL", "BLOCKER"}
    VALID_ISSUE_TYPES = {"CODE_SMELL", "BUG", "VULNERABILITY", "SECURITY_HOTSPOT"}
    VALID_ISSUE_STATUSES = {
        "OPEN",
        "CONFIRMED",
        "REOPENED",
        "RESOLVED",
        "CLOSED",
        "TO_REVIEW",
        "IN_REVIEW",
        "REVIEWED",
    }
    VALID_RESOLUTIONS = {"FIXED", "WONTFIX", "FALSE_POSITIVE", "REMOVED", "SAFE"}
    VALID_VISIBILITIES = {"public", "private"}

    @classmethod
    def validate_project_key(cls, key: str) -> str:
        """
        Validate and sanitize project key.

        Args:
            key: Project key to validate

        Returns:
            Sanitized project key

        Raises:
            ValidationError: If key is invalid
        """
        if not key or not isinstance(key, str):
            raise ValidationError("Project key must be a non-empty string")

        key = key.strip()
        if len(key) > 400:
            raise ValidationError("Project key must be 400 characters or less")

        if not cls.PROJECT_KEY_PATTERN.match(key):
            raise ValidationError(
                "Project key can only contain letters, numbers, hyphens, "
                "underscores, dots, and colons"
            )

        return key

    @classmethod
    def validate_issue_key(cls, key: str) -> str:
        """
        Validate and sanitize issue key.

        Args:
            key: Issue key to validate

        Returns:
            Sanitized issue key

        Raises:
            ValidationError: If key is invalid
        """
        if not key or not isinstance(key, str):
            raise ValidationError("Issue key must be a non-empty string")

        key = key.strip()
        if not cls.ISSUE_KEY_PATTERN.match(key):
            raise ValidationError("Invalid issue key format")

        return key

    @classmethod
    def validate_user_login(cls, login: str) -> str:
        """
        Validate and sanitize user login.

        Args:
            login: User login to validate

        Returns:
            Sanitized user login

        Raises:
            ValidationError: If login is invalid
        """
        if not login or not isinstance(login, str):
            raise ValidationError("User login must be a non-empty string")

        login = login.strip()
        if len(login) > 255:
            raise ValidationError("User login must be 255 characters or less")

        if not cls.USER_LOGIN_PATTERN.match(login):
            raise ValidationError(
                "User login can only contain letters, numbers, hyphens, "
                "underscores, dots, and @ symbols"
            )

        return login

    @classmethod
    def validate_metric_keys(cls, keys: List[str]) -> List[str]:
        """
        Validate and sanitize metric keys.

        Args:
            keys: List of metric keys to validate

        Returns:
            List of sanitized metric keys

        Raises:
            ValidationError: If any key is invalid
        """
        if not keys or not isinstance(keys, list):
            raise ValidationError("Metric keys must be a non-empty list")

        validated_keys = []
        for key in keys:
            if not isinstance(key, str):
                raise ValidationError("All metric keys must be strings")

            key = key.strip()
            if not cls.METRIC_KEY_PATTERN.match(key):
                raise ValidationError(f"Invalid metric key format: {key}")

            validated_keys.append(key)

        return validated_keys

    @classmethod
    def validate_severity(cls, severity: str) -> str:
        """
        Validate severity value.

        Args:
            severity: Severity to validate

        Returns:
            Validated severity

        Raises:
            ValidationError: If severity is invalid
        """
        if not severity or not isinstance(severity, str):
            raise ValidationError("Severity must be a non-empty string")

        severity = severity.upper().strip()
        if severity not in cls.VALID_SEVERITIES:
            raise ValidationError(
                f"Invalid severity: {severity}. "
                f"Valid values: {', '.join(cls.VALID_SEVERITIES)}"
            )

        return severity

    @classmethod
    def validate_issue_type(cls, issue_type: str) -> str:
        """
        Validate issue type value.

        Args:
            issue_type: Issue type to validate

        Returns:
            Validated issue type

        Raises:
            ValidationError: If issue type is invalid
        """
        if not issue_type or not isinstance(issue_type, str):
            raise ValidationError("Issue type must be a non-empty string")

        issue_type = issue_type.upper().strip()
        if issue_type not in cls.VALID_ISSUE_TYPES:
            raise ValidationError(
                f"Invalid issue type: {issue_type}. "
                f"Valid values: {', '.join(cls.VALID_ISSUE_TYPES)}"
            )

        return issue_type

    @classmethod
    def validate_issue_status(cls, status: str) -> str:
        """
        Validate issue status value.

        Args:
            status: Issue status to validate

        Returns:
            Validated issue status

        Raises:
            ValidationError: If status is invalid
        """
        if not status or not isinstance(status, str):
            raise ValidationError("Issue status must be a non-empty string")

        status = status.upper().strip()
        if status not in cls.VALID_ISSUE_STATUSES:
            raise ValidationError(
                f"Invalid issue status: {status}. "
                f"Valid values: {', '.join(cls.VALID_ISSUE_STATUSES)}"
            )

        return status

    @classmethod
    def validate_url(cls, url: str) -> str:
        """
        Validate and sanitize URL.

        Args:
            url: URL to validate

        Returns:
            Sanitized URL

        Raises:
            ValidationError: If URL is invalid
        """
        if not url or not isinstance(url, str):
            raise ValidationError("URL must be a non-empty string")

        url = url.strip()
        
        # Add protocol if missing
        if not url.startswith(("http://", "https://")):
            url = f"https://{url}"

        try:
            parsed = urlparse(url)
            if not parsed.netloc:
                raise ValidationError(f"Invalid URL format: {url}")
        except Exception as e:
            raise ValidationError(f"Invalid URL: {str(e)}")

        return url

    @classmethod
    def sanitize_search_query(cls, query: str) -> str:
        """
        Sanitize search query to prevent injection attacks.

        Args:
            query: Search query to sanitize

        Returns:
            Sanitized search query
        """
        if not query or not isinstance(query, str):
            return ""

        # Remove potentially dangerous characters
        query = query.strip()
        
        # Remove SQL injection patterns
        dangerous_patterns = [
            r"[';\"\\]",  # Quotes and backslashes
            r"--",        # SQL comments
            r"/\*.*?\*/", # Multi-line comments
            r"\b(DROP|DELETE|INSERT|UPDATE|CREATE|ALTER|EXEC|EXECUTE)\b",  # SQL keywords
        ]
        
        for pattern in dangerous_patterns:
            query = re.sub(pattern, "", query, flags=re.IGNORECASE)

        # Limit length
        if len(query) > 1000:
            query = query[:1000]

        return query

    @classmethod
    def validate_pagination_params(cls, page: int, page_size: int) -> tuple[int, int]:
        """
        Validate pagination parameters.

        Args:
            page: Page number (1-based)
            page_size: Number of items per page

        Returns:
            Tuple of validated (page, page_size)

        Raises:
            ValidationError: If parameters are invalid
        """
        if not isinstance(page, int) or page < 1:
            raise ValidationError("Page must be a positive integer")

        if not isinstance(page_size, int) or page_size < 1:
            raise ValidationError("Page size must be a positive integer")

        if page_size > 500:
            raise ValidationError("Page size cannot exceed 500")

        return page, page_size

    @classmethod
    def validate_api_parameters(cls, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate and sanitize API parameters.

        Args:
            params: Dictionary of API parameters

        Returns:
            Dictionary of validated parameters

        Raises:
            ValidationError: If any parameter is invalid
        """
        if not isinstance(params, dict):
            raise ValidationError("Parameters must be a dictionary")

        validated_params = {}
        
        for key, value in params.items():
            if not isinstance(key, str):
                raise ValidationError("Parameter keys must be strings")

            # Sanitize key
            key = key.strip()
            if not key:
                continue

            # Validate specific parameters
            if key == "projectKeys" and isinstance(value, list):
                validated_params[key] = [cls.validate_project_key(k) for k in value]
            elif key == "severities" and isinstance(value, list):
                validated_params[key] = [cls.validate_severity(s) for s in value]
            elif key == "types" and isinstance(value, list):
                validated_params[key] = [cls.validate_issue_type(t) for t in value]
            elif key == "statuses" and isinstance(value, list):
                validated_params[key] = [cls.validate_issue_status(s) for s in value]
            elif key in ("p", "page") and isinstance(value, (int, str)):
                page = int(value) if isinstance(value, str) else value
                validated_params[key] = cls.validate_pagination_params(page, 100)[0]
            elif key in ("ps", "pageSize") and isinstance(value, (int, str)):
                page_size = int(value) if isinstance(value, str) else value
                validated_params[key] = cls.validate_pagination_params(1, page_size)[1]
            elif isinstance(value, str):
                # Sanitize string values
                validated_params[key] = cls.sanitize_search_query(value)
            else:
                # Pass through other types as-is
                validated_params[key] = value

        return validated_params
