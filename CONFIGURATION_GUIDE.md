# SonarQube MCP Configuration Guide

This guide explains the important configuration changes and how to properly set up the SonarQube MCP application.

## 🚨 Important Changes

### API Endpoint Corrections

The SonarQube API endpoint has been corrected from the previous incorrect configuration:

- ❌ **Old (Incorrect)**: `/web_api/api`
- ✅ **New (Correct)**: `/api`

The system now automatically appends `/api` to your base SonarQube URL.

### Service Port Updates

- **MCP Server**: Port **8001** (previously incorrectly configured as 8000)
- **Streamlit App**: Port **8501** 
- **SonarQube**: Port **9000** with context path `/sonarqube`

## 📋 Configuration Steps

### 1. SonarQube Setup

1. **Access SonarQube**: http://localhost:9000/sonarqube
2. **Login**: Default credentials are `admin/admin` (you'll be prompted to change on first login)
3. **Generate Token**:
   - Go to **My Account** → **Security** → **Generate Tokens**
   - Create a token named "Streamlit App" or similar
   - Copy the generated token

### 2. Environment Configuration

Edit your environment file (`docker/environments/.env.development`):

```bash
# Replace with your actual token
SONARQUBE_TOKEN=your_actual_token_here

# Keep these URLs as-is for Docker network communication
SONARQUBE_INTERNAL_URL=http://sonarqube:9000/sonarqube
MCP_SERVER_INTERNAL_URL=http://mcp-server:8001
```

### 3. Streamlit App Configuration

When configuring the Streamlit app through the UI:

- **SonarQube Server URL**: `http://localhost:9000/sonarqube`
- **Authentication Token**: Use the token generated in step 1
- **Organization**: Leave empty for SonarQube Server (only needed for SonarCloud)

## 🔧 Docker Compose Updates

The `docker-compose.yml` has been updated with correct configurations:

```yaml
# MCP Server
mcp-server:
  ports:
    - "8001:8001"  # Correct port
  healthcheck:
    test: ["CMD", "curl", "-f", "http://localhost:8001/health"]

# Streamlit App  
streamlit-app:
  environment:
    SONARQUBE_URL: http://sonarqube:9000/sonarqube  # Internal network URL
    MCP_SERVER_URL: http://mcp-server:8001          # Correct MCP port
  ports:
    - "8501:8501"
```

## 🌐 Network Architecture

### Internal Docker Network (`sonarqube-mcp`)

Services communicate using internal hostnames:

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Streamlit     │───▶│   MCP Server    │───▶│   SonarQube     │
│   :8501         │    │   :8001         │    │   :9000         │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         │                       │                       │
    ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
    │   Redis         │    │   PostgreSQL    │    │   Nginx         │
    │   :6379         │    │   :5432         │    │   :80/:443      │
    └─────────────────┘    └─────────────────┘    └─────────────────┘
```

### External Access (Host Machine)

```
Browser ──▶ http://localhost:8501 ──▶ Streamlit App
Browser ──▶ http://localhost:9000/sonarqube ──▶ SonarQube
Browser ──▶ http://localhost:8001 ──▶ MCP Server (for debugging)
```

## 🐛 Troubleshooting

### Common Issues

1. **"Server is not responding or is down"**
   - ✅ Use `http://localhost:9000/sonarqube` in the Streamlit UI
   - ❌ Don't use `http://sonarqube-server:9000/sonarqube` in the UI

2. **MCP Server Connection Failed**
   - Check that MCP server is running on port 8001
   - Verify: `curl http://localhost:8001/health`

3. **SonarQube API Errors**
   - Ensure you're using a valid token
   - Check SonarQube is accessible: `curl http://localhost:9000/sonarqube/api/system/status`

### Verification Commands

```bash
# Check all services are running
docker ps

# Test SonarQube API
curl http://localhost:9000/sonarqube/api/system/status

# Test MCP Server
curl http://localhost:8001/health

# Check Streamlit health
curl http://localhost:8501/_stcore/health

# View logs
docker logs sonarqube-streamlit-app
docker logs sonarqube-mcp-server
docker logs sonarqube-server
```

## 📝 Configuration Templates

### Development Environment

```bash
# docker/environments/.env.development
SONARQUBE_TOKEN=your_token_here
SONARQUBE_INTERNAL_URL=http://sonarqube:9000/sonarqube
MCP_SERVER_INTERNAL_URL=http://mcp-server:8001
LOG_LEVEL=DEBUG
SERVER_DEBUG=true
CACHE_TTL=60
```

### Production Environment

```bash
# docker/environments/.env.production
SONARQUBE_TOKEN=your_secure_token_here
SONARQUBE_INTERNAL_URL=http://sonarqube:9000/sonarqube
MCP_SERVER_INTERNAL_URL=http://mcp-server:8001
LOG_LEVEL=INFO
SERVER_DEBUG=false
CACHE_TTL=300
```

## 🔒 Security Notes

1. **Never commit real tokens** to version control
2. **Use strong passwords** for database and Redis
3. **Enable HTTPS** in production environments
4. **Regularly rotate tokens** and passwords
5. **Use Docker secrets** for production deployments

## 📚 Additional Resources

- [SonarQube Documentation](https://docs.sonarqube.org/)
- [Docker Compose Documentation](https://docs.docker.com/compose/)
- [Streamlit Documentation](https://docs.streamlit.io/)

---

**Last Updated**: October 2025  
**Version**: 2.0 (Post API Endpoint Fix)