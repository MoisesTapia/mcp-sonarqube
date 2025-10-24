# Docker Configuration for SonarQube MCP

This directory contains Docker Compose configurations for running the SonarQube MCP system in different environments.

## 📁 Directory Structure

```
docker/
├── README.md                           # This file
├── compose/
│   ├── base/
│   │   └── docker-compose.yml         # Base services configuration
│   └── environments/
│       ├── development.yml            # Development overrides
│       ├── staging.yml               # Staging overrides (future)
│       └── production.yml            # Production overrides (future)
├── dockerfiles/
│   ├── mcp-server.Dockerfile         # MCP Server image
│   ├── mcp-server.prod.Dockerfile    # Production MCP Server image
│   ├── streamlit.Dockerfile          # Streamlit App image
│   └── streamlit.prod.Dockerfile     # Production Streamlit App image
├── environments/
│   ├── .env.development              # Development environment variables
│   ├── .env.staging                  # Staging environment variables (future)
│   └── .env.production               # Production environment variables (future)
└── config/
    ├── postgresql/
    │   └── init/
    │       └── init.sql              # PostgreSQL initialization
    ├── redis/
    │   └── redis.conf                # Redis configuration
    └── pgadmin/
        └── servers.json              # pgAdmin server configuration
```

## 🚀 Quick Start

### Development Environment

1. **Configure environment variables**:
   ```bash
   # Copy and edit the development environment file
   cp docker/environments/.env.development.example docker/environments/.env.development
   # Edit the file with your SonarQube token and other settings
   ```

2. **Start all services**:
   ```bash
   docker compose -f docker/compose/base/docker-compose.yml \
                   -f docker/compose/environments/development.yml \
                   --env-file docker/environments/.env.development \
                   up --build
   ```

3. **Access services**:

### 🌐 Service Access Table

| Service | Container Name | URL | Port | Internal Port | Credentials | Status |
|---------|----------------|-----|------|---------------|-------------|---------|
| **Streamlit App** | sonarqube-streamlit-app | http://localhost:8501 | 8501 | 8501 | - | Main UI |
| **SonarQube** | sonarqube-server | http://localhost:9000/sonarqube | 9000 | 9000 | admin / admin | Code Analysis |
| **MCP Server** | sonarqube-mcp-server | http://localhost:8001 | 8001 | 8001 | - | API Server |
| **pgAdmin** | sonarqube-pgadmin | http://localhost:8082 | 8082 | 80 | admin@example.com / admin | DB Admin |
| **Redis Commander** | sonarqube-redis-commander | http://localhost:8081 | 8081 | 8081 | - | Cache Admin |
| **Mailhog** | sonarqube-mailhog | http://localhost:8025 | 8025 | 8025 | - | Email Testing |
| **PostgreSQL** | sonarqube-postgres | localhost:5432 | 5432 | 5432 | sonarqube / sonarqube_dev_password | Database |
| **Redis** | sonarqube-redis | localhost:6379 | 6379 | 6379 | redis_dev_password | Cache |

## 🐳 Services Overview

### 🐳 Container Details

#### Core Services

| Service | Container Name | Image | Host Port | Container Port | Network | Description |
|---------|----------------|-------|-----------|----------------|---------|-------------|
| **postgres** | sonarqube-postgres | postgres:15-alpine | 5432 | 5432 | sonarqube-mcp | PostgreSQL database for SonarQube |
| **redis** | sonarqube-redis | redis:7-alpine | 6379 | 6379 | sonarqube-mcp | Redis cache for performance |
| **sonarqube** | sonarqube-server | sonarqube:10.3-community | 9000 | 9000 | sonarqube-mcp | SonarQube code analysis platform |
| **mcp-server** | sonarqube-mcp-server | Custom build | 8001 | 8001 | sonarqube-mcp | MCP protocol server |
| **streamlit-app** | sonarqube-streamlit-app | Custom build | 8501 | 8501 | sonarqube-mcp | Streamlit web interface |

#### Development Tools (Development Environment Only)

