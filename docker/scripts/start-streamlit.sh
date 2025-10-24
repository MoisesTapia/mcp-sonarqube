#!/bin/bash

# Start script for Streamlit app
# This script ensures Streamlit runs in headless mode without prompts

echo "Starting SonarQube MCP Streamlit App..."

# Set environment variables to avoid prompts
export STREAMLIT_BROWSER_GATHER_USAGE_STATS=false
export STREAMLIT_SERVER_HEADLESS=true
export STREAMLIT_SERVER_ENABLE_CORS=false
export STREAMLIT_SERVER_ENABLE_XSRF_PROTECTION=false

# Create credentials file to avoid email prompt
mkdir -p ~/.streamlit
echo '{"email": ""}' > ~/.streamlit/credentials.toml

# Create config file
cat > ~/.streamlit/config.toml << EOF
[server]
port = 8501
address = "0.0.0.0"
headless = true
enableCORS = false
enableXsrfProtection = false

[browser]
gatherUsageStats = false

[global]
showWarningOnDirectExecution = false
EOF

# Start Streamlit
exec streamlit run src/streamlit_app/app.py \
    --server.port=8501 \
    --server.address=0.0.0.0 \
    --server.headless=true \
    --browser.gatherUsageStats=false \
    --global.showWarningOnDirectExecution=false