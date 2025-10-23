"""Tests for advanced visualization components."""

import pytest
import pandas as pd
from datetime import datetime
from unittest.mock import Mock, patch

from src.streamlit_app.components.visualization import AdvancedVisualization
from src.streamlit_app.components.reporting import ReportGenerator, DataExporter


class TestAdvancedVisualization:
    """Test cases for AdvancedVisualization class."""
    
    def test_create_custom_chart_with_valid_data(self):
        """Test creating a custom chart with valid data."""
        # Arrange
        data = [
            {'name': 'Project A', 'bugs': 5, 'coverage': 80.5},
            {'name': 'Project B', 'bugs': 3, 'coverage': 85.2},
            {'name': 'Project C', 'bugs': 8, 'coverage': 75.1}
        ]
        
        # Act
        fig = AdvancedVisualization.create_custom_chart(
            data=data,
            chart_type='bar',
            x_column='name',
            y_column='bugs',
            title='Bugs by Project'
        )
        
        # Assert
        assert fig is not None
        assert fig.layout.title.text == 'Bugs by Project'
    
    def test_create_custom_chart_with_empty_data(self):
        """Test creating a custom chart with empty data."""
        # Arrange
        data = []
        
        # Act
        fig = AdvancedVisualization.create_custom_chart(
            data=data,
            chart_type='bar',
            x_column='name',
            y_column='bugs',
            title='Empty Chart'
        )
        
        # Assert
        assert fig is not None
        # Should contain "No data available" annotation
        assert len(fig.layout.annotations) > 0
    
    def test_create_comparison_matrix_with_valid_data(self):
        """Test creating a comparison matrix with valid data."""
        # Arrange
        projects_data = [
            {'name': 'Project A', 'bugs': 5, 'coverage': 80.5, 'vulnerabilities': 2},
            {'name': 'Project B', 'bugs': 3, 'coverage': 85.2, 'vulnerabilities': 1},
            {'name': 'Project C', 'bugs': 8, 'coverage': 75.1, 'vulnerabilities': 4}
        ]
        metrics = ['bugs', 'coverage', 'vulnerabilities']
        
        # Act
        fig = AdvancedVisualization.create_comparison_matrix(projects_data, metrics)
        
        # Assert
        assert fig is not None
        assert 'Comparison Matrix' in fig.layout.title.text
    
    def test_create_comparison_matrix_with_empty_data(self):
        """Test creating a comparison matrix with empty data."""
        # Arrange
        projects_data = []
        metrics = ['bugs', 'coverage']
        
        # Act
        fig = AdvancedVisualization.create_comparison_matrix(projects_data, metrics)
        
        # Assert
        assert fig is not None
        assert len(fig.layout.annotations) > 0
    
    def test_generate_historical_data(self):
        """Test generating historical data for trends."""
        # Arrange
        df = pd.DataFrame([
            {'name': 'Project A', 'coverage': 80.5, 'bugs': 5},
            {'name': 'Project B', 'coverage': 85.2, 'bugs': 3}
        ])
        
        # Act
        historical_data = AdvancedVisualization._generate_historical_data(df)
        
        # Assert
        assert historical_data is not None
        assert isinstance(historical_data, pd.DataFrame)
        assert len(historical_data) > 0
        assert 'project' in historical_data.columns
        assert 'date' in historical_data.columns
        assert 'metric' in historical_data.columns
        assert 'value' in historical_data.columns


