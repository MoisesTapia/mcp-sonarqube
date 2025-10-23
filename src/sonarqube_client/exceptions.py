"""Custom exceptions for SonarQube client."""

from typing import Optional


class SonarQubeException(Exception):
    """Base exception for SonarQube client errors."""

    def __init__(
        self,
        message: str,
        error_code: Optional[str] = None,
        status_code: Optional[int] = None,
    ):
        self.message = message
        self.error_code = error_code
        self.status_code = status_code
        super().__init__(message)


class AuthenticationError(SonarQubeException):
    """Raised when authentication fails."""

    def __init__(self, message: str = "Authentication failed"):
        super().__init__(message, error_code="AUTH_FAILED", status_code=401)


class AuthorizationError(SonarQubeException):
    """Raised when user lacks permissions for an operation."""

    def __init__(self, message: str = "Insufficient permissions"):
        super().__init__(message, error_code="AUTH_INSUFFICIENT", status_code=403)


class NetworkError(SonarQubeException):
    """Raised when network communication fails."""

    def __init__(self, message: str, original_error: Optional[Exception] = None):
        self.original_error = original_error
        super().__init__(message, error_code="NETWORK_ERROR")


class APIError(SonarQubeException):
    """Raised when SonarQube API returns an error."""

    def __init__(
        self,
        message: str,
        status_code: int,
        error_code: Optional[str] = None,
        response_data: Optional[dict] = None,
    ):
        self.response_data = response_data
        super().__init__(message, error_code=error_code, status_code=status_code)


class ValidationError(SonarQubeException):
    """Raised when input validation fails."""

    def __init__(self, message: str, field: Optional[str] = None):
        self.field = field
        super().__init__(message, error_code="VALIDATION_ERROR", status_code=400)


class RateLimitError(SonarQubeException):
    """Raised when rate limit is exceeded."""

    def __init__(
        self,
        message: str = "Rate limit exceeded",
        retry_after: Optional[int] = None,
    ):
        self.retry_after = retry_after
        super().__init__(message, error_code="RATE_LIMIT", status_code=429)


class ServerError(SonarQubeException):
    """Raised when SonarQube server returns a 5xx error."""

    def __init__(self, message: str, status_code: int = 500):
        super().__init__(message, error_code="SERVER_ERROR", status_code=status_code)