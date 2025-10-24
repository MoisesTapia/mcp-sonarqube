# Makefile for SonarQube MCP project

.PHONY: help install test lint format clean dev prod build stop restart logs logs-service ps \
         config-validate config-generate health cleanup verify-endpoints check-ports status \
         migrate update-v1.1 reset info-detailed fix-permissions validate-setup help-new quickstart

# Default target
help:
	@echo "SonarQube MCP - Available Commands"
	@echo "=================================="
	@echo ""
	@echo "Development:"
	@echo "  install          - Install Python dependencies"
	@echo "  test             - Run tests"
	@echo "  lint             - Run linting"
	@echo "  format           - Format code"
	@echo "  clean            - Clean build artifacts"
	@echo ""
	@echo "Docker Operations:"
	@echo "  build            - Build Docker images"
	@echo "  dev              - Start development environment"
	@echo "  prod             - Start production environment"
	@echo "  stop             - Stop all services"
	@echo "  restart          - Restart all services"
	@echo "  logs             - Show logs for all services"
	@echo "  logs-service     - Show logs for specific service"
	@echo "  ps               - Show running containers"
	@echo ""
	@echo "Configuration:"
	@echo "  config-validate  - Validate configuration"
	@echo "  config-generate  - Generate configuration files"
	@echo ""
	@echo "Maintenance:"
	@echo "  health           - Check service health"
	@echo "  cleanup          - Clean up Docker resources"
	@echo "  verify-endpoints - Verify API endpoints are working"
	@echo "  check-ports      - Check if services are running on correct ports"
	@echo "  validate-setup   - Validate current setup"
	@echo "  fix-permissions  - Fix file permissions"
	@echo ""
	@echo "Migration & Updates:"
	@echo "  migrate          - Migrate old configurations"
	@echo "  update-v1.1      - Update from v1.0.0 to v1.1.0"
	@echo "  reset            - Reset everything to clean state"
	@echo ""
	@echo "Information:"
	@echo "  status           - Show current status"
	@echo "  info-detailed    - Show detailed system information"
	@echo ""
	@echo "Quick Start:"
	@echo "  quickstart       - Complete setup and start all services"
	@echo "  help-new         - Detailed guide for new users"

# Variables
DOCKER_COMPOSE_DEV = docker compose -f docker/compose/base/docker-compose.yml -f docker/compose/environments/development.yml --env-file docker/environments/.env.development
DOCKER_COMPOSE_PROD = docker compose -f docker/compose/base/docker-compose.yml -f docker/compose/environments/production.yml --env-file docker/environments/.env.production
PYTHON = python
PIP = pip

# =============================================================================
# DEVELOPMENT COMMANDS
# =============================================================================

# Install dependencies
install:
	@echo "Installing Python dependencies..."
	$(PIP) install -r requirements-dev.txt
	@echo "Dependencies installed successfully"

# Run tests
test:
	@echo "Running tests..."
	pytest tests/ -v --cov=src --cov-report=html --cov-report=term
	@echo "Tests completed"

# Run linting
lint:
	@echo "Running linting..."
	ruff check src/ tests/
	mypy src/
	@echo "Linting completed"

# Format code
format:
	@echo "Formatting code..."
	black src/ tests/
	ruff check --fix src/ tests/
	@echo "Code formatting completed"

# Clean build artifacts
clean:
	@echo "Cleaning build artifacts..."
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	rm -rf build/ dist/ .coverage htmlcov/ .pytest_cache/
	@echo "Cleanup completed"

# =============================================================================
# DOCKER OPERATIONS
# =============================================================================

# Build Docker images
build:
	@echo "Building Docker images..."
	$(DOCKER_COMPOSE_DEV) build
	@echo "Docker images built successfully"

# Development environment
dev:
	@echo "Starting development environment..."
	$(DOCKER_COMPOSE_DEV) up -d
	@echo "Development environment started"

# Production environment
prod:
	@echo "Starting production environment..."
	$(DOCKER_COMPOSE_PROD) up -d
	@echo "Production environment started"

# Stop all services
stop:
	@echo "Stopping all services..."
	$(DOCKER_COMPOSE_DEV) down
	@echo "All services stopped"

# Restart all services
restart:
	@echo "Restarting all services..."
	$(DOCKER_COMPOSE_DEV) restart
	@echo "All services restarted"

# Show logs
logs:
	@echo "Showing logs for all services..."
	$(DOCKER_COMPOSE_DEV) logs -f

# Show logs for specific service
logs-service:
	@read -p "Enter service name (mcp-server, streamlit-app, sonarqube, postgres, redis): " service; \
	$(DOCKER_COMPOSE_DEV) logs -f $$service

# Show running containers
ps:
	@echo "Running containers:"
	$(DOCKER_COMPOSE_DEV) ps

