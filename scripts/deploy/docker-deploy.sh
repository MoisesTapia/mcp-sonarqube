#!/bin/bash

# Docker Compose Deployment Script for SonarQube MCP
# This script handles deployment using Docker Compose for different environments

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
ENVIRONMENT="${ENVIRONMENT:-development}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] $1${NC}"
}

warn() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] WARNING: $1${NC}"
}

error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ERROR: $1${NC}"
    exit 1
}

info() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')] INFO: $1${NC}"
}

usage() {
    echo "Usage: $0 [OPTIONS]"
    echo "Options:"
    echo "  -e, --environment ENV     Target environment (development|staging|production) [default: development]"
    echo "  -f, --force               Force deployment without confirmation"
    echo "  -b, --build               Force rebuild of images"
    echo "  -d, --dry-run             Show what would be deployed without applying"
    echo "  -h, --help                Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 --environment production --build"
    echo "  $0 --dry-run --environment staging"
    exit 1
}

# Parse command line arguments
parse_args() {
    FORCE_DEPLOY=false
    FORCE_BUILD=false
    DRY_RUN=false
    
    while [[ $# -gt 0 ]]; do
        case $1 in
            -e|--environment)
                ENVIRONMENT="$2"
                shift 2
                ;;
            -f|--force)
                FORCE_DEPLOY=true
                shift
                ;;
            -b|--build)
                FORCE_BUILD=true
                shift
                ;;
            -d|--dry-run)
                DRY_RUN=true
                shift
                ;;
            -h|--help)
                usage
                ;;
            *)
                error "Unknown option: $1"
                ;;
        esac
    done
}

# Validate environment
validate_environment() {
    case "$ENVIRONMENT" in
        development|staging|production)
            log "Deploying to $ENVIRONMENT environment"
            ;;
        *)
            error "Invalid environment: $ENVIRONMENT. Must be 'development', 'staging', or 'production'"
            ;;
    esac
    
    # Set compose files based on environment
    COMPOSE_FILES="-f docker/compose/base/docker-compose.yml"
    ENV_FILE="--env-file docker/environments/.env.$ENVIRONMENT"
    
    if [[ -f "docker/compose/environments/$ENVIRONMENT.yml" ]]; then
        COMPOSE_FILES="$COMPOSE_FILES -f docker/compose/environments/$ENVIRONMENT.yml"
    else
        warn "Environment-specific compose file not found: docker/compose/environments/$ENVIRONMENT.yml"
    fi
    
    if [[ ! -f "docker/environments/.env.$ENVIRONMENT" ]]; then
        error "Environment file not found: docker/environments/.env.$ENVIRONMENT"
    fi
}

# Check prerequisites
check_prerequisites() {
    log "Checking prerequisites..."
    
    if ! command -v docker &> /dev/null; then
        error "Docker is not installed or not in PATH"
    fi
    
    if ! docker compose version &> /dev/null; then
        error "Docker Compose is not available"
    fi
    
    # Check if Docker daemon is running
    if ! docker info &> /dev/null; then
        error "Docker daemon is not running"
    fi
    
    cd "$PROJECT_ROOT"
    
    log "Prerequisites check passed"
}

# Confirm deployment
confirm_deployment() {
    if [[ "$FORCE_DEPLOY" == "true" ]] || [[ "$DRY_RUN" == "true" ]]; then
        return 0
    fi
    
    info "Deployment Summary:"
    echo "  Environment: $ENVIRONMENT"
    echo "  Compose Files: $COMPOSE_FILES"
    echo "  Environment File: $ENV_FILE"
    echo "  Force Build: $FORCE_BUILD"
    echo ""
    
    if [[ "$ENVIRONMENT" == "production" ]]; then
        warn "You are about to deploy to PRODUCTION environment!"
        warn "This will affect live users and services."
    fi
    
    read -p "Do you want to continue? (yes/no): " confirmation
    
    if [[ "$confirmation" != "yes" ]]; then
        log "Deployment cancelled"
        exit 0
    fi
}

