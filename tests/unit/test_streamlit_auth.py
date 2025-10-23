"""Tests for Streamlit authentication components."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import asyncio

from src.streamlit_app.utils.auth import AuthManager
from src.streamlit_app.config.settings import ConfigManager, SonarQubeConfig
from src.sonarqube_client.exceptions import (
    AuthenticationError,
    AuthorizationError,
    NetworkError,
    SonarQubeException
)


class TestAuthManager:
    """Test authentication manager."""
    
    def setup_method(self):
        """Set up test environment."""
        self.config_manager = MagicMock(spec=ConfigManager)
        self.auth_manager = AuthManager(self.config_manager)
    
    @pytest.mark.asyncio
    async def test_create_client_success(self):
        """Test successful client creation."""
        # Mock configuration
        self.config_manager.is_configured.return_value = True
        self.config_manager.get_connection_params.return_value = {
            "base_url": "https://sonarqube.example.com",
            "token": "test_token",
            "organization": None,
            "timeout": 30,
            "max_retries": 3,
            "verify_ssl": True
        }
        
        with patch("src.streamlit_app.utils.auth.SonarQubeClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client_class.return_value = mock_client
            
            client = await self.auth_manager.create_client()
            
            assert client is not None
            mock_client_class.assert_called_once_with(
                base_url="https://sonarqube.example.com",
                token="test_token",
                organization=None,
                timeout=30,
                max_retries=3,
                verify_ssl=True
            )
    
    @pytest.mark.asyncio
    async def test_create_client_not_configured(self):
        """Test client creation when not configured."""
        self.config_manager.is_configured.return_value = False
        
        client = await self.auth_manager.create_client()
        
        assert client is None
    
    @pytest.mark.asyncio
    async def test_create_client_exception(self):
        """Test client creation with exception."""
        self.config_manager.is_configured.return_value = True
        self.config_manager.get_connection_params.side_effect = Exception("Config error")
        
        with patch("streamlit.error") as mock_error:
            client = await self.auth_manager.create_client()
            
            assert client is None
            mock_error.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_test_connection_success(self):
        """Test successful connection test."""
        self.config_manager.is_configured.return_value = True
        
        mock_client = AsyncMock()
        mock_client.validate_connection.return_value = True
        mock_client.authenticate.return_value = True
        mock_client.get.return_value = {"status": "UP", "version": "9.9"}
        
        with patch.object(self.auth_manager, "create_client", return_value=mock_client):
            success, message, system_info = await self.auth_manager.test_connection()
            
            assert success is True
            assert "Connection successful" in message
            assert system_info == {"status": "UP", "version": "9.9"}
            mock_client.close.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_test_connection_not_configured(self):
        """Test connection test when not configured."""
        self.config_manager.is_configured.return_value = False
        
        success, message, system_info = await self.auth_manager.test_connection()
        
        assert success is False
        assert "not configured" in message.lower()
        assert system_info is None
    
    @pytest.mark.asyncio
    async def test_test_connection_server_down(self):
        """Test connection test with server down."""
        self.config_manager.is_configured.return_value = True
        
        mock_client = AsyncMock()
        mock_client.validate_connection.return_value = False
        
        with patch.object(self.auth_manager, "create_client", return_value=mock_client):
            success, message, system_info = await self.auth_manager.test_connection()
            
            assert success is False
            assert "not responding" in message.lower()
            assert system_info is None
    
    @pytest.mark.asyncio
    async def test_test_connection_auth_failed(self):
        """Test connection test with authentication failure."""
        self.config_manager.is_configured.return_value = True
        
        mock_client = AsyncMock()
        mock_client.validate_connection.return_value = True
        mock_client.authenticate.return_value = False
        
        with patch.object(self.auth_manager, "create_client", return_value=mock_client):
            success, message, system_info = await self.auth_manager.test_connection()
            
            assert success is False
            assert "Authentication failed" in message
            assert system_info is None
    
    @pytest.mark.asyncio
    async def test_test_connection_authentication_error(self):
        """Test connection test with AuthenticationError exception."""
        self.config_manager.is_configured.return_value = True
        
        mock_client = AsyncMock()
        mock_client.validate_connection.side_effect = AuthenticationError("Invalid token")
        
        with patch.object(self.auth_manager, "create_client", return_value=mock_client):
            success, message, system_info = await self.auth_manager.test_connection()
            
            assert success is False
            assert "Authentication failed" in message
            assert system_info is None
    
    @pytest.mark.asyncio
    async def test_test_connection_authorization_error(self):
        """Test connection test with AuthorizationError exception."""
        self.config_manager.is_configured.return_value = True
        
        mock_client = AsyncMock()
        mock_client.validate_connection.side_effect = AuthorizationError("Insufficient permissions")
        
        with patch.object(self.auth_manager, "create_client", return_value=mock_client):
            success, message, system_info = await self.auth_manager.test_connection()
            
            assert success is False
            assert "Authorization failed" in message
            assert system_info is None
    
    @pytest.mark.asyncio
    async def test_test_connection_network_error(self):
        """Test connection test with NetworkError exception."""
        self.config_manager.is_configured.return_value = True
        
        mock_client = AsyncMock()
        mock_client.validate_connection.side_effect = NetworkError("Connection timeout")
        
        with patch.object(self.auth_manager, "create_client", return_value=mock_client):
            success, message, system_info = await self.auth_manager.test_connection()
            
            assert success is False
            assert "Network error" in message
            assert system_info is None
    
    def test_test_connection_sync(self):
        """Test synchronous wrapper for test_connection."""
        with patch.object(self.auth_manager, "test_connection") as mock_async:
            mock_async.return_value = (True, "Success", {"status": "UP"})
            
            success, message, system_info = self.auth_manager.test_connection_sync()
            
            assert success is True
            assert message == "Success"
            assert system_info == {"status": "UP"}
    
    @pytest.mark.asyncio
    async def test_validate_credentials_success(self):
        """Test successful credential validation."""
        with patch("src.streamlit_app.utils.auth.SonarQubeClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.validate_connection.return_value = True
            mock_client.authenticate.return_value = True
            mock_client_class.return_value = mock_client
            
            success, message = await self.auth_manager.validate_credentials(
                "https://sonarqube.example.com",
                "test_token",
                "test_org"
            )
            
            assert success is True
            assert "valid" in message.lower()
            mock_client.close.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_validate_credentials_missing_params(self):
        """Test credential validation with missing parameters."""
        success, message = await self.auth_manager.validate_credentials("", "")
        
        assert success is False
        assert "required" in message.lower()
    
    @pytest.mark.asyncio
    async def test_validate_credentials_connection_failed(self):
        """Test credential validation with connection failure."""
        with patch("src.streamlit_app.utils.auth.SonarQubeClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.validate_connection.return_value = False
            mock_client_class.return_value = mock_client
            
            success, message = await self.auth_manager.validate_credentials(
                "https://sonarqube.example.com",
                "test_token"
            )
            
            assert success is False
            assert "Cannot connect" in message
    
    @pytest.mark.asyncio
    async def test_validate_credentials_auth_failed(self):
        """Test credential validation with authentication failure."""
        with patch("src.streamlit_app.utils.auth.SonarQubeClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.validate_connection.return_value = True
            mock_client.authenticate.return_value = False
            mock_client_class.return_value = mock_client
            
            success, message = await self.auth_manager.validate_credentials(
                "https://sonarqube.example.com",
                "test_token"
            )
            
            assert success is False
            assert "Invalid authentication token" in message
    
    def test_validate_credentials_sync(self):
        """Test synchronous wrapper for validate_credentials."""
        with patch.object(self.auth_manager, "validate_credentials") as mock_async:
            mock_async.return_value = (True, "Valid")
            
            success, message = self.auth_manager.validate_credentials_sync(
                "https://sonarqube.example.com",
                "test_token"
            )
            
            assert success is True
            assert message == "Valid"
    
    @pytest.mark.asyncio
    async def test_get_user_info_success(self):
        """Test successful user info retrieval."""
        mock_client = AsyncMock()
        mock_client.get.return_value = {
            "login": "testuser",
            "name": "Test User",
            "email": "test@example.com"
        }
        
        with patch.object(self.auth_manager, "create_client", return_value=mock_client):
            user_info = await self.auth_manager.get_user_info()
            
            assert user_info is not None
            assert user_info["login"] == "testuser"
            assert user_info["name"] == "Test User"
            mock_client.close.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_user_info_no_client(self):
        """Test user info retrieval with no client."""
        with patch.object(self.auth_manager, "create_client", return_value=None):
            user_info = await self.auth_manager.get_user_info()
            
            assert user_info is None
    
    @pytest.mark.asyncio
    async def test_get_user_info_exception(self):
        """Test user info retrieval with exception."""
        mock_client = AsyncMock()
        mock_client.get.side_effect = Exception("API error")
        
        with patch.object(self.auth_manager, "create_client", return_value=mock_client), \
             patch("streamlit.error") as mock_error:
            user_info = await self.auth_manager.get_user_info()
            
            assert user_info is None
            mock_error.assert_called_once()
    
    def test_get_user_info_sync(self):
        """Test synchronous wrapper for get_user_info."""
        with patch.object(self.auth_manager, "get_user_info") as mock_async:
            mock_async.return_value = {"login": "testuser"}
            
            user_info = self.auth_manager.get_user_info_sync()
            
            assert user_info == {"login": "testuser"}
    
    @pytest.mark.asyncio
    async def test_check_permissions_success(self):
        """Test successful permission check."""
        mock_client = AsyncMock()
        mock_client.get.return_value = {
            "permissions": {
                "global": ["admin", "scan", "provisioning"]
            }
        }
        
        with patch.object(self.auth_manager, "create_client", return_value=mock_client):
            permissions = await self.auth_manager.check_permissions()
            
            assert permissions["admin"] is True
            assert permissions["scan"] is True
            assert permissions["provisioning"] is True
            assert permissions["profileadmin"] is False
            assert permissions["gateadmin"] is False
    
    @pytest.mark.asyncio
    async def test_check_permissions_no_client(self):
        """Test permission check with no client."""
        with patch.object(self.auth_manager, "create_client", return_value=None):
            permissions = await self.auth_manager.check_permissions()
            
            assert permissions == {}
    
    @pytest.mark.asyncio
    async def test_check_permissions_exception(self):
        """Test permission check with exception."""
        mock_client = AsyncMock()
        mock_client.get.side_effect = Exception("API error")
        
        with patch.object(self.auth_manager, "create_client", return_value=mock_client), \
             patch("streamlit.error") as mock_error:
            permissions = await self.auth_manager.check_permissions()
            
            # Should return default permissions (all False)
            assert all(not perm for perm in permissions.values())
            mock_error.assert_called_once()
    
    def test_check_permissions_sync(self):
        """Test synchronous wrapper for check_permissions."""
        with patch.object(self.auth_manager, "check_permissions") as mock_async:
            mock_async.return_value = {"admin": True}
            
            permissions = self.auth_manager.check_permissions_sync()
            
            assert permissions == {"admin": True}