# =============================================================================
# CONFIGURATION MANAGEMENT
# =============================================================================

# Validate configuration
config-validate:
	@echo "Validating configuration..."
	@$(DOCKER_COMPOSE_DEV) config --quiet
	@echo "Configuration validation completed"

# Generate configuration files
config-generate:
	@echo "Generating configuration files..."
	@if [ ! -f docker/environments/.env.development.local ]; then \
		cp docker/environments/.env.development docker/environments/.env.development.local; \
		echo "Created .env.development.local from template"; \
		echo "Please edit docker/environments/.env.development.local with your SonarQube token"; \
	else \
		echo ".env.development.local already exists"; \
	fi

# =============================================================================
# MAINTENANCE OPERATIONS
# =============================================================================

# Check service health
health:
	@echo "Checking service health..."
	@make verify-endpoints
	@echo "Health check completed"

# Clean up Docker resources
cleanup:
	@echo "Cleaning up Docker resources..."
	docker system prune -f
	docker volume prune -f
	@echo "Docker cleanup completed"

# =============================================================================
# VERIFICATION AND DEBUGGING
# =============================================================================

# Verify API endpoints are working correctly
verify-endpoints:
	@echo "Verifying API endpoints..."
	@echo "Testing SonarQube API..."
	@curl -s http://localhost:9000/sonarqube/api/system/status | jq . || echo "❌ SonarQube API failed"
	@echo "Testing MCP Server..."
	@curl -s http://localhost:8001/health | jq . || echo "❌ MCP Server failed"
	@echo "Testing Streamlit health..."
	@curl -s http://localhost:8501/_stcore/health || echo "❌ Streamlit health check failed"
	@echo "✅ Endpoint verification completed"

# Check if services are running on correct ports
check-ports:
	@echo "Checking service ports..."
	@echo "SonarQube (9000):"
	@docker ps --filter "name=sonarqube-server" --format "table {{.Names}}\t{{.Ports}}" || echo "❌ SonarQube not running"
	@echo "MCP Server (8001):"
	@docker ps --filter "name=sonarqube-mcp-server" --format "table {{.Names}}\t{{.Ports}}" || echo "❌ MCP Server not running"
	@echo "Streamlit (8501):"
	@docker ps --filter "name=sonarqube-streamlit-app" --format "table {{.Names}}\t{{.Ports}}" || echo "❌ Streamlit not running"

# Show current configuration status
status:
	@echo "SonarQube MCP Status"
	@echo "==================="
	@make check-ports
	@echo ""
	@make verify-endpoints
	@echo ""
	@echo "Docker Compose Status:"
	@$(DOCKER_COMPOSE_DEV) ps

# =============================================================================
# MIGRATION AND UPDATES
# =============================================================================

# Migration helper - updates old configurations
migrate:
	@echo "🔄 Migrating to new configuration..."
	@echo "Stopping old containers..."
	@$(DOCKER_COMPOSE_DEV) down 2>/dev/null || true
	@echo "Removing old images..."
	@docker rmi $$(docker images -q sonarqube-mcp* 2>/dev/null) 2>/dev/null || true
	@echo "Updating configuration files..."
	@make config-generate
	@echo "Starting with new configuration..."
	@make dev
	@echo "✅ Migration completed!"
	@echo "Please reconfigure your Streamlit app with:"
	@echo "  URL: http://localhost:9000/sonarqube"
	@echo "  MCP Server: http://localhost:8001"

# Update from v1.0.0 to v1.1.0
update-v1.1:
	@echo "🔄 Updating to SonarQube MCP v1.1.0..."
	@echo "This will update port configurations and fix known issues"
	@read -p "Continue with update? (y/N): " confirm; \
	if [ "$$confirm" = "y" ] || [ "$$confirm" = "Y" ]; then \
		echo "Stopping services..."; \
		$(DOCKER_COMPOSE_DEV) down; \
		echo "Updating environment files..."; \
		sed -i.bak 's/8000/8001/g' docker/environments/.env.development 2>/dev/null || true; \
		echo "Rebuilding images..."; \
		make build; \
		echo "Starting updated services..."; \
		make dev; \
		echo "✅ Update to v1.1.0 completed!"; \
		echo "Changes applied:"; \
		echo "  - MCP Server port: 8000 → 8001"; \
		echo "  - Fixed session state issues"; \
		echo "  - Updated Streamlit compatibility"; \
		make verify-endpoints; \
	else \
		echo "Update cancelled"; \
	fi

