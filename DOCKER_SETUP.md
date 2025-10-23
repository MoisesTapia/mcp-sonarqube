# Docker Setup Guide for SonarQube MCP

This guide provides comprehensive instructions for setting up and managing the SonarQube MCP project using the new organized Docker structure.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Quick Start](#quick-start)
- [New Docker Structure](#new-docker-structure)
- [Configuration](#configuration)
- [Environment Management](#environment-management)
- [Services Overview](#services-overview)
- [Management Commands](#management-commands)
- [Troubleshooting](#troubleshooting)

## Prerequisites

### System Requirements

- **Docker**: Version 20.10 or higher
- **Docker Compose**: Version 2.0 or higher
- **Memory**: Minimum 8GB RAM (16GB recommended for production)
- **Storage**: Minimum 20GB free space
- **OS**: Linux, macOS, or Windows with WSL2

## Quick Start

### 1. Clone and Setup

```bash
git clone <repository-url>
cd sonarqube-mcp
make quickstart
```

### 2. Configure Environment

Edit the appropriate environment file:
```bash
# For development
vim docker/environments/.env.development

# Set your SonarQube token
SONARQUBE_TOKEN=your_sonarqube_token_here
```

### 3. Start Services

```bash
# Development environment
make dev
# or
bash docker/scripts/deploy.sh deploy development

# Production environment
make prod
# or
bash docker/scripts/deploy.sh deploy production
```

## New Docker Structure

The Docker configuration is now organized in a clean, hierarchical structure:

```
docker/
├── README.md                    # Docker documentation
├── .dockerignore               # Docker ignore file
├── dockerfiles/                # All Dockerfile definitions
│   ├── mcp-server.Dockerfile   # MCP server image
│   └── streamlit.Dockerfile    # Streamlit application image
├── compose/                    # Docker Compose configurations
│   ├── base/                   # Base compose files
│   │   └── docker-compose.yml  # Core services
│   ├── environments/           # Environment-specific overrides
│   │   ├── development.yml     # Development settings
│   │   ├── staging.yml         # Staging settings
│   │   └── production.yml      # Production settings
│   └── services/               # Service-specific compose files
│       ├── monitoring.yml      # Monitoring stack
│       └── infrastructure.yml  # Infrastructure services
├── config/                     # Service configurations
│   ├── nginx/                  # Nginx configurations
│   ├── postgresql/             # PostgreSQL configurations
│   ├── redis/                  # Redis configurations
│   ├── prometheus/             # Prometheus configurations
│   ├── grafana/                # Grafana configurations
│   └── alertmanager/           # Alertmanager configurations
├── scripts/                    # Docker management scripts
│   ├── build.sh               # Build all images
│   ├── deploy.sh              # Deployment script
│   ├── health-check.sh        # Health check script
│   ├── backup-restore.sh      # Backup and restore
│   ├── validate-config.sh     # Configuration validation
│   ├── manage-secrets.sh      # Secrets management
│   └── resource-monitor.sh    # Resource monitoring
└── environments/               # Environment-specific configurations
    ├── .env.development        # Development variables
    ├── .env.staging           # Staging variables
    ├── .env.production        # Production variables
    └── secrets/               # Secrets management (gitignored)
```

## Configuration

### Environment Files

Each environment has its own configuration file with appropriate settings:

- **`docker/environments/.env.development`**: Development settings with debug enabled
- **`docker/environments/.env.staging`**: Staging environment with production-like settings
- **`docker/environments/.env.production`**: Production environment with security hardening

### Key Benefits of New Structure

1. **Environment Separation**: Clear separation between development, staging, and production
2. **Service Modularity**: Services can be enabled/disabled per environment
3. **Configuration Management**: Centralized configuration with environment-specific overrides
4. **Security**: Secrets are properly managed and separated by environment
5. **Scalability**: Easy to add new services or environments

## Environment Management

### Development Environment

```bash
# Start development environment
bash docker/scripts/deploy.sh deploy development

# Features:
# - Hot reload enabled
# - Debug logging
# - Development tools (Redis Commander, pgAdmin, Mailhog)
# - Exposed ports for direct access
# - Relaxed security settings
```

**Development Services:**
- Streamlit App: http://localhost:8501
- SonarQube: http://localhost:9000
- Grafana: http://localhost:3000 (admin/admin)
- Prometheus: http://localhost:9090
- Redis Commander: http://localhost:8081
- pgAdmin: http://localhost:8082
- Mailhog: http://localhost:8025

### Staging Environment

```bash
# Start staging environment
bash docker/scripts/deploy.sh deploy staging

# Features:
# - Production-like settings
# - Limited debugging
# - Resource constraints
# - Security enabled
```

### Production Environment

```bash
# Start production environment
bash docker/scripts/deploy.sh deploy production

# Features:
# - Security hardening
# - Resource optimization
# - Monitoring and alerting
# - Backup automation
# - SSL/TLS enabled
```

## Services Overview

### Core Application Services

- **MCP Server**: FastMCP server for SonarQube integration
- **Streamlit App**: Web interface for SonarQube MCP
- **SonarQube**: Code quality analysis platform

### Infrastructure Services

- **PostgreSQL**: Database for SonarQube
- **Redis**: Caching and session storage
- **Nginx**: Reverse proxy and load balancer

### Monitoring Services

- **Prometheus**: Metrics collection
- **Grafana**: Monitoring dashboards
- **Node Exporter**: System metrics
- **Alertmanager**: Alert management (production only)

## Management Commands

### Using Make Commands

```bash
# Build images
make build

# Start environments
make dev              # Development
make prod             # Production

# Configuration
make config-validate  # Validate configuration
make config-generate  # Generate configuration
make secrets-generate # Generate secrets

# Maintenance
make backup           # Create backup
make health           # Check service health
make monitor          # Start monitoring
make cleanup          # Clean up resources
```

### Using Docker Scripts

```bash
# Build operations
bash docker/scripts/build.sh build development
bash docker/scripts/build.sh build-cache production
bash docker/scripts/build.sh clean-build

# Deployment operations
bash docker/scripts/deploy.sh deploy development
bash docker/scripts/deploy.sh scale production mcp-server 3
bash docker/scripts/deploy.sh update staging
bash docker/scripts/deploy.sh status production

# Configuration management
bash docker/scripts/validate-config.sh docker/environments/.env.production
bash docker/scripts/manage-secrets.sh generate
bash docker/scripts/manage-secrets.sh rotate

# Maintenance operations
bash docker/scripts/health-check.sh
bash docker/scripts/backup-restore.sh backup
bash docker/scripts/resource-monitor.sh
```

## Configuration Management

### Environment Variables

Each environment file contains comprehensive configuration:

```bash
# Core services
SONARQUBE_TOKEN=your_token_here
POSTGRES_PASSWORD=secure_password
REDIS_PASSWORD=secure_redis_password

# Application settings
LOG_LEVEL=INFO
CACHE_TTL=300
SERVER_DEBUG=false

# Resource limits
SONARQUBE_MEMORY_LIMIT=4g
POSTGRES_MEMORY_LIMIT=1g
REDIS_MEMORY_LIMIT=512m
```

### Secrets Management

```bash
# Generate new secrets
bash docker/scripts/manage-secrets.sh generate

# Rotate existing secrets
bash docker/scripts/manage-secrets.sh rotate

# Export secrets to environment file
bash docker/scripts/manage-secrets.sh export docker/environments/.env.production
```

### Configuration Validation

```bash
# Validate specific environment
bash docker/scripts/validate-config.sh docker/environments/.env.production

# Validate current .env file
make config-validate
```

## Deployment Workflows

### Development Deployment

```bash
# Quick development setup
make quickstart

# Manual development setup
bash docker/scripts/build.sh build development
bash docker/scripts/deploy.sh deploy development
```

### Production Deployment

```bash
# Prepare production environment
cp docker/environments/.env.production .env
bash docker/scripts/manage-secrets.sh generate
bash docker/scripts/validate-config.sh .env

# Deploy to production
bash docker/scripts/build.sh build production
bash docker/scripts/deploy.sh deploy production

# Verify deployment
bash docker/scripts/health-check.sh
bash docker/scripts/deploy.sh status production
```

### Staging Deployment

```bash
# Deploy to staging
bash docker/scripts/deploy.sh deploy staging

# Update staging with latest changes
bash docker/scripts/deploy.sh update staging
```

## Monitoring and Maintenance

### Health Checks

```bash
# Check all services
bash docker/scripts/health-check.sh

# Check specific environment
bash docker/scripts/deploy.sh status production
```

### Resource Monitoring

```bash
# Start continuous monitoring
bash docker/scripts/resource-monitor.sh

# Generate resource report
bash docker/scripts/resource-monitor.sh --report
```

### Backup and Restore

```bash
# Create backup
bash docker/scripts/backup-restore.sh backup

# List available backups
bash docker/scripts/backup-restore.sh list

# Restore from backup
bash docker/scripts/backup-restore.sh restore backup-name
```

### Log Management

```bash
# View logs for environment
bash docker/scripts/deploy.sh logs development

# View logs for specific service
bash docker/scripts/deploy.sh logs production mcp-server

# Aggregate logs
bash docker/scripts/log-aggregator.sh collect
```

## Troubleshooting

### Common Issues

1. **Port Conflicts**: Development environment uses different ports (8080, 8443) to avoid conflicts
2. **Resource Issues**: Check resource limits in environment files
3. **Configuration Errors**: Use `bash docker/scripts/validate-config.sh` to validate
4. **Service Health**: Use `bash docker/scripts/health-check.sh` to check all services

### Debug Mode

Enable debug mode by editing the environment file:
```bash
# In docker/environments/.env.development
DEBUG=true
LOG_LEVEL=DEBUG
SERVER_DEBUG=true
```

### Service Scaling

```bash
# Scale MCP server to 3 replicas
bash docker/scripts/deploy.sh scale production mcp-server 3

# Scale back to 1 replica
bash docker/scripts/deploy.sh scale production mcp-server 1
```

## Migration from Old Structure

If you're migrating from the old Docker structure:

1. **Remove old files**: Old docker-compose files and Dockerfiles have been cleaned up
2. **Update commands**: Use new make commands or docker scripts
3. **Update CI/CD**: Update deployment scripts to use new structure
4. **Environment files**: Migrate settings to new environment files in `docker/environments/`

## Security Considerations

### Production Security

1. **Secrets Management**: Use `docker/scripts/manage-secrets.sh` for secure secret generation
2. **Environment Separation**: Each environment has its own configuration and secrets
3. **Network Security**: Custom Docker networks with proper isolation
4. **SSL/TLS**: Automatic SSL certificate management
5. **Resource Limits**: Proper resource constraints to prevent resource exhaustion

### Security Checklist

- [ ] Generate strong secrets for production
- [ ] Enable HTTPS in production environment
- [ ] Configure firewall rules
- [ ] Set up monitoring and alerting
- [ ] Enable audit logging
- [ ] Configure backup encryption
- [ ] Review and update security settings regularly

## Performance Optimization

### Resource Tuning

Resource limits are configured per environment in the environment files:

```bash
# Production resource limits
SONARQUBE_MEMORY_LIMIT=4g
POSTGRES_MEMORY_LIMIT=1g
REDIS_MEMORY_LIMIT=512m
MCP_SERVER_MEMORY_LIMIT=1g
STREAMLIT_MEMORY_LIMIT=1g
```

### JVM Tuning

SonarQube JVM settings are environment-specific:

```bash
# Production JVM settings
SONAR_WEB_JAVAOPTS=-Xmx2G -Xms1G -XX:+UseG1GC
SONAR_CE_JAVAOPTS=-Xmx2G -Xms1G -XX:+UseG1GC
```

## Support and Documentation

### Additional Resources

- [Docker Documentation](https://docs.docker.com/)
- [SonarQube Documentation](https://docs.sonarqube.org/)
- [Streamlit Documentation](https://docs.streamlit.io/)

### Getting Help

1. **Check service health**: `bash docker/scripts/health-check.sh`
2. **Review logs**: `bash docker/scripts/deploy.sh logs <environment>`
3. **Validate configuration**: `bash docker/scripts/validate-config.sh`
4. **Monitor resources**: `bash docker/scripts/resource-monitor.sh`

The new Docker structure provides a professional, scalable, and maintainable approach to managing the SonarQube MCP project across different environments.