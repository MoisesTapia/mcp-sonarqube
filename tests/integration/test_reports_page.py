"""Integration tests for the reports page."""

import pytest
from unittest.mock import Mock, patch, MagicMock
import pandas as pd

# Mock streamlit before importing the module
with patch.dict('sys.modules', {'streamlit': MagicMock()}):
    from src.streamlit_app.pages.reports import (
        render_advanced_visualizations,
        render_custom_chart_builder,
        render_comparison_matrix,
        render_trend_analysis
    )


class TestReportsPageIntegration:
    """Integration tests for reports page functionality."""
    
    @patch('src.streamlit_app.pages.reports.st')
    def test_render_advanced_visualizations_with_no_projects(self, mock_st):
        """Test rendering advanced visualizations with no projects."""
        # Arrange
        mock_service = Mock()
        mock_service.get_projects.return_value = []
        
        # Act
        render_advanced_visualizations(mock_service)
        
        # Assert
        mock_st.info.assert_called_with("No projects found.")
    
    @patch('src.streamlit_app.pages.reports.st')
    def test_render_advanced_visualizations_with_projects(self, mock_st):
        """Test rendering advanced visualizations with projects."""
        # Arrange
        mock_service = Mock()
        mock_service.get_projects.return_value = [
            {'key': 'project1', 'name': 'Project 1', 'lastAnalysisDate': '2023-01-01'},
            {'key': 'project2', 'name': 'Project 2', 'lastAnalysisDate': '2023-01-02'}
        ]
        mock_service.get_project_measures.return_value = {
            'bugs': '5', 'vulnerabilities': '2', 'coverage': '80.5'
        }
        mock_service.get_quality_gate_status.return_value = {'status': 'OK'}
        
        # Mock streamlit components
        mock_st.spinner.return_value.__enter__ = Mock()
        mock_st.spinner.return_value.__exit__ = Mock()
        mock_st.selectbox.return_value = 'metrics_dashboard'
        mock_st.columns.return_value = [Mock(), Mock(), Mock()]
        mock_st.button.return_value = False
        
        # Act
        render_advanced_visualizations(mock_service)
        
        # Assert
        mock_service.get_projects.assert_called_once()
        assert mock_service.get_project_measures.call_count >= 1
        assert mock_service.get_quality_gate_status.call_count >= 1
    
    @patch('src.streamlit_app.pages.reports.st')
    def test_render_custom_chart_builder_with_valid_data(self, mock_st):
        """Test rendering custom chart builder with valid data."""
        # Arrange
        projects_data = [
            {'name': 'Project A', 'bugs': 5, 'coverage': 80.5},
            {'name': 'Project B', 'bugs': 3, 'coverage': 85.2}
        ]
        chart_type = 'bar'
        
        # Mock streamlit components
        mock_st.columns.return_value = [Mock(), Mock(), Mock()]
        mock_st.selectbox.side_effect = ['name', 'bugs', None]  # x_column, y_column, color_column
        mock_st.expander.return_value.__enter__ = Mock()
        mock_st.expander.return_value.__exit__ = Mock()
        mock_st.text_input.return_value = 'Test Chart'
        mock_st.slider.return_value = 500
        mock_st.button.return_value = False
        mock_st.plotly_chart = Mock()
        
        # Act
        render_custom_chart_builder(projects_data, chart_type)
        
        # Assert
        mock_st.plotly_chart.assert_called_once()
    
    @patch('src.streamlit_app.pages.reports.st')
    def test_render_comparison_matrix_with_valid_data(self, mock_st):
        """Test rendering comparison matrix with valid data."""
        # Arrange
        projects_data = [
            {'name': 'Project A', 'bugs': 5, 'coverage': 80.5, 'vulnerabilities': 2},
            {'name': 'Project B', 'bugs': 3, 'coverage': 85.2, 'vulnerabilities': 1}
        ]
        
        # Mock streamlit components
        mock_st.multiselect.side_effect = [
            ['bugs', 'coverage'],  # selected_metrics
            [0, 1]  # selected_projects
        ]
        mock_st.button.return_value = False
        mock_st.plotly_chart = Mock()
        
        # Act
        render_comparison_matrix(projects_data)
        
        # Assert
        mock_st.plotly_chart.assert_called_once()
    
    @patch('src.streamlit_app.pages.reports.st')
    def test_render_comparison_matrix_with_no_data(self, mock_st):
        """Test rendering comparison matrix with no data."""
        # Arrange
        projects_data = []
        
        # Act
        render_comparison_matrix(projects_data)
        
        # Assert
        mock_st.warning.assert_called_with("No data available for comparison.")
    
    @patch('src.streamlit_app.pages.reports.st')
    def test_render_trend_analysis_with_valid_data(self, mock_st):
        """Test rendering trend analysis with valid data."""
        # Arrange
        projects_data = [
            {'name': 'Project A', 'coverage': 80.5, 'bugs': 5},
            {'name': 'Project B', 'coverage': 85.2, 'bugs': 3}
        ]
        
        # Mock streamlit components
        mock_st.columns.return_value = [Mock(), Mock(), Mock()]
        mock_st.selectbox.side_effect = ['coverage', '30d']  # trend_metric, time_period
        mock_st.multiselect.return_value = [0, 1]  # trend_projects
        mock_st.plotly_chart = Mock()
        mock_st.button.return_value = False
        
        # Act
        render_trend_analysis(projects_data)
        
        # Assert
        mock_st.plotly_chart.assert_called_once()
    
    @patch('src.streamlit_app.pages.reports.st')
    def test_render_trend_analysis_with_no_projects_selected(self, mock_st):
        """Test rendering trend analysis with no projects selected."""
        # Arrange
        projects_data = [
            {'name': 'Project A', 'coverage': 80.5, 'bugs': 5}
        ]
        
        # Mock streamlit components
        mock_st.columns.return_value = [Mock(), Mock(), Mock()]
        mock_st.selectbox.side_effect = ['coverage', '30d']
        mock_st.multiselect.return_value = []  # No projects selected
        
        # Act
        render_trend_analysis(projects_data)
        
        # Assert
        mock_st.info.assert_called_with("Please select projects and ensure the selected metric is available.")


if __name__ == '__main__':
    pytest.main([__file__])