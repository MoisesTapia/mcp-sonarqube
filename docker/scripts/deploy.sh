#!/bin/bash
# Deployment script for SonarQube MCP

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
DOCKER_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

# Logging functions
log() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1" >&2
}

warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

# Check if Docker Compose is available
check_docker_compose() {
    if ! command -v docker-compose > /dev/null 2>&1; then
        if ! docker compose version > /dev/null 2>&1; then
            error "Docker Compose is not available"
            exit 1
        fi
        DOCKER_COMPOSE_CMD="docker compose"
    else
        DOCKER_COMPOSE_CMD="docker-compose"
    fi
}

# Validate environment
validate_environment() {
    local environment="$1"
    
    case $environment in
        development|staging|production)
            log "Deploying to $environment environment"
            ;;
        *)
            error "Invalid environment: $environment"
            error "Valid environments: development, staging, production"
            exit 1
            ;;
    esac
}

# Check environment file
check_env_file() {
    local environment="$1"
    local env_file="$DOCKER_DIR/environments/.env.$environment"
    
    if [ ! -f "$env_file" ]; then
        error "Environment file not found: $env_file"
        exit 1
    fi
    
    log "Using environment file: $env_file"
}

# Build compose file arguments
build_compose_args() {
    local environment="$1"
    
    COMPOSE_FILES=(
        "-f" "$DOCKER_DIR/compose/base/docker-compose.yml"
        "-f" "$DOCKER_DIR/compose/services/infrastructure.yml"
        "-f" "$DOCKER_DIR/compose/services/monitoring.yml"
        "-f" "$DOCKER_DIR/compose/environments/$environment.yml"
    )
    
    ENV_FILE="--env-file $DOCKER_DIR/environments/.env.$environment"
}

# Pre-deployment checks
pre_deployment_checks() {
    local environment="$1"
    
    log "Running pre-deployment checks for $environment..."
    
    # Check Docker daemon
    if ! docker info > /dev/null 2>&1; then
        error "Docker daemon is not running"
        exit 1
    fi
    
    # Check available disk space
    local available_space=$(df / | awk 'NR==2 {print $4}')
    if [ "$available_space" -lt 5000000 ]; then  # 5GB in KB
        warning "Low disk space available: $(($available_space / 1024 / 1024))GB"
    fi
    
    # Check available memory
    local available_memory=$(free -m | awk 'NR==2{print $7}')
    if [ "$available_memory" -lt 4096 ]; then  # 4GB
        warning "Low memory available: ${available_memory}MB"
    fi
    
    # Validate environment configuration
    log "Validating environment configuration..."
    if [ -f "$PROJECT_ROOT/docker/scripts/validate-config.sh" ]; then
        bash "$PROJECT_ROOT/docker/scripts/validate-config.sh" "$DOCKER_DIR/environments/.env.$environment"
    fi
    
    success "Pre-deployment checks completed"
}

# Initialize services
initialize_services() {
    local environment="$1"
    
    log "Initializing services for $environment environment..."
    
    cd "$PROJECT_ROOT"
    
    # Create necessary directories
    mkdir -p logs data backups
    
    # Generate SSL certificates for development
    if [ "$environment" = "development" ]; then
        if [ ! -f "$DOCKER_DIR/config/nginx/ssl/nginx.crt" ]; then
            log "Generating SSL certificates for development..."
            bash "$DOCKER_DIR/config/nginx/generate-ssl.sh" || true
        fi
    fi
    
    success "Services initialized"
}

# Deploy services
deploy_services() {
    local environment="$1"
    
    log "Deploying services for $environment environment..."
    
    cd "$PROJECT_ROOT"
    
    # Stop existing services
    log "Stopping existing services..."
    $DOCKER_COMPOSE_CMD "${COMPOSE_FILES[@]}" $ENV_FILE down --remove-orphans || true
    
    # Pull latest images (for production)
    if [ "$environment" = "production" ]; then
        log "Pulling latest images..."
        $DOCKER_COMPOSE_CMD "${COMPOSE_FILES[@]}" $ENV_FILE pull
    fi
    
    # Start services
    log "Starting services..."
    $DOCKER_COMPOSE_CMD "${COMPOSE_FILES[@]}" $ENV_FILE up -d
    
    success "Services deployed successfully"
}

# Wait for services to be ready
wait_for_services() {
    local environment="$1"
    local timeout=300  # 5 minutes
    local elapsed=0
    
    log "Waiting for services to be ready..."
    
    cd "$PROJECT_ROOT"
    
    while [ $elapsed -lt $timeout ]; do
        # Check if all services are healthy
        local unhealthy_services=$($DOCKER_COMPOSE_CMD "${COMPOSE_FILES[@]}" $ENV_FILE ps --filter "health=unhealthy" -q | wc -l)
        local starting_services=$($DOCKER_COMPOSE_CMD "${COMPOSE_FILES[@]}" $ENV_FILE ps --filter "health=starting" -q | wc -l)
        
        if [ "$unhealthy_services" -eq 0 ] && [ "$starting_services" -eq 0 ]; then
            success "All services are ready"
            return 0
        fi
        
        log "Waiting for services to be ready... ($elapsed/$timeout seconds)"
        sleep 10
        elapsed=$((elapsed + 10))
    done
    
    warning "Timeout waiting for services to be ready"
    return 1
}

# Post-deployment checks
post_deployment_checks() {
    local environment="$1"
    
    log "Running post-deployment checks..."
    
    cd "$PROJECT_ROOT"
    
    # Check service health
    if [ -f "$PROJECT_ROOT/docker/scripts/health-check.sh" ]; then
        bash "$PROJECT_ROOT/docker/scripts/health-check.sh"
    fi
    
    # Display service URLs
    display_service_urls "$environment"
    
    success "Post-deployment checks completed"
}

