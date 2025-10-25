"""HTTP health check server for Docker health checks."""

import asyncio
import json
from typing import Dict, Any
from aiohttp import web, ClientSession
import logging

logger = logging.getLogger(__name__)


class HealthCheckServer:
    """Simple HTTP server for health checks."""
    
    def __init__(self, port: int = 8001, mcp_server=None):
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
        
        # Add MCP tool endpoints for HTTP access
        self.app.router.add_post('/tools/{tool_name}', self.execute_tool)
        self.app.router.add_get('/tools', self.list_tools)
        self.app.router.add_get('/debug/mcp', self.debug_mcp_server)
    
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
    
    async def list_tools(self, request) -> web.Response:
        """List available MCP tools."""
        try:
            if not self.mcp_server or not hasattr(self.mcp_server, 'app') or not self.mcp_server.app:
                return web.json_response({
                    "error": "MCP server not initialized"
                }, status=503)
            
            # Debug: Check what attributes the FastMCP app has
            app_attrs = [attr for attr in dir(self.mcp_server.app) if not attr.startswith('__')]
            logger.info(f"FastMCP app attributes: {app_attrs}")
            
            # Get available tools from MCP server using FastMCP's methods
            tools = []
            
            # Go directly to the tool manager since that's where tools are actually stored
            logger.info("Getting tools directly from _tool_manager")
            if not tools and hasattr(self.mcp_server.app, '_tool_manager'):
                try:
                    tool_manager = self.mcp_server.app._tool_manager
                    logger.info(f"Found _tool_manager: {type(tool_manager)}")
                    
                    # Check if tool manager has tools
                    if hasattr(tool_manager, 'tools'):
                        tool_storage = tool_manager.tools
                        logger.info(f"Tool manager has tools: {type(tool_storage)} with {len(tool_storage) if hasattr(tool_storage, '__len__') else 'unknown'} items")
                        
                        if isinstance(tool_storage, dict):
                            for tool_name, tool_obj in tool_storage.items():
                                try:
                                    name = getattr(tool_obj, 'name', tool_name)
                                    description = getattr(tool_obj, 'description', 'No description available')
                                    
                                    tools.append({
                                        "name": name,
                                        "description": description,
                                        "source": "_tool_manager.tools",
                                        "type": str(type(tool_obj).__name__)
                                    })
                                except Exception as e:
                                    logger.warning(f"Error processing tool {tool_name}: {e}")
                    
                    # Also try other possible attributes of tool manager
                    for attr_name in ['_tools', 'registry', '_registry']:
                        if hasattr(tool_manager, attr_name):
                            tool_storage = getattr(tool_manager, attr_name)
                            logger.info(f"Tool manager has {attr_name}: {type(tool_storage)}")
                            
                            if isinstance(tool_storage, dict) and tool_storage:
                                for tool_name, tool_obj in tool_storage.items():
                                    try:
                                        name = getattr(tool_obj, 'name', tool_name)
                                        description = getattr(tool_obj, 'description', 'No description available')
                                        
                                        tools.append({
                                            "name": name,
                                            "description": description,
                                            "source": f"_tool_manager.{attr_name}",
                                            "type": str(type(tool_obj).__name__)
                                        })
                                    except Exception as e:
                                        logger.warning(f"Error processing tool {tool_name}: {e}")
                                break
                                
                except Exception as e:
                    logger.warning(f"Error accessing _tool_manager: {e}")
            
            # If still no tools, try the original approach with more attributes
            if not tools:
                possible_tool_attrs = ['_tools', 'tools', '_tool_registry', 'tool_registry', '_handlers', 'handlers']
                
                for attr_name in possible_tool_attrs:
                    if hasattr(self.mcp_server.app, attr_name):
                        tool_storage = getattr(self.mcp_server.app, attr_name)
                        logger.info(f"Found {attr_name}: {type(tool_storage)} with {len(tool_storage) if hasattr(tool_storage, '__len__') else 'unknown'} items")
                        
                        if isinstance(tool_storage, dict) and tool_storage:
                            for tool_name, tool_obj in tool_storage.items():
                                try:
                                    name = getattr(tool_obj, 'name', tool_name)
                                    description = getattr(tool_obj, 'description', 'No description available')
                                    
                                    tools.append({
                                        "name": name,
                                        "description": description,
                                        "source": attr_name,
                                        "type": str(type(tool_obj).__name__)
                                    })
                                except Exception as e:
                                    logger.warning(f"Error processing tool {tool_name}: {e}")
                            break
            
            # If no tools found, provide debug info
            if not tools:
                debug_info = {
                    "app_type": str(type(self.mcp_server.app)),
                    "app_attributes": app_attrs,
                    "checked_attributes": possible_tool_attrs
                }
                logger.warning(f"No tools found. Debug info: {debug_info}")
                
                return web.json_response({
                    "tools": [],
                    "count": 0,
                    "debug": debug_info,
                    "message": "No tools found - check server initialization"
                })
            
            return web.json_response({
                "tools": tools,
                "count": len(tools)
            })
            
        except Exception as e:
            logger.error(f"Error listing tools: {e}")
            return web.json_response({
                "error": str(e)
            }, status=500)
    
    async def execute_tool(self, request) -> web.Response:
        """Execute an MCP tool via HTTP."""
        try:
            tool_name = request.match_info['tool_name']
            
            if not self.mcp_server or not hasattr(self.mcp_server, 'app') or not self.mcp_server.app:
                return web.json_response({
                    "error": "MCP server not initialized"
                }, status=503)
            
            # Parse request body
            try:
                body = await request.json()
                arguments = body.get('arguments', {})
            except Exception:
                arguments = {}
            
            # Find the tool using FastMCP's methods
            tool_obj = None
            tool_func = None
            
            # Skip FastMCP's get_tool and get_tools methods since they don't seem to work
            # Go directly to the tool manager where we know the tools are stored
            logger.info(f"Looking for tool {tool_name} directly in _tool_manager")
            
            # If still not found, try tool manager (this is where tools are actually stored)
            if not tool_func and hasattr(self.mcp_server.app, '_tool_manager'):
                try:
                    tool_manager = self.mcp_server.app._tool_manager
                    logger.info(f"Searching in tool_manager for {tool_name}")
                    
                    # Check various attributes of tool manager, prioritizing _tools
                    for attr_name in ['_tools', 'tools', 'registry', '_registry']:
                        if hasattr(tool_manager, attr_name):
                            tool_storage = getattr(tool_manager, attr_name)
                            logger.info(f"Checking _tool_manager.{attr_name}: {type(tool_storage)} with {len(tool_storage) if hasattr(tool_storage, '__len__') else 'no length'} items")
                            
                            if isinstance(tool_storage, dict) and tool_name in tool_storage:
                                tool_obj = tool_storage[tool_name]
                                logger.info(f"Found tool {tool_name} via _tool_manager.{attr_name}: {type(tool_obj)}")
                                
                                # Extract the function from FastMCP FunctionTool
                                logger.info(f"Inspecting FunctionTool {tool_name}: {dir(tool_obj)}")
                                
                                # Try different possible attributes for the actual function
                                # Based on logs, FunctionTool has 'fn' attribute
                                possible_func_attrs = [
                                    'fn', 'func', 'function', 'handler', 'callback', '_func', '_function', 
                                    '_handler', '_callback', 'call_func', 'execute', '_execute', 'run'
                                ]
                                
                                for func_attr in possible_func_attrs:
                                    if hasattr(tool_obj, func_attr):
                                        potential_func = getattr(tool_obj, func_attr)
                                        logger.info(f"Found {func_attr} in {tool_name}: {type(potential_func)}, callable: {callable(potential_func)}")
                                        if callable(potential_func):
                                            tool_func = potential_func
                                            logger.info(f"✅ Using {func_attr} from {tool_name}: {type(tool_func)}")
                                            break
                                
                                # If no function attribute found, try if the object itself is callable
                                if not tool_func and callable(tool_obj):
                                    tool_func = tool_obj
                                    logger.info(f"✅ Tool {tool_name} is directly callable: {type(tool_func)}")
                                
                                # Last resort: try to call the object directly (some FastMCP tools work this way)
                                if not tool_func:
                                    logger.warning(f"No callable function found in {tool_name}, will try direct call")
                                    # We'll handle this in the execution part
                                break
                except Exception as e:
                    logger.warning(f"Error accessing _tool_manager for {tool_name}: {e}")
            
            # Last resort: try direct attributes
            if not tool_func:
                possible_tool_attrs = ['_tools', 'tools', '_tool_registry', 'tool_registry', '_handlers', 'handlers']
                
                for attr_name in possible_tool_attrs:
                    if hasattr(self.mcp_server.app, attr_name):
                        tool_storage = getattr(self.mcp_server.app, attr_name)
                        if isinstance(tool_storage, dict) and tool_name in tool_storage:
                            tool_obj = tool_storage[tool_name]
                            logger.info(f"Found tool {tool_name} via {attr_name}: {type(tool_obj)}")
                            if hasattr(tool_obj, 'func'):
                                tool_func = tool_obj.func
                            elif callable(tool_obj):
                                tool_func = tool_obj
                            break
            
            if not tool_func and not tool_obj:
                logger.error(f"Tool '{tool_name}' not found in any location")
                return web.json_response({
                    "error": f"Tool '{tool_name}' not found"
                }, status=404)
            
            try:
                # Call the tool function with arguments
                if tool_func:
                    # We found a callable function
                    logger.info(f"Calling tool function {tool_name} with args: {arguments}")
                    if arguments:
                        result = await tool_func(**arguments)
                    else:
                        result = await tool_func()
                elif tool_obj:
                    # Try to call the tool object directly (FastMCP style)
                    logger.info(f"Calling tool object {tool_name} directly with args: {arguments}")
                    if hasattr(tool_obj, '__call__'):
                        if arguments:
                            result = await tool_obj(**arguments)
                        else:
                            result = await tool_obj()
                    else:
                        # Try using FastMCP's internal call mechanism
                        if hasattr(self.mcp_server.app._tool_manager, 'call_tool'):
                            logger.info(f"Using tool_manager.call_tool for {tool_name} with args: {arguments}")
                            try:
                                result = await self.mcp_server.app._tool_manager.call_tool(tool_name, arguments or {})
                                logger.info(f"Tool {tool_name} executed successfully via tool_manager")
                            except Exception as e:
                                logger.error(f"Error in tool_manager.call_tool for {tool_name}: {e}")
                                raise
                        else:
                            raise Exception(f"Cannot find a way to execute tool {tool_name}")
                else:
                    raise Exception(f"No callable found for tool {tool_name}")
                
                return web.json_response({
                    "success": True,
                    "result": result
                })
                
            except TypeError as e:
                # Handle parameter mismatch
                return web.json_response({
                    "error": f"Invalid parameters for tool '{tool_name}': {str(e)}"
                }, status=400)
            except Exception as e:
                logger.error(f"Tool execution error for {tool_name}: {e}")
                return web.json_response({
                    "error": f"Tool execution failed: {str(e)}"
                }, status=500)
            
        except Exception as e:
            logger.error(f"Error executing tool: {e}")
            return web.json_response({
                "error": str(e)
            }, status=500)
    
    async def debug_mcp_server(self, request) -> web.Response:
        """Debug endpoint to inspect MCP server state."""
        try:
            debug_info = {
                "mcp_server_exists": self.mcp_server is not None,
                "mcp_server_type": str(type(self.mcp_server)) if self.mcp_server else None,
                "app_exists": hasattr(self.mcp_server, 'app') and self.mcp_server.app is not None if self.mcp_server else False,
                "app_type": str(type(self.mcp_server.app)) if self.mcp_server and hasattr(self.mcp_server, 'app') and self.mcp_server.app else None,
            }
            
            if self.mcp_server and hasattr(self.mcp_server, 'app') and self.mcp_server.app:
                app = self.mcp_server.app
                debug_info["app_attributes"] = [attr for attr in dir(app) if not attr.startswith('__')]
                
                # Check for tools in various possible locations
                tool_locations = {}
                possible_attrs = ['_tools', 'tools', '_tool_registry', 'tool_registry', '_handlers', 'handlers', '_routes', 'routes']
                
                for attr_name in possible_attrs:
                    if hasattr(app, attr_name):
                        attr_value = getattr(app, attr_name)
                        try:
                            # Handle different types of tool storage
                            if hasattr(attr_value, '__len__'):
                                length = len(attr_value)
                            else:
                                length = "no length"
                            
                            if hasattr(attr_value, 'keys'):
                                # For dict-like objects, get keys safely
                                keys = []
                                try:
                                    keys = list(attr_value.keys())
                                except Exception:
                                    keys = "error getting keys"
                            else:
                                keys = "no keys"
                            
                            # Get a safe string representation
                            try:
                                if hasattr(attr_value, 'items') and length > 0:
                                    # For dict-like with items, show tool names
                                    sample_items = []
                                    for k, v in list(attr_value.items())[:3]:
                                        tool_name = str(k)
                                        tool_type = str(type(v).__name__)
                                        sample_items.append(f"{tool_name}:{tool_type}")
                                    sample = f"[{', '.join(sample_items)}]"
                                else:
                                    sample = str(type(attr_value))
                            except Exception:
                                sample = "serialization error"
                            
                            tool_locations[attr_name] = {
                                "type": str(type(attr_value)),
                                "length": length,
                                "keys": keys,
                                "sample": sample
                            }
                        except Exception as e:
                            tool_locations[attr_name] = {
                                "type": str(type(attr_value)),
                                "error": f"Error processing: {str(e)}"
                            }
                
                debug_info["tool_locations"] = tool_locations
                
                # Try to get tools using FastMCP's internal methods
                if hasattr(app, 'get_tools'):
                    try:
                        tools_result = app.get_tools()
                        if isinstance(tools_result, dict):
                            debug_info["get_tools_count"] = len(tools_result)
                            debug_info["get_tools_keys"] = list(tools_result.keys())
                        else:
                            debug_info["get_tools_type"] = str(type(tools_result))
                            debug_info["get_tools_length"] = len(tools_result) if hasattr(tools_result, '__len__') else "no length"
                    except Exception as e:
                        debug_info["get_tools_error"] = str(e)
                
                # Check tool manager details
                if hasattr(app, '_tool_manager'):
                    try:
                        tool_manager = app._tool_manager
                        tm_info = {
                            "type": str(type(tool_manager)),
                            "attributes": [attr for attr in dir(tool_manager) if not attr.startswith('__')]
                        }
                        
                        # Check for tools in tool manager
                        for attr_name in ['tools', '_tools', 'registry', '_registry']:
                            if hasattr(tool_manager, attr_name):
                                attr_value = getattr(tool_manager, attr_name)
                                tm_info[f"{attr_name}_type"] = str(type(attr_value))
                                tm_info[f"{attr_name}_length"] = len(attr_value) if hasattr(attr_value, '__len__') else "no length"
                                if isinstance(attr_value, dict):
                                    tm_info[f"{attr_name}_keys"] = list(attr_value.keys())[:10]  # First 10 keys
                        
                        debug_info["tool_manager_info"] = tm_info
                    except Exception as e:
                        debug_info["tool_manager_error"] = str(e)
            
            return web.json_response(debug_info)
            
        except Exception as e:
            logger.error(f"Debug endpoint error: {e}")
            return web.json_response({
                "error": str(e),
                "traceback": str(e.__traceback__) if hasattr(e, '__traceback__') else None
            }, status=500)
    
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
