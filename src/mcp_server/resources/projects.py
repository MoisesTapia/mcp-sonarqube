"""Project resources for MCP."""

from typing import Any, Dict, List, Optional

from ...sonarqube_client import InputValidator
from .base import BaseResource, ResourceURI


class ProjectResource(BaseResource):
    """Resource handler for project-related URIs."""
    
    def supports_uri(self, uri: ResourceURI) -> bool:
        """Check if this resource supports the URI."""
        return uri.resource_type == "projects"
    
    async def get_resource(self, uri: ResourceURI) -> Dict[str, Any]:
        """Get project resource data."""
        try:
            if uri.resource_id:
                # Specific project: sonarqube://projects/{project_key}
                return await self._get_project_details(uri)
            else:
                # All projects: sonarqube://projects
                return await self._get_projects_list(uri)
        except Exception as e:
            self.logger.error(f"Failed to get project resource {uri}: {e}")
            raise RuntimeError(f"Failed to get project resource: {str(e)}")
    
    async def _get_projects_list(self, uri: ResourceURI) -> Dict[str, Any]:
        """Get list of projects with optional filtering."""
        async def fetch_projects():
            # Extract query parameters
            search = uri.query_params.get("search")
            organization = uri.query_params.get("organization")
            visibility = uri.query_params.get("visibility")
            page = int(uri.query_params.get("page", 1))
            page_size = int(uri.query_params.get("page_size", 100))
            
            # Validate parameters
            page, page_size = InputValidator.validate_pagination_params(page, page_size)
            
            # Build API parameters
            params = {
                "p": page,
                "ps": page_size,
            }
            
            if search:
                params["q"] = InputValidator.sanitize_search_query(search)
            if organization:
                params["organization"] = organization
            if visibility and visibility in ["public", "private"]:
                params["visibility"] = visibility
            
            # Make API call
            response = await self.client.get("/projects/search", params=params)
            
            projects = response.get("components", [])
            paging = response.get("paging", {})
            
            # Enrich project data
            enriched_projects = []
            for project in projects:
                enriched_project = await self._enrich_project_data(project)
                enriched_projects.append(enriched_project)
            
            return {
                "uri": str(uri),
                "resource_type": "projects_list",
                "projects": enriched_projects,
                "total_count": paging.get("total", len(projects)),
                "page": page,
                "page_size": page_size,
                "has_more": len(projects) == page_size,
                "filters": {
                    "search": search,
                    "organization": organization,
                    "visibility": visibility,
                },
                "metadata": {
                    "generated_at": self._get_current_timestamp(),
                    "cache_ttl": 300,
                }
            }
        
        return await self._get_cached_or_fetch(uri, fetch_projects, ttl=300)
    
    async def _get_project_details(self, uri: ResourceURI) -> Dict[str, Any]:
        """Get detailed information about a specific project."""
        project_key = uri.resource_id
        
        async def fetch_project_details():
            # Validate project key
            project_key_validated = InputValidator.validate_project_key(project_key)
            
            # Get basic project information
            projects_response = await self.client.get(
                "/projects/search",
                params={"projects": project_key_validated}
            )
            
            projects = projects_response.get("components", [])
            if not projects:
                raise RuntimeError(f"Project not found: {project_key}")
            
            project = projects[0]
            
            # Enrich with additional data
            enriched_project = await self._enrich_project_data(project, detailed=True)
            
            # Get project branches if requested
            include_branches = uri.query_params.get("include_branches", "false").lower() == "true"
            if include_branches:
                try:
                    branches_response = await self.client.get(
                        "/project_branches/list",
                        params={"project": project_key_validated}
                    )
                    enriched_project["branches"] = branches_response.get("branches", [])
                except Exception as e:
                    self.logger.warning(f"Failed to get branches for {project_key}: {e}")
                    enriched_project["branches"] = []
            
            # Get project analyses if requested
            include_analyses = uri.query_params.get("include_analyses", "false").lower() == "true"
            if include_analyses:
                try:
                    analyses_response = await self.client.get(
                        "/project_analyses/search",
                        params={"project": project_key_validated, "ps": 10}
                    )
                    enriched_project["recent_analyses"] = analyses_response.get("analyses", [])
                except Exception as e:
                    self.logger.warning(f"Failed to get analyses for {project_key}: {e}")
                    enriched_project["recent_analyses"] = []
            
            return {
                "uri": str(uri),
                "resource_type": "project_details",
                "project": enriched_project,
                "metadata": {
                    "generated_at": self._get_current_timestamp(),
                    "cache_ttl": 300,
                    "includes": {
                        "branches": include_branches,
                        "analyses": include_analyses,
                    }
                }
            }
        
        return await self._get_cached_or_fetch(uri, fetch_project_details, ttl=300)
    
    async def _enrich_project_data(self, project: Dict[str, Any], detailed: bool = False) -> Dict[str, Any]:
        """Enrich project data with additional information."""
        project_key = project.get("key")
        if not project_key:
            return project
        
        enriched = project.copy()
        
        try:
            # Get basic metrics
            metrics_response = await self.client.get(
                "/measures/component",
                params={
                    "component": project_key,
                    "metricKeys": "ncloc,bugs,vulnerabilities,code_smells,coverage,duplicated_lines_density"
                }
            )
            
            component = metrics_response.get("component", {})
            measures = component.get("measures", [])
            
            # Convert measures to a more usable format
            metrics = {}
            for measure in measures:
                metric_key = measure.get("metric")
                value = measure.get("value")
                if metric_key and value is not None:
                    # Try to convert to appropriate type
                    try:
                        if "." in value:
                            metrics[metric_key] = float(value)
                        else:
                            metrics[metric_key] = int(value)
                    except ValueError:
                        metrics[metric_key] = value
            
            enriched["metrics"] = metrics
            
            # Get Quality Gate status if detailed
            if detailed:
                try:
                    qg_response = await self.client.get(
                        "/qualitygates/project_status",
                        params={"projectKey": project_key}
                    )
                    enriched["quality_gate"] = qg_response.get("projectStatus", {})
                except Exception as e:
                    self.logger.warning(f"Failed to get Quality Gate for {project_key}: {e}")
                    enriched["quality_gate"] = {"status": "UNKNOWN"}
            
        except Exception as e:
            self.logger.warning(f"Failed to enrich project data for {project_key}: {e}")
            enriched["metrics"] = {}
            if detailed:
                enriched["quality_gate"] = {"status": "UNKNOWN"}
        
        return enriched
    
    def _get_current_timestamp(self) -> str:
        """Get current timestamp in ISO format."""
        from datetime import datetime
        return datetime.utcnow().isoformat() + "Z"