# Makefile for SonarQube MCP project

.PHONY: help install test lint format clean dev prod build push deploy backup restore logs monitor

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
	@echo "  ps               - Show running containers"
	@echo ""
	@echo "Configuration:"
	@echo "  config-validate  - Validate configuration"
	@echo "  config-generate  - Generate configuration files"
	@echo "  secrets-generate - Generate secrets"
	@echo "  secrets-rotate   - Rotate secrets"
	@echo ""
	@echo "Maintenance:"
	@echo "  backup           - Create backup"
	@echo "  restore          - Restore from backup"
	@echo "  health           - Check service health"
	@echo "  monitor          - Start resource monitoring"
	@echo "  cleanup          - Clean up Docker resources"
	@echo ""
	@echo "Deployment:"
	@echo "  deploy-dev       - Deploy to development"
	@echo "  deploy-staging   - Deploy to staging"
	@echo "  deploy-prod      - Deploy to production"

# Variables
DOCKER_COMPOSE_DEV = docker-compose -f docker/compose/base/docker-compose.yml -f docker/compose/services/infrastructure.yml -f docker/compose/services/monitoring.yml -f docker/compose/environments/development.yml --env-file docker/environments/.env.development
DOCKER_COMPOSE_PROD = docker-compose -f docker/compose/base/docker-compose.yml -f docker/compose/services/infrastructure.yml -f docker/compose/services/monitoring.yml -f docker/compose/environments/production.yml --env-file docker/environments/.env.production
PYTHON = python
PIP = pip

# =============================================================================
# DEVELOPMENT COMMANDS
# =============================================================================

# Install dependencies
install:
	@echo "Installing Python dependencies..."
	$(PIP) install -r requirements-dev.txt
	pre-commit install
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
	bash docker/scripts/build.sh build development
	@echo "Docker images built successfully"

# Development environment
dev:
	@echo "Starting development environment..."
	bash docker/scripts/deploy.sh deploy development
	@echo "Development environment started"

# Production environment
prod:
	@echo "Starting production environment..."
	bash docker/scripts/deploy.sh deploy production
	@echo "Production environment started"

# Stop all services
stop:
	@echo "Stopping all services..."
	docker-compose down
	@echo "All services stopped"

# Restart all services
restart:
	@echo "Restarting all services..."
	docker-compose restart
	@echo "All services restarted"

# Show logs
logs:
	@echo "Showing logs for all services..."
	docker-compose logs -f

# Show running containers
ps:
	@echo "Running containers:"
	docker-compose ps

# =============================================================================
# CONFIGURATION MANAGEMENT
# =============================================================================

# Validate configuration
config-validate:
	@echo "Validating configuration..."
	bash docker/scripts/validate-config.sh
	@echo "Configuration validation completed"

# Generate configuration files
config-generate:
	@echo "Generating configuration files..."
	@if [ ! -f .env ]; then \
		cp docker/environments/.env.development .env; \
		echo "Created .env from development template"; \
		echo "Please edit .env with your configuration"; \
	else \
		echo ".env already exists"; \
	fi

# Generate secrets
secrets-generate:
	@echo "Generating secrets..."
	bash docker/scripts/manage-secrets.sh generate
	@echo "Secrets generated successfully"

# Rotate secrets
secrets-rotate:
	@echo "Rotating secrets..."
	bash docker/scripts/manage-secrets.sh rotate
	@echo "Secrets rotated successfully"

# =============================================================================
# MAINTENANCE OPERATIONS
# =============================================================================

# Create backup
backup:
	@echo "Creating backup..."
	bash docker/scripts/backup-restore.sh backup
	@echo "Backup completed"

# Restore from backup
restore:
	@echo "Restoring from backup..."
	@read -p "Enter backup file path: " backup_file; \
	bash docker/scripts/backup-restore.sh restore "$$backup_file"
	@echo "Restore completed"

# Check service health
health:
	@echo "Checking service health..."
	bash docker/scripts/health-check.sh
	@echo "Health check completed"

