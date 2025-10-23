"""SonarQube HTTP client with authentication and error handling."""

import asyncio
import time
from typing import Any, Dict, List, Optional, Union
from urllib.parse import urljoin, urlparse

import httpx
from pydantic import ValidationError

from ..utils.logger import PerformanceLogger, SecurityLogger, get_logger
from .exceptions import (
    APIError,
    AuthenticationError,
    AuthorizationError,
    NetworkError,
    RateLimitError,
    ServerError,
    SonarQubeException,
    ValidationError as SQValidationError,
)
from .models import SonarQubeResponse
from .rate_limiter import RateLimiter
from .validators import InputValidator

logger = get_logger(__name__)
security_logger = SecurityLogger(__name__)
perf_logger = PerformanceLogger(__name__)


class SonarQubeClient:
    """Async HTTP client for SonarQube API with authentication and retry logic."""

    def __init__(
        self,
        base_url: str,
        token: str,
        organization: Optional[str] = None,
        timeout: int = 30,
        max_retries: int = 3,
        verify_ssl: bool = True,
        rate_limit_requests: int = 100,
        rate_limit_window: int = 60,
    ):
        """
        Initialize SonarQube client.

        Args:
            base_url: SonarQube server URL
            token: Authentication token
            organization: Organization key (optional)
            timeout: Request timeout in seconds
            max_retries: Maximum number of retries for failed requests
            verify_ssl: Whether to verify SSL certificates
            rate_limit_requests: Maximum requests per time window
            rate_limit_window: Rate limit time window in seconds
        """
        self.base_url = self._normalize_url(base_url)
        self.token = token
        self.organization = organization
        self.timeout = timeout
        self.max_retries = max_retries
        self.verify_ssl = verify_ssl
        
        # Initialize rate limiter
        self.rate_limiter = RateLimiter(
            max_requests=rate_limit_requests,
            time_window=rate_limit_window,
        )

        # Create HTTP client with authentication
        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            auth=(token, ""),  # SonarQube uses token as username, empty password
            timeout=httpx.Timeout(timeout),
            verify=verify_ssl,
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json",
                "User-Agent": "SonarQube-MCP/1.0",
            },
        )

        logger.info(f"Initialized SonarQube client for {self.base_url}")

    def _normalize_url(self, url: str) -> str:
        """Normalize and validate the base URL."""
        if not url:
            raise SQValidationError("Base URL cannot be empty")

        # Add protocol if missing
        if not url.startswith(("http://", "https://")):
            url = f"https://{url}"

        # Parse and validate URL
        parsed = urlparse(url)
        if not parsed.netloc:
            raise SQValidationError(f"Invalid URL format: {url}")

        # Ensure URL ends with /api
        if not parsed.path.endswith("/api"):
            if parsed.path.endswith("/"):
                url = url + "api"
            else:
                url = url + "/api"

        return url

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()

    async def close(self):
        """Close the HTTP client."""
        if self._client:
            await self._client.aclose()
            logger.info("SonarQube client closed")

    async def validate_connection(self) -> bool:
        """
        Validate connection to SonarQube server.

        Returns:
            True if connection is valid, False otherwise
        """
        try:
            response = await self.get("/system/status")
            return response.get("status") == "UP"
        except Exception as e:
            logger.error(f"Connection validation failed: {e}")
            return False

    async def authenticate(self) -> bool:
        """
        Validate authentication token.

        Returns:
            True if authentication is valid, False otherwise
        """
        try:
            await self.get("/authentication/validate")
            return True
        except AuthenticationError:
            return False
        except Exception as e:
            logger.error(f"Authentication validation failed: {e}")
            return False

    async def get(
        self,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Perform GET request.

        Args:
            endpoint: API endpoint (without /api prefix)
            params: Query parameters
            **kwargs: Additional arguments for httpx request

        Returns:
            Response data as dictionary
        """
        return await self._request("GET", endpoint, params=params, **kwargs)

    async def post(
        self,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Perform POST request.

        Args:
            endpoint: API endpoint (without /api prefix)
            data: Request body data
            params: Query parameters
            **kwargs: Additional arguments for httpx request

        Returns:
            Response data as dictionary
        """
        return await self._request("POST", endpoint, json=data, params=params, **kwargs)

    async def put(
        self,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Perform PUT request.

        Args:
            endpoint: API endpoint (without /api prefix)
            data: Request body data
            params: Query parameters
            **kwargs: Additional arguments for httpx request

        Returns:
            Response data as dictionary
        """
        return await self._request("PUT", endpoint, json=data, params=params, **kwargs)

    async def delete(
        self,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Perform DELETE request.

        Args:
            endpoint: API endpoint (without /api prefix)
            params: Query parameters
            **kwargs: Additional arguments for httpx request

        Returns:
            Response data as dictionary
        """
        return await self._request("DELETE", endpoint, params=params, **kwargs)

    async def _request(
        self,
        method: str,
        endpoint: str,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Perform HTTP request with retry logic and error handling.

        Args:
            method: HTTP method
            endpoint: API endpoint
            **kwargs: Additional arguments for httpx request

        Returns:
            Response data as dictionary

        Raises:
            SonarQubeException: Various exceptions based on error type
        """
        # Validate and sanitize parameters
        if "params" in kwargs and kwargs["params"]:
            kwargs["params"] = InputValidator.validate_api_parameters(kwargs["params"])

        # Add organization parameter if configured
        if self.organization:
            if "params" not in kwargs or kwargs["params"] is None:
                kwargs["params"] = {}
            kwargs["params"]["organization"] = self.organization

        url = endpoint.lstrip("/")
        start_time = time.time()
        
        for attempt in range(self.max_retries + 1):
            try:
                # Apply rate limiting
                await self.rate_limiter.wait_for_tokens()
                
                logger.debug(
                    "Making API request",
                    method=method,
                    url=url,
                    attempt=attempt + 1,
                    max_retries=self.max_retries + 1,
                )
                
                response = await self._client.request(method, url, **kwargs)
                duration_ms = (time.time() - start_time) * 1000
                
                # Log API access
                security_logger.log_api_access(
                    endpoint=url,
                    method=method,
                    status_code=response.status_code,
                    response_time_ms=duration_ms,
                )
                
                # Log performance
                perf_logger.log_api_call(
                    endpoint=url,
                    method=method,
                    duration_ms=duration_ms,
                    status_code=response.status_code,
                )
                
                # Handle successful responses
                if response.status_code < 400:
                    return await self._parse_response(response)
                
                # Handle error responses
                await self._handle_error_response(response)
                
            except httpx.TimeoutException as e:
                duration_ms = (time.time() - start_time) * 1000
                perf_logger.log_error_with_context(
                    error=e,
                    context={
                        "method": method,
                        "url": url,
                        "attempt": attempt + 1,
                        "duration_ms": duration_ms,
                    },
                    operation="http_request_timeout",
                )
                
                if attempt == self.max_retries:
                    raise NetworkError(f"Request timeout after {self.max_retries + 1} attempts") from e
                await self._wait_before_retry(attempt)
                
            except httpx.NetworkError as e:
                duration_ms = (time.time() - start_time) * 1000
                perf_logger.log_error_with_context(
                    error=e,
                    context={
                        "method": method,
                        "url": url,
                        "attempt": attempt + 1,
                        "duration_ms": duration_ms,
                    },
                    operation="http_network_error",
                )
                
                if attempt == self.max_retries:
                    raise NetworkError(f"Network error: {str(e)}") from e
                await self._wait_before_retry(attempt)
                
            except SonarQubeException as e:
                # Log security events for authentication/authorization errors
                if isinstance(e, (AuthenticationError, AuthorizationError)):
                    security_logger.log_security_event(
                        event_type="api_access_denied",
                        details={
                            "method": method,
                            "endpoint": url,
                            "error_type": type(e).__name__,
                            "status_code": e.status_code,
                        },
                        severity="WARNING",
                    )
                
                # Don't retry on client errors (4xx) or authentication issues
                raise
                
            except Exception as e:
                duration_ms = (time.time() - start_time) * 1000
                perf_logger.log_error_with_context(
                    error=e,
                    context={
                        "method": method,
                        "url": url,
                        "attempt": attempt + 1,
                        "duration_ms": duration_ms,
                    },
                    operation="http_unexpected_error",
                )
                
                if attempt == self.max_retries:
                    raise NetworkError(f"Unexpected error: {str(e)}") from e
                await self._wait_before_retry(attempt)

        # This should never be reached, but just in case
        raise NetworkError("Maximum retries exceeded")

    async def _parse_response(self, response: httpx.Response) -> Dict[str, Any]:
        """Parse HTTP response and return data."""
        try:
            if response.headers.get("content-type", "").startswith("application/json"):
                return response.json()
            else:
                # Handle non-JSON responses
                return {"content": response.text, "status_code": response.status_code}
        except Exception as e:
            logger.error(f"Failed to parse response: {e}")
            return {"content": response.text, "status_code": response.status_code}

    async def _handle_error_response(self, response: httpx.Response) -> None:
        """Handle HTTP error responses and raise appropriate exceptions."""
        status_code = response.status_code
        
        try:
            error_data = response.json()
            error_message = error_data.get("message", f"HTTP {status_code} error")
            errors = error_data.get("errors", [])
            if errors:
                error_message = "; ".join(errors)
        except Exception:
            error_message = f"HTTP {status_code}: {response.text}"
            error_data = None

        if status_code == 401:
            raise AuthenticationError(error_message)
        elif status_code == 403:
            raise AuthorizationError(error_message)
        elif status_code == 429:
            retry_after = response.headers.get("Retry-After")
            retry_after_int = int(retry_after) if retry_after else None
            raise RateLimitError(error_message, retry_after=retry_after_int)
        elif 400 <= status_code < 500:
            raise APIError(error_message, status_code, response_data=error_data)
        elif status_code >= 500:
            raise ServerError(error_message, status_code)
        else:
            raise APIError(error_message, status_code, response_data=error_data)

    async def _wait_before_retry(self, attempt: int) -> None:
        """Wait before retrying with exponential backoff."""
        wait_time = min(2 ** attempt, 30)  # Cap at 30 seconds
        logger.debug(f"Waiting {wait_time} seconds before retry")
        await asyncio.sleep(wait_time)

    def get_rate_limit_status(self) -> Dict[str, Any]:
        """Get current rate limiter status."""
        return self.rate_limiter.get_status()