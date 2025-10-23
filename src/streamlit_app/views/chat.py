"""Chat page with MCP tool execution interface."""

import streamlit as st
from streamlit_app.components import render_mcp_tool_executor, render_sync_controls


def render():
    """Render the chat page."""
    st.title("💬 Chat & MCP Tools")
    
    # Add tabs for different interfaces
    tab1, tab2, tab3 = st.tabs(["🔧 MCP Tools", "🔄 Data Sync", "💬 Chat (Coming Soon)"])
    
    with tab1:
        st.subheader("MCP Tool Execution")
        st.info("Execute MCP tools directly from the interface")
        
        # Render MCP tool executor
        render_mcp_tool_executor("chat_page_mcp")
    
    with tab2:
        st.subheader("Real-time Data Synchronization")
        st.info("Monitor and control data synchronization across the application")
        
        # Render sync controls
        render_sync_controls("chat_page")
        
        # Show MCP connection status
        if "mcp_client" in st.session_state:
            mcp_client = st.session_state.mcp_client
            connection_info = mcp_client.get_connection_info()
            
            st.subheader("🔗 MCP Connection Status")
            
            col1, col2, col3 = st.columns(3)
            with col1:
                if connection_info["status"] == "connected":
                    st.success("✅ Connected")
                else:
                    st.error(f"❌ {connection_info['status']}")
            
            with col2:
                st.info(f"📞 {connection_info['total_calls']} total calls")
            
            with col3:
                error_stats = connection_info.get("error_stats", {})
                success_rate = error_stats.get("success_rate", 0)
                st.info(f"📊 {success_rate:.1f}% success rate")
            
            # Show recent tool calls
            with st.expander("📜 Recent MCP Tool Calls"):
                history = mcp_client.get_tool_history(limit=10)
                if history:
                    for call in history:
                        status_icon = "✅" if call.get("success") else "❌"
                        execution_time = call.get("execution_time", 0)
                        st.write(f"{status_icon} **{call['tool_name']}** - {execution_time:.2f}s - {call['timestamp']}")
                        
                        if call.get("error"):
                            st.error(f"Error: {call['error']}")
                else:
                    st.info("No recent tool calls")
    
    with tab3:
        st.subheader("Interactive Chat Interface")
        
        # Import and render the chat interface
        from streamlit_app.components.chat_interface import ChatInterface
        
        chat_interface = ChatInterface()
        chat_interface.render_chat_interface()
        
        # Add additional features
        st.markdown("---")
        
        col1, col2 = st.columns(2)
        
        with col1:
            chat_interface.render_command_suggestions()
        
        with col2:
            chat_interface.render_conversation_export()