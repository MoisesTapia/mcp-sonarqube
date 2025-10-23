"""Tests for Streamlit configuration components."""

import pytest
import tempfile
import json
from pathlib import Path
from unittest.mock import patch, MagicMock

from src.streamlit_app.config.settings import ConfigManager, SonarQubeConfig


class TestSonarQubeConfig:
    """Test SonarQube configuration data class."""
    
    def test_default_config(self):
        """Test default configuration values."""
        config = SonarQubeConfig()
        
        assert config.url == ""
        assert config.token == ""
        assert config.organization is None
        assert config.verify_ssl is True
        assert config.timeout == 30
        assert config.max_retries == 3
    
    def test_config_with_values(self):
        """Test configuration with custom values."""
        config = SonarQubeConfig(
            url="https://sonarqube.example.com",
            token="test_token",
            organization="test_org",
            verify_ssl=False,
            timeout=60,
            max_retries=5
        )
        
        assert config.url == "https://sonarqube.example.com"
        assert config.token == "test_token"
        assert config.organization == "test_org"
        assert config.verify_ssl is False
        assert config.timeout == 60
        assert config.max_retries == 5
    
    def test_to_dict(self):
        """Test conversion to dictionary."""
        config = SonarQubeConfig(
            url="https://sonarqube.example.com",
            token="test_token"
        )
        
        config_dict = config.to_dict()
        
        assert isinstance(config_dict, dict)
        assert config_dict["url"] == "https://sonarqube.example.com"
        assert config_dict["token"] == "test_token"
        assert "organization" in config_dict
        assert "verify_ssl" in config_dict
    
    def test_from_dict(self):
        """Test creation from dictionary."""
        config_dict = {
            "url": "https://sonarqube.example.com",
            "token": "test_token",
            "organization": "test_org",
            "verify_ssl": False,
            "timeout": 45,
            "max_retries": 2
        }
        
        config = SonarQubeConfig.from_dict(config_dict)
        
        assert config.url == "https://sonarqube.example.com"
        assert config.token == "test_token"
        assert config.organization == "test_org"
        assert config.verify_ssl is False
        assert config.timeout == 45
        assert config.max_retries == 2
    
    def test_is_valid_true(self):
        """Test valid configuration."""
        config = SonarQubeConfig(
            url="https://sonarqube.example.com",
            token="test_token"
        )
        
        assert config.is_valid() is True
    
    def test_is_valid_false_no_url(self):
        """Test invalid configuration - no URL."""
        config = SonarQubeConfig(token="test_token")
        
        assert config.is_valid() is False
    
    def test_is_valid_false_no_token(self):
        """Test invalid configuration - no token."""
        config = SonarQubeConfig(url="https://sonarqube.example.com")
        
        assert config.is_valid() is False
    
    def test_is_valid_false_empty_values(self):
        """Test invalid configuration - empty values."""
        config = SonarQubeConfig(url="", token="")
        
        assert config.is_valid() is False


