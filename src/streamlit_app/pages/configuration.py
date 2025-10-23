"""Configuration page for SonarQube connection setup."""

import streamlit as st
from typing import Optional

from ..config.settings import SonarQubeConfig
from ..utils.session import SessionManager


def render():
    """Render the configuration page."""
    st.title("⚙️ SonarQube Configuration")
    st.markdown("Configure your SonarQube server connection and authentication.")
    
    # Get managers from session state
    config_manager = st.session_state.config_manager
    auth_manager = st.session_state.auth_manager
    
    # Current configuration status
    current_config = config_manager.get_config()
    
    if current_config.is_valid():
        st.success("✅ SonarQube is configured")
        
        # Show current configuration (masked)
        with st.expander("Current Configuration", expanded=False):
            masked_config = config_manager.mask_sensitive_data()
            st.json(masked_config)
        
        # Connection status
        connection_status = SessionManager.get_connection_status()
        if connection_status == "connected":
            st.success("🔗 Connected to SonarQube")
            
            # Show system info if available
            system_info = st.session_state.get("system_info")
            if system_info:
                with st.expander("Server Information", expanded=False):
                    col1, col2 = st.columns(2)
                    with col1:
                        st.metric("Status", system_info.get("status", "Unknown"))
                        st.metric("Version", system_info.get("version", "Unknown"))
                    with col2:
                        st.metric("Server ID", system_info.get("serverId", "Unknown")[:8] + "...")
                        st.metric("Edition", system_info.get("edition", "Community"))
            
            # Show user info if available
            user_info = SessionManager.get_user_info()
            if user_info:
                with st.expander("User Information", expanded=False):
                    col1, col2 = st.columns(2)
                    with col1:
                        st.write(f"**Name:** {user_info.get('name', 'Unknown')}")
                        st.write(f"**Login:** {user_info.get('login', 'Unknown')}")
                    with col2:
                        st.write(f"**Email:** {user_info.get('email', 'Not provided')}")
                        st.write(f"**Active:** {'Yes' if user_info.get('active') else 'No'}")
                
                # Show permissions
                permissions = SessionManager.get_user_permissions()
                if permissions:
                    with st.expander("Permissions", expanded=False):
                        col1, col2 = st.columns(2)
                        with col1:
                            st.write(f"**Admin:** {'✅' if permissions.get('admin') else '❌'}")
                            st.write(f"**Scan:** {'✅' if permissions.get('scan') else '❌'}")
                        with col2:
                            st.write(f"**Provisioning:** {'✅' if permissions.get('provisioning') else '❌'}")
                            st.write(f"**Profile Admin:** {'✅' if permissions.get('profileadmin') else '❌'}")
        
        elif connection_status == "error":
            st.error("❌ Connection failed")
        else:
            st.info("🔄 Connection status unknown")
    
    else:
        st.warning("⚠️ SonarQube configuration is incomplete")
    
    st.divider()
    
    # Configuration form
    st.subheader("Connection Settings")
    
    with st.form("sonarqube_config"):
        col1, col2 = st.columns([2, 1])
        
        with col1:
            url = st.text_input(
                "SonarQube Server URL",
                value=current_config.url,
                placeholder="https://sonarqube.example.com",
                help="The base URL of your SonarQube server"
            )
            
            token = st.text_input(
                "Authentication Token",
                value=current_config.token,
                type="password",
                placeholder="squ_1234567890abcdef...",
                help="User token from SonarQube (User > My Account > Security)"
            )
            
            organization = st.text_input(
                "Organization (Optional)",
                value=current_config.organization or "",
                placeholder="my-organization",
                help="Organization key (required for SonarCloud)"
            )
        
        with col2:
            st.subheader("Advanced Settings")
            
            verify_ssl = st.checkbox(
                "Verify SSL Certificate",
                value=current_config.verify_ssl,
                help="Uncheck for self-signed certificates"
            )
            
            timeout = st.number_input(
                "Request Timeout (seconds)",
                min_value=5,
                max_value=300,
                value=current_config.timeout,
                help="HTTP request timeout"
            )
            
            max_retries = st.number_input(
                "Max Retries",
                min_value=0,
                max_value=10,
                value=current_config.max_retries,
                help="Maximum number of retry attempts"
            )
        
        col1, col2, col3 = st.columns([1, 1, 1])
        
        with col1:
            test_button = st.form_submit_button(
                "🔍 Test Connection",
                type="secondary",
                use_container_width=True
            )
        
        with col2:
            save_button = st.form_submit_button(
                "💾 Save Configuration",
                type="primary",
                use_container_width=True
            )
        
        with col3:
            clear_button = st.form_submit_button(
                "🗑️ Clear Configuration",
                type="secondary",
                use_container_width=True
            )
    
    # Handle form submissions
    if test_button:
        if not url or not token:
            st.error("URL and token are required for testing")
        else:
            with st.spinner("Testing connection..."):
                success, message = auth_manager.validate_credentials_sync(
                    url, token, organization if organization else None
                )
                
                if success:
                    st.success(f"✅ {message}")
                else:
                    st.error(f"❌ {message}")
    
    if save_button:
        if not url or not token:
            st.error("URL and token are required")
        else:
            # Create new configuration
            new_config = SonarQubeConfig(
                url=url.strip(),
                token=token.strip(),
                organization=organization.strip() if organization else None,
                verify_ssl=verify_ssl,
                timeout=timeout,
                max_retries=max_retries
            )
            
            # Save configuration
            if config_manager.save_config(new_config):
                st.success("✅ Configuration saved successfully")
                
                # Test connection after saving
                with st.spinner("Testing connection..."):
                    success, message, system_info = auth_manager.test_connection_sync()
                    
                    if success:
                        SessionManager.set_connection_status("connected", system_info)
                        st.success(f"🔗 {message}")
                        
                        # Get user info and permissions
                        user_info = auth_manager.get_user_info_sync()
                        if user_info:
                            SessionManager.set_user_info(user_info)
                        
                        permissions = auth_manager.check_permissions_sync()
                        SessionManager.set_user_permissions(permissions)
                        
                        st.rerun()
                    else:
                        SessionManager.set_connection_status("error")
                        st.error(f"❌ {message}")
            else:
                st.error("❌ Failed to save configuration")
    
    if clear_button:
        if config_manager.clear_config():
            SessionManager.clear_session()
            st.success("✅ Configuration cleared")
            st.rerun()
        else:
            st.error("❌ Failed to clear configuration")
    
    # Environment variables info
    st.divider()
    st.subheader("Environment Variables")
    st.markdown("""
    You can also configure SonarQube using environment variables:
    
    - `SONARQUBE_URL` - SonarQube server URL
    - `SONARQUBE_TOKEN` - Authentication token
    - `SONARQUBE_ORGANIZATION` - Organization key (optional)
    - `SONARQUBE_VERIFY_SSL` - Verify SSL certificates (true/false)
    - `SONARQUBE_TIMEOUT` - Request timeout in seconds
    - `SONARQUBE_MAX_RETRIES` - Maximum retry attempts
    
    Environment variables take precedence over saved configuration.
    """)
    
    # Connection troubleshooting
    with st.expander("🔧 Troubleshooting", expanded=False):
        st.markdown("""
        **Common Issues:**
        
        1. **Authentication Failed**
           - Verify your token is correct and not expired
           - Check if the token has sufficient permissions
           - Ensure you're using a User Token, not a Project Token
        
        2. **Connection Timeout**
           - Check if the SonarQube server URL is correct
           - Verify network connectivity to the server
           - Try increasing the timeout value
        
        3. **SSL Certificate Issues**
           - For self-signed certificates, uncheck "Verify SSL Certificate"
           - Ensure your certificate is properly configured
        
        4. **Organization Issues**
           - Organization is required for SonarCloud
           - Leave empty for on-premise SonarQube installations
           - Check the organization key in SonarQube settings
        
        **Token Generation:**
        1. Log in to SonarQube
        2. Go to User > My Account > Security
        3. Generate a new token
        4. Copy the token immediately (it won't be shown again)
        """)