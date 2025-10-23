"""Pydantic models for SonarQube API responses."""

from datetime import datetime
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, ConfigDict, Field, field_validator


class Paging(BaseModel):
    """Pagination information for API responses."""
    
    model_config = ConfigDict(populate_by_name=True)

    page_index: int = Field(alias="pageIndex")
    page_size: int = Field(alias="pageSize")
    total: int


class SonarQubeResponse(BaseModel):
    """Base response model for SonarQube API."""

    paging: Optional[Paging] = None
    data: Union[List[Dict[str, Any]], Dict[str, Any], None] = None
    errors: Optional[List[str]] = None

    @field_validator("data", mode="before")
    @classmethod
    def validate_data(cls, v):
        """Ensure data is properly formatted."""
        if v is None:
            return None
        return v


class Project(BaseModel):
    """SonarQube project model."""
    
    model_config = ConfigDict(populate_by_name=True)

    key: str
    name: str
    qualifier: str = "TRK"
    visibility: str = "public"
    last_analysis_date: Optional[datetime] = Field(None, alias="lastAnalysisDate")
    revision: Optional[str] = None
    organization: Optional[str] = None

    @field_validator("last_analysis_date", mode="before")
    @classmethod
    def parse_datetime(cls, v):
        """Parse datetime from ISO string."""
        if isinstance(v, str):
            return datetime.fromisoformat(v.replace("Z", "+00:00"))
        return v


class Metric(BaseModel):
    """SonarQube metric model."""
    
    model_config = ConfigDict(populate_by_name=True)

    key: str
    value: Union[str, int, float]
    best_value: Optional[bool] = Field(None, alias="bestValue")
    periods: Optional[List[Dict[str, Any]]] = None


class Issue(BaseModel):
    """SonarQube issue model."""
    
    model_config = ConfigDict(populate_by_name=True)

    key: str
    rule: str
    severity: str
    component: str
    project: str
    line: Optional[int] = None
    hash: Optional[str] = None
    text_range: Optional[Dict[str, int]] = Field(None, alias="textRange")
    flows: Optional[List[Dict[str, Any]]] = None
    status: str
    message: str
    effort: Optional[str] = None
    debt: Optional[str] = None
    assignee: Optional[str] = None
    author: Optional[str] = None
    tags: List[str] = []
    type: str
    scope: Optional[str] = None
    creation_date: datetime = Field(alias="creationDate")
    update_date: datetime = Field(alias="updateDate")
    close_date: Optional[datetime] = Field(None, alias="closeDate")

    @field_validator("creation_date", "update_date", "close_date", mode="before")
    @classmethod
    def parse_datetime(cls, v):
        """Parse datetime from ISO string."""
        if isinstance(v, str):
            return datetime.fromisoformat(v.replace("Z", "+00:00"))
        return v


class QualityGateCondition(BaseModel):
    """Quality Gate condition model."""

    id: str
    metric: str
    op: str  # operator: LT, GT, EQ, NE
    error: Optional[str] = None
    warning: Optional[str] = None
    actual_value: Optional[str] = Field(None, alias="actualValue")
    status: str  # OK, WARN, ERROR

    model_config = ConfigDict(populate_by_name=True)


class QualityGate(BaseModel):
    """Quality Gate model."""

    id: Optional[str] = None
    name: str
    status: str  # OK, WARN, ERROR, NONE
    conditions: List[QualityGateCondition] = []
    ignored_conditions: List[QualityGateCondition] = Field(
        default=[], alias="ignoredConditions"
    )

    model_config = ConfigDict(populate_by_name=True)


class SecurityHotspot(BaseModel):
    """Security hotspot model."""

    key: str
    component: str
    project: str
    security_category: str = Field(alias="securityCategory")
    vulnerability_probability: str = Field(alias="vulnerabilityProbability")
    status: str
    resolution: Optional[str] = None
    line: Optional[int] = None
    hash: Optional[str] = None
    text_range: Optional[Dict[str, int]] = Field(None, alias="textRange")
    flows: Optional[List[Dict[str, Any]]] = None
    message: str
    assignee: Optional[str] = None
    author: Optional[str] = None
    creation_date: datetime = Field(alias="creationDate")
    update_date: datetime = Field(alias="updateDate")

    model_config = ConfigDict(populate_by_name=True)

    @field_validator("creation_date", "update_date", mode="before")
    @classmethod
    def parse_datetime(cls, v):
        """Parse datetime from ISO string."""
        if isinstance(v, str):
            return datetime.fromisoformat(v.replace("Z", "+00:00"))
        return v