| Service | Container Name | Image | Host Port | Container Port | Network | Description |
|---------|----------------|-------|-----------|----------------|---------|-------------|
| **pgadmin** | sonarqube-pgadmin | dpage/pgadmin4 | 8082 | 80 | sonarqube-mcp | PostgreSQL administration |
| **redis-commander** | sonarqube-redis-commander | rediscommander/redis-commander | 8081 | 8081 | sonarqube-mcp | Redis management interface |
| **mailhog** | sonarqube-mailhog | mailhog/mailhog | 8025, 1025 | 8025, 1025 | sonarqube-mcp | Email testing tool |

## ⚙️ Environment Configuration

### Development (.env.development)

```env
# Database Configuration
POSTGRES_DB=sonarqube
POSTGRES_USER=sonarqube
POSTGRES_PASSWORD=sonarqube_dev_password

# Redis Configuration
REDIS_PASSWORD=redis_dev_password

# SonarQube Configuration
SONARQUBE_TOKEN=your_sonarqube_token_here
SONARQUBE_ORGANIZATION=

# Application Configuration
CACHE_TTL=60
LOG_LEVEL=DEBUG
SERVER_DEBUG=true

# Streamlit Configuration
STREAMLIT_SERVER_HEADLESS=false
STREAMLIT_BROWSER_GATHER_USAGE_STATS=false

# Java Options (reduced for development)
SONAR_CE_JAVAOPTS=-Xmx512m -Xms256m
SONAR_WEB_JAVAOPTS=-Xmx512m -Xms256m
```

### Required Environment Variables

| Variable | Description | Required | Default |
|----------|-------------|----------|---------|
| `POSTGRES_PASSWORD` | PostgreSQL password | Yes | - |
| `REDIS_PASSWORD` | Redis password | Yes | - |
| `SONARQUBE_TOKEN` | SonarQube user token | Yes | - |
| `SONARQUBE_ORGANIZATION` | SonarQube organization (optional) | No | - |
| `LOG_LEVEL` | Application log level | No | INFO |
| `SERVER_DEBUG` | Enable debug mode | No | false |
| `CACHE_TTL` | Cache time-to-live in seconds | No | 300 |

## 🔧 Common Commands

### Basic Operations

```bash
# Start services in foreground
docker compose -f docker/compose/base/docker-compose.yml \
                -f docker/compose/environments/development.yml \
                --env-file docker/environments/.env.development \
                up --build

# Start services in background
docker compose -f docker/compose/base/docker-compose.yml \
                -f docker/compose/environments/development.yml \
                --env-file docker/environments/.env.development \
                up --build -d

# Stop services
docker compose down

# Stop services and remove volumes
docker compose down -v

# View logs
docker compose logs -f

# View logs for specific service
docker compose logs -f mcp-server
```

### Development Commands

```bash
# Rebuild specific service
docker compose up --build mcp-server

# Execute command in running container
docker compose exec mcp-server bash
docker compose exec postgres psql -U sonarqube -d sonarqube

# Restart specific service
docker compose restart streamlit-app

# Scale service (if supported)
docker compose up --scale mcp-server=2
```

### Maintenance Commands

```bash
# Clean up unused images and containers
docker system prune -f

# Clean up everything including volumes
docker system prune -a --volumes

# View resource usage
docker compose top
docker stats

# Export/Import volumes
docker run --rm -v sonarqube_data:/data -v $(pwd):/backup alpine tar czf /backup/sonarqube_backup.tar.gz -C /data .
```

## 🏗️ Custom Images

### MCP Server Image

Built from `docker/dockerfiles/mcp-server.Dockerfile`:
- Based on Python 3.11-slim
- Includes all Python dependencies
- Runs as non-root user for security
- Health check endpoint at `/health`

### Streamlit App Image

Built from `docker/dockerfiles/streamlit.Dockerfile`:
- Based on Python 3.11-slim
- Includes Streamlit and dependencies
- Configured for production use
- Health check endpoint at `/_stcore/health`

## 🔒 Security Considerations

### Development Environment

- Uses default passwords (change for production)
- Exposes all ports for development access
- Includes development tools with admin access
- Debug mode enabled for troubleshooting

