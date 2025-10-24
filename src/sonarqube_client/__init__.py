"""SonarQube Client package."""

from .client import SonarQubeClient
from .exceptions import (
    APIError,
    AuthenticationError,
    AuthorizationError,
    NetworkError,
    RateLimitError,
    ServerError,
    SonarQubeException,
    ValidationError,
)
from .models import (
    Component,
    Coverage,
    Duplication,
    Group,
    Issue,
    IssuesResponse,
    MeasuresResponse,
    Metric,
    Organization,
    Paging,
    Permission,
    Project,
    ProjectAnalysis,
    ProjectsResponse,
    QualityGate,
    QualityGateCondition,
    Rule,
    SecurityHotspot,
    SonarQubeResponse,
    SystemInfo,
    TaskStatus,
    User,
    WebhookDelivery,
)
from .rate_limiter import RateLimiter
from .validators import InputValidator

__all__ = [
    # Client
    "SonarQubeClient",
    # Exceptions
    "SonarQubeException",
    "AuthenticationError",
    "AuthorizationError",
    "NetworkError",
    "APIError",
    "ValidationError",
    "RateLimitError",
    "ServerError",
    # Models
    "SonarQubeResponse",
    "Paging",
    "Project",
    "ProjectsResponse",
    "Metric",
    "MeasuresResponse",
    "Issue",
    "IssuesResponse",
    "Component",
    "QualityGate",
    "QualityGateCondition",
    "SecurityHotspot",
    "User",
    "SystemInfo",
    "Rule",
    "Organization",
    "Permission",
    "Group",
    "ProjectAnalysis",
    "TaskStatus",
    "WebhookDelivery",
    "Coverage",
    "Duplication",
    # Validators and utilities
    "InputValidator",
    "RateLimiter",
]
