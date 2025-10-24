"""Configuration management for SonarQube MCP server."""

import os
from typing import Dict, Optional

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict, SettingsConfigDict


class SonarQubeConfig(BaseModel):
    """SonarQube connection configuration."""

    url: str = Field(..., description="SonarQube server URL")
    token: str = Field(..., description="SonarQube authentication token")
    organization: Optional[str] = Field(None, description="SonarQube organization")
    timeout: int = Field(30, description="Request timeout in seconds")
    max_retries: int = Field(3, description="Maximum number of retries")
    verify_ssl: bool = Field(True, description="Verify SSL certificates")


class CacheConfig(BaseModel):
    """Cache configuration."""

    enabled: bool = Field(True, description="Enable caching")
    ttl: int = Field(300, description="Default TTL in seconds")
    redis_url: Optional[str] = Field(None, description="Redis URL for distributed cache")
    ttl_by_type: Dict[str, int] = Field(
        default_factory=lambda: {
            "projects": 300,
            "metrics": 300,
            "issues": 60,
            "quality_gates": 600,
            "users": 1800,
        },
        description="TTL by data type",
    )


class ServerConfig(BaseModel):
    """MCP server configuration."""

    host: str = Field("localhost", description="Server host")
    port: int = Field(8001, description="Server port")
    log_level: str = Field("INFO", description="Logging level")
    debug: bool = Field(False, description="Debug mode")


class MCPServerSettings(BaseSettings):
    """Main settings for the MCP server."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # SonarQube configuration
    sonarqube_url: str = Field(..., description="SonarQube server URL")
    sonarqube_token: str = Field(..., description="SonarQube authentication token")
    sonarqube_organization: Optional[str] = Field(None, description="SonarQube organization")
    sonarqube_timeout: int = Field(30, description="Request timeout in seconds")
    sonarqube_max_retries: int = Field(3, description="Maximum number of retries")
    sonarqube_verify_ssl: bool = Field(True, description="Verify SSL certificates")

    # Server configuration
    server_host: str = Field("localhost", description="Server host")
    server_port: int = Field(8001, description="Server port")
    server_log_level: str = Field("INFO", description="Logging level")
    server_debug: bool = Field(False, description="Debug mode")

    # Cache configuration
    cache_enabled: bool = Field(True, description="Enable caching")
    cache_ttl: int = Field(300, description="Default cache TTL")
    cache_redis_url: Optional[str] = Field(None, description="Redis URL for distributed cache")

    # Performance configuration
    max_concurrent_requests: int = Field(50, description="Maximum concurrent requests")
    request_timeout: int = Field(30, description="Request timeout")

    @property
    def sonarqube_config(self) -> SonarQubeConfig:
        """Get SonarQube configuration."""
        return SonarQubeConfig(
            url=self.sonarqube_url,
            token=self.sonarqube_token,
            organization=self.sonarqube_organization,
            timeout=self.sonarqube_timeout,
            max_retries=self.sonarqube_max_retries,
            verify_ssl=self.sonarqube_verify_ssl,
        )

    @property
    def cache_config(self) -> CacheConfig:
        """Get cache configuration."""
        return CacheConfig(
            enabled=self.cache_enabled,
            ttl=self.cache_ttl,
            redis_url=self.cache_redis_url,
        )

    @property
    def server_config(self) -> ServerConfig:
        """Get server configuration."""
        return ServerConfig(
            host=self.server_host,
            port=self.server_port,
            log_level=self.server_log_level,
            debug=self.server_debug,
        )


def get_settings() -> MCPServerSettings:
    """Get application settings."""
    return MCPServerSettings()
