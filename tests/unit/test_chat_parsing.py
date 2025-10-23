#!/usr/bin/env python3
"""
Unit tests for chat interface message parsing functionality.
"""

import pytest
import re
from typing import Dict, Any, List, Optional, Tuple


def parse_user_intent(message: str) -> Tuple[Optional[str], Dict[str, Any]]:
    """Parse user message to identify intent and extract parameters with enhanced NLP."""
    message_lower = message.lower()
    params = {}
    
    # Enhanced project key extraction patterns
    project_patterns = [
        r"project[:\s]+([a-zA-Z0-9_.-]+)",
        r"(?:for|of|in)\s+([a-zA-Z0-9_.-]+)",
        r"([a-zA-Z0-9_.-]+)\s+project",
        r"key[:\s]+([a-zA-Z0-9_.-]+)"
    ]
    
    def extract_project_key(text: str) -> Optional[str]:
        for pattern in project_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1)
        return None
    
    # Enhanced intent patterns with synonyms and variations
    intent_patterns = {
        "list_projects": [
            r"(?:list|show|get|display|find)\s+(?:all\s+)?projects",
            r"what\s+projects\s+(?:do\s+)?(?:i\s+have|are\s+available)",
            r"show\s+me\s+(?:all\s+)?projects",
            r"projects\s+list"
        ],
        "get_project_details": [
            r"(?:project\s+)?(?:details|info|information)\s+(?:for|of|about)",
            r"(?:tell\s+me\s+about|describe|show\s+details\s+of)",
            r"what\s+(?:is|about)\s+(?:project\s+)?([a-zA-Z0-9_.-]+)",
            r"(?:project\s+)?([a-zA-Z0-9_.-]+)\s+(?:details|info)"
        ],
        "get_measures": [
            r"(?:metrics|measures|stats|statistics)\s+(?:for|of)",
            r"(?:code\s+)?quality\s+(?:metrics|measures)",
            r"(?:show|get|display)\s+(?:metrics|measures)",
            r"how\s+(?:good|bad)\s+is\s+(?:the\s+)?(?:code|quality)",
            r"coverage\s+(?:for|of)",
            r"technical\s+debt"
        ],
        "search_issues": [
            r"(?:issues|bugs|problems|defects)\s+(?:in|for|of)",
            r"(?:show|find|get|list)\s+(?:issues|bugs|problems)",
            r"what\s+(?:issues|bugs|problems)\s+(?:are\s+there|exist)",
            r"code\s+(?:issues|problems|smells)"
        ],
        "get_quality_gate_status": [
            r"quality\s+gate\s+(?:status|result)",
            r"(?:did|has)\s+(?:the\s+)?(?:project\s+)?(?:pass|fail)",
            r"gate\s+(?:status|result|check)",
            r"quality\s+(?:check|validation|gate)"
        ],
        "search_hotspots": [
            r"(?:security\s+)?(?:hotspots|vulnerabilities|issues)",
            r"security\s+(?:problems|issues|risks)",
            r"(?:find|show|get)\s+(?:security\s+)?(?:hotspots|vulnerabilities)",
            r"(?:is\s+(?:the\s+)?(?:code|project)\s+)?secure"
        ]
    }
    
    # Try to match intent patterns
    for intent, patterns in intent_patterns.items():
        for pattern in patterns:
            if re.search(pattern, message_lower):
                # Extract project key if needed
                project_key = extract_project_key(message)
                if project_key and intent != "list_projects":
                    params["project_key"] = project_key
                
                # Extract additional parameters based on intent
                if intent == "search_issues":
                    # Extract severity filter
                    severity_match = re.search(r"(?:severity|priority)[:\s]+(major|minor|critical|blocker|info)", message_lower)
                    if severity_match:
                        params["severities"] = [severity_match.group(1).upper()]
                    
                    # Extract type filter
                    type_match = re.search(r"(?:type|kind)[:\s]+(bug|vulnerability|code_smell)", message_lower)
                    if type_match:
                        params["types"] = [type_match.group(1).upper()]
                
                elif intent == "get_measures":
                    # Extract specific metrics
                    metric_keywords = {
                        "coverage": ["coverage", "test coverage"],
                        "bugs": ["bugs", "bug count"],
                        "vulnerabilities": ["vulnerabilities", "security"],
                        "code_smells": ["code smells", "maintainability"],
                        "duplicated_lines_density": ["duplication", "duplicated"],
                        "complexity": ["complexity", "cyclomatic"]
                    }
                    
                    requested_metrics = []
                    for metric_key, keywords in metric_keywords.items():
                        if any(keyword in message_lower for keyword in keywords):
                            requested_metrics.append(metric_key)
                    
                    if requested_metrics:
                        params["metric_keys"] = requested_metrics
                
                return intent, params
    
    # Fallback: try to extract project key for generic queries
    project_key = extract_project_key(message)
    if project_key:
        # If we have a project key but no clear intent, default to project details
        return "get_project_details", {"project_key": project_key}
    
    return None, {}


