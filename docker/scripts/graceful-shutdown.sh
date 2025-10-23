#!/bin/bash
# Graceful shutdown script for SonarQube MCP services

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging function
log() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1" >&2
}

success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
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

# Signal handler for graceful shutdown
cleanup() {
    log "Received shutdown signal, initiating graceful shutdown..."
    
    # Stop application services first
    log "Stopping application services..."
    $DOCKER_COMPOSE_CMD stop streamlit-app mcp-server nginx
    
    # Stop SonarQube (may take time to shutdown gracefully)
    log "Stopping SonarQube..."
    $DOCKER_COMPOSE_CMD stop sonarqube
    
    # Stop monitoring services
    log "Stopping monitoring services..."
    $DOCKER_COMPOSE_CMD stop prometheus grafana node-exporter redis-exporter postgres-exporter
    
    # Stop data services last
    log "Stopping data services..."
    $DOCKER_COMPOSE_CMD stop redis postgres
    
    success "All services stopped gracefully"
    exit 0
}

# Set up signal handlers
trap cleanup SIGTERM SIGINT

# Graceful shutdown with timeout
graceful_shutdown() {
    local timeout=${1:-60}  # Default 60 seconds timeout
    
    log "Starting graceful shutdown (timeout: ${timeout}s)..."
    
    # Get list of running containers
    running_containers=$($DOCKER_COMPOSE_CMD ps -q)
    
    if [ -z "$running_containers" ]; then
        log "No running containers found"
        return 0
    fi
    
    # Stop services in order with graceful shutdown
    services_order=(
        "nginx"
        "streamlit-app"
        "mcp-server"
        "grafana"
        "prometheus"
        "node-exporter"
        "redis-exporter"
        "postgres-exporter"
        "sonarqube"
        "redis"
        "postgres"
    )
    
    for service in "${services_order[@]}"; do
        if $DOCKER_COMPOSE_CMD ps -q "$service" > /dev/null 2>&1; then
            log "Stopping $service..."
            
            # Send SIGTERM first
            $DOCKER_COMPOSE_CMD kill -s SIGTERM "$service" 2>/dev/null || true
            
            # Wait for graceful shutdown
            local wait_time=0
            local service_timeout=30
            
            while [ $wait_time -lt $service_timeout ]; do
                if ! $DOCKER_COMPOSE_CMD ps -q "$service" | grep -q .; then
                    success "$service stopped gracefully"
                    break
                fi
                sleep 2
                wait_time=$((wait_time + 2))
            done
            
            # Force stop if still running
            if $DOCKER_COMPOSE_CMD ps -q "$service" | grep -q .; then
                warning "$service did not stop gracefully, forcing stop..."
                $DOCKER_COMPOSE_CMD stop "$service"
            fi
        fi
    done
    
    # Final cleanup
    log "Performing final cleanup..."
    $DOCKER_COMPOSE_CMD down --remove-orphans
    
    success "Graceful shutdown completed"
}

# Backup data before shutdown (optional)
backup_data() {
    if [ "$1" = "--backup" ]; then
        log "Creating data backup before shutdown..."
        
        # Create backup directory with timestamp
        backup_dir="backups/$(date +%Y%m%d_%H%M%S)"
        mkdir -p "$backup_dir"
        
        # Backup PostgreSQL data
        log "Backing up PostgreSQL data..."
        $DOCKER_COMPOSE_CMD exec -T postgres pg_dumpall -U sonarqube > "$backup_dir/postgres_backup.sql"
        
        # Backup Redis data
        log "Backing up Redis data..."
        $DOCKER_COMPOSE_CMD exec -T redis redis-cli --rdb - > "$backup_dir/redis_backup.rdb"
        
        # Backup SonarQube data
        log "Backing up SonarQube data..."
        docker cp $(docker-compose ps -q sonarqube):/opt/sonarqube/data "$backup_dir/sonarqube_data"
        
        success "Data backup completed: $backup_dir"
    fi
}

# Main function
main() {
    log "SonarQube MCP Graceful Shutdown"
    
    check_docker_compose
    
    # Check for backup flag
    backup_data "$1"
    
    # Perform graceful shutdown
    graceful_shutdown 120  # 2 minute timeout
    
    success "Shutdown completed successfully"
}

# Run main function
main "$@"