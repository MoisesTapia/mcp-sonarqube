"""Tests for the interactive chat interface."""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime
import json

from src.streamlit_app.components.chat_interface import ChatInterface
from src.streamlit_app.services.mcp_client import MCPClient, MCPToolResult


class TestChatInterface:
    """Test chat interface functionality."""
    
    @pytest.fixture
    def chat_interface(self):
        """Create a chat interface instance."""
        return ChatInterface()
    
    @pytest.fixture
    def mock_mcp_client(self):
        """Mock MCP client."""
        client = Mock(spec=MCPClient)
        client.check_health = AsyncMock(return_value=True)
        client.get_available_tools.return_value = [
            {"name": "list_projects", "description": "List all projects"},
            {"name": "get_measures", "description": "Get project metrics"}
        ]
        client.call_tool = AsyncMock()
        return client
    
    def test_parse_user_intent_projects(self, chat_interface):
        """Test parsing project-related intents."""
        # Test list projects
        intent, params = chat_interface._parse_user_intent("List all projects")
        assert intent == "list_projects"
        assert params == {}
        
        # Test project details
        intent, params = chat_interface._parse_user_intent("Show project details for my-app")
        assert intent == "get_project_details"
        assert params["project_key"] == "my-app"
        
        # Test alternative phrasing
        intent, params = chat_interface._parse_user_intent("Tell me about project: backend-service")
        assert intent == "get_project_details"
        assert params["project_key"] == "backend-service"
    
    def test_parse_user_intent_metrics(self, chat_interface):
        """Test parsing metrics-related intents."""
        # Test basic metrics request
        intent, params = chat_interface._parse_user_intent("Get metrics for test-project")
        assert intent == "get_measures"
        assert params["project_key"] == "test-project"
        
        # Test quality request
        intent, params = chat_interface._parse_user_intent("How is the code quality of frontend-app?")
        assert intent == "get_measures"
        assert params["project_key"] == "frontend-app"
        
        # Test specific metrics
        intent, params = chat_interface._parse_user_intent("Show coverage for my-project")
        assert intent == "get_measures"
        assert params["project_key"] == "my-project"
        assert "coverage" in params.get("metric_keys", [])
    
    def test_parse_user_intent_issues(self, chat_interface):
        """Test parsing issue-related intents."""
        # Test basic issues request
        intent, params = chat_interface._parse_user_intent("Show issues in my-app")
        assert intent == "search_issues"
        assert params["project_key"] == "my-app"
        
        # Test with severity filter
        intent, params = chat_interface._parse_user_intent("Find critical issues in backend")
        assert intent == "search_issues"
        assert params["project_key"] == "backend"
        
        # Test bugs specifically
        intent, params = chat_interface._parse_user_intent("What bugs are there in frontend?")
        assert intent == "search_issues"
        assert params["project_key"] == "frontend"
    
    def test_parse_user_intent_quality_gate(self, chat_interface):
        """Test parsing Quality Gate intents."""
        # Test quality gate status
        intent, params = chat_interface._parse_user_intent("Check quality gate for my-project")
        assert intent == "get_quality_gate_status"
        assert params["project_key"] == "my-project"
        
        # Test alternative phrasing
        intent, params = chat_interface._parse_user_intent("Did the project backend-service pass?")
        assert intent == "get_quality_gate_status"
        assert params["project_key"] == "backend-service"
    
    def test_parse_user_intent_security(self, chat_interface):
        """Test parsing security-related intents."""
        # Test security hotspots
        intent, params = chat_interface._parse_user_intent("Find security vulnerabilities in my-app")
        assert intent == "search_hotspots"
        assert params["project_key"] == "my-app"
        
        # Test alternative phrasing
        intent, params = chat_interface._parse_user_intent("Is the code secure in frontend?")
        assert intent == "search_hotspots"
        assert params["project_key"] == "frontend"
    
    def test_parse_user_intent_unknown(self, chat_interface):
        """Test parsing unknown intents."""
        intent, params = chat_interface._parse_user_intent("What's the weather like?")
        assert intent is None
        assert params == {}
        
        # Test with project key but unclear intent
        intent, params = chat_interface._parse_user_intent("Something about my-project")
        assert intent == "get_project_details"
        assert params["project_key"] == "my-project"
    
    @pytest.mark.asyncio
    async def test_process_user_message_success(self, chat_interface, mock_mcp_client):
        """Test successful message processing."""
        chat_interface.mcp_client = mock_mcp_client
        
        # Mock successful tool call
        mock_result = MCPToolResult(
            success=True,
            data=[{"key": "test-project", "name": "Test Project"}]
        )
        mock_mcp_client.call_tool.return_value = mock_result
        
        response = await chat_interface._process_user_message("List all projects")
        
        assert response["tool_name"] == "list_projects"
        assert response["tool_result"] == mock_result.data
        assert "summary" in response
        mock_mcp_client.call_tool.assert_called_once_with("list_projects", {})
    
    @pytest.mark.asyncio
    async def test_process_user_message_error(self, chat_interface, mock_mcp_client):
        """Test message processing with error."""
        chat_interface.mcp_client = mock_mcp_client
        
        # Mock failed tool call
        mock_result = MCPToolResult(
            success=False,
            error="Connection failed"
        )
        mock_mcp_client.call_tool.return_value = mock_result
        
        response = await chat_interface._process_user_message("List all projects")
        
        assert "error" in response
        assert response["error"] == "Connection failed"
    
    @pytest.mark.asyncio
    async def test_process_user_message_unknown_intent(self, chat_interface, mock_mcp_client):
        """Test message processing with unknown intent."""
        chat_interface.mcp_client = mock_mcp_client
        
        response = await chat_interface._process_user_message("What's the weather?")
        
        assert "error" in response
        assert "couldn't understand" in response["error"].lower()
        mock_mcp_client.call_tool.assert_not_called()
    
    def test_generate_summary(self, chat_interface):
        """Test summary generation for different tool results."""
        # Test list_projects
        result = [{"key": "proj1"}, {"key": "proj2"}]
        summary = chat_interface._generate_summary("list_projects", result)
        assert "2 projects" in summary
        
        # Test get_project_details
        result = {"name": "My Project", "key": "my-proj"}
        summary = chat_interface._generate_summary("get_project_details", result)
        assert "My Project" in summary
        
        # Test get_measures
        result = {"measures": [{"metric": "coverage"}, {"metric": "bugs"}]}
        summary = chat_interface._generate_summary("get_measures", result)
        assert "2 metrics" in summary
        
        # Test search_issues
        result = [{"key": "issue1"}, {"key": "issue2"}, {"key": "issue3"}]
        summary = chat_interface._generate_summary("search_issues", result)
        assert "3 issues" in summary
        
        # Test get_quality_gate_status
        result = {"status": "PASSED"}
        summary = chat_interface._generate_summary("get_quality_gate_status", result)
        assert "PASSED" in summary
        
        # Test search_hotspots
        result = [{"key": "hotspot1"}]
        summary = chat_interface._generate_summary("search_hotspots", result)
        assert "1 security hotspots" in summary
    
    @patch('streamlit.session_state', new_callable=dict)
    def test_initialize_session_state(self, mock_session_state, chat_interface):
        """Test session state initialization."""
        chat_interface.initialize_session_state()
        
        assert "chat_messages" in mock_session_state
        assert "mcp_connected" in mock_session_state
        assert "available_tools" in mock_session_state
        assert "chat_session_id" in mock_session_state
        assert "conversation_started" in mock_session_state
        assert "recent_projects" in mock_session_state
        
        assert mock_session_state["chat_messages"] == []
        assert mock_session_state["mcp_connected"] is False
        assert mock_session_state["available_tools"] == []
    
    def test_get_recent_projects_from_session(self, chat_interface):
        """Test getting recent projects from session state."""
        with patch('streamlit.session_state', {"recent_projects": [{"key": "test", "name": "Test"}]}):
            projects = chat_interface._get_recent_projects()
            assert len(projects) == 1
            assert projects[0]["key"] == "test"
    
    def test_get_recent_projects_from_history(self, chat_interface):
        """Test getting recent projects from tool history."""
        mock_client = Mock()
        mock_client.get_tool_history.return_value = [
            {
                "tool_name": "list_projects",
                "success": True,
                "result": [{"key": "proj1", "name": "Project 1"}]
            }
        ]
        chat_interface.mcp_client = mock_client
        
        with patch('streamlit.session_state', {}):
            projects = chat_interface._get_recent_projects()
            assert len(projects) == 1
            assert projects[0]["key"] == "proj1"
    
    def test_generate_markdown_export(self, chat_interface):
        """Test Markdown export generation."""
        messages = [
            {
                "role": "user",
                "content": "List projects",
                "timestamp": datetime.now()
            },
            {
                "role": "assistant", 
                "content": {"tool_result": [{"key": "test"}]},
                "timestamp": datetime.now()
            }
        ]
        
        with patch('streamlit.session_state', {"chat_messages": messages}):
            markdown = chat_interface._generate_markdown_export()
            
            assert "# SonarQube Chat Conversation" in markdown
            assert "Message 1 - User" in markdown
            assert "Message 2 - Assistant" in markdown
            assert "List projects" in markdown
    
    def test_generate_csv_export(self, chat_interface):
        """Test CSV export generation."""
        messages = [
            {
                "role": "user",
                "content": "List projects",
                "timestamp": datetime.now()
            },
            {
                "role": "assistant",
                "content": {"tool_result": [{"key": "test"}]},
                "timestamp": datetime.now()
            }
        ]
        
        with patch('streamlit.session_state', {"chat_messages": messages}):
            csv_content = chat_interface._generate_csv_export()
            
            lines = csv_content.strip().split('\n')
            assert len(lines) == 3  # Header + 2 data rows
            assert "Message_ID,Role,Content,Timestamp,Content_Length,Has_Tool_Result" in lines[0]
            assert "user" in lines[1]
            assert "assistant" in lines[2]
            assert "Yes" in lines[2]  # Assistant message has tool result


