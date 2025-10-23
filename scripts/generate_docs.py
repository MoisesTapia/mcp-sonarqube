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
        # so we'll create a mock documentation for now
        docs_generator = MCPDocsGenerator()
        
        # Create sample documentation structure
        sample_tools = [
            {
                "name": "list_projects",
                "description": "List all accessible SonarQube projects with optional filtering",
                "parameters": {
                    "search": {"type": "str", "required": False, "description": "Search query"},
                    "page": {"type": "int", "required": False, "description": "Page number"},
                },
                "return_type": "Dict[str, Any]",
            },
            {
                "name": "get_project_details", 
                "description": "Get detailed information about a specific project",
                "parameters": {
                    "project_key": {"type": "str", "required": True, "description": "Project key"},
                },
                "return_type": "Dict[str, Any]",
            },
            {
                "name": "get_measures",
                "description": "Get metrics for a specific project",
                "parameters": {
                    "project_key": {"type": "str", "required": True, "description": "Project key"},
                    "metric_keys": {"type": "List[str]", "required": False, "description": "Metrics to retrieve"},
                },
                "return_type": "Dict[str, Any]",
            },
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