# Display service URLs
display_service_urls() {
    local environment="$1"
    
    log "Service URLs for $environment environment:"
    
    case $environment in
        development)
            echo "  - Streamlit App: http://localhost:8501"
            echo "  - SonarQube: http://localhost:9000"
            echo "  - Grafana: http://localhost:3000 (admin/admin)"
            echo "  - Prometheus: http://localhost:9090"
            echo "  - Redis Commander: http://localhost:8081"
            echo "  - pgAdmin: http://localhost:8082 (admin@example.com/admin)"
            echo "  - Mailhog: http://localhost:8025"
            echo "  - Nginx: http://localhost:8080"
            ;;
        staging|production)
            echo "  - Streamlit App: https://localhost"
            echo "  - SonarQube: https://localhost/sonarqube"
            echo "  - Grafana: https://localhost:3000"
            echo "  - Prometheus: https://localhost:9090"
            ;;
    esac
}

# Rollback deployment
rollback_deployment() {
    local environment="$1"
    
    log "Rolling back deployment for $environment environment..."
    
    cd "$PROJECT_ROOT"
    
    # Stop current services
    $DOCKER_COMPOSE_CMD "${COMPOSE_FILES[@]}" $ENV_FILE down
    
    # Restore from backup if available
    if [ -f "$PROJECT_ROOT/docker/scripts/backup.sh" ]; then
        warning "Consider restoring from backup if needed"
        echo "Run: bash docker/scripts/backup.sh restore"
    fi
    
    success "Rollback completed"
}

# Scale services
scale_services() {
    local environment="$1"
    local service="$2"
    local replicas="$3"
    
    if [ -z "$service" ] || [ -z "$replicas" ]; then
        error "Service and replica count are required for scaling"
        exit 1
    fi
    
    log "Scaling $service to $replicas replicas in $environment environment..."
    
    cd "$PROJECT_ROOT"
    
    $DOCKER_COMPOSE_CMD "${COMPOSE_FILES[@]}" $ENV_FILE up -d --scale "$service=$replicas"
    
    success "Service $service scaled to $replicas replicas"
}

# Update services
update_services() {
    local environment="$1"
    
    log "Updating services for $environment environment..."
    
    cd "$PROJECT_ROOT"
    
    # Pull latest images
    $DOCKER_COMPOSE_CMD "${COMPOSE_FILES[@]}" $ENV_FILE pull
    
    # Recreate services with new images
    $DOCKER_COMPOSE_CMD "${COMPOSE_FILES[@]}" $ENV_FILE up -d --force-recreate
    
    success "Services updated successfully"
}

# Usage information
usage() {
    echo "Usage: $0 COMMAND ENVIRONMENT [OPTIONS]"
    echo
    echo "Deploy SonarQube MCP to different environments"
    echo
    echo "Commands:"
    echo "  deploy ENV            Deploy to environment"
    echo "  rollback ENV          Rollback deployment"
    echo "  scale ENV SVC NUM     Scale service to number of replicas"
    echo "  update ENV            Update services with latest images"
    echo "  status ENV            Show deployment status"
    echo "  logs ENV [SVC]        Show logs for environment"
    echo "  stop ENV              Stop all services"
    echo "  restart ENV           Restart all services"
    echo
    echo "Environments:"
    echo "  development           Development environment"
    echo "  staging              Staging environment"
    echo "  production           Production environment"
    echo
    echo "Examples:"
    echo "  $0 deploy development"
    echo "  $0 scale production mcp-server 3"
    echo "  $0 update staging"
    echo "  $0 logs production mcp-server"
}

# Main function
main() {
    local command="$1"
    local environment="$2"
    shift 2 || true
    
    if [ -z "$command" ] || [ -z "$environment" ]; then
        error "Command and environment are required"
        usage
        exit 1
    fi
    
    check_docker_compose
    validate_environment "$environment"
    check_env_file "$environment"
    build_compose_args "$environment"
    
    case $command in
        deploy)
            pre_deployment_checks "$environment"
            initialize_services "$environment"
            deploy_services "$environment"
            wait_for_services "$environment"
            post_deployment_checks "$environment"
            ;;
        rollback)
            rollback_deployment "$environment"
            ;;
        scale)
            scale_services "$environment" "$1" "$2"
            ;;
        update)
            update_services "$environment"
            ;;
        status)
            cd "$PROJECT_ROOT"
            $DOCKER_COMPOSE_CMD "${COMPOSE_FILES[@]}" $ENV_FILE ps
            ;;
        logs)
            cd "$PROJECT_ROOT"
            if [ -n "$1" ]; then
                $DOCKER_COMPOSE_CMD "${COMPOSE_FILES[@]}" $ENV_FILE logs -f "$1"
            else
                $DOCKER_COMPOSE_CMD "${COMPOSE_FILES[@]}" $ENV_FILE logs -f
            fi
            ;;
        stop)
            cd "$PROJECT_ROOT"
            $DOCKER_COMPOSE_CMD "${COMPOSE_FILES[@]}" $ENV_FILE down
            ;;
        restart)
            cd "$PROJECT_ROOT"
            $DOCKER_COMPOSE_CMD "${COMPOSE_FILES[@]}" $ENV_FILE restart
            ;;
        *)
            error "Unknown command: $command"
            usage
            exit 1
            ;;
    esac
}

# Check for help flag
if [ "$1" = "-h" ] || [ "$1" = "--help" ]; then
    usage
    exit 0
fi

# Run main function
main "$@"