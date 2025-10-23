# SonarQube MCP Setup Guide

## Overview

This guide will walk you through setting up the SonarQube MCP system, from initial installation to configuration and first use. The system consists of three main components:

1. **SonarQube MCP Server**: The core MCP server that interfaces with SonarQube
2. **Streamlit Application**: Web-based user interface for configuration and visualization
3. **SonarQube Instance**: Your SonarQube server (existing or new)

## Prerequisites

### System Requirements

- **Operating System**: Linux, macOS, or Windows
- **Python**: 3.11 or higher
- **Docker**: 20.10 or higher (for containerized deployment)
- **Kubernetes**: 1.25 or higher (for production deployment)
- **Memory**: Minimum 4GB RAM (8GB recommended for production)
- **Storage**: Minimum 10GB free space (50GB+ recommended for production)

### SonarQube Requirements

- **SonarQube**: Community Edition 9.9+ or Enterprise Edition
- **User Token**: SonarQube user token with appropriate permissions
- **Network Access**: HTTP/HTTPS access to SonarQube instance

### Required Permissions

Your SonarQube user token must have the following permissions:
- Browse projects
- Execute analysis (for project creation)
- Administer issues (for issue management)
- Administer security hotspots (for security analysis)

## Installation Methods

### Method 1: Docker Compose (Recommended for Development)

This is the easiest way to get started with the SonarQube MCP system.

#### Step 1: Clone the Repository

```bash
git clone https://github.com/your-org/sonarqube-mcp.git
cd sonarqube-mcp
```

#### Step 2: Configure Environment Variables

Create a `.env` file in the project root:

```bash
cp .env.example .env
```

Edit the `.env` file with your configuration:

```env
# SonarQube Configuration
SONARQUBE_URL=https://your-sonarqube-instance.com
SONARQUBE_TOKEN=your_sonarqube_token_here
SONARQUBE_ORGANIZATION=your_organization  # Optional for SonarCloud

# Database Configuration
POSTGRES_DB=sonarqube
POSTGRES_USER=sonarqube
POSTGRES_PASSWORD=secure_password_here

# Redis Configuration
REDIS_PASSWORD=secure_redis_password

# Application Configuration
CACHE_TTL=300
LOG_LEVEL=INFO
SERVER_DEBUG=false

# Streamlit Configuration
STREAMLIT_SERVER_HEADLESS=true
STREAMLIT_BROWSER_GATHER_USAGE_STATS=false
```

#### Step 3: Start the Services

```bash
# Start all services
docker-compose -f docker/compose/base/docker-compose.yml up -d

# Check service status
docker-compose -f docker/compose/base/docker-compose.yml ps

# View logs
docker-compose -f docker/compose/base/docker-compose.yml logs -f
```

#### Step 4: Verify Installation

1. **SonarQube**: http://localhost:9000/sonarqube
2. **Streamlit App**: http://localhost:8501
3. **MCP Server Health**: http://localhost:8000/health

### Method 2: Local Development Setup

For development or when you want more control over the components.

#### Step 1: Install Python Dependencies

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

#### Step 2: Configure Environment

```bash
export SONARQUBE_URL="https://your-sonarqube-instance.com"
export SONARQUBE_TOKEN="your_sonarqube_token_here"
export REDIS_URL="redis://localhost:6379/0"  # Optional
```

#### Step 3: Start Redis (Optional)

```bash
# Using Docker
docker run -d --name redis -p 6379:6379 redis:7-alpine

# Or install locally and start
redis-server
```

#### Step 4: Start the MCP Server

```bash
python -m src.mcp_server.server
```

#### Step 5: Start the Streamlit Application

```bash
streamlit run src/streamlit_app/app.py
```

### Method 3: Kubernetes Deployment (Production)

For production deployments with high availability and scalability.

#### Step 1: Prepare Kubernetes Cluster

Ensure you have:
- A running Kubernetes cluster (1.25+)
- `kubectl` configured to access your cluster
- Ingress controller installed (nginx recommended)
- Cert-manager for SSL certificates (optional but recommended)

#### Step 2: Configure Secrets

Create the secrets file with your actual values:

```bash
# Create namespace
kubectl apply -f k8s/namespace.yaml

# Update secrets with your values
kubectl create secret generic sonarqube-mcp-secrets \
  --from-literal=postgres-password=your_postgres_password \
  --from-literal=redis-password=your_redis_password \
  --from-literal=sonarqube-token=your_sonarqube_token \
  -n sonarqube-mcp
```