### Production Recommendations

- Use strong, unique passwords
- Limit exposed ports
- Remove development tools
- Enable SSL/TLS termination
- Use secrets management
- Regular security updates

## 🔌 Port Reference

### Quick Port Reference

| Port | Service | Protocol | Access | Purpose |
|------|---------|----------|--------|---------|
| **8501** | Streamlit App | HTTP | External | Main web interface |
| **9000** | SonarQube | HTTP | External | Code analysis dashboard |
| **8001** | MCP Server | HTTP | External | MCP API endpoints |
| **8082** | pgAdmin | HTTP | External | Database administration |
| **8081** | Redis Commander | HTTP | External | Cache management |
| **8025** | Mailhog Web | HTTP | External | Email testing interface |
| **5432** | PostgreSQL | TCP | External | Database connections |
| **6379** | Redis | TCP | External | Cache connections |
| **1025** | Mailhog SMTP | SMTP | External | Email testing SMTP |

### Port Conflicts Resolution

If you encounter port conflicts, you can modify the ports in `docker/compose/environments/development.yml`:

```yaml
services:
  streamlit-app:
    ports:
      - "8502:8501"  # Change host port to 8502
  
  sonarqube:
    ports:
      - "9001:9000"  # Change host port to 9001
```

## 📊 Monitoring and Health Checks

### Health Check Endpoints

| Service | Endpoint | Expected Response |
|---------|----------|-------------------|
| MCP Server | http://localhost:8001/health | 200 OK |
| Streamlit App | http://localhost:8501/_stcore/health | 200 OK |
| SonarQube | http://localhost:9000/sonarqube/api/system/status | 200 OK |
| PostgreSQL | `pg_isready` command | Success |
| Redis | `redis-cli ping` command | PONG |

### Resource Monitoring

```bash
# View resource usage
docker stats

# View detailed container info
docker compose ps
docker inspect <container_name>

# Check logs for errors
docker compose logs --tail=100 | grep -i error
```

## 🐛 Troubleshooting

### Common Issues

#### Port-Related Issues

1. **Port conflicts**:
   ```bash
   # Check what's using specific ports
   netstat -tulpn | grep :8501  # Streamlit
   netstat -tulpn | grep :9000  # SonarQube
   netstat -tulpn | grep :8001  # MCP Server
   netstat -tulpn | grep :5432  # PostgreSQL
   netstat -tulpn | grep :6379  # Redis
   
   # Or check all our ports at once
   netstat -tulpn | grep -E ":(8501|9000|8001|8082|8081|8025|5432|6379)"
   
   # Change ports in development.yml if conflicts exist
   ```

2. **Service not accessible on expected port**:
   ```bash
   # Check if container is running and port is mapped
   docker ps | grep <service_name>
   
   # Check specific port mapping
   docker port <container_name>
   
   # Test port connectivity
   curl -f http://localhost:8501/_stcore/health  # Streamlit
   curl -f http://localhost:8001/health          # MCP Server
   curl -f http://localhost:9000/sonarqube/api/system/status  # SonarQube
   ```

3. **Port binding errors during startup**:
   ```bash
   # Check what's using the port
   netstat -tulpn | grep :<port_number>
   
   # Kill process using the port (if safe)
   sudo kill -9 $(lsof -t -i:<port_number>)
   
   # Or change the port mapping in development.yml
   ```

4. **Permission issues**:
   ```bash
   # Fix volume permissions
   sudo chown -R $USER:$USER logs/ data/
   ```

3. **Memory issues**:
   ```bash
   # Reduce Java heap size in .env file
   SONAR_WEB_JAVAOPTS=-Xmx256m -Xms128m
   ```

4. **Database connection issues**:
   ```bash
   # Check PostgreSQL logs
   docker compose logs postgres
   # Test connection
   docker compose exec postgres psql -U sonarqube -d sonarqube -c "SELECT 1;"
   ```

### Debug Commands

