"""Configuration management for SonarQube connection."""

import os
from typing import Dict, Any, Optional
from dataclasses import dataclass, asdict
import json
import streamlit as st
from pathlib import Path


@dataclass
class SonarQubeConfig:
    """SonarQube configuration data class."""
    
    url: str = ""
    token: str = ""
    organization: Optional[str] = None
    verify_ssl: bool = True
    timeout: int = 30
    max_retries: int = 3
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SonarQubeConfig":
        """Create from dictionary."""
        return cls(**data)
    
    def is_valid(self) -> bool:
        """Check if configuration is valid."""
        return bool(self.url and self.token)


class ConfigManager:
    """Manages SonarQube configuration and persistence."""
    
    def __init__(self):
        """Initialize configuration manager."""
        # Use /app/data directory which exists and has proper permissions
        config_dir = Path("/app/data") / ".sonarqube_mcp"
        config_dir.mkdir(parents=True, exist_ok=True)
        self.config_file = config_dir / "config.json"
        self._config: Optional[SonarQubeConfig] = None
        self._load_config()
    
    def _load_config(self) -> None:
        """Load configuration from file and environment variables."""
        # Start with default config
        config_data = {}
        
        # Load from file if exists
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r') as f:
                    file_config = json.load(f)
                    config_data.update(file_config)
            except (json.JSONDecodeError, IOError) as e:
                st.error(f"Error loading config file: {e}")
        
        # Override with environment variables if present
        env_config = {
            "url": os.getenv("SONARQUBE_URL"),
            "token": os.getenv("SONARQUBE_TOKEN"),
            "organization": os.getenv("SONARQUBE_ORGANIZATION"),
            "verify_ssl": os.getenv("SONARQUBE_VERIFY_SSL", "true").lower() == "true",
            "timeout": int(os.getenv("SONARQUBE_TIMEOUT", "30")),
            "max_retries": int(os.getenv("SONARQUBE_MAX_RETRIES", "3")),
        }
        
        # Only update with non-None environment values
        for key, value in env_config.items():
            if value is not None:
                config_data[key] = value
        
        self._config = SonarQubeConfig.from_dict(config_data)
    
    def save_config(self, config: SonarQubeConfig) -> bool:
        """Save configuration to file."""
        try:
            with open(self.config_file, 'w') as f:
                json.dump(config.to_dict(), f, indent=2)
            self._config = config
            return True
        except IOError as e:
            st.error(f"Error saving configuration: {e}")
            return False
    
    def get_config(self) -> SonarQubeConfig:
        """Get current configuration."""
        if self._config is None:
            self._load_config()
        return self._config
    
    def is_configured(self) -> bool:
        """Check if SonarQube is properly configured."""
        config = self.get_config()
        return config.is_valid()
    
    def update_config(self, **kwargs) -> bool:
        """Update configuration with new values."""
        config = self.get_config()
        config_dict = config.to_dict()
        config_dict.update(kwargs)
        new_config = SonarQubeConfig.from_dict(config_dict)
        return self.save_config(new_config)
    
    def clear_config(self) -> bool:
        """Clear configuration."""
        try:
            if self.config_file.exists():
                self.config_file.unlink()
            self._config = SonarQubeConfig()
            return True
        except IOError as e:
            st.error(f"Error clearing configuration: {e}")
            return False
    
    def get_connection_params(self) -> Dict[str, Any]:
        """Get parameters for SonarQube client connection."""
        config = self.get_config()
        return {
            "base_url": config.url,
            "token": config.token,
            "organization": config.organization,
            "timeout": config.timeout,
            "max_retries": config.max_retries,
            "verify_ssl": config.verify_ssl,
        }
    
    def mask_sensitive_data(self) -> Dict[str, Any]:
        """Get configuration with sensitive data masked for display."""
        config = self.get_config()
        config_dict = config.to_dict()
        
        # Mask token
        if config_dict.get("token"):
            token = config_dict["token"]
            if len(token) > 8:
                config_dict["token"] = f"{token[:4]}...{token[-4:]}"
            else:
                config_dict["token"] = "***"
        
        return config_dict