class TestChatInterfaceRendering:
    """Test chat interface rendering components."""
    
    @pytest.fixture
    def chat_interface(self):
        """Create a chat interface instance."""
        return ChatInterface()
    
    def test_render_projects_list(self, chat_interface):
        """Test rendering projects list."""
        projects = [
            {"key": "proj1", "name": "Project 1", "visibility": "public"},
            {"key": "proj2", "name": "Project 2", "visibility": "private"}
        ]
        
        with patch('streamlit.metric') as mock_metric, \
             patch('streamlit.dataframe') as mock_dataframe, \
             patch('plotly.express.pie') as mock_pie:
            
            chat_interface._render_projects_list(projects)
            
            # Should show metrics
            assert mock_metric.call_count == 3  # Total, Public, Private
            mock_dataframe.assert_called_once()
            mock_pie.assert_called_once()
    
    def test_render_project_details(self, chat_interface):
        """Test rendering project details."""
        project = {
            "key": "test-project",
            "name": "Test Project", 
            "visibility": "public",
            "lastAnalysisDate": "2025-01-01T10:00:00Z"
        }
        
        with patch('streamlit.metric') as mock_metric, \
             patch('streamlit.info') as mock_info, \
             patch('streamlit.json') as mock_json:
            
            chat_interface._render_project_details(project)
            
            assert mock_metric.call_count == 3  # Key, Name, Visibility
            mock_info.assert_called_once()  # Last analysis date
            mock_json.assert_called_once()  # Full details
    
    def test_render_metrics_visualization(self, chat_interface):
        """Test rendering metrics with visualizations."""
        metrics_result = {
            "measures": [
                {"metric": "coverage", "value": "85.5", "bestValue": False},
                {"metric": "bugs", "value": "3", "bestValue": False},
                {"metric": "reliability_rating", "value": "2.0", "bestValue": False}
            ]
        }
        
        with patch('streamlit.metric') as mock_metric, \
             patch('streamlit.plotly_chart') as mock_chart, \
             patch('streamlit.dataframe') as mock_dataframe:
            
            chat_interface._render_metrics_visualization(metrics_result)
            
            # Should show key metrics
            assert mock_metric.call_count >= 3
            mock_chart.assert_called()  # Rating visualization
            mock_dataframe.assert_called()  # All metrics table
    
    def test_render_issues_analysis(self, chat_interface):
        """Test rendering issues analysis."""
        issues = [
            {"key": "ISSUE-1", "severity": "CRITICAL", "type": "BUG", "status": "OPEN"},
            {"key": "ISSUE-2", "severity": "MAJOR", "type": "VULNERABILITY", "status": "CONFIRMED"}
        ]
        
        with patch('streamlit.metric') as mock_metric, \
             patch('streamlit.plotly_chart') as mock_chart, \
             patch('streamlit.dataframe') as mock_dataframe:
            
            chat_interface._render_issues_analysis(issues)
            
            assert mock_metric.call_count == 4  # Total, Critical, Bugs, Open
            mock_chart.assert_called()  # Severity distribution
            mock_dataframe.assert_called()  # Issues table
    
    def test_render_quality_gate_status(self, chat_interface):
        """Test rendering Quality Gate status."""
        qg_result = {
            "status": "FAILED",
            "conditions": [
                {
                    "status": "ERROR",
                    "metricKey": "coverage",
                    "actualValue": "75.0",
                    "errorThreshold": "80.0"
                },
                {
                    "status": "OK",
                    "metricKey": "bugs",
                    "actualValue": "0",
                    "errorThreshold": "5"
                }
            ]
        }
        
        with patch('streamlit.error') as mock_error, \
             patch('streamlit.success') as mock_success, \
             patch('streamlit.dataframe') as mock_dataframe:
            
            chat_interface._render_quality_gate_status(qg_result)
            
            mock_error.assert_called()  # Failed status and failed conditions
            mock_success.assert_called()  # Passed conditions
            assert mock_dataframe.call_count == 2  # Failed and passed conditions tables
    
    def test_render_security_analysis(self, chat_interface):
        """Test rendering security analysis."""
        hotspots = [
            {
                "key": "HOTSPOT-1",
                "vulnerabilityProbability": "HIGH",
                "status": "TO_REVIEW",
                "securityCategory": "sql-injection"
            },
            {
                "key": "HOTSPOT-2", 
                "vulnerabilityProbability": "MEDIUM",
                "status": "REVIEWED",
                "securityCategory": "xss"
            }
        ]
        
        with patch('streamlit.metric') as mock_metric, \
             patch('streamlit.plotly_chart') as mock_chart, \
             patch('streamlit.dataframe') as mock_dataframe:
            
            chat_interface._render_security_analysis(hotspots)
            
            assert mock_metric.call_count == 3  # Total, High Risk, To Review
            assert mock_chart.call_count == 2  # Risk and category charts
            mock_dataframe.assert_called()  # Hotspots table


if __name__ == "__main__":
    pytest.main([__file__])