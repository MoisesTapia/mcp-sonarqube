"""Authentication and connection management for SonarQube."""

import asyncio
from typing import Dict, Any, Optional, Tuple
import streamlit as st

from sonarqube_client.client import SonarQubeClient
from sonarqube_client.exceptions import (
    AuthenticationError,
    AuthorizationError,
    NetworkError,
    SonarQubeException
)
from streamlit_app.config.settings import ConfigManager


class AuthManager:
    """Manages authentication and connection to SonarQube."""
    
    def __init__(self, config_manager: ConfigManager):
        """Initialize authentication manager."""
        self.config_manager = config_manager
        self._client: Optional[SonarQubeClient] = None
    
    async def create_client(self) -> Optional[SonarQubeClient]:
        """Create SonarQube client with current configuration."""
        if not self.config_manager.is_configured():
            return None
        
        try:
            params = self.config_manager.get_connection_params()
            client = SonarQubeClient(**params)
            return client
        except Exception as e:
            st.error(f"Failed to create SonarQube client: {e}")
            return None
    
    async def test_connection(self) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """
        Test connection to SonarQube server.
        
        Returns:
            Tuple of (success, message, system_info)
        """
        if not self.config_manager.is_configured():
            return False, "SonarQube not configured", None
        
        client = await self.create_client()
        if not client:
            return False, "Failed to create client", None
        
        try:
            # Test basic connectivity
            is_connected = await client.validate_connection()
            if not is_connected:
                return False, "Server is not responding or is down", None
            
            # Test authentication
            is_authenticated = await client.authenticate()
            if not is_authenticated:
                return False, "Authentication failed - invalid token", None
            
            # Get system information
            try:
                system_info = await client.get("/system/status")
                return True, "Connection successful", system_info
            except Exception as e:
                return True, f"Connected but failed to get system info: {e}", None
                
        except AuthenticationError:
            return False, "Authentication failed - invalid token", None
        except AuthorizationError:
            return False, "Authorization failed - insufficient permissions", None
        except NetworkError as e:
            return False, f"Network error: {e}", None
        except SonarQubeException as e:
            return False, f"SonarQube error: {e}", None
        except Exception as e:
            return False, f"Unexpected error: {e}", None
        finally:
            if client:
                await client.close()
    
    def test_connection_sync(self) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """Synchronous wrapper for test_connection."""
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        return loop.run_until_complete(self.test_connection())
    
    async def validate_credentials(self, url: str, token: str, organization: Optional[str] = None) -> Tuple[bool, str]:
        """
        Validate credentials without saving them.
        
        Args:
            url: SonarQube server URL
            token: Authentication token
            organization: Optional organization key
            
        Returns:
            Tuple of (success, message)
        """
        if not url or not token:
            return False, "URL and token are required"
        
        try:
            client = SonarQubeClient(
                base_url=url,
                token=token,
                organization=organization,
                timeout=10,  # Shorter timeout for validation
                max_retries=1
            )
            
            # Test connection and authentication
            is_connected = await client.validate_connection()
            if not is_connected:
                return False, "Cannot connect to SonarQube server"
            
            is_authenticated = await client.authenticate()
            if not is_authenticated:
                return False, "Invalid authentication token"
            
            return True, "Credentials are valid"
            
        except AuthenticationError:
            return False, "Invalid authentication token"
        except AuthorizationError:
            return False, "Insufficient permissions"
        except NetworkError as e:
            return False, f"Network error: {e}"
        except Exception as e:
            return False, f"Validation error: {e}"
        finally:
            if 'client' in locals():
                await client.close()
    
    def validate_credentials_sync(self, url: str, token: str, organization: Optional[str] = None) -> Tuple[bool, str]:
        """Synchronous wrapper for validate_credentials."""
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        return loop.run_until_complete(self.validate_credentials(url, token, organization))
    
    async def get_user_info(self) -> Optional[Dict[str, Any]]:
        """Get current user information."""
        client = await self.create_client()
        if not client:
            return None
        
        try:
            user_info = await client.get("/users/current")
            return user_info
        except Exception as e:
            st.error(f"Failed to get user info: {e}")
            return None
        finally:
            await client.close()
    
    def get_user_info_sync(self) -> Optional[Dict[str, Any]]:
        """Synchronous wrapper for get_user_info."""
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        return loop.run_until_complete(self.get_user_info())
    
    async def check_permissions(self) -> Dict[str, bool]:
        """Check user permissions for various operations."""
        client = await self.create_client()
        if not client:
            return {}
        
        permissions = {
            "admin": False,
            "scan": False,
            "provisioning": False,
            "profileadmin": False,
            "gateadmin": False,
        }
        
        try:
            # Get user permissions
            user_info = await client.get("/users/current")
            user_permissions = user_info.get("permissions", {}).get("global", [])
            
            for permission in user_permissions:
                if permission in permissions:
                    permissions[permission] = True
            
            return permissions
        except Exception as e:
            st.error(f"Failed to check permissions: {e}")
            return permissions
        finally:
            await client.close()
    
    def check_permissions_sync(self) -> Dict[str, bool]:
        """Synchronous wrapper for check_permissions."""
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        return loop.run_until_complete(self.check_permissions())
