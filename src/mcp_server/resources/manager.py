"""Resource manager for MCP resources."""

from typing import Any, Dict, List, Optional

from ...utils import get_logger
from .base import BaseResource, ResourceURI
from .projects import ProjectResource
from .metrics import MetricsResource
from .issues import IssuesResource
from .quality_gates import QualityGatesResource

logger = get_logger(__name__)


class ResourceManager:
    """Manages MCP resources and URI routing."""
    
    def __init__(self, sonarqube_client, cache_manager=None):
        """Initialize resource manager."""
        self.client = sonarqube_client
        self.cache = cache_manager
        self.logger = logger
        
        # Initialize resource handlers
        self.resources: List[BaseResource] = [
            ProjectResource(sonarqube_client, cache_manager),
            MetricsResource(sonarqube_client, cache_manager),
            IssuesResource(sonarqube_client, cache_manager),
            QualityGatesResource(sonarqube_client, cache_manager),
        ]
    
    async def get_resource(self, uri: str) -> Dict[str, Any]:
        """Get resource data for the given URI."""
        try:
            # Parse the URI
            parsed_uri = ResourceURI(uri)
            self.logger.info(f"Getting resource: {uri}")
            
            # Find appropriate resource handler
            handler = self._find_resource_handler(parsed_uri)
            if not handler:
                raise ValueError(f"No handler found for resource type: {parsed_uri.resource_type}")
            
            # Get resource data
            return await handler.get_resource(parsed_uri)
            
        except Exception as e:
            self.logger.error(f"Failed to get resource {uri}: {e}")
            raise RuntimeError(f"Failed to get resource: {str(e)}")
    
    def _find_resource_handler(self, uri: ResourceURI) -> Optional[BaseResource]:
        """Find the appropriate resource handler for the URI."""
        for resource in self.resources:
            if resource.supports_uri(uri):
                return resource
        return None
    
    def list_supported_resources(self) -> List[Dict[str, Any]]:
        """List all supported resource types and their capabilities."""
        return [
            {
                "type": "projects",
                "description": "SonarQube project information and metrics",
                "uri_patterns": [
                    "sonarqube://projects",
                    "sonarqube://projects/{project_key}",
                ],
                "query_parameters": [
                    "search", "organization", "visibility", "page", "page_size",
                    "include_branches", "include_analyses"
                ],
                "examples": [
                    "sonarqube://projects",
                    "sonarqube://projects/my-project",
                    "sonarqube://projects?search=test&visibility=public",
                    "sonarqube://projects/my-project?include_branches=true",
                ]
            },
            {
                "type": "metrics",
                "description": "Project metrics and quality measurements",
                "uri_patterns": [
                    "sonarqube://metrics/{project_key}",
                ],
                "query_parameters": [
                    "metrics", "groups", "include_history", "from_date", "to_date"
                ],
                "examples": [
                    "sonarqube://metrics/my-project",
                    "sonarqube://metrics/my-project?groups=reliability,security",
                    "sonarqube://metrics/my-project?metrics=coverage,bugs,vulnerabilities",
                    "sonarqube://metrics/my-project?include_history=true&from_date=2025-01-01",
                ]
            },
            {
                "type": "issues",
                "description": "Project issues and code quality problems",
                "uri_patterns": [
                    "sonarqube://issues",
                    "sonarqube://issues/{project_key}",
                ],
                "query_parameters": [
                    "severities", "types", "statuses", "assignees", "tags",
                    "created_after", "created_before", "page", "page_size"
                ],
                "examples": [
                    "sonarqube://issues",
                    "sonarqube://issues/my-project",
                    "sonarqube://issues/my-project?severities=MAJOR,CRITICAL",
                    "sonarqube://issues/my-project?types=BUG&statuses=OPEN",
                ]
            },
            {
                "type": "quality_gates",
                "description": "Quality Gate definitions and project status",
                "uri_patterns": [
                    "sonarqube://quality_gates",
                    "sonarqube://quality_gate/{project_key}",
                ],
                "query_parameters": [
                    "include_conditions", "include_gate_details"
                ],
                "examples": [
                    "sonarqube://quality_gates",
                    "sonarqube://quality_gates?include_conditions=true",
                    "sonarqube://quality_gate/my-project",
                    "sonarqube://quality_gate/my-project?include_gate_details=true",
                ]
            }
        ]
    
    def validate_uri(self, uri: str) -> Dict[str, Any]:
        """Validate a resource URI and return parsing information."""
        try:
            parsed_uri = ResourceURI(uri)
            handler = self._find_resource_handler(parsed_uri)
            
            return {
                "valid": True,
                "parsed": {
                    "scheme": parsed_uri.parsed.scheme,
                    "resource_type": parsed_uri.resource_type,
                    "resource_id": parsed_uri.resource_id,
                    "sub_resource": parsed_uri.sub_resource,
                    "query_params": parsed_uri.query_params,
                },
                "handler_found": handler is not None,
                "handler_type": type(handler).__name__ if handler else None,
            }
        except Exception as e:
            return {
                "valid": False,
                "error": str(e),
                "parsed": None,
                "handler_found": False,
                "handler_type": None,
            }