def generate_summary(tool_name: str, result: Any) -> str:
    """Generate a human-readable summary of the tool result."""
    if tool_name == "list_projects":
        if isinstance(result, list):
            return f"Found {len(result)} projects in your SonarQube instance."
        return "Retrieved project list."
    
    elif tool_name == "get_project_details":
        if isinstance(result, dict) and "name" in result:
            return f"Retrieved details for project: {result['name']}"
        return "Retrieved project details."
    
    elif tool_name == "get_measures":
        if isinstance(result, dict) and "measures" in result:
            return f"Retrieved {len(result['measures'])} metrics for the project."
        return "Retrieved project metrics."
    
    elif tool_name == "search_issues":
        if isinstance(result, list):
            return f"Found {len(result)} issues in the project."
        return "Retrieved project issues."
    
    elif tool_name == "get_quality_gate_status":
        if isinstance(result, dict) and "status" in result:
            status = result["status"]
            return f"Quality Gate status: {status}"
        return "Retrieved Quality Gate status."
    
    elif tool_name == "search_hotspots":
        if isinstance(result, list):
            return f"Found {len(result)} security hotspots in the project."
        return "Retrieved security hotspots."
    
    return "Tool executed successfully."


class TestChatParsing:
    """Test cases for chat interface message parsing."""
    
    def test_list_projects_intent(self):
        """Test parsing of list projects messages."""
        test_cases = [
            "List all projects",
            "Show me projects", 
            "What projects do I have",
            "Display all projects"
        ]
        
        for message in test_cases:
            intent, params = parse_user_intent(message)
            assert intent == "list_projects"
            assert params == {}
    
    def test_project_details_intent(self):
        """Test parsing of project details messages."""
        test_cases = [
            ("Show project details for my-project-key", "my-project-key"),
            ("Tell me about test-project", "test-project"),
            ("What is project awesome-app", "awesome-app"),
            ("Project info for backend-service", "backend-service")
        ]
        
        for message, expected_key in test_cases:
            intent, params = parse_user_intent(message)
            assert intent == "get_project_details"
            assert params.get("project_key") == expected_key
    
    def test_metrics_intent(self):
        """Test parsing of metrics messages."""
        test_cases = [
            "Get metrics for test-project",
            "Show code quality for my-app",
            "Coverage for frontend",
            "How good is the code quality"
        ]
        
        for message in test_cases:
            intent, params = parse_user_intent(message)
            assert intent == "get_measures"
    
    def test_issues_intent(self):
        """Test parsing of issues messages."""
        test_cases = [
            "Show issues in my-app",
            "Find bugs in backend",
            "What problems exist in frontend",
            "List code smells"
        ]
        
        for message in test_cases:
            intent, params = parse_user_intent(message)
            assert intent == "search_issues"
    
    def test_quality_gate_intent(self):
        """Test parsing of quality gate messages."""
        test_cases = [
            "Check quality gate status for backend-service",
            "Did the project pass",
            "Quality gate result",
            "Gate status check"
        ]
        
        for message in test_cases:
            intent, params = parse_user_intent(message)
            assert intent == "get_quality_gate_status"
    
    def test_security_intent(self):
        """Test parsing of security messages."""
        test_cases = [
            "Find security vulnerabilities in frontend-app",
            "Show security hotspots",
            "Is the code secure",
            "Security analysis"
        ]
        
        for message in test_cases:
            intent, params = parse_user_intent(message)
            assert intent == "search_hotspots"
    
    def test_no_intent_match(self):
        """Test messages that don't match any intent."""
        test_cases = [
            "What's the weather like?",
            "Hello there",
            "Random message"
        ]
        
        for message in test_cases:
            intent, params = parse_user_intent(message)
            assert intent is None
            assert params == {}
    
    def test_parameter_extraction(self):
        """Test extraction of additional parameters."""
        # Test severity extraction for issues
        intent, params = parse_user_intent("Show issues severity: major in my-project")
        assert intent == "search_issues"
        assert params.get("severities") == ["MAJOR"]
        assert params.get("project_key") == "my-project"
        
        # Test metric extraction for measures
        intent, params = parse_user_intent("Show coverage metrics for test-app")
        assert intent == "get_measures"
        assert "coverage" in params.get("metric_keys", [])
        assert params.get("project_key") == "test-app"


