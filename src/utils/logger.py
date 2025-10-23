"""Logging utilities for the entire application."""

import logging
import sys
from typing import Optional
from datetime import datetime
import os


class PerformanceLogger:
    """Logger for performance metrics."""
    
    def __init__(self, name: str = "performance", level: str = "INFO"):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(getattr(logging, level.upper()))
        
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
    
    def log_api_call(self, method: str, endpoint: str, duration: float, status_code: int):
        """Log API call performance."""
        self.logger.info(f"API {method} {endpoint} - {duration:.2f}ms - {status_code}")
    
    def log_cache_hit(self, key: str, hit: bool):
        """Log cache hit/miss."""
        status = "HIT" if hit else "MISS"
        self.logger.debug(f"Cache {status}: {key}")
    
    def log_error_with_context(self, message: str = None, error: Exception = None, context: dict = None, **kwargs):
        """Log error with additional context."""
        # If message is not provided, try to get it from kwargs
        if message is None:
            message = kwargs.get('operation', 'Error occurred')
        
        error_str = f" - {str(error)}" if error else ""
        context_str = f" Context: {context}" if context else ""
        
        # Remove operation from kwargs to avoid duplication
        filtered_kwargs = {k: v for k, v in kwargs.items() if k != 'operation'}
        kwargs_str = f" {filtered_kwargs}" if filtered_kwargs else ""
        
        self.logger.error(f"{message}{error_str}{context_str}{kwargs_str}")


class SecurityLogger:
    """Logger for security events."""
    
    def __init__(self, name: str = "security", level: str = "INFO"):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(getattr(logging, level.upper()))
        
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
    
    def log_auth_attempt(self, user: str, success: bool, ip: str = None):
        """Log authentication attempt."""
        status = "SUCCESS" if success else "FAILED"
        msg = f"Auth {status} for user: {user}"
        if ip:
            msg += f" from IP: {ip}"
        self.logger.info(msg)
    
    def log_permission_check(self, user: str, resource: str, allowed: bool):
        """Log permission check."""
        status = "ALLOWED" if allowed else "DENIED"
        self.logger.info(f"Permission {status}: {user} -> {resource}")
    
    def log_api_access(self, endpoint: str, method: str, status_code: int, response_time_ms: float):
        """Log API access for security monitoring."""
        self.logger.info(f"API Access: {method} {endpoint} - {status_code} - {response_time_ms:.2f}ms")
    
    def log_security_event(self, event_type: str, details: dict, severity: str = "INFO"):
        """Log security event."""
        self.logger.log(
            getattr(logging, severity.upper(), logging.INFO),
            f"Security Event [{event_type}]: {details}"
        )


class ApplicationLogger:
    """General application logger."""
    
    def __init__(self, name: str = "app", level: str = "INFO"):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(getattr(logging, level.upper()))
        
        # Prevent duplicate handlers
        if not self.logger.handlers:
            self._setup_handlers()
    
    def _setup_handlers(self):
        """Setup logging handlers."""
        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        
        # File handler (if logs directory exists)
        log_dir = os.getenv("LOG_DIR", "/app/logs")
        if os.path.exists(log_dir):
            log_file = os.path.join(log_dir, "app.log")
            file_handler = logging.FileHandler(log_file)
            file_handler.setLevel(logging.DEBUG)
            
            # File formatter with more details
            file_formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(module)s:%(lineno)d - %(message)s'
            )
            file_handler.setFormatter(file_formatter)
            self.logger.addHandler(file_handler)
        
        # Console formatter
        console_formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s',
            datefmt='%H:%M:%S'
        )
        console_handler.setFormatter(console_formatter)
        self.logger.addHandler(console_handler)
    
    def debug(self, message: str, **kwargs):
        """Log debug message."""
        self.logger.debug(message, extra=kwargs)
    
    def info(self, message: str, **kwargs):
        """Log info message."""
        self.logger.info(message, extra=kwargs)
    
    def warning(self, message: str, **kwargs):
        """Log warning message."""
        self.logger.warning(message, extra=kwargs)
    
    def error(self, message: str, **kwargs):
        """Log error message."""
        self.logger.error(message, extra=kwargs)
    
    def critical(self, message: str, **kwargs):
        """Log critical message."""
        self.logger.critical(message, extra=kwargs)
    
    def exception(self, message: str, **kwargs):
        """Log exception with traceback."""
        self.logger.exception(message, extra=kwargs)


# Global logger instances
_logger: Optional[ApplicationLogger] = None
_performance_logger: Optional[PerformanceLogger] = None
_security_logger: Optional[SecurityLogger] = None


def get_logger(name: str = "app", level: str = "INFO") -> ApplicationLogger:
    """Get or create logger instance."""
    global _logger
    if _logger is None:
        log_level = os.getenv("LOG_LEVEL", level)
        _logger = ApplicationLogger(name, log_level)
    return _logger


def get_performance_logger() -> PerformanceLogger:
    """Get or create performance logger instance."""
    global _performance_logger
    if _performance_logger is None:
        _performance_logger = PerformanceLogger()
    return _performance_logger


def get_security_logger() -> SecurityLogger:
    """Get or create security logger instance."""
    global _security_logger
    if _security_logger is None:
        _security_logger = SecurityLogger()
    return _security_logger


def setup_logging(log_level: str = "INFO", log_format: str = "plain"):
    """Setup application logging."""
    # Configure root logger
    level = getattr(logging, log_level.upper(), logging.INFO)
    
    if log_format == "json":
        format_str = '{"timestamp": "%(asctime)s", "level": "%(levelname)s", "logger": "%(name)s", "message": "%(message)s"}'
    else:
        format_str = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    
    logging.basicConfig(
        level=level,
        format=format_str,
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Reduce noise from external libraries
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("requests").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    
    return get_logger()