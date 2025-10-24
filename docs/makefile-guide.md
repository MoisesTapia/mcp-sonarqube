# Makefile Guide - SonarQube MCP

This guide explains how to use the Makefile commands for SonarQube MCP development and deployment.

## 🚀 Quick Start Commands

### For New Users

```bash
# Complete setup in one command
make quickstart

# Or step by step
make help-new          # Show detailed new user guide
make config-generate   # Create configuration files
# Edit docker/environments/.env.development.local with your SonarQube token
make build            # Build Docker images
make dev              # Start development environment
```

### For Existing Users

```bash
make status           # Check current status
make dev              # Start development environment
make stop             # Stop all services
make logs             # View logs
```

## 📋 Command Categories

### Development Commands

| Command | Description | Usage |
|---------|-------------|-------|
| `make install` | Install Python dependencies | Development setup |
| `make test` | Run tests with coverage | Code validation |
| `make lint` | Run linting (ruff, mypy) | Code quality |
| `make format` | Format code (black, ruff) | Code formatting |
| `make clean` | Clean build artifacts | Cleanup |

### Docker Operations

| Command | Description | Usage |
|---------|-------------|-------|
| `make build` | Build Docker images | Initial setup |
| `make dev` | Start development environment | Daily development |
| `make prod` | Start production environment | Production deployment |
| `make stop` | Stop all services | Shutdown |
| `make restart` | Restart all services | Apply changes |
| `make logs` | Show logs for all services | Debugging |
| `make logs-service` | Show logs for specific service | Targeted debugging |
| `make ps` | Show running containers | Status check |

### Configuration Management

| Command | Description | Usage |
|---------|-------------|-------|
| `make config-validate` | Validate configuration | Pre-deployment |
| `make config-generate` | Generate configuration files | Initial setup |

### Maintenance Operations

| Command | Description | Usage |
|---------|-------------|-------|
| `make health` | Check service health | Health monitoring |
| `make cleanup` | Clean up Docker resources | Disk space management |
| `make verify-endpoints` | Verify API endpoints | Integration testing |
| `make check-ports` | Check service ports | Network troubleshooting |
| `make validate-setup` | Validate current setup | System validation |
| `make fix-permissions` | Fix file permissions | Permission issues |

### Migration & Updates

| Command | Description | Usage |
|---------|-------------|-------|
| `make migrate` | Migrate old configurations | Version updates |
| `make update-v1.1` | Update from v1.0.0 to v1.1.0 | Specific version update |
| `make reset` | Reset everything to clean state | Nuclear option |

### Information Commands

| Command | Description | Usage |
|---------|-------------|-------|
| `make status` | Show current status | Quick overview |
| `make info` | Show environment info | System information |
| `make info-detailed` | Show detailed system information | Comprehensive diagnostics |
| `make help` | Show main help | Command reference |
| `make help-new` | Help guide for new users | New user onboarding |

### Quick Start Commands

| Command | Description | Usage |
|---------|-------------|-------|
| `make quickstart` | Complete setup and start all services | New user onboarding |
| `make help-new` | Detailed guide for new users | New user guidance |

## 🔧 Common Workflows

### Initial Setup

```bash
# 1. Clone repository
git clone <repository-url>
cd sonarqube-mcp

# 2. Quick start
make quickstart

# 3. Configure SonarQube token
# Edit docker/environments/.env.development.local
# Replace 'your_sonarqube_token_here' with actual token

# 4. Restart to apply configuration
make restart

# 5. Verify everything works
make verify-endpoints
```

### Daily Development

```bash
# Start development environment
make dev

# View logs while developing
make logs

# Run tests
make test

# Format and lint code
make format
make lint

# Stop when done
make stop
```

### Troubleshooting

```bash
# Check overall status
make status

# Validate setup
make validate-setup

# Check specific service logs
make logs-service
# Enter service name when prompted: mcp-server, streamlit-app, etc.

# Verify endpoints are working
make verify-endpoints

# Check port conflicts
make check-ports

# Fix permission issues
make fix-permissions

# Nuclear option - reset everything
make reset
```

### Updating from v1.0.0

```bash
# Automated update to v1.1.0
make update-v1.1

# Or manual migration
make migrate
```

### Production Deployment

```bash
# Validate configuration first
make config-validate

# Start production environment
make prod

# Monitor deployment
make status
make verify-endpoints
```

## 🔍 Debugging Commands

### Service-Specific Debugging

```bash
# Check individual service status
docker ps | grep sonarqube

# View specific service logs
make logs-service
# Then enter: mcp-server, streamlit-app, sonarqube, postgres, redis

# Execute commands in containers
docker compose exec mcp-server bash
docker compose exec postgres psql -U sonarqube -d sonarqube
```

### Network Debugging

```bash
# Check port mappings
make check-ports

# Test connectivity between services
docker compose exec streamlit-app curl http://mcp-server:8001/health
docker compose exec mcp-server curl http://sonarqube:9000/sonarqube/api/system/status
```

### Performance Monitoring

```bash
# Show resource usage
make info-detailed

# Monitor in real-time
docker stats

# Check disk usage
docker system df
```

## ⚠️ Important Notes

### Environment Files

The Makefile uses these environment configurations:

- **Development**: `docker/environments/.env.development`
- **Local Override**: `docker/environments/.env.development.local` (created by `make config-generate`)
- **Production**: `docker/environments/.env.production`

### Port Configuration

Current port mappings (v1.1.0):

- **Streamlit App**: 8501
- **SonarQube**: 9000
- **MCP Server**: 8001 (updated from 8000)
- **PostgreSQL**: 5432
- **Redis**: 6379
- **pgAdmin**: 8082
- **Redis Commander**: 8081
- **Mailhog**: 8025

### Docker Compose Files

The Makefile uses layered Docker Compose configuration:

```bash
# Development
docker compose -f docker/compose/base/docker-compose.yml \
               -f docker/compose/environments/development.yml \
               --env-file docker/environments/.env.development

# Production  
docker compose -f docker/compose/base/docker-compose.yml \
               -f docker/compose/environments/production.yml \
               --env-file docker/environments/.env.production
```

## 🆘 Getting Help

### Built-in Help

```bash
make help           # Main command reference
make help-new       # New user guide
make info           # System information
make status         # Current status
```

### Troubleshooting Steps

1. **Check Status**: `make status`
2. **Validate Setup**: `make validate-setup`
3. **Check Logs**: `make logs`
4. **Verify Endpoints**: `make verify-endpoints`
5. **Check Ports**: `make check-ports`
6. **Fix Permissions**: `make fix-permissions`
7. **Reset if Needed**: `make reset`

### Common Issues

| Issue | Solution |
|-------|----------|
| Port conflicts | `make check-ports`, change ports in development.yml |
| Permission errors | `make fix-permissions` |
| Service not starting | `make logs-service`, check specific service logs |
| Configuration errors | `make validate-setup`, `make config-generate` |
| Old version issues | `make update-v1.1` or `make migrate` |
| Complete failure | `make reset`, then `make quickstart` |

---

**For more help, see the main [README.md](../README.md) or [Docker documentation](../docker/README.md)**