class User(BaseModel):
    """SonarQube user model."""

    login: str
    name: str
    email: Optional[str] = None
    active: bool = True
    local: bool = True
    external_identity: Optional[str] = Field(None, alias="externalIdentity")
    external_provider: Optional[str] = Field(None, alias="externalProvider")
    avatar: Optional[str] = None
    groups: List[str] = []

    model_config = ConfigDict(populate_by_name=True)


class SystemInfo(BaseModel):
    """SonarQube system information model."""

    server_id: str = Field(alias="serverId")
    version: str
    status: str
    instance_usage_type: str = Field(alias="instanceUsageType")
    edition: Optional[str] = None
    license_type: Optional[str] = Field(None, alias="licenseType")
    external_users_and_groups_provisioning: Optional[str] = Field(
        None, alias="externalUsersAndGroupsProvisioning"
    )

    model_config = ConfigDict(populate_by_name=True)


class Component(BaseModel):
    """SonarQube component model."""

    key: str
    name: str
    qualifier: str
    path: Optional[str] = None
    language: Optional[str] = None
    long_name: Optional[str] = Field(None, alias="longName")
    
    model_config = ConfigDict(populate_by_name=True)


class Duplication(BaseModel):
    """Code duplication model."""

    from_: int = Field(alias="from")
    size: int
    duplicated_blocks: List[Dict[str, Any]] = Field(alias="duplicatedBlocks")

    model_config = ConfigDict(populate_by_name=True)


class Coverage(BaseModel):
    """Code coverage model."""

    line_coverage: Optional[float] = Field(None, alias="lineCoverage")
    branch_coverage: Optional[float] = Field(None, alias="branchCoverage")
    lines_to_cover: Optional[int] = Field(None, alias="linesToCover")
    uncovered_lines: Optional[int] = Field(None, alias="uncoveredLines")
    conditions_to_cover: Optional[int] = Field(None, alias="conditionsToCover")
    uncovered_conditions: Optional[int] = Field(None, alias="uncoveredConditions")

    model_config = ConfigDict(populate_by_name=True)


class Rule(BaseModel):
    """SonarQube rule model."""

    key: str
    name: str
    lang: str
    lang_name: str = Field(alias="langName")
    type: str
    severity: str
    status: str
    is_template: bool = Field(alias="isTemplate")
    tags: List[str] = []
    system_tags: List[str] = Field(default=[], alias="sysTags")
    params: List[Dict[str, Any]] = []
    html_desc: Optional[str] = Field(None, alias="htmlDesc")
    md_desc: Optional[str] = Field(None, alias="mdDesc")

    model_config = ConfigDict(populate_by_name=True)


class Organization(BaseModel):
    """SonarQube organization model."""

    key: str
    name: str
    description: Optional[str] = None
    url: Optional[str] = None
    avatar: Optional[str] = None
    guarded: bool = False

    model_config = ConfigDict(populate_by_name=True)


class Permission(BaseModel):
    """SonarQube permission model."""

    key: str
    name: str
    description: Optional[str] = None


class Group(BaseModel):
    """SonarQube group model."""

    id: Optional[str] = None
    name: str
    description: Optional[str] = None
    members_count: int = Field(default=0, alias="membersCount")
    default: bool = False

    model_config = ConfigDict(populate_by_name=True)


class ProjectAnalysis(BaseModel):
    """Project analysis model."""

    key: str
    date: datetime
    project_version: Optional[str] = Field(None, alias="projectVersion")
    build_string: Optional[str] = Field(None, alias="buildString")
    revision: Optional[str] = None
    manual_new_code_period_baseline: bool = Field(
        default=False, alias="manualNewCodePeriodBaseline"
    )
    detected_ci: Optional[str] = Field(None, alias="detectedCI")

    model_config = ConfigDict(populate_by_name=True)

    @field_validator("date", mode="before")
    @classmethod
    def parse_datetime(cls, v):
        """Parse datetime from ISO string."""
        if isinstance(v, str):
            return datetime.fromisoformat(v.replace("Z", "+00:00"))
        return v


