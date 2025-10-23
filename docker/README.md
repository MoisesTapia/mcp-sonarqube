# Docker Configuration Structure

This directory contains all Docker-related configurations organized by environment and service type.

## Directory Structure

```
docker/
├── README.md                    # This file
├── dockerfiles/                 # All Dockerfile definitions
│   ├── mcp-server.Dockerfile   # MCP server image
│   └── streamlit.Dockerfile    # Streamlit application image
├── compose/                     # Docker Compose configurations
│   ├── base/                   # Base compose files
│   │   └── docker-compose.yml  # Base services configuration
│   ├── environments/           # Environment-specific overrides
│   │   ├── development.yml     # Development environment
│   │   ├── staging.yml         # Staging environment
│   │   └── production.yml      # Production environment
│   └── services/               # Service-specific compose files
│       ├── monitoring.yml      # Monitoring stack (Prometheus, Grafana)
│       ├── databases.yml       # Database services (PostgreSQL, Redis)
│       └── infrastructure.yml  # Infrastructure services (Nginx, etc.)
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
│   ├── backup.sh              # Backup script
│   ├── logs.sh                # Log management
│   └── cleanup.sh             # Cleanup script
└── environments/               # Environment-specific configurations
    ├── .env.development        # Development environment variables
    ├── .env.staging           # Staging environment variables
    ├── .env.production        # Production environment variables
    └── secrets/               # Secrets management
        ├── development/       # Development secrets
        ├── staging/          # Staging secrets
        └── production/       # Production secrets
```

## Usage

### Development Environment
```bash
# Start development environment
docker-compose -f docker/compose/base/docker-compose.yml \
               -f docker/compose/environments/development.yml \
               --env-file docker/environments/.env.development up -d

# Or use the script
bash docker/scripts/deploy.sh development
```

### Staging Environment
```bash
# Start staging environment
docker-compose -f docker/compose/base/docker-compose.yml \
               -f docker/compose/environments/staging.yml \
               --env-file docker/environments/.env.staging up -d

# Or use the script
bash docker/scripts/deploy.sh staging
```

### Production Environment
```bash
# Start production environment
docker-compose -f docker/compose/base/docker-compose.yml \
               -f docker/compose/environments/production.yml \
               --env-file docker/environments/.env.production up -d

# Or use the script
bash docker/scripts/deploy.sh production
```

## Environment Variables

Each environment has its own `.env` file with appropriate configurations:

- **Development**: Relaxed security, debug enabled, development tools included
- **Staging**: Production-like settings with some debugging capabilities
- **Production**: Hardened security, optimized performance, monitoring enabled

## Scripts

All management operations are available through scripts in the `scripts/` directory:

- `build.sh`: Build all Docker images
- `deploy.sh`: Deploy to specific environment
- `health-check.sh`: Check health of all services
- `backup.sh`: Create backups of persistent data
- `logs.sh`: Aggregate and manage logs
- `cleanup.sh`: Clean up Docker resources

## Security

- Secrets are managed separately for each environment
- Production secrets should never be committed to version control
- Use Docker secrets or external secret management in production
- All images run with non-root users
- Network segmentation is implemented for production