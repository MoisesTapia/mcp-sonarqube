"""Structured logging utilities for SonarQube MCP."""

import logging
import logging.handlers
import os
import sys
from pathlib import Path
from typing import Any, Dict, Optional

import structlog


def setup_logging(
    log_level: str = "INFO",
    log_format: str = "json",
    log_file: Optional[str] = None,
    max_file_size: str = "10MB",
    backup_count: int = 5,
) -> None:
    """
    Set up structured logging configuration.

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_format: Log format (json, plain)
        log_file: Path to log file (optional)
        max_file_size: Maximum log file size before rotation
        backup_count: Number of backup files to keep
    """
    # Convert log level string to logging constant
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)

    # Configure structlog
    processors = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.StackInfoRenderer(),
        structlog.dev.set_exc_info,
        structlog.processors.TimeStamper(fmt="iso"),
    ]

    if log_format.lower() == "json":
        processors.append(structlog.processors.JSONRenderer())
    else:
        processors.append(structlog.dev.ConsoleRenderer())

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(numeric_level),
        logger_factory=structlog.WriteLoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # Configure standard logging
    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)

    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(numeric_level)
    
    if log_format.lower() == "json":
        console_formatter = logging.Formatter(
            '{"timestamp": "%(asctime)s", "level": "%(levelname)s", '
            '"logger": "%(name)s", "message": "%(message)s"}'
        )
    else:
        console_formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
    
    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)

    # File handler (if specified)
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        # Parse file size
        size_bytes = _parse_file_size(max_file_size)
        
        file_handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=size_bytes,
            backupCount=backup_count,
            encoding="utf-8",
        )
        file_handler.setLevel(numeric_level)
        file_handler.setFormatter(console_formatter)
        root_logger.addHandler(file_handler)

    # Set specific logger levels
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)


def _parse_file_size(size_str: str) -> int:
    """Parse file size string to bytes."""
    size_str = size_str.upper().strip()
    
    if size_str.endswith("KB"):
        return int(size_str[:-2]) * 1024
    elif size_str.endswith("MB"):
        return int(size_str[:-2]) * 1024 * 1024
    elif size_str.endswith("GB"):
        return int(size_str[:-2]) * 1024 * 1024 * 1024
    else:
        return int(size_str)


def get_logger(name: str) -> structlog.BoundLogger:
    """
    Get a structured logger instance.

    Args:
        name: Logger name (usually __name__)

    Returns:
        Configured structlog logger
    """
    return structlog.get_logger(name)


class SecurityLogger:
    """Logger for security-related events with sanitization."""

    def __init__(self, name: str):
        self.logger = get_logger(name)

    def log_authentication_attempt(
        self,
        success: bool,
        user: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> None:
        """Log authentication attempt."""
        self.logger.info(
            "Authentication attempt",
            success=success,
            user=self._sanitize_user(user),
            ip_address=ip_address,
            user_agent=self._sanitize_user_agent(user_agent),
        )

    def log_api_access(
        self,
        endpoint: str,
        method: str,
        user: Optional[str] = None,
        status_code: Optional[int] = None,
        response_time_ms: Optional[float] = None,
    ) -> None:
        """Log API access."""
        self.logger.info(
            "API access",
            endpoint=endpoint,
            method=method,
            user=self._sanitize_user(user),
            status_code=status_code,
            response_time_ms=response_time_ms,
        )

    def log_permission_denied(
        self,
        operation: str,
        resource: str,
        user: Optional[str] = None,
    ) -> None:
        """Log permission denied event."""
        self.logger.warning(
            "Permission denied",
            operation=operation,
            resource=resource,
            user=self._sanitize_user(user),
        )

    def log_security_event(
        self,
        event_type: str,
        details: Dict[str, Any],
        severity: str = "INFO",
    ) -> None:
        """Log general security event."""
        # Sanitize sensitive data in details
        sanitized_details = self._sanitize_dict(details)
        
        log_method = getattr(self.logger, severity.lower(), self.logger.info)
        log_method(
            "Security event",
            event_type=event_type,
            **sanitized_details,
        )

    def _sanitize_user(self, user: Optional[str]) -> Optional[str]:
        """Sanitize user identifier."""
        if not user:
            return None
        
        # Mask email addresses partially
        if "@" in user:
            parts = user.split("@")
            if len(parts) == 2:
                username, domain = parts
                if len(username) > 2:
                    username = username[:2] + "*" * (len(username) - 2)
                return f"{username}@{domain}"
        
        # Mask long usernames
        if len(user) > 4:
            return user[:2] + "*" * (len(user) - 4) + user[-2:]
        
        return user

    def _sanitize_user_agent(self, user_agent: Optional[str]) -> Optional[str]:
        """Sanitize user agent string."""
        if not user_agent:
            return None
        
        # Truncate long user agent strings
        if len(user_agent) > 100:
            return user_agent[:100] + "..."
        
        return user_agent

    def _sanitize_dict(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Sanitize dictionary by removing/masking sensitive keys."""
        sensitive_keys = {
            "password", "token", "secret", "key", "auth", "credential",
            "authorization", "x-auth-token", "api-key"
        }
        
        sanitized = {}
        for key, value in data.items():
            key_lower = key.lower()
            
            if any(sensitive in key_lower for sensitive in sensitive_keys):
                sanitized[key] = "***REDACTED***"
            elif isinstance(value, dict):
                sanitized[key] = self._sanitize_dict(value)
            elif isinstance(value, str) and len(value) > 1000:
                sanitized[key] = value[:1000] + "...[TRUNCATED]"
            else:
                sanitized[key] = value
        
        return sanitized


class PerformanceLogger:
    """Logger for performance metrics and monitoring."""

    def __init__(self, name: str):
        self.logger = get_logger(name)

    def log_api_call(
        self,
        endpoint: str,
        method: str,
        duration_ms: float,
        status_code: int,
        cache_hit: bool = False,
    ) -> None:
        """Log API call performance."""
        self.logger.info(
            "API call completed",
            endpoint=endpoint,
            method=method,
            duration_ms=round(duration_ms, 2),
            status_code=status_code,
            cache_hit=cache_hit,
        )

    def log_cache_operation(
        self,
        operation: str,
        cache_key: str,
        hit: bool,
        ttl_seconds: Optional[int] = None,
    ) -> None:
        """Log cache operation."""
        self.logger.debug(
            "Cache operation",
            operation=operation,
            cache_key=cache_key,
            hit=hit,
            ttl_seconds=ttl_seconds,
        )

    def log_error_with_context(
        self,
        error: Exception,
        context: Dict[str, Any],
        operation: str,
    ) -> None:
        """Log error with contextual information."""
        self.logger.error(
            "Operation failed",
            operation=operation,
            error_type=type(error).__name__,
            error_message=str(error),
            **context,
            exc_info=True,
        )