class TestConfigManager:
    """Test configuration manager."""
    
    def setup_method(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.config_file = Path(self.temp_dir) / "config.json"
    
    def test_init_creates_config_directory(self):
        """Test that initialization creates config directory."""
        with patch("pathlib.Path.home") as mock_home:
            mock_home.return_value = Path(self.temp_dir)
            
            config_manager = ConfigManager()
            
            expected_dir = Path(self.temp_dir) / ".sonarqube_mcp"
            assert expected_dir.exists()
    
    def test_save_and_load_config(self):
        """Test saving and loading configuration."""
        with patch("pathlib.Path.home") as mock_home:
            mock_home.return_value = Path(self.temp_dir)
            
            config_manager = ConfigManager()
            
            # Create test configuration
            test_config = SonarQubeConfig(
                url="https://sonarqube.example.com",
                token="test_token",
                organization="test_org"
            )
            
            # Save configuration
            result = config_manager.save_config(test_config)
            assert result is True
            
            # Load configuration
            loaded_config = config_manager.get_config()
            assert loaded_config.url == "https://sonarqube.example.com"
            assert loaded_config.token == "test_token"
            assert loaded_config.organization == "test_org"
    
    def test_load_config_from_env_variables(self):
        """Test loading configuration from environment variables."""
        with patch("pathlib.Path.home") as mock_home, \
             patch.dict("os.environ", {
                 "SONARQUBE_URL": "https://env.sonarqube.com",
                 "SONARQUBE_TOKEN": "env_token",
                 "SONARQUBE_ORGANIZATION": "env_org",
                 "SONARQUBE_VERIFY_SSL": "false",
                 "SONARQUBE_TIMEOUT": "45",
                 "SONARQUBE_MAX_RETRIES": "2"
             }):
            mock_home.return_value = Path(self.temp_dir)
            
            config_manager = ConfigManager()
            config = config_manager.get_config()
            
            assert config.url == "https://env.sonarqube.com"
            assert config.token == "env_token"
            assert config.organization == "env_org"
            assert config.verify_ssl is False
            assert config.timeout == 45
            assert config.max_retries == 2
    
    def test_env_variables_override_file_config(self):
        """Test that environment variables override file configuration."""
        with patch("pathlib.Path.home") as mock_home, \
             patch.dict("os.environ", {
                 "SONARQUBE_URL": "https://env.sonarqube.com",
                 "SONARQUBE_TOKEN": "env_token"
             }):
            mock_home.return_value = Path(self.temp_dir)
            
            config_manager = ConfigManager()
            
            # Save file configuration
            file_config = SonarQubeConfig(
                url="https://file.sonarqube.com",
                token="file_token"
            )
            config_manager.save_config(file_config)
            
            # Create new manager to reload config
            config_manager = ConfigManager()
            config = config_manager.get_config()
            
            # Environment variables should override file config
            assert config.url == "https://env.sonarqube.com"
            assert config.token == "env_token"
    
    def test_is_configured_true(self):
        """Test is_configured returns True for valid config."""
        with patch("pathlib.Path.home") as mock_home:
            mock_home.return_value = Path(self.temp_dir)
            
            config_manager = ConfigManager()
            test_config = SonarQubeConfig(
                url="https://sonarqube.example.com",
                token="test_token"
            )
            config_manager.save_config(test_config)
            
            assert config_manager.is_configured() is True
    
    def test_is_configured_false(self):
        """Test is_configured returns False for invalid config."""
        with patch("pathlib.Path.home") as mock_home:
            mock_home.return_value = Path(self.temp_dir)
            
            config_manager = ConfigManager()
            
            assert config_manager.is_configured() is False
    
    def test_update_config(self):
        """Test updating configuration."""
        with patch("pathlib.Path.home") as mock_home:
            mock_home.return_value = Path(self.temp_dir)
            
            config_manager = ConfigManager()
            
            # Save initial config
            initial_config = SonarQubeConfig(
                url="https://sonarqube.example.com",
                token="test_token"
            )
            config_manager.save_config(initial_config)
            
            # Update config
            result = config_manager.update_config(
                organization="new_org",
                timeout=60
            )
            
            assert result is True
            
            # Verify update
            updated_config = config_manager.get_config()
            assert updated_config.url == "https://sonarqube.example.com"  # Unchanged
            assert updated_config.token == "test_token"  # Unchanged
            assert updated_config.organization == "new_org"  # Updated
            assert updated_config.timeout == 60  # Updated
    
    def test_clear_config(self):
        """Test clearing configuration."""
        with patch("pathlib.Path.home") as mock_home:
            mock_home.return_value = Path(self.temp_dir)
            
            config_manager = ConfigManager()
            
            # Save config
            test_config = SonarQubeConfig(
                url="https://sonarqube.example.com",
                token="test_token"
            )
            config_manager.save_config(test_config)
            
            # Clear config
            result = config_manager.clear_config()
            assert result is True
            
            # Verify config is cleared
            config = config_manager.get_config()
            assert config.url == ""
            assert config.token == ""
    
    def test_get_connection_params(self):
        """Test getting connection parameters."""
        with patch("pathlib.Path.home") as mock_home:
            mock_home.return_value = Path(self.temp_dir)
            
            config_manager = ConfigManager()
            test_config = SonarQubeConfig(
                url="https://sonarqube.example.com",
                token="test_token",
                organization="test_org",
                verify_ssl=False,
                timeout=45,
                max_retries=2
            )
            config_manager.save_config(test_config)
            
            params = config_manager.get_connection_params()
            
            expected_params = {
                "base_url": "https://sonarqube.example.com",
                "token": "test_token",
                "organization": "test_org",
                "timeout": 45,
                "max_retries": 2,
                "verify_ssl": False,
            }
            
            assert params == expected_params
    
    def test_mask_sensitive_data(self):
        """Test masking sensitive data."""
        with patch("pathlib.Path.home") as mock_home:
            mock_home.return_value = Path(self.temp_dir)
            
            config_manager = ConfigManager()
            test_config = SonarQubeConfig(
                url="https://sonarqube.example.com",
                token="very_long_secret_token_12345"
            )
            config_manager.save_config(test_config)
            
            masked_config = config_manager.mask_sensitive_data()
            
            assert masked_config["url"] == "https://sonarqube.example.com"
            assert masked_config["token"] == "very...2345"
    
    def test_mask_sensitive_data_short_token(self):
        """Test masking short token."""
        with patch("pathlib.Path.home") as mock_home:
            mock_home.return_value = Path(self.temp_dir)
            
            config_manager = ConfigManager()
            test_config = SonarQubeConfig(
                url="https://sonarqube.example.com",
                token="short"
            )
            config_manager.save_config(test_config)
            
            masked_config = config_manager.mask_sensitive_data()
            
            assert masked_config["token"] == "***"