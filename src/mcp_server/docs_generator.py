"""Automatic documentation generator for MCP tools."""

import inspect
from typing import Any, Dict, List

from ..utils import get_logger

logger = get_logger(__name__)


class MCPDocsGenerator:
    """Generate documentation for MCP tools automatically."""

    def __init__(self):
        """Initialize documentation generator."""
        self.tools_docs = {}

    def extract_tool_documentation(self, tool_func) -> Dict[str, Any]:
        """
        Extract documentation from a tool function.

        Args:
            tool_func: The tool function to document

        Returns:
            Dictionary containing tool documentation
        """
        try:
            # Get function signature
            sig = inspect.signature(tool_func)
            
            # Get docstring
            docstring = inspect.getdoc(tool_func) or "No description available"
            
            # Parse docstring for description and args
            doc_parts = docstring.split("Args:")
            description = doc_parts[0].strip()
            
            args_info = {}
            if len(doc_parts) > 1:
                args_section = doc_parts[1].split("Returns:")[0].strip()
                args_info = self._parse_args_section(args_section)

            # Extract parameter information
            parameters = {}
            for param_name, param in sig.parameters.items():
                param_info = {
                    "type": str(param.annotation) if param.annotation != inspect.Parameter.empty else "Any",
                    "required": param.default == inspect.Parameter.empty,
                    "default": param.default if param.default != inspect.Parameter.empty else None,
                    "description": args_info.get(param_name, "No description available"),
                }
                parameters[param_name] = param_info

            # Extract return type
            return_type = str(sig.return_annotation) if sig.return_annotation != inspect.Parameter.empty else "Any"

            return {
                "name": tool_func.__name__,
                "description": description,
                "parameters": parameters,
                "return_type": return_type,
                "docstring": docstring,
            }

        except Exception as e:
            logger.error(f"Error extracting documentation for {tool_func.__name__}: {e}")
            return {
                "name": tool_func.__name__,
                "description": "Documentation extraction failed",
                "parameters": {},
                "return_type": "Any",
                "error": str(e),
            }

    def _parse_args_section(self, args_section: str) -> Dict[str, str]:
        """Parse the Args section of a docstring."""
        args_info = {}
        
        for line in args_section.split("\n"):
            line = line.strip()
            if ":" in line:
                parts = line.split(":", 1)
                if len(parts) == 2:
                    param_name = parts[0].strip()
                    description = parts[1].strip()
                    args_info[param_name] = description
        
        return args_info

    def generate_tools_documentation(self, tools: List[Any]) -> Dict[str, Any]:
        """
        Generate comprehensive documentation for all tools.

        Args:
            tools: List of tool functions

        Returns:
            Dictionary containing complete documentation
        """
        documentation = {
            "title": "SonarQube MCP Tools Documentation",
            "description": "Comprehensive documentation for all available MCP tools",
            "tools": {},
            "categories": {
                "system": [],
                "projects": [],
                "metrics": [],
                "cache": [],
            }
        }

        for tool in tools:
            tool_doc = self.extract_tool_documentation(tool)
            tool_name = tool_doc["name"]
            documentation["tools"][tool_name] = tool_doc
            
            # Categorize tools
            if tool_name.startswith(("health_", "get_server_")):
                documentation["categories"]["system"].append(tool_name)
            elif "project" in tool_name:
                documentation["categories"]["projects"].append(tool_name)
            elif any(keyword in tool_name for keyword in ["measure", "metric", "quality", "analyze"]):
                documentation["categories"]["metrics"].append(tool_name)
            elif "cache" in tool_name:
                documentation["categories"]["cache"].append(tool_name)

        return documentation

    def generate_markdown_documentation(self, documentation: Dict[str, Any]) -> str:
        """
        Generate Markdown documentation from tool documentation.

        Args:
            documentation: Documentation dictionary

        Returns:
            Markdown formatted documentation
        """
        md_lines = [
            f"# {documentation['title']}",
            "",
            documentation['description'],
            "",
            "## Table of Contents",
            "",
        ]

        # Add table of contents
        for category, tools in documentation["categories"].items():
            if tools:
                md_lines.append(f"- [{category.title()} Tools](#{category}-tools)")

        md_lines.extend(["", "---", ""])

        # Add detailed documentation for each category
        for category, tools in documentation["categories"].items():
            if not tools:
                continue
                
            md_lines.extend([
                f"## {category.title()} Tools",
                "",
            ])

            for tool_name in tools:
                tool_doc = documentation["tools"][tool_name]
                md_lines.extend(self._generate_tool_markdown(tool_doc))

        return "\n".join(md_lines)

    def _generate_tool_markdown(self, tool_doc: Dict[str, Any]) -> List[str]:
        """Generate Markdown for a single tool."""
        lines = [
            f"### {tool_doc['name']}",
            "",
            tool_doc['description'],
            "",
        ]

        # Parameters section
        if tool_doc['parameters']:
            lines.extend([
                "**Parameters:**",
                "",
            ])
            
            for param_name, param_info in tool_doc['parameters'].items():
                required_text = "**required**" if param_info['required'] else "optional"
                default_text = f" (default: `{param_info['default']}`)" if param_info['default'] is not None else ""
                
                lines.extend([
                    f"- `{param_name}` ({param_info['type']}) - {required_text}{default_text}",
                    f"  {param_info['description']}",
                ])
            
            lines.append("")

        # Return type
        lines.extend([
            f"**Returns:** `{tool_doc['return_type']}`",
            "",
        ])

        # Example usage (if available)
        lines.extend([
            "**Example:**",
            "```python",
            f"result = await {tool_doc['name']}(...)",
            "```",
            "",
            "---",
            "",
        ])

        return lines

    def save_documentation(self, documentation: Dict[str, Any], filepath: str) -> None:
        """
        Save documentation to a file.

        Args:
            documentation: Documentation dictionary
            filepath: Path to save the documentation
        """
        try:
            markdown_content = self.generate_markdown_documentation(documentation)
            
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(markdown_content)
            
            logger.info(f"Documentation saved to {filepath}")
            
        except Exception as e:
            logger.error(f"Error saving documentation to {filepath}: {e}")
            raise