class TestSummaryGeneration:
    """Test cases for summary generation."""
    
    def test_list_projects_summary(self):
        """Test summary generation for list projects."""
        result = [{"key": "proj1", "name": "Project 1"}, {"key": "proj2", "name": "Project 2"}]
        summary = generate_summary("list_projects", result)
        assert "Found 2 projects" in summary
    
    def test_project_details_summary(self):
        """Test summary generation for project details."""
        result = {"name": "My Project", "key": "my-proj"}
        summary = generate_summary("get_project_details", result)
        assert "My Project" in summary
    
    def test_measures_summary(self):
        """Test summary generation for measures."""
        result = {"measures": [{"metric": "coverage", "value": "85.2"}, {"metric": "bugs", "value": "3"}]}
        summary = generate_summary("get_measures", result)
        assert "Retrieved 2 metrics" in summary
    
    def test_issues_summary(self):
        """Test summary generation for issues."""
        result = [{"key": "issue1"}, {"key": "issue2"}, {"key": "issue3"}]
        summary = generate_summary("search_issues", result)
        assert "Found 3 issues" in summary
    
    def test_quality_gate_summary(self):
        """Test summary generation for quality gate."""
        result = {"status": "PASSED"}
        summary = generate_summary("get_quality_gate_status", result)
        assert "PASSED" in summary
    
    def test_hotspots_summary(self):
        """Test summary generation for security hotspots."""
        result = [{"key": "hotspot1"}]
        summary = generate_summary("search_hotspots", result)
        assert "Found 1 security hotspots" in summary


def main():
    """Run the test suite manually."""
    print("🚀 SonarQube MCP Chat Interface Parsing Test")
    print("=" * 50)
    
    # Test message parsing
    test_messages = [
        "List all projects",
        "Show project details for my-project-key", 
        "Get metrics for test-project",
        "Show issues in my-app",
        "Check quality gate status for backend-service",
        "Find security vulnerabilities in frontend-app",
        "What's the weather like?",  # Should not match any intent
        "Show me the quality for project: awesome-app"
    ]
    
    print("\n📝 Testing message parsing:")
    print("-" * 30)
    
    for message in test_messages:
        intent, params = parse_user_intent(message)
        print(f"Message: '{message}'")
        print(f"  → Intent: {intent}")
        print(f"  → Params: {params}")
        print()
    
    # Test summary generation
    print("\n📊 Testing summary generation:")
    print("-" * 30)
    
    test_results = [
        ("list_projects", [{"key": "proj1", "name": "Project 1"}, {"key": "proj2", "name": "Project 2"}]),
        ("get_project_details", {"name": "My Project", "key": "my-proj"}),
        ("get_measures", {"measures": [{"metric": "coverage", "value": "85.2"}, {"metric": "bugs", "value": "3"}]}),
        ("search_issues", [{"key": "issue1"}, {"key": "issue2"}, {"key": "issue3"}]),
        ("get_quality_gate_status", {"status": "PASSED"}),
        ("search_hotspots", [{"key": "hotspot1"}])
    ]
    
    for tool_name, result in test_results:
        summary = generate_summary(tool_name, result)
        print(f"Tool: {tool_name}")
        print(f"  → Summary: {summary}")
        print()
    
    print("✅ Chat interface parsing test completed successfully!")


if __name__ == "__main__":
    main()