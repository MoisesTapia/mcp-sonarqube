#!/bin/bash

# Start SonarQube MCP in development mode
# This script ensures all environment variables are properly loaded

echo "🚀 Starting SonarQube MCP Development Environment"

# Check if .env file exists
if [ ! -f .env ]; then
    echo "📋 Creating .env file from development template..."
    cp docker/environments/.env.development .env
    echo "✅ .env file created. Please edit it with your SonarQube token."
    echo ""
    echo "To get a SonarQube token:"
    echo "1. Go to http://localhost:9000/sonarqube"
    echo "2. Login with admin/admin"
    echo "3. Go to My Account > Security > Generate Token"
    echo "4. Edit .env file and replace SONARQUBE_TOKEN value"
    echo ""
fi

# Load environment variables
export $(grep -v '^#' .env | xargs)

# Start services
echo "🐳 Starting Docker services..."
docker compose -f docker/compose/base/docker-compose.yml up -d

echo ""
echo "✅ Services started!"
echo ""
echo "📊 Access your applications:"
echo "  - Streamlit App: http://localhost:8501"
echo "  - SonarQube: http://localhost:9000/sonarqube"
echo "  - MCP Server: http://localhost:8001"
echo ""
echo "📝 View logs:"
echo "  docker compose -f docker/compose/base/docker-compose.yml logs -f streamlit-app"
echo "  docker compose -f docker/compose/base/docker-compose.yml logs -f mcp-server"
echo "  docker compose -f docker/compose/base/docker-compose.yml logs -f sonarqube"
echo ""