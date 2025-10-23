"""HTTP health check server for Docker health checks."""

import asyncio
import json
from typing import Dict, Any
from aiohttp import web, ClientSession
import logging

logger = logging.getLogger(__name__)


class HealthCheckServer:
    """Simple HTTP server for health checks."""
    
    def __init__(self, port: int = 8000, mcp_server=None):
        """Initialize health check server."""
        self.port = port
        self.mcp_server = mcp_server
        self.app = web.Application()
        self.setup_routes()
    
    def setup_routes(self):
        """Setup HTTP routes."""
        self.app.router.add_get('/health', self.health_check)
        self.app.router.add_get('/ready', self.readiness_check)
        self.app.router.add_get('/live', self.liveness_check)
    
    async def health_check(self, request) -> web.Response:
        """Health check endpoint."""
        try:
            health_data = {
                "status": "healthy",
                "timestamp": asyncio.get_event_loop().time(),
                "service": "sonarqube-mcp-server"
            }
            
            # If MCP server is available, check its health
            if self.mcp_server and hasattr(self.mcp_server, 'sonarqube_client'):
                try:
                    if self.mcp_server.sonarqube_client:
                        sonarqube_status = await self.mcp_server.sonarqube_client.validate_connection()
                        health_data["sonarqube_connected"] = sonarqube_status
                        if not sonarqube_status:
                            health_data["status"] = "degraded"
                except Exception as e:
                    logger.warning(f"SonarQube health check failed: {e}")
                    health_data["status"] = "degraded"
                    health_data["sonarqube_connected"] = False
            
            status_code = 200 if health_data["status"] == "healthy" else 503
            return web.json_response(health_data, status=status_code)
            
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return web.json_response({
                "status": "unhealthy",
                "error": str(e),
                "service": "sonarqube-mcp-server"
            }, status=503)
    
    async def readiness_check(self, request) -> web.Response:
        """Readiness check endpoint."""
        try:
            # Check if the service is ready to accept requests
            ready = True
            
            if self.mcp_server and hasattr(self.mcp_server, 'sonarqube_client'):
                if not self.mcp_server.sonarqube_client:
                    ready = False
            
            status_code = 200 if ready else 503
            return web.json_response({
                "status": "ready" if ready else "not_ready",
                "service": "sonarqube-mcp-server"
            }, status=status_code)
            
        except Exception as e:
            logger.error(f"Readiness check failed: {e}")
            return web.json_response({
                "status": "not_ready",
                "error": str(e),
                "service": "sonarqube-mcp-server"
            }, status=503)
    
    async def liveness_check(self, request) -> web.Response:
        """Liveness check endpoint."""
        # Simple liveness check - if we can respond, we're alive
        return web.json_response({
            "status": "alive",
            "service": "sonarqube-mcp-server"
        })
    
    async def start(self):
        """Start the health check server."""
        runner = web.AppRunner(self.app)
        await runner.setup()
        site = web.TCPSite(runner, '0.0.0.0', self.port)
        await site.start()
        logger.info(f"Health check server started on port {self.port}")
        return runner
    
    async def stop(self, runner):
        """Stop the health check server."""
        if runner:
            await runner.cleanup()
            logger.info("Health check server stopped")