# Validate configuration
validate_configuration() {
    log "Validating configuration..."
    
    if [[ "$DRY_RUN" == "true" ]]; then
        info "[DRY RUN] Would validate configuration"
        docker compose $COMPOSE_FILES $ENV_FILE config --quiet
        return 0
    fi
    
    # Validate compose configuration
    if ! docker compose $COMPOSE_FILES $ENV_FILE config --quiet; then
        error "Docker Compose configuration is invalid"
    fi
    
    # Check for required environment variables
    local required_vars=("SONARQUBE_TOKEN" "POSTGRES_PASSWORD" "REDIS_PASSWORD")
    
    for var in "${required_vars[@]}"; do
        if ! grep -q "^${var}=" "docker/environments/.env.$ENVIRONMENT"; then
            warn "Required environment variable $var not found in environment file"
        fi
    done
    
    log "Configuration validation completed"
}

# Build images if needed
build_images() {
    if [[ "$FORCE_BUILD" == "true" ]] || [[ ! "$(docker images -q sonarqube-mcp/mcp-server 2> /dev/null)" ]]; then
        log "Building Docker images..."
        
        if [[ "$DRY_RUN" == "true" ]]; then
            info "[DRY RUN] Would build images"
            return 0
        fi
        
        docker compose $COMPOSE_FILES $ENV_FILE build --no-cache
        
        log "Images built successfully"
    else
        log "Using existing images (use --build to force rebuild)"
    fi
}

# Deploy services
deploy_services() {
    log "Deploying services..."
    
    if [[ "$DRY_RUN" == "true" ]]; then
        info "[DRY RUN] Would deploy services with:"
        echo "  docker compose $COMPOSE_FILES $ENV_FILE up -d"
        return 0
    fi
    
    # Stop existing services
    log "Stopping existing services..."
    docker compose $COMPOSE_FILES $ENV_FILE down || true
    
    # Start services
    log "Starting services..."
    docker compose $COMPOSE_FILES $ENV_FILE up -d
    
    log "Services deployed successfully"
}

# Wait for services to be ready
wait_for_services() {
    if [[ "$DRY_RUN" == "true" ]]; then
        info "[DRY RUN] Would wait for services to be ready"
        return 0
    fi
    
    log "Waiting for services to be ready..."
    
    # Wait for database services first
    local max_wait=120
    local wait_time=0
    
    while ! docker compose $COMPOSE_FILES $ENV_FILE exec -T postgres pg_isready -U sonarqube &> /dev/null; do
        if [[ $wait_time -ge $max_wait ]]; then
            error "PostgreSQL failed to start within ${max_wait} seconds"
        fi
        sleep 5
        wait_time=$((wait_time + 5))
        info "Waiting for PostgreSQL... (${wait_time}s)"
    done
    
    log "PostgreSQL is ready"
    
    # Wait for Redis
    wait_time=0
    while ! docker compose $COMPOSE_FILES $ENV_FILE exec -T redis redis-cli ping &> /dev/null; do
        if [[ $wait_time -ge $max_wait ]]; then
            error "Redis failed to start within ${max_wait} seconds"
        fi
        sleep 5
        wait_time=$((wait_time + 5))
        info "Waiting for Redis... (${wait_time}s)"
    done
    
    log "Redis is ready"
    
    # Wait for application services
    wait_time=0
    while ! curl -f http://localhost:8001/health &> /dev/null; do
        if [[ $wait_time -ge $max_wait ]]; then
            warn "MCP server may not be ready yet"
            break
        fi
        sleep 5
        wait_time=$((wait_time + 5))
        info "Waiting for MCP server... (${wait_time}s)"
    done
    
    if curl -f http://localhost:8001/health &> /dev/null; then
        log "MCP server is ready"
    fi
    
    wait_time=0
    while ! curl -f http://localhost:8501/_stcore/health &> /dev/null; do
        if [[ $wait_time -ge $max_wait ]]; then
            warn "Streamlit app may not be ready yet"
            break
        fi
        sleep 5
        wait_time=$((wait_time + 5))
        info "Waiting for Streamlit app... (${wait_time}s)"
    done
    
    if curl -f http://localhost:8501/_stcore/health &> /dev/null; then
        log "Streamlit app is ready"
    fi
}