class TestReportGenerator:
    """Test cases for ReportGenerator class."""
    
    def test_generate_summary_with_valid_data(self):
        """Test generating report summary with valid data."""
        # Arrange
        generator = ReportGenerator()
        projects_data = [
            {'name': 'Project A', 'quality_gate_status': 'OK', 'bugs': 5, 'coverage': 80.5},
            {'name': 'Project B', 'quality_gate_status': 'ERROR', 'bugs': 3, 'coverage': 85.2},
            {'name': 'Project C', 'quality_gate_status': 'OK', 'bugs': 8, 'coverage': 75.1}
        ]
        metrics = ['bugs', 'coverage']
        
        # Act
        summary = generator._generate_summary(projects_data, metrics)
        
        # Assert
        assert summary['total_projects'] == 3
        assert 'quality_gates' in summary
        assert summary['quality_gates']['passed'] == 2
        assert summary['quality_gates']['failed'] == 1
        assert 'bugs_total' in summary
        assert 'coverage_average' in summary
    
    def test_generate_summary_with_empty_data(self):
        """Test generating report summary with empty data."""
        # Arrange
        generator = ReportGenerator()
        projects_data = []
        metrics = ['bugs', 'coverage']
        
        # Act
        summary = generator._generate_summary(projects_data, metrics)
        
        # Assert
        assert summary == {}
    
    def test_generate_section_overview(self):
        """Test generating overview section."""
        # Arrange
        generator = ReportGenerator()
        projects_data = [
            {'name': 'Project A', 'bugs': 5, 'coverage': 80.5},
            {'name': 'Project B', 'bugs': 3, 'coverage': 85.2}
        ]
        metrics = ['bugs', 'coverage']
        
        # Act
        section = generator._generate_section('overview', projects_data, metrics)
        
        # Assert
        assert section['title'] == 'Overview'
        assert 'content' in section
        assert section['content']['total_projects'] == 2
        assert 'key_metrics' in section['content']
    
    def test_generate_section_quality_gates(self):
        """Test generating quality gates section."""
        # Arrange
        generator = ReportGenerator()
        projects_data = [
            {'name': 'Project A', 'quality_gate_status': 'OK'},
            {'name': 'Project B', 'quality_gate_status': 'ERROR'},
            {'name': 'Project C', 'quality_gate_status': 'OK'}
        ]
        metrics = []
        
        # Act
        section = generator._generate_section('quality_gates', projects_data, metrics)
        
        # Assert
        assert section['title'] == 'Quality Gates'
        assert 'content' in section
        assert 'status_distribution' in section['content']
        assert section['content']['status_distribution']['OK'] == 2
        assert section['content']['status_distribution']['ERROR'] == 1


class TestDataExporter:
    """Test cases for DataExporter class."""
    
    def test_export_to_csv(self):
        """Test exporting data to CSV format."""
        # Arrange
        data = [
            {'name': 'Project A', 'bugs': 5, 'coverage': 80.5},
            {'name': 'Project B', 'bugs': 3, 'coverage': 85.2}
        ]
        
        # Act
        csv_data = DataExporter.export_to_csv(data)
        
        # Assert
        assert isinstance(csv_data, bytes)
        csv_string = csv_data.decode('utf-8')
        assert 'name,bugs,coverage' in csv_string
        assert 'Project A,5,80.5' in csv_string
        assert 'Project B,3,85.2' in csv_string
    
    def test_export_to_json(self):
        """Test exporting data to JSON format."""
        # Arrange
        data = [
            {'name': 'Project A', 'bugs': 5, 'coverage': 80.5},
            {'name': 'Project B', 'bugs': 3, 'coverage': 85.2}
        ]
        
        # Act
        json_data = DataExporter.export_to_json(data)
        
        # Assert
        assert isinstance(json_data, bytes)
        json_string = json_data.decode('utf-8')
        assert '"name": "Project A"' in json_string
        assert '"bugs": 5' in json_string
        assert '"coverage": 80.5' in json_string
    
    def test_export_to_csv_with_dataframe(self):
        """Test exporting DataFrame to CSV format."""
        # Arrange
        df = pd.DataFrame([
            {'name': 'Project A', 'bugs': 5, 'coverage': 80.5},
            {'name': 'Project B', 'bugs': 3, 'coverage': 85.2}
        ])
        
        # Act
        csv_data = DataExporter.export_to_csv(df)
        
        # Assert
        assert isinstance(csv_data, bytes)
        csv_string = csv_data.decode('utf-8')
        assert 'name,bugs,coverage' in csv_string
    
    def test_export_to_json_with_dataframe(self):
        """Test exporting DataFrame to JSON format."""
        # Arrange
        df = pd.DataFrame([
            {'name': 'Project A', 'bugs': 5, 'coverage': 80.5},
            {'name': 'Project B', 'bugs': 3, 'coverage': 85.2}
        ])
        
        # Act
        json_data = DataExporter.export_to_json(df)
        
        # Assert
        assert isinstance(json_data, bytes)
        json_string = json_data.decode('utf-8')
        assert '"name": "Project A"' in json_string
    
    def test_create_download_link(self):
        """Test creating download link."""
        # Arrange
        data = b"test,data\n1,2\n"
        filename = "test.csv"
        mime_type = "text/csv"
        
        # Act
        link = DataExporter.create_download_link(data, filename, mime_type)
        
        # Assert
        assert isinstance(link, str)
        assert 'href="data:text/csv;base64,' in link
        assert 'download="test.csv"' in link
        assert 'Download test.csv' in link


if __name__ == '__main__':
    pytest.main([__file__])