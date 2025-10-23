"""Project management tools for SonarQube MCP."""

from typing import Any, Dict, List, Optional

from ...sonarqube_client import SonarQubeClient, InputValidator
from ...utils import CacheManager, get_logger

logger = get_logger(__name__)


class ProjectTools:
    """Tools for SonarQube project management."""

    def __init__(self, client: SonarQubeClient, cache_manager: Optional[CacheManager] = None):
        """Initialize project tools."""
        self.client = client
        self.cache = cache_manager
        self.logger = logger

    async def list_projects(
        self,
        search: Optional[str] = None,
        organization: Optional[str] = None,
        visibility: Optional[str] = None,
        page: int = 1,
        page_size: int = 100,
    ) -> Dict[str, Any]:
        """
        List all accessible SonarQube projects.

        Args:
            search: Search query to filter projects by name or key
            organization: Organization key to filter projects
            visibility: Project visibility (public, private)
            page: Page number (1-based)
            page_size: Number of projects per page (max 500)

        Returns:
            Dictionary containing projects list and pagination info
        """
        try:
            # Validate parameters
            page, page_size = InputValidator.validate_pagination_params(page, page_size)
            
            # Build cache key
            cache_key_params = {
                "search": search,
                "organization": organization,
                "visibility": visibility,
                "page": page,
                "page_size": page_size,
            }
            
            # Try cache first
            if self.cache:
                cached_result = await self.cache.get("projects", "list", **cache_key_params)
                if cached_result:
                    self.logger.debug("Returning cached project list")
                    return cached_result

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
            
            # Format response
            result = {
                "projects": response.get("components", []),
                "paging": response.get("paging", {}),
                "total": response.get("paging", {}).get("total", 0),
            }
            
            # Cache result
            if self.cache:
                await self.cache.set("projects", "list", result, **cache_key_params)
            
            self.logger.info(f"Retrieved {len(result['projects'])} projects")
            return result
            
        except Exception as e:
            self.logger.error(f"Failed to list projects: {e}")
            raise RuntimeError(f"Failed to list projects: {str(e)}")

    async def get_project_details(self, project_key: str) -> Dict[str, Any]:
        """
        Get detailed information about a specific project.

        Args:
            project_key: Unique project key

        Returns:
            Dictionary containing detailed project information
        """
        try:
            # Validate project key
            project_key = InputValidator.validate_project_key(project_key)
            
            # Try cache first
            if self.cache:
                cached_result = await self.cache.get("projects", "details", project_key=project_key)
                if cached_result:
                    self.logger.debug(f"Returning cached project details for {project_key}")
                    return cached_result

            # Get basic project info
            projects_response = await self.client.get(
                "/projects/search",
                params={"projects": project_key}
            )
            
            projects = projects_response.get("components", [])
            if not projects:
                raise RuntimeError(f"Project not found: {project_key}")
            
            project = projects[0]
            
            # Get additional project metrics
            try:
                metrics_response = await self.client.get(
                    "/measures/component",
                    params={
                        "component": project_key,
                        "metricKeys": "ncloc,coverage,bugs,vulnerabilities,code_smells,sqale_index"
                    }
                )
                
                metrics = {}
                for measure in metrics_response.get("component", {}).get("measures", []):
                    metrics[measure["metric"]] = measure.get("value")
                
                project["metrics"] = metrics
                
            except Exception as e:
                self.logger.warning(f"Failed to get metrics for project {project_key}: {e}")
                project["metrics"] = {}

            # Get Quality Gate status
            try:
                qg_response = await self.client.get(
                    "/qualitygates/project_status",
                    params={"projectKey": project_key}
                )
                
                project["quality_gate"] = qg_response.get("projectStatus", {})
                
            except Exception as e:
                self.logger.warning(f"Failed to get Quality Gate for project {project_key}: {e}")
                project["quality_gate"] = {}

            # Cache result
            if self.cache:
                await self.cache.set("projects", "details", project, project_key=project_key)
            
            self.logger.info(f"Retrieved details for project {project_key}")
            return project
            
        except Exception as e:
            self.logger.error(f"Failed to get project details for {project_key}: {e}")
            raise RuntimeError(f"Failed to get project details: {str(e)}")

    async def create_project(
        self,
        name: str,
        project_key: str,
        visibility: str = "private",
        main_branch: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Create a new SonarQube project.

        Args:
            name: Project name
            project_key: Unique project key
            visibility: Project visibility (public, private)
            main_branch: Main branch name (optional)

        Returns:
            Dictionary containing created project information
        """
        try:
            # Validate parameters
            project_key = InputValidator.validate_project_key(project_key)
            
            if visibility not in ["public", "private"]:
                raise ValueError("Visibility must be 'public' or 'private'")
            
            if not name or not name.strip():
                raise ValueError("Project name cannot be empty")
            
            name = name.strip()
            
            # Build API parameters
            params = {
                "name": name,
                "project": project_key,
                "visibility": visibility,
            }
            
            if main_branch:
                params["mainBranch"] = main_branch.strip()

            # Make API call
            response = await self.client.post("/projects/create", data=params)
            
            # Invalidate projects cache
            if self.cache:
                await self.cache.invalidate_pattern("projects", "*")
            
            self.logger.info(f"Created project {project_key}: {name}")
            return response.get("project", {})
            
        except Exception as e:
            self.logger.error(f"Failed to create project {project_key}: {e}")
            raise RuntimeError(f"Failed to create project: {str(e)}")

    async def delete_project(self, project_key: str) -> Dict[str, Any]:
        """
        Delete a SonarQube project.

        Args:
            project_key: Unique project key to delete

        Returns:
            Dictionary containing deletion confirmation
        """
        try:
            # Validate project key
            project_key = InputValidator.validate_project_key(project_key)
            
            # Verify project exists first
            try:
                await self.get_project_details(project_key)
            except RuntimeError:
                raise RuntimeError(f"Project not found: {project_key}")

            # Make API call
            await self.client.post("/projects/delete", data={"project": project_key})
            
            # Invalidate caches
            if self.cache:
                await self.cache.invalidate_pattern("projects", "*")
                await self.cache.delete("projects", "details", project_key=project_key)
            
            self.logger.info(f"Deleted project {project_key}")
            return {
                "success": True,
                "message": f"Project {project_key} deleted successfully",
                "project_key": project_key,
            }
            
        except Exception as e:
            self.logger.error(f"Failed to delete project {project_key}: {e}")
            raise RuntimeError(f"Failed to delete project: {str(e)}")

    async def get_project_branches(self, project_key: str) -> Dict[str, Any]:
        """
        Get branches for a specific project.

        Args:
            project_key: Unique project key

        Returns:
            Dictionary containing project branches
        """
        try:
            # Validate project key
            project_key = InputValidator.validate_project_key(project_key)
            
            # Try cache first
            if self.cache:
                cached_result = await self.cache.get("projects", "branches", project_key=project_key)
                if cached_result:
                    self.logger.debug(f"Returning cached branches for {project_key}")
                    return cached_result

            # Make API call
            response = await self.client.get(
                "/project_branches/list",
                params={"project": project_key}
            )
            
            result = {
                "project_key": project_key,
                "branches": response.get("branches", []),
            }
            
            # Cache result
            if self.cache:
                await self.cache.set("projects", "branches", result, project_key=project_key)
            
            self.logger.info(f"Retrieved {len(result['branches'])} branches for project {project_key}")
            return result
            
        except Exception as e:
            self.logger.error(f"Failed to get branches for project {project_key}: {e}")
            raise RuntimeError(f"Failed to get project branches: {str(e)}")

    async def get_project_analyses(
        self,
        project_key: str,
        page: int = 1,
        page_size: int = 100,
    ) -> Dict[str, Any]:
        """
        Get analysis history for a specific project.

        Args:
            project_key: Unique project key
            page: Page number (1-based)
            page_size: Number of analyses per page

        Returns:
            Dictionary containing project analyses
        """
        try:
            # Validate parameters
            project_key = InputValidator.validate_project_key(project_key)
            page, page_size = InputValidator.validate_pagination_params(page, page_size)
            
            # Try cache first
            cache_key_params = {"project_key": project_key, "page": page, "page_size": page_size}
            if self.cache:
                cached_result = await self.cache.get("projects", "analyses", **cache_key_params)
                if cached_result:
                    self.logger.debug(f"Returning cached analyses for {project_key}")
                    return cached_result

            # Make API call
            response = await self.client.get(
                "/project_analyses/search",
                params={
                    "project": project_key,
                    "p": page,
                    "ps": page_size,
                }
            )
            
            result = {
                "project_key": project_key,
                "analyses": response.get("analyses", []),
                "paging": response.get("paging", {}),
            }
            
            # Cache result with shorter TTL (analyses change frequently)
            if self.cache:
                await self.cache.set("projects", "analyses", result, ttl=60, **cache_key_params)
            
            self.logger.info(f"Retrieved {len(result['analyses'])} analyses for project {project_key}")
            return result
            
        except Exception as e:
            self.logger.error(f"Failed to get analyses for project {project_key}: {e}")
            raise RuntimeError(f"Failed to get project analyses: {str(e)}")