#### Step 3: Deploy Infrastructure

```bash
# Deploy PostgreSQL and Redis
kubectl apply -f k8s/postgres.yaml
kubectl apply -f k8s/redis.yaml

# Wait for databases to be ready
kubectl wait --for=condition=ready pod -l app=postgres -n sonarqube-mcp --timeout=300s
kubectl wait --for=condition=ready pod -l app=redis -n sonarqube-mcp --timeout=300s
```

#### Step 4: Deploy SonarQube (Optional)

If you don't have an existing SonarQube instance:

```bash
kubectl apply -f k8s/sonarqube.yaml
kubectl wait --for=condition=ready pod -l app=sonarqube -n sonarqube-mcp --timeout=600s
```

#### Step 5: Deploy Applications

```bash
# Build and push Docker images (if not using pre-built images)
docker build -f docker/dockerfiles/mcp-server.prod.Dockerfile -t your-registry/mcp-server:latest .
docker build -f docker/dockerfiles/streamlit.prod.Dockerfile -t your-registry/streamlit-app:latest .
docker push your-registry/mcp-server:latest
docker push your-registry/streamlit-app:latest

# Update image references in manifests
sed -i 's|sonarqube-mcp/mcp-server:latest|your-registry/mcp-server:latest|g' k8s/mcp-server.yaml
sed -i 's|sonarqube-mcp/streamlit-app:latest|your-registry/streamlit-app:latest|g' k8s/streamlit-app.yaml

# Deploy applications
kubectl apply -f k8s/mcp-server.yaml
kubectl apply -f k8s/streamlit-app.yaml

# Wait for applications to be ready
kubectl wait --for=condition=ready pod -l app=mcp-server -n sonarqube-mcp --timeout=300s
kubectl wait --for=condition=ready pod -l app=streamlit-app -n sonarqube-mcp --timeout=300s
```

#### Step 6: Configure Ingress

Update the ingress configuration with your domain:

```bash
# Edit ingress.yaml to use your domain
sed -i 's|sonarqube-mcp.yourdomain.com|your-actual-domain.com|g' k8s/ingress.yaml
sed -i 's|api.sonarqube-mcp.yourdomain.com|api.your-actual-domain.com|g' k8s/ingress.yaml

# Apply ingress
kubectl apply -f k8s/ingress.yaml
```

#### Step 7: Deploy Monitoring (Optional)

```bash
kubectl apply -f k8s/monitoring/
```

## Configuration

### SonarQube Token Setup

1. **Log in to SonarQube** as an administrator or user with appropriate permissions

2. **Navigate to User Settings**:
   - Click on your profile picture → My Account
   - Go to Security tab

3. **Generate Token**:
   - Enter a token name (e.g., "MCP Integration")
   - Select appropriate permissions or use existing permissions
   - Click "Generate"
   - **Important**: Copy the token immediately as it won't be shown again

4. **Test Token**:
   ```bash
   curl -u your_token: https://your-sonarqube-instance.com/api/authentication/validate
   ```

### Environment Configuration

#### Required Environment Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `SONARQUBE_URL` | SonarQube instance URL | `https://sonarqube.company.com` |
| `SONARQUBE_TOKEN` | SonarQube user token | `squ_1234567890abcdef` |
| `SONARQUBE_ORGANIZATION` | Organization key (SonarCloud only) | `my-org` |

#### Optional Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `REDIS_URL` | Redis connection URL | `redis://localhost:6379/0` |
| `CACHE_TTL` | Cache time-to-live in seconds | `300` |
| `LOG_LEVEL` | Logging level | `INFO` |
| `SERVER_DEBUG` | Enable debug mode | `false` |
| `MAX_RETRIES` | Maximum API retry attempts | `3` |
| `REQUEST_TIMEOUT` | API request timeout in seconds | `30` |

### Streamlit Configuration

The Streamlit application can be configured through environment variables or the web interface.

#### Web Interface Configuration

1. **Access the Application**: Navigate to your Streamlit application URL
2. **Go to Configuration Page**: Click on "Configuration" in the sidebar
3. **Enter SonarQube Details**:
   - SonarQube URL
   - Authentication token
   - Organization (if using SonarCloud)
