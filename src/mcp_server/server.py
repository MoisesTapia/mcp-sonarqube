"""FastMCP server for SonarQube integration."""

import asyncio
import signal
import sys
from contextlib import asynccontextmanager
from typing import Any, Dict, List, Optional

from fastmcp import FastMCP
from mcp.types import Tool

from ..sonarqube_client import SonarQubeClient, InputValidator
from ..utils import create_cache_manager, get_logger, setup_logging
from .cache_manager import MCPCacheManager
from .config import get_settings
from .docs_generator import MCPDocsGenerator
from .health_server import HealthCheckServer


class SonarQubeMCPServer:
    """SonarQube MCP Server implementation."""

    def __init__(self):
        """Initialize the MCP server."""
        self.settings = get_settings()
        self.logger = get_logger(__name__)
        self.sonarqube_client: Optional[SonarQubeClient] = None
        self.cache_manager = None
        self.mcp_cache_manager: Optional[MCPCacheManager] = None
        self.docs_generator = MCPDocsGenerator()
        self.app: Optional[FastMCP] = None
        self.health_server: Optional[HealthCheckServer] = None
        self.health_runner = None
        self._shutdown_event = asyncio.Event()

    async def initialize(self) -> None:
        """Initialize server components."""
        # Setup logging
        setup_logging(
            log_level=self.settings.server_log_level,
            log_format="json" if not self.settings.server_debug else "plain",
        )

        self.logger.info("Initializing SonarQube MCP Server")

        # Initialize SonarQube client
        sonarqube_config = self.settings.sonarqube_config
        self.sonarqube_client = SonarQubeClient(
            base_url=sonarqube_config.url,
            token=sonarqube_config.token,
            organization=sonarqube_config.organization,
            timeout=sonarqube_config.timeout,
            max_retries=sonarqube_config.max_retries,
            verify_ssl=sonarqube_config.verify_ssl,
        )

        # Validate SonarQube connection
        try:
            is_connected = await self.sonarqube_client.validate_connection()
            if not is_connected:
                raise RuntimeError("Failed to connect to SonarQube server")

            is_authenticated = await self.sonarqube_client.authenticate()
            if not is_authenticated:
                raise RuntimeError("Failed to authenticate with SonarQube")

            self.logger.info("Successfully connected to SonarQube")
        except Exception as e:
            self.logger.error(f"SonarQube connection failed: {e}")
            raise

        # Initialize cache manager
        cache_config = self.settings.cache_config
        if cache_config.enabled:
            self.cache_manager = create_cache_manager(
                redis_url=cache_config.redis_url,
                default_ttl=cache_config.ttl,
                ttl_by_type=cache_config.ttl_by_type,
            )
            self.mcp_cache_manager = MCPCacheManager(self.cache_manager)
            await self.mcp_cache_manager.start_background_tasks()
            self.logger.info("Cache manager initialized")

        # Initialize FastMCP app
        self.app = FastMCP("SonarQube MCP Server")
        
        # Register tools
        await self._register_tools()
        
        self.logger.info("SonarQube MCP Server initialized successfully")

    async def _register_tools(self) -> None:
        """Register MCP tools."""
        if not self.app:
            raise RuntimeError("FastMCP app not initialized")

        # Initialize tool classes
        from .tools.projects import ProjectTools
        from .tools.measures import MeasureTools
        from .tools.security import SecurityTools
        from .tools.issues import IssueTools
        from .tools.quality_gates import QualityGateTools
        from .resources import ResourceManager
        from .prompts import PromptManager
        
        project_tools = ProjectTools(self.sonarqube_client, self.cache_manager)
        measure_tools = MeasureTools(self.sonarqube_client, self.cache_manager)
        security_tools = SecurityTools(self.sonarqube_client, self.cache_manager)
        issue_tools = IssueTools(self.sonarqube_client, self.cache_manager)
        quality_gate_tools = QualityGateTools(self.sonarqube_client, self.cache_manager)
        
        # Initialize resource and prompt managers
        resource_manager = ResourceManager(self.sonarqube_client, self.cache_manager)
        prompt_manager = PromptManager(self.sonarqube_client, self.cache_manager)

        # Health check tool
        @self.app.tool()
        async def health_check() -> Dict[str, Any]:
            """Check server health and SonarQube connectivity."""
            try:
                # Check SonarQube connection
                sonarqube_status = await self.sonarqube_client.validate_connection()
                
                # Check cache status
                cache_status = "enabled" if self.cache_manager else "disabled"
                
                return {
                    "status": "healthy" if sonarqube_status else "unhealthy",
                    "sonarqube_connected": sonarqube_status,
                    "cache_status": cache_status,
                    "server_version": "1.0.0",
                }
            except Exception as e:
                self.logger.error(f"Health check failed: {e}")
                return {
                    "status": "unhealthy",
                    "error": str(e),
                    "server_version": "1.0.0",
                }

        @self.app.tool()
        async def get_server_info() -> Dict[str, Any]:
            """Get SonarQube server information."""
            try:
                if not self.sonarqube_client:
                    raise RuntimeError("SonarQube client not initialized")
                
                system_info = await self.sonarqube_client.get("/system/status")
                return {
                    "server_id": system_info.get("id", "unknown"),
                    "version": system_info.get("version", "unknown"),
                    "status": system_info.get("status", "unknown"),
                }
            except Exception as e:
                self.logger.error(f"Failed to get server info: {e}")
                raise RuntimeError(f"Failed to get server info: {str(e)}")

        # Project management tools
        @self.app.tool()
        async def list_projects(
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
            """
            return await project_tools.list_projects(search, organization, visibility, page, page_size)

        @self.app.tool()
        async def get_project_details(project_key: str) -> Dict[str, Any]:
            """
            Get detailed information about a specific project.
            
            Args:
                project_key: Unique project key
            """
            return await project_tools.get_project_details(project_key)

        @self.app.tool()
        async def create_project(
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
            """
            return await project_tools.create_project(name, project_key, visibility, main_branch)

        @self.app.tool()
        async def delete_project(project_key: str) -> Dict[str, Any]:
            """
            Delete a SonarQube project.
            
            Args:
                project_key: Unique project key to delete
            """
            return await project_tools.delete_project(project_key)

        @self.app.tool()
        async def get_project_branches(project_key: str) -> Dict[str, Any]:
            """
            Get branches for a specific project.
            
            Args:
                project_key: Unique project key
            """
            return await project_tools.get_project_branches(project_key)

        @self.app.tool()
        async def get_project_analyses(
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
            """
            return await project_tools.get_project_analyses(project_key, page, page_size)

        # Metrics and quality analysis tools
        @self.app.tool()
        async def get_measures(
            project_key: str,
            metric_keys: Optional[List[str]] = None,
            additional_fields: Optional[List[str]] = None,
        ) -> Dict[str, Any]:
            """
            Get metrics for a specific project.
            
            Args:
                project_key: Unique project key
                metric_keys: List of metric keys to retrieve (defaults to core metrics)
                additional_fields: Additional fields to include (periods, metrics)
            """
            return await measure_tools.get_measures(project_key, metric_keys, additional_fields)

        @self.app.tool()
        async def get_quality_gate_status(project_key: str) -> Dict[str, Any]:
            """
            Get Quality Gate status for a specific project.
            
            Args:
                project_key: Unique project key
            """
            return await measure_tools.get_quality_gate_status(project_key)

        @self.app.tool()
        async def get_project_history(
            project_key: str,
            metrics: Optional[List[str]] = None,
            from_date: Optional[str] = None,
            to_date: Optional[str] = None,
            page: int = 1,
            page_size: int = 1000,
        ) -> Dict[str, Any]:
            """
            Get historical metrics data for a project.
            
            Args:
                project_key: Unique project key
                metrics: List of metrics to retrieve history for
                from_date: Start date (YYYY-MM-DD format)
                to_date: End date (YYYY-MM-DD format)
                page: Page number (1-based)
                page_size: Number of records per page
            """
            return await measure_tools.get_project_history(
                project_key, metrics, from_date, to_date, page, page_size
            )

        @self.app.tool()
        async def get_metrics_definitions() -> Dict[str, Any]:
            """Get definitions of all available metrics."""
            return await measure_tools.get_metrics_definitions()

        @self.app.tool()
        async def analyze_project_quality(project_key: str) -> Dict[str, Any]:
            """
            Perform comprehensive quality analysis of a project.
            
            Args:
                project_key: Unique project key
            """
            return await measure_tools.analyze_project_quality(project_key)

        # Security analysis tools
        @self.app.tool()
        async def search_hotspots(
            project_key: str,
            statuses: Optional[List[str]] = None,
            resolutions: Optional[List[str]] = None,
            hotspot_keys: Optional[List[str]] = None,
            branch: Optional[str] = None,
            pull_request: Optional[str] = None,
            since_leak_period: bool = False,
            only_mine: bool = False,
            page: int = 1,
            page_size: int = 100,
        ) -> Dict[str, Any]:
            """
            Search for security hotspots in a project.
            
            Args:
                project_key: Unique project key
                statuses: List of hotspot statuses (TO_REVIEW, IN_REVIEW, REVIEWED)
                resolutions: List of resolutions (FIXED, SAFE, ACKNOWLEDGED)
                hotspot_keys: List of specific hotspot keys to retrieve
                branch: Branch name to analyze
                pull_request: Pull request key to analyze
                since_leak_period: Only return hotspots from leak period
                only_mine: Only return hotspots assigned to current user
                page: Page number (1-based)
                page_size: Number of hotspots per page (max 500)
            """
            return await security_tools.search_hotspots(
                project_key, statuses, resolutions, hotspot_keys, branch, 
                pull_request, since_leak_period, only_mine, page, page_size
            )

        @self.app.tool()
        async def get_hotspot_details(hotspot_key: str) -> Dict[str, Any]:
            """
            Get detailed information about a specific security hotspot.
            
            Args:
                hotspot_key: Unique hotspot key
            """
            return await security_tools.get_hotspot_details(hotspot_key)

        @self.app.tool()
        async def generate_security_assessment(
            project_key: str,
            include_resolved: bool = False,
            time_period_days: int = 30,
        ) -> Dict[str, Any]:
            """
            Generate a comprehensive security assessment report for a project.
            
            Args:
                project_key: Unique project key
                include_resolved: Include resolved hotspots in analysis
                time_period_days: Number of days to look back for trend analysis
            """
            return await security_tools.generate_security_assessment(
                project_key, include_resolved, time_period_days
            )

        @self.app.tool()
        async def update_hotspot_status(
            hotspot_key: str,
            status: str,
            resolution: Optional[str] = None,
            comment: Optional[str] = None,
        ) -> Dict[str, Any]:
            """
            Update the status of a security hotspot.
            
            Args:
                hotspot_key: Unique hotspot key
                status: New status (TO_REVIEW, IN_REVIEW, REVIEWED)
                resolution: Resolution if status is REVIEWED (FIXED, SAFE, ACKNOWLEDGED)
                comment: Optional comment explaining the change
            """
            return await security_tools.update_hotspot_status(
                hotspot_key, status, resolution, comment
            )

        # Issue management tools
        @self.app.tool()
        async def search_issues(
            project_keys: Optional[List[str]] = None,
            severities: Optional[List[str]] = None,
            types: Optional[List[str]] = None,
            statuses: Optional[List[str]] = None,
            resolutions: Optional[List[str]] = None,
            assignees: Optional[List[str]] = None,
            authors: Optional[List[str]] = None,
            tags: Optional[List[str]] = None,
            created_after: Optional[str] = None,
            created_before: Optional[str] = None,
            page: int = 1,
            page_size: int = 100,
        ) -> Dict[str, Any]:
            """
            Search for issues with comprehensive filtering options.
            
            Args:
                project_keys: List of project keys to search in
                severities: List of severities (INFO, MINOR, MAJOR, CRITICAL, BLOCKER)
                types: List of issue types (CODE_SMELL, BUG, VULNERABILITY, SECURITY_HOTSPOT)
                statuses: List of statuses (OPEN, CONFIRMED, REOPENED, RESOLVED, CLOSED, etc.)
                resolutions: List of resolutions (FIXED, WONTFIX, FALSE_POSITIVE, etc.)
                assignees: List of assignee logins
                authors: List of author logins
                tags: List of tags to filter by
                created_after: Created after date (YYYY-MM-DD format)
                created_before: Created before date (YYYY-MM-DD format)
                page: Page number (1-based)
                page_size: Number of issues per page (max 500)
            """
            return await issue_tools.search_issues(
                project_keys, severities, types, statuses, resolutions,
                assignees, authors, tags, created_after, created_before, page, page_size
            )

        @self.app.tool()
        async def get_issue_details(issue_key: str) -> Dict[str, Any]:
            """
            Get detailed information about a specific issue.
            
            Args:
                issue_key: Unique issue key
            """
            return await issue_tools.get_issue_details(issue_key)

        @self.app.tool()
        async def update_issue(
            issue_key: str,
            assign: Optional[str] = None,
            transition: Optional[str] = None,
            comment: Optional[str] = None,
            severity: Optional[str] = None,
            type: Optional[str] = None,
        ) -> Dict[str, Any]:
            """
            Update an issue (assign, transition, comment, etc.).
            
            Args:
                issue_key: Unique issue key
                assign: Login of user to assign issue to
                transition: Transition to apply (confirm, resolve, reopen, etc.)
                comment: Comment to add to the issue
                severity: New severity (INFO, MINOR, MAJOR, CRITICAL, BLOCKER)
                type: New type (CODE_SMELL, BUG, VULNERABILITY)
            """
            return await issue_tools.update_issue(
                issue_key, assign, transition, comment, severity, type
            )

        @self.app.tool()
        async def add_issue_comment(
            issue_key: str,
            comment_text: str,
        ) -> Dict[str, Any]:
            """
            Add a comment to an issue.
            
            Args:
                issue_key: Unique issue key
                comment_text: Comment text to add
            """
            return await issue_tools.add_issue_comment(issue_key, comment_text)

        @self.app.tool()
        async def get_issue_transitions(issue_key: str) -> Dict[str, Any]:
            """
            Get available transitions for an issue.
            
            Args:
                issue_key: Unique issue key
            """
            return await issue_tools.get_issue_transitions(issue_key)

        # Quality Gates management tools
        @self.app.tool()
        async def list_quality_gates() -> Dict[str, Any]:
            """List all available Quality Gates."""
            return await quality_gate_tools.list_quality_gates()

        @self.app.tool()
        async def get_quality_gate_conditions(quality_gate_name: str) -> Dict[str, Any]:
            """
            Get conditions for a specific Quality Gate.
            
            Args:
                quality_gate_name: Name of the Quality Gate
            """
            return await quality_gate_tools.get_quality_gate_conditions(quality_gate_name)

        @self.app.tool()
        async def get_project_quality_gate_status(project_key: str) -> Dict[str, Any]:
            """
            Get Quality Gate status for a specific project with detailed analysis.
            
            Args:
                project_key: Unique project key
            """
            return await quality_gate_tools.get_project_quality_gate_status(project_key)

        # Cache management tools
        @self.app.tool()
        async def get_cache_info() -> Dict[str, Any]:
            """Get comprehensive cache information and statistics."""
            if not self.mcp_cache_manager:
                return {"error": "Cache not enabled"}
            return await self.mcp_cache_manager.get_cache_info()

        @self.app.tool()
        async def clear_all_caches() -> Dict[str, Any]:
            """Clear all cache entries."""
            if not self.mcp_cache_manager:
                return {"error": "Cache not enabled"}
            return await self.mcp_cache_manager.clear_all_caches()

        @self.app.tool()
        async def clear_cache_by_type(cache_type: str) -> Dict[str, Any]:
            """
            Clear cache entries of a specific type.
            
            Args:
                cache_type: Type of cache to clear (projects, metrics, quality_gates, issues, security)
            """
            if not self.mcp_cache_manager:
                return {"error": "Cache not enabled"}
            return await self.mcp_cache_manager.clear_cache_by_type(cache_type)

        @self.app.tool()
        async def invalidate_project_caches(project_key: str) -> Dict[str, Any]:
            """
            Invalidate all caches related to a specific project.
            
            Args:
                project_key: Project key to invalidate caches for
            """
            if not self.mcp_cache_manager:
                return {"error": "Cache not enabled"}
            
            try:
                project_key = InputValidator.validate_project_key(project_key)
                await self.mcp_cache_manager.invalidate_project_caches(project_key)
                return {
                    "success": True,
                    "message": f"Invalidated all caches for project {project_key}",
                    "project_key": project_key,
                }
            except Exception as e:
                return {"success": False, "error": str(e)}

        @self.app.tool()
        async def optimize_cache_performance() -> Dict[str, Any]:
            """Perform cache optimization operations."""
            if not self.mcp_cache_manager:
                return {"error": "Cache not enabled"}
            return await self.mcp_cache_manager.optimize_cache_performance()

        # Resource management tools
        @self.app.tool()
        async def get_resource(uri: str) -> Dict[str, Any]:
            """
            Get MCP resource data for the given URI.
            
            Args:
                uri: Resource URI (e.g., sonarqube://projects/my-project)
            """
            return await resource_manager.get_resource(uri)

        @self.app.tool()
        async def list_supported_resources() -> Dict[str, Any]:
            """List all supported resource types and their capabilities."""
            return {
                "success": True,
                "resources": resource_manager.list_supported_resources(),
            }

        @self.app.tool()
        async def validate_resource_uri(uri: str) -> Dict[str, Any]:
            """
            Validate a resource URI and return parsing information.
            
            Args:
                uri: Resource URI to validate
            """
            return resource_manager.validate_uri(uri)

        # Prompt execution tools
        @self.app.tool()
        async def execute_prompt(name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
            """
            Execute an MCP prompt with given arguments.
            
            Args:
                name: Prompt name (analyze_project_quality, security_assessment, code_review_summary)
                arguments: Prompt arguments as dictionary
            """
            try:
                result = await prompt_manager.execute_prompt(name, arguments)
                return {
                    "success": True,
                    "result": result,
                }
            except Exception as e:
                return {
                    "success": False,
                    "error": str(e),
                }

        @self.app.tool()
        async def list_available_prompts() -> Dict[str, Any]:
            """List all available prompts with their metadata."""
            return {
                "success": True,
                "prompts": prompt_manager.list_prompts(),
            }

        @self.app.tool()
        async def get_prompt_schema(name: str) -> Dict[str, Any]:
            """
            Get the schema for a specific prompt.
            
            Args:
                name: Prompt name
            """
            schema = prompt_manager.get_prompt_schema(name)
            if schema:
                return {
                    "success": True,
                    "schema": schema,
                }
            else:
                return {
                    "success": False,
                    "error": f"Prompt not found: {name}",
                }

        # Documentation tools
        @self.app.tool()
        async def get_tools_documentation() -> Dict[str, Any]:
            """Get comprehensive documentation for all available MCP tools."""
            try:
                # Get all registered tools from FastMCP app
                tools = []
                if hasattr(self.app, '_tools'):
                    tools = list(self.app._tools.values())
                
                documentation = self.docs_generator.generate_tools_documentation(tools)
                return {
                    "success": True,
                    "documentation": documentation,
                }
            except Exception as e:
                self.logger.error(f"Error generating documentation: {e}")
                return {
                    "success": False,
                    "error": str(e),
                }

        @self.app.tool()
        async def get_rate_limit_status() -> Dict[str, Any]:
            """Get current rate limiting status for SonarQube API calls."""
            if not self.sonarqube_client:
                return {"error": "SonarQube client not initialized"}
            
            try:
                status = self.sonarqube_client.get_rate_limit_status()
                return {
                    "success": True,
                    "rate_limit_status": status,
                }
            except Exception as e:
                return {"success": False, "error": str(e)}

        self.logger.info("All MCP tools registered successfully")

    async def start(self) -> None:
        """Start the MCP server."""
        if not self.app:
            raise RuntimeError("Server not initialized")

        server_config = self.settings.server_config
        
        self.logger.info(
            f"Starting SonarQube MCP Server on {server_config.host}:{server_config.port}"
        )

        # Setup signal handlers for graceful shutdown
        if sys.platform != "win32":
            loop = asyncio.get_event_loop()
            for sig in (signal.SIGTERM, signal.SIGINT):
                loop.add_signal_handler(sig, self._signal_handler)

        try:
            # Run the FastMCP server
            await self.app.run(
                transport="stdio",  # Use stdio transport for MCP
            )
        except KeyboardInterrupt:
            self.logger.info("Received keyboard interrupt")
        except Exception as e:
            self.logger.error(f"Server error: {e}")
            raise
        finally:
            await self.shutdown()

    def _signal_handler(self) -> None:
        """Handle shutdown signals."""
        self.logger.info("Received shutdown signal")
        self._shutdown_event.set()

    async def shutdown(self) -> None:
        """Shutdown server components."""
        self.logger.info("Shutting down SonarQube MCP Server")

        # Close SonarQube client
        if self.sonarqube_client:
            await self.sonarqube_client.close()
            self.logger.info("SonarQube client closed")

        # Stop cache background tasks
        if self.mcp_cache_manager:
            await self.mcp_cache_manager.stop_background_tasks()

        # Close cache manager
        if self.cache_manager:
            await self.cache_manager.close()
            self.logger.info("Cache manager closed")

        self.logger.info("SonarQube MCP Server shutdown complete")

    @asynccontextmanager
    async def lifespan(self):
        """Async context manager for server lifecycle."""
        await self.initialize()
        
        # Start health check server
        self.health_server = HealthCheckServer(port=8000, mcp_server=self)
        self.health_runner = await self.health_server.start()
        
        try:
            yield self
        finally:
            # Stop health check server
            if self.health_server and self.health_runner:
                await self.health_server.stop(self.health_runner)
            await self.shutdown()


async def main() -> None:
    """Main entry point for the MCP server."""
    server = SonarQubeMCPServer()
    
    try:
        async with server.lifespan():
            await server.start()
    except KeyboardInterrupt:
        print("\nShutdown requested by user")
    except Exception as e:
        print(f"Server failed to start: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())