# Reset everything to clean state
reset:
	@echo "⚠️  This will remove all containers, images, and volumes!"
	@read -p "Are you sure? This cannot be undone! (y/N): " confirm; \
	if [ "$$confirm" = "y" ] || [ "$$confirm" = "Y" ]; then \
		echo "Stopping all services..."; \
		$(DOCKER_COMPOSE_DEV) down -v --remove-orphans; \
		echo "Removing all project images..."; \
		docker rmi $$(docker images -q "*sonarqube*" "*mcp*" 2>/dev/null) 2>/dev/null || true; \
		echo "Cleaning up Docker system..."; \
		docker system prune -f; \
		echo "✅ Reset completed!"; \
		echo "Run 'make quickstart' to start fresh"; \
	else \
		echo "Reset cancelled"; \
	fi

# =============================================================================
# INFORMATION AND UTILITIES
# =============================================================================

# Show detailed service information
info-detailed:
	@echo "SonarQube MCP Detailed Information"
	@echo "================================="
	@echo ""
	@echo "🐳 Docker Information:"
	@docker --version
	@docker compose version
	@echo ""
	@echo "📦 Container Status:"
	@$(DOCKER_COMPOSE_DEV) ps
	@echo ""
	@echo "🔌 Port Mappings:"
	@docker ps --format "table {{.Names}}\t{{.Ports}}" | grep sonarqube || echo "No containers running"
	@echo ""
	@echo "💾 Volume Usage:"
	@docker system df
	@echo ""
	@echo "🌐 Network Information:"
	@docker network ls | grep sonarqube || echo "No networks found"
	@echo ""
	@echo "📊 Resource Usage:"
	@docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}" | head -6

# Fix common issues
fix-permissions:
	@echo "🔧 Fixing file permissions..."
	@sudo chown -R $$USER:$$USER logs/ data/ 2>/dev/null || true
	@chmod -R 755 logs/ data/ 2>/dev/null || true
	@echo "✅ Permissions fixed"

# Validate current setup
validate-setup:
	@echo "🔍 Validating SonarQube MCP setup..."
	@echo "Checking Docker..."
	@docker --version > /dev/null && echo "✅ Docker installed" || echo "❌ Docker not found"
	@docker compose version > /dev/null && echo "✅ Docker Compose installed" || echo "❌ Docker Compose not found"
	@echo "Checking configuration files..."
	@[ -f docker/environments/.env.development ] && echo "✅ Development config exists" || echo "❌ Development config missing"
	@[ -f docker/compose/base/docker-compose.yml ] && echo "✅ Base compose file exists" || echo "❌ Base compose file missing"
	@echo "Checking ports..."
	@netstat -tulpn 2>/dev/null | grep -E ":(8501|9000|8001|5432|6379)" > /dev/null && echo "⚠️  Some ports may be in use" || echo "✅ Ports available"
	@echo "Validation completed"

# =============================================================================
# QUICK START AND HELP
# =============================================================================

# Quick development setup with verification
quickstart: config-generate dev
	@echo "Waiting for services to start..."
	@sleep 15
	@echo "Verifying setup..."
	@make verify-endpoints
	@echo ""
	@echo "🎉 Quick start completed!"
	@echo "Access your applications:"
	@echo "  - Streamlit App: http://localhost:8501"
	@echo "  - SonarQube: http://localhost:9000/sonarqube"
	@echo "  - MCP Server: http://localhost:8001"
	@echo ""
	@echo "⚠️  IMPORTANT: Configure your SonarQube token!"
	@echo "1. Get a SonarQube token from http://localhost:9000/sonarqube"
	@echo "   (Login: admin / Password: admin)"
	@echo "2. Edit docker/environments/.env.development.local"
	@echo "3. Replace 'your_sonarqube_token_here' with your actual token"
	@echo "4. Restart services: make restart"
	@echo "5. Configure Streamlit app at http://localhost:8501"
	@echo "6. Use URL: http://localhost:9000/sonarqube in the configuration"

# Show help for new users
help-new:
	@echo "🚀 SonarQube MCP - New User Guide"
	@echo "================================="
	@echo ""
	@echo "Quick Start (recommended):"
	@echo "  make quickstart          - Complete setup and start all services"
	@echo ""
	@echo "Step by step:"
	@echo "  1. make config-generate  - Create configuration files"
	@echo "  2. Edit docker/environments/.env.development.local with your SonarQube token"
	@echo "  3. make build           - Build Docker images"
	@echo "  4. make dev             - Start development environment"
	@echo "  5. make verify-endpoints - Check that everything is working"
	@echo ""
	@echo "Getting SonarQube token:"
	@echo "  1. Go to http://localhost:9000/sonarqube"
	@echo "  2. Login with admin/admin"
	@echo "  3. Go to My Account > Security > Generate Token"
	@echo "  4. Copy the token to your .env file"
	@echo ""
	@echo "Troubleshooting:"
	@echo "  make status             - Check service status"
	@echo "  make logs               - View service logs"
	@echo "  make validate-setup     - Validate your setup"
	@echo "  make reset              - Reset everything (nuclear option)"