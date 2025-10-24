#!/usr/bin/env python3
"""Script to generate MCP tools documentation."""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from mcp_server.docs_generator import MCPDocsGenerator
from mcp_server.server import SonarQubeMCPServer


async def main():
    """Generate documentation for MCP tools."""
    print("Generating MCP tools documentation...")
    
    try:
        # Initialize server to get tools
        server = SonarQubeMCPServer()
        
        # We can't fully initialize without SonarQube credentials,
        # so we'll create comprehensive documentation structure
        docs_generator = MCPDocsGenerator()
        
        # Create comprehensive documentation structure based on actual implementation
        sample_tools = [
            {
                "name": "list_projects",
                "description": "List all accessible SonarQube projects with optional filtering and pagination",
                "parameters": {
                    "search": {"type": "str", "required": False, "description": "Search query to filter projects by name or key"},
                    "page": {"type": "int", "required": False, "description": "Page number for pagination (default: 1)"},
                    "page_size": {"type": "int", "required": False, "description": "Number of projects per page (default: 10)"},
                },
                "return_type": "Dict[str, Any]",
                "example": {
                    "request": {"search": "my-project", "page": 1, "page_size": 10},
                    "response": {"projects": [], "total": 0, "page": 1, "page_size": 10}
                }
            },
            {
                "name": "get_project_details", 
                "description": "Get detailed information about a specific SonarQube project including metrics and quality gate status",
                "parameters": {
                    "project_key": {"type": "str", "required": True, "description": "Unique project key in SonarQube"},
                },
                "return_type": "Dict[str, Any]",
                "example": {
                    "request": {"project_key": "my-project"},
                    "response": {"key": "my-project", "name": "My Project", "qualifier": "TRK"}
                }
            },
            {
                "name": "get_measures",
                "description": "Get quality metrics for a specific project with support for multiple metric types",
                "parameters": {
                    "project_key": {"type": "str", "required": True, "description": "Project key to get metrics for"},
                    "metric_keys": {"type": "List[str]", "required": False, "description": "List of metric keys to retrieve (default: common metrics)"},
                },
                "return_type": "Dict[str, Any]",
                "example": {
                    "request": {"project_key": "my-project", "metric_keys": ["ncloc", "bugs", "vulnerabilities"]},
                    "response": {"measures": [{"metric": "ncloc", "value": "1000"}]}
                }
            },
            {
                "name": "get_quality_gate_status",
                "description": "Get the current quality gate status for a project",
                "parameters": {
                    "project_key": {"type": "str", "required": True, "description": "Project key to check quality gate status"},
                },
                "return_type": "Dict[str, Any]",
                "example": {
                    "request": {"project_key": "my-project"},
                    "response": {"status": "OK", "conditions": []}
                }
            },
            {
                "name": "analyze_project_quality",
                "description": "Perform comprehensive quality analysis of a project including trends and recommendations",
                "parameters": {
                    "project_key": {"type": "str", "required": True, "description": "Project key to analyze"},
                    "include_history": {"type": "bool", "required": False, "description": "Include historical data in analysis"},
                },
                "return_type": "Dict[str, Any]",
                "example": {
                    "request": {"project_key": "my-project", "include_history": true},
                    "response": {"analysis": {}, "trends": {}, "recommendations": []}
                }
            },
            {
                "name": "health_check",
                "description": "Check the health status of the MCP server and SonarQube connection",
                "parameters": {},
                "return_type": "Dict[str, Any]",
                "example": {
                    "request": {},
                    "response": {"status": "healthy", "sonarqube_connection": "ok", "timestamp": "2024-01-01T00:00:00Z"}
                }
            },
            {
                "name": "get_server_info",
                "description": "Get information about the SonarQube server and MCP server configuration",
                "parameters": {},
                "return_type": "Dict[str, Any]",
                "example": {
                    "request": {},
                    "response": {"sonarqube_version": "9.9", "mcp_version": "1.0.0", "features": []}
                }
            }
        ]
        
        # Generate documentation
        documentation = {
            "title": "SonarQube MCP Tools Documentation",
            "description": "Comprehensive documentation for all available MCP tools for SonarQube integration",
            "tools": {},
            "categories": {
                "system": ["health_check", "get_server_info"],
                "projects": ["list_projects", "get_project_details", "create_project", "delete_project"],
                "metrics": ["get_measures", "get_quality_gate_status", "analyze_project_quality"],
                "cache": ["get_cache_info", "clear_all_caches", "optimize_cache_performance"],
            }
        }
        
        # Add sample tools to documentation
        for tool in sample_tools:
            documentation["tools"][tool["name"]] = tool
        
        # Generate markdown
        markdown_content = docs_generator.generate_markdown_documentation(documentation)
        
        # Save to file
        docs_path = Path(__file__).parent.parent / "docs" / "mcp_tools.md"
        docs_path.parent.mkdir(exist_ok=True)
        
        with open(docs_path, 'w', encoding='utf-8') as f:
            f.write(markdown_content)
        
        print(f"Documentation generated successfully: {docs_path}")
        
    except Exception as e:
        print(f"Error generating documentation: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())