4. **Test Connection**: Click "Test Connection" to verify settings
5. **Save Configuration**: Click "Save" to persist settings

#### File-based Configuration

Create a configuration file at `config/config.yaml`:

```yaml
sonarqube:
  url: "https://your-sonarqube-instance.com"
  token: "your_token_here"
  organization: "your_org"  # Optional

cache:
  ttl: 300
  redis_url: "redis://localhost:6379/0"

logging:
  level: "INFO"
  format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

server:
  debug: false
  max_retries: 3
  request_timeout: 30
```

## First Steps

### 1. Verify Installation

After installation, verify that all components are working:

```bash
# Check MCP server health
curl http://localhost:8000/health

# Check Streamlit application
curl http://localhost:8501/_stcore/health

# Test SonarQube connectivity
curl -u your_token: https://your-sonarqube-instance.com/api/system/status
```

### 2. Configure Authentication

1. Open the Streamlit application
2. Navigate to the Configuration page
3. Enter your SonarQube credentials
4. Test the connection
5. Save the configuration

### 3. Explore the Interface

#### Streamlit Application Features

- **Dashboard**: Overview of projects and quality metrics
- **Projects**: Detailed project exploration and management
- **Issues**: Issue management and assignment
- **Security**: Security analysis and vulnerability management
- **Chat**: Interactive MCP interface for natural language queries

#### MCP Server Integration

The MCP server can be integrated with AI assistants like Claude:

1. **Configure MCP Client**: Set up your AI assistant to connect to the MCP server
2. **Test Basic Commands**: Try simple commands like listing projects
3. **Explore Advanced Features**: Use natural language to query metrics and manage issues

### 4. Create Your First Project

Using the Streamlit interface:

1. Go to the Projects page
2. Click "Create New Project"
3. Enter project details
4. Configure quality gates
5. Run your first analysis

Using the MCP interface:

```json
{
  "name": "create_project",
  "arguments": {
    "project_key": "my-first-project",
    "name": "My First Project",
    "visibility": "private"
  }
}
```

## Troubleshooting

### Common Issues

#### Connection Issues

**Problem**: Cannot connect to SonarQube
**Solutions**:
1. Verify SonarQube URL is correct and accessible
2. Check network connectivity and firewall settings
3. Ensure SonarQube is running and healthy
4. Verify SSL certificates if using HTTPS

#### Authentication Issues

**Problem**: Authentication failed
**Solutions**:
1. Verify token is correct and not expired
2. Check token permissions in SonarQube
3. Ensure token has necessary scopes
4. Try regenerating the token

#### Performance Issues

**Problem**: Slow response times
**Solutions**:
1. Enable Redis caching
2. Increase cache TTL values
3. Check SonarQube server performance
4. Monitor network latency

#### Docker Issues

**Problem**: Containers not starting
**Solutions**:
1. Check Docker logs: `docker-compose logs`
2. Verify environment variables are set
3. Ensure ports are not in use
4. Check disk space and memory

### Getting Help

1. **Check Logs**: Always check application logs first
2. **Documentation**: Review the troubleshooting guide
3. **GitHub Issues**: Search existing issues or create a new one
4. **Community**: Join our community discussions

### Log Locations

- **Docker Compose**: `docker-compose logs [service_name]`
- **Local Development**: Console output
- **Kubernetes**: `kubectl logs -n sonarqube-mcp [pod_name]`

## Next Steps

After successful installation:

1. **Explore Features**: Try different tools and interfaces
2. **Configure Quality Gates**: Set up custom quality gates for your projects
3. **Integrate with CI/CD**: Connect with your build pipelines
4. **Set Up Monitoring**: Configure alerts and dashboards
5. **Train Your Team**: Share knowledge with team members

## Security Considerations

1. **Token Security**: Store tokens securely and rotate regularly
2. **Network Security**: Use HTTPS and proper network segmentation
3. **Access Control**: Implement proper user permissions in SonarQube
4. **Updates**: Keep all components updated with security patches
5. **Monitoring**: Monitor for suspicious activities and unauthorized access

## Performance Optimization

1. **Caching**: Enable and tune caching settings
2. **Resource Limits**: Set appropriate CPU and memory limits
3. **Database Tuning**: Optimize PostgreSQL configuration
4. **Network**: Minimize network latency between components
5. **Monitoring**: Use monitoring tools to identify bottlenecks