# Run health checks
run_health_checks() {
    if [[ "$DRY_RUN" == "true" ]]; then
        info "[DRY RUN] Would run health checks"
        return 0
    fi
    
    log "Running health checks..."
    
    # Check container status
    local containers=$(docker compose $COMPOSE_FILES $ENV_FILE ps -q)
    local running_count=0
    local total_count=0
    
    for container in $containers; do
        total_count=$((total_count + 1))
        if docker inspect "$container" --format='{{.State.Status}}' | grep -q "running"; then
            running_count=$((running_count + 1))
        fi
    done
    
    info "Container status: $running_count/$total_count running"
    
    # Check service endpoints
    local health_status=0
    
    if curl -f http://localhost:8001/health &> /dev/null; then
        log "✅ MCP server health check passed"
    else
        warn "❌ MCP server health check failed"
        health_status=1
    fi
    
    if curl -f http://localhost:8501/_stcore/health &> /dev/null; then
        log "✅ Streamlit app health check passed"
    else
        warn "❌ Streamlit app health check failed"
        health_status=1
    fi
    
    # Check SonarQube (may take longer to start)
    if curl -f http://localhost:9000/sonarqube/api/system/status &> /dev/null; then
        log "✅ SonarQube health check passed"
    else
        warn "❌ SonarQube health check failed (may still be starting)"
    fi
    
    if [[ $health_status -eq 0 ]]; then
        log "All critical health checks passed"
    else
        warn "Some health checks failed"
    fi
}

# Show deployment summary
show_deployment_summary() {
    log "Deployment completed!"
    
    info "Deployment Summary:"
    echo "  Environment: $ENVIRONMENT"
    echo "  Status: $(if [[ "$DRY_RUN" == "true" ]]; then echo "DRY RUN"; else echo "DEPLOYED"; fi)"
    echo ""
    
    if [[ "$DRY_RUN" != "true" ]]; then
        echo "🌐 Service URLs:"
        echo "  • Streamlit App: http://localhost:8501"
        echo "  • MCP Server: http://localhost:8001"
        echo "  • SonarQube: http://localhost:9000/sonarqube"
        echo ""
        
        echo "🔧 Management Commands:"
        echo "  • Check status: docker compose $COMPOSE_FILES $ENV_FILE ps"
        echo "  • View logs: docker compose $COMPOSE_FILES $ENV_FILE logs -f"
        echo "  • Stop services: docker compose $COMPOSE_FILES $ENV_FILE down"
        echo ""
        
        if [[ "$ENVIRONMENT" == "production" ]]; then
            echo "🚨 Production Notes:"
            echo "  • Monitor service health regularly"
            echo "  • Set up proper backup schedule"
            echo "  • Configure monitoring and alerting"
            echo "  • Review security settings"
        fi
    fi
}

# Cleanup function
cleanup() {
    if [[ "${CLEANUP_ON_ERROR:-false}" == "true" ]]; then
        warn "Cleaning up due to error..."
        docker compose $COMPOSE_FILES $ENV_FILE down || true
    fi
}

# Main deployment function
main() {
    log "Starting SonarQube MCP deployment..."
    
    trap cleanup EXIT
    
    parse_args "$@"
    validate_environment
    check_prerequisites
    confirm_deployment
    
    validate_configuration
    build_images
    deploy_services
    wait_for_services
    run_health_checks
    
    show_deployment_summary
    
    if [[ "$DRY_RUN" == "true" ]]; then
        log "Dry run completed successfully!"
    else
        log "Deployment completed successfully! 🚀"
    fi
}

# Run main function
main "$@"