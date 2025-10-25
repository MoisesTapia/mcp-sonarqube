"""
Configuración específica para Streamlit para mejorar el rendimiento y reducir warnings.
"""

import streamlit as st
import logging
import warnings
from typing import Dict, Any


def configure_streamlit_logging():
    """Configure Streamlit logging to reduce noise."""
    # Reduce Streamlit logging noise
    streamlit_logger = logging.getLogger('streamlit')
    streamlit_logger.setLevel(logging.ERROR)
    
    # Reduce specific warnings
    warnings.filterwarnings("ignore", message=".*ScriptRunContext.*")
    warnings.filterwarnings("ignore", message=".*missing ScriptRunContext.*")
    
    # Configure other noisy loggers
    logging.getLogger('streamlit.runtime.scriptrunner_utils.script_run_context').setLevel(logging.ERROR)
    logging.getLogger('streamlit.runtime.state.session_state_proxy').setLevel(logging.ERROR)


def configure_streamlit_performance():
    """Configure Streamlit for better performance."""
    # Set page config if not already set
    try:
        st.set_page_config(
            page_title="SonarQube MCP Assistant",
            page_icon="🔍",
            layout="wide",
            initial_sidebar_state="expanded"
        )
    except st.errors.StreamlitAPIException:
        # Page config already set
        pass


def get_streamlit_config() -> Dict[str, Any]:
    """Get optimized Streamlit configuration."""
    return {
        "server": {
            "headless": True,
            "enableCORS": False,
            "enableXsrfProtection": False,
            "maxUploadSize": 200,
            "maxMessageSize": 200,
            "enableWebsocketCompression": True
        },
        "browser": {
            "gatherUsageStats": False,
            "serverAddress": "0.0.0.0",
            "serverPort": 8501
        },
        "logger": {
            "level": "error",
            "messageFormat": "%(asctime)s %(message)s"
        },
        "client": {
            "caching": True,
            "displayEnabled": True,
            "showErrorDetails": False
        }
    }


def suppress_streamlit_warnings():
    """Suppress common Streamlit warnings that are not critical."""
    import warnings
    
    # Suppress ScriptRunContext warnings
    warnings.filterwarnings(
        "ignore", 
        message=".*Thread.*missing ScriptRunContext.*",
        category=UserWarning
    )
    
    # Suppress session state warnings
    warnings.filterwarnings(
        "ignore",
        message=".*Session state does not function.*",
        category=UserWarning
    )
    
    # Suppress other common Streamlit warnings
    warnings.filterwarnings(
        "ignore",
        message=".*streamlit run.*",
        category=UserWarning
    )


def initialize_streamlit_app():
    """Initialize Streamlit app with optimized configuration."""
    # Configure logging first
    configure_streamlit_logging()
    
    # Suppress warnings
    suppress_streamlit_warnings()
    
    # Configure performance
    configure_streamlit_performance()
    
    # Initialize session state if needed
    if 'app_initialized' not in st.session_state:
        st.session_state.app_initialized = True
        st.session_state.mcp_connection_status = "disconnected"
        st.session_state.last_health_check = None


# Auto-initialize when imported
try:
    initialize_streamlit_app()
except Exception as e:
    # Fail silently if there are issues during initialization
    pass