# Start resource monitoring
monitor:
	@echo "Starting resource monitoring..."
	bash docker/scripts/resource-monitor.sh

# Clean up Docker resources
cleanup:
	@echo "Cleaning up Docker resources..."
	docker system prune -f
	docker volume prune -f
	@echo "Docker cleanup completed"

# =============================================================================
# DEPLOYMENT COMMANDS
# =============================================================================

# Deploy to development
deploy-dev: config-validate build
	@echo "Deploying to development environment..."
	$(DOCKER_COMPOSE_DEV) down
	$(DOCKER_COMPOSE_DEV) up -d
	@echo "Development deployment completed"

# Deploy to staging
deploy-staging: config-validate build
	@echo "Deploying to staging environment..."
	@if [ ! -f .env.staging ]; then \
		echo "Error: .env.staging not found"; \
		exit 1; \
	fi
	cp .env.staging .env
	docker-compose down
	docker-compose up -d
	@echo "Staging deployment completed"

# Deploy to production
deploy-prod: config-validate build
	@echo "Deploying to production environment..."
	@if [ ! -f .env.prod ]; then \
		echo "Error: .env.prod not found"; \
		exit 1; \
	fi
	@read -p "Are you sure you want to deploy to production? (y/N): " confirm; \
	if [ "$$confirm" = "y" ] || [ "$$confirm" = "Y" ]; then \
		cp .env.prod .env; \
		$(DOCKER_COMPOSE_PROD) down; \
		$(DOCKER_COMPOSE_PROD) up -d; \
		echo "Production deployment completed"; \
	else \
		echo "Production deployment cancelled"; \
	fi

# =============================================================================
# TESTING IN DOCKER
# =============================================================================

# Run tests in Docker container
test-docker:
	@echo "Running tests in Docker container..."
	docker run --rm -v $(PWD):/app -w /app python:3.11-slim bash -c "\
		pip install -r requirements-dev.txt && \
		pytest tests/ -v --cov=src --cov-report=term"

# Run linting in Docker container
lint-docker:
	@echo "Running linting in Docker container..."
	docker run --rm -v $(PWD):/app -w /app python:3.11-slim bash -c "\
		pip install -r requirements-dev.txt && \
		ruff check src/ tests/ && \
		mypy src/"

# =============================================================================
# UTILITY COMMANDS
# =============================================================================

# Initialize project
init: install config-generate secrets-generate
	@echo "Project initialization completed"
	@echo "Next steps:"
	@echo "1. Edit .env with your SonarQube configuration"
	@echo "2. Run 'make dev' to start development environment"

# Full development setup
setup: clean install build dev
	@echo "Full development setup completed"

# Quick start for new developers
quickstart:
	@echo "Quick start for SonarQube MCP development"
	@echo "========================================"
	@echo ""
	@echo "1. Installing dependencies..."
	@$(MAKE) install
	@echo ""
	@echo "2. Generating configuration..."
	@$(MAKE) config-generate
	@echo ""
	@echo "3. Building Docker images..."
	@$(MAKE) build
	@echo ""
	@echo "4. Starting development environment..."
	@$(MAKE) dev
	@echo ""
	@echo "Quick start completed!"
	@echo ""
	@echo "Next steps:"
	@echo "- Edit .env with your SonarQube token"
	@echo "- Visit http://localhost:8501 for the Streamlit app"
	@echo "- Visit http://localhost:9000 for SonarQube"
	@echo "- Run 'make health' to check service status"

# Show environment info
info:
	@echo "SonarQube MCP Environment Information"
	@echo "===================================="
	@echo "Docker version: $$(docker --version)"
	@echo "Docker Compose version: $$(docker-compose --version 2>/dev/null || docker compose version)"
	@echo "Python version: $$(python --version)"
	@echo "Current directory: $$(pwd)"
	@echo "Git branch: $$(git branch --show-current 2>/dev/null || echo 'Not a git repository')"
	@echo "Git commit: $$(git rev-parse --short HEAD 2>/dev/null || echo 'Not a git repository')"