class WebhookDelivery(BaseModel):
    """Webhook delivery model."""

    id: str
    component_key: str = Field(alias="componentKey")
    ce_task_id: Optional[str] = Field(None, alias="ceTaskId")
    name: str
    url: str
    at: datetime
    success: bool
    http_status: Optional[int] = Field(None, alias="httpStatus")
    duration_ms: int = Field(alias="durationMs")
    payload: Optional[str] = None
    error_stacktrace: Optional[str] = Field(None, alias="errorStacktrace")

    model_config = ConfigDict(populate_by_name=True)

    @field_validator("at", mode="before")
    @classmethod
    def parse_datetime(cls, v):
        """Parse datetime from ISO string."""
        if isinstance(v, str):
            return datetime.fromisoformat(v.replace("Z", "+00:00"))
        return v


class TaskStatus(BaseModel):
    """Background task status model."""

    id: str
    type: str
    component_id: Optional[str] = Field(None, alias="componentId")
    component_key: Optional[str] = Field(None, alias="componentKey")
    component_name: Optional[str] = Field(None, alias="componentName")
    component_qualifier: Optional[str] = Field(None, alias="componentQualifier")
    analysis_id: Optional[str] = Field(None, alias="analysisId")
    status: str  # PENDING, IN_PROGRESS, SUCCESS, FAILED, CANCELED
    submitted_at: datetime = Field(alias="submittedAt")
    started_at: Optional[datetime] = Field(None, alias="startedAt")
    executed_at: Optional[datetime] = Field(None, alias="executedAt")
    execution_time_ms: Optional[int] = Field(None, alias="executionTimeMs")
    logs: bool = False
    has_error_stacktrace: bool = Field(default=False, alias="hasErrorStacktrace")
    has_scanner_context: bool = Field(default=False, alias="hasScannerContext")
    organization: Optional[str] = None
    warning_count: Optional[int] = Field(None, alias="warningCount")
    warnings: List[str] = []

    model_config = ConfigDict(populate_by_name=True)

    @field_validator("submitted_at", "started_at", "executed_at", mode="before")
    @classmethod
    def parse_datetime(cls, v):
        """Parse datetime from ISO string."""
        if isinstance(v, str):
            return datetime.fromisoformat(v.replace("Z", "+00:00"))
        return v


# Response wrapper models for specific endpoints
class ProjectsResponse(SonarQubeResponse):
    """Response model for projects endpoint."""

    components: List[Project] = []

    @field_validator("components", mode="before")
    @classmethod
    def parse_components(cls, v):
        """Parse components from response data."""
        if isinstance(v, list):
            return [Project.model_validate(item) for item in v]
        return v


class IssuesResponse(SonarQubeResponse):
    """Response model for issues endpoint."""

    issues: List[Issue] = []
    components: List[Component] = []
    rules: List[Rule] = []
    users: List[User] = []

    @field_validator("issues", mode="before")
    @classmethod
    def parse_issues(cls, v):
        """Parse issues from response data."""
        if not isinstance(v, list):
            return []
        return [Issue.model_validate(item) for item in v]

    @field_validator("components", mode="before")
    @classmethod
    def parse_components(cls, v):
        """Parse components from response data."""
        if not isinstance(v, list):
            return []
        return [Component.model_validate(item) for item in v]

    @field_validator("rules", mode="before")
    @classmethod
    def parse_rules(cls, v):
        """Parse rules from response data."""
        if not isinstance(v, list):
            return []
        return [Rule.model_validate(item) for item in v]

    @field_validator("users", mode="before")
    @classmethod
    def parse_users(cls, v):
        """Parse users from response data."""
        if not isinstance(v, list):
            return []
        return [User.model_validate(item) for item in v]


class MeasuresResponse(SonarQubeResponse):
    """Response model for measures endpoint."""

    component: Optional[Component] = None
    metrics: List[Metric] = []
    periods: List[Dict[str, Any]] = []

    @field_validator("component", mode="before")
    @classmethod
    def parse_component(cls, v):
        """Parse component from response data."""
        if isinstance(v, dict):
            return Component.model_validate(v)
        return v

    @field_validator("metrics", mode="before")
    @classmethod
    def parse_metrics(cls, v):
        """Parse metrics from response data."""
        if isinstance(v, list):
            return [Metric.model_validate(item) for item in v]
        return v