```bash
# Enter container for debugging
docker compose exec mcp-server bash

# Check environment variables
docker compose exec mcp-server env

# Test network connectivity
docker compose exec mcp-server ping postgres
docker compose exec mcp-server curl http://sonarqube:9000/sonarqube/api/system/status

# Check file permissions
docker compose exec mcp-server ls -la /app/
```

## 🔄 Updates and Maintenance

### Updating Images

```bash
# Pull latest base images
docker compose pull

# Rebuild custom images
docker compose build --no-cache

# Update and restart
docker compose up --build --force-recreate
```

### Backup and Restore

```bash
# Backup volumes
docker run --rm -v postgres_data:/data -v $(pwd):/backup alpine tar czf /backup/postgres_backup.tar.gz -C /data .
docker run --rm -v sonarqube_data:/data -v $(pwd):/backup alpine tar czf /backup/sonarqube_backup.tar.gz -C /data .

# Restore volumes
docker run --rm -v postgres_data:/data -v $(pwd):/backup alpine tar xzf /backup/postgres_backup.tar.gz -C /data
docker run --rm -v sonarqube_data:/data -v $(pwd):/backup alpine tar xzf /backup/sonarqube_backup.tar.gz -C /data
```

## 📝 Configuration Files

### PostgreSQL Configuration

- **Location**: `docker/config/postgresql/init/init.sql`
- **Purpose**: Database initialization and optimization
- **Customization**: Add custom schemas, users, or settings

### Redis Configuration

- **Location**: `docker/config/redis/redis.conf`
- **Purpose**: Redis server configuration
- **Customization**: Memory limits, persistence settings, security

### pgAdmin Configuration

- **Location**: `docker/config/pgadmin/servers.json`
- **Purpose**: Pre-configure PostgreSQL server in pgAdmin
- **Customization**: Add multiple servers or change connection settings

## 📋 Recent Updates and Changes

### Version 1.1.0 - Latest Changes

#### ✅ **Fixed Issues**
- **MCP Server Port**: Corrected from 8000 to 8001 for consistency across all configurations
- **Session State Initialization**: Fixed Streamlit session state initialization errors
- **Deprecation Warnings**: Updated `use_container_width=True` to `width="stretch"` for Streamlit 1.50+
- **Docker Compose Syntax**: Removed obsolete `version` field from production configuration
- **URL Consistency**: Fixed MCP server URL references in client configurations

#### 🔧 **Configuration Updates**
- **Production Environment**: Updated `.env.production` with correct MCP server port (8001)
- **Docker Compose**: Cleaned up production overrides and commented unused services
- **Health Checks**: Improved health check endpoints and error handling
- **Logging**: Enhanced structured logging with better error tracking

#### 🐛 **Bug Fixes**
- **TypeError in fromisoformat**: Added robust datetime handling for sync status
- **MCP Connection Recursion**: Fixed infinite recursion in health check methods
- **Container Networking**: Corrected service name references in Docker network
- **Permission Issues**: Improved file permission handling with graceful fallbacks

#### 🚀 **Performance Improvements**
- **Async Operations**: Better async/await handling in MCP client
- **Error Handling**: More robust error handling with fallback mechanisms
- **Resource Usage**: Optimized container resource limits and health checks

### Migration Notes

If you're upgrading from a previous version:

1. **Update Environment Files**: 
   ```bash
   # Update MCP server port in your .env files
   sed -i 's/8000/8001/g' docker/environments/.env.development
   ```

2. **Rebuild Containers**:
   ```bash
   docker compose down
   docker compose build --no-cache
   docker compose up -d
   ```

3. **Verify Services**:
   ```bash
   # Check all services are healthy
   docker compose ps
   curl -f http://localhost:8001/health  # MCP Server (new port)
   curl -f http://localhost:8501/_stcore/health  # Streamlit
   ```

## 🚀 Next Steps

1. **Configure your SonarQube token** in the environment file
2. **Start the development environment** with the provided commands
3. **Access the Streamlit interface** at http://localhost:8501
4. **Explore the API** at http://localhost:8001 (updated port)
5. **Check the troubleshooting section** if you encounter issues

For more detailed information, see the main [README.md](../README.md) and [documentation](../docs/).