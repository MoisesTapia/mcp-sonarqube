#!/bin/bash

# Docker Helper Script for SonarQube MCP
# This script provides convenient commands for Docker operations

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
COMPOSE_FILES="-f docker/compose/base/docker-compose.yml -f docker/compose/environments/development.yml"
ENV_FILE="--env-file docker/environments/.env.development"

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
    echo "SonarQube MCP Docker Helper"
    echo "Usage: $0 <command> [options]"
    echo ""
    echo "Commands:"
    echo "  setup           - Initial setup (copy env file, create directories)"
    echo "  start           - Start all services"
    echo "  stop            - Stop all services"
    echo "  restart         - Restart all services"
    echo "  build           - Build custom images"
    echo "  rebuild         - Rebuild and restart services"
    echo "  logs            - Show logs for all services"
    echo "  logs <service>  - Show logs for specific service"
    echo "  shell <service> - Open shell in service container"
    echo "  status          - Show status of all services"
    echo "  clean           - Clean up containers and images"
    echo "  reset           - Reset everything (including volumes)"
    echo "  backup          - Backup volumes"
    echo "  restore         - Restore volumes from backup"
    echo "  health          - Check health of all services"
    echo "  urls            - Show service URLs
  ports           - Show port mapping table"
    echo ""
    echo "Examples:"
    echo "  $0 setup"
    echo "  $0 start"
    echo "  $0 logs mcp-server"
    echo "  $0 shell postgres"
    echo "  $0 clean"
    exit 1
}

check_prerequisites() {
    if ! command -v docker &> /dev/null; then
        error "Docker is not installed or not in PATH"
    fi
    
    if ! docker compose version &> /dev/null; then
        error "Docker Compose is not available"
    fi
}

setup() {
    log "Setting up SonarQube MCP Docker environment..."
    
    # Create environment file if it doesn't exist
    if [[ ! -f "docker/environments/.env.development" ]]; then
        if [[ -f "docker/environments/.env.development.example" ]]; then
            cp docker/environments/.env.development.example docker/environments/.env.development
            warn "Created .env.development from example. Please edit it with your settings."
        else
            error "Example environment file not found"
        fi
    else
        info "Environment file already exists"
    fi
    
    # Create necessary directories
    mkdir -p logs data
    
    log "Setup completed! Please edit docker/environments/.env.development with your settings."
}

start_services() {
    log "Starting SonarQube MCP services..."
    
    if [[ ! -f "docker/environments/.env.development" ]]; then
        error "Environment file not found. Run '$0 setup' first."
    fi
    
    docker compose $COMPOSE_FILES $ENV_FILE up --build -d
    
    log "Services started! Use '$0 status' to check status."
    show_urls
}

stop_services() {
    log "Stopping SonarQube MCP services..."
    docker compose $COMPOSE_FILES down
    log "Services stopped."
}

restart_services() {
    log "Restarting SonarQube MCP services..."
    docker compose $COMPOSE_FILES $ENV_FILE down
    docker compose $COMPOSE_FILES $ENV_FILE up --build -d
    log "Services restarted."
}

build_images() {
    log "Building custom images..."
    docker compose $COMPOSE_FILES $ENV_FILE build --no-cache
    log "Images built."
}

rebuild_services() {
    log "Rebuilding and restarting services..."
    docker compose $COMPOSE_FILES $ENV_FILE down
    docker compose $COMPOSE_FILES $ENV_FILE build --no-cache
    docker compose $COMPOSE_FILES $ENV_FILE up -d
    log "Services rebuilt and restarted."
}

show_logs() {
    local service=${1:-}
    
    if [[ -n "$service" ]]; then
        log "Showing logs for $service..."
        docker compose $COMPOSE_FILES logs -f "$service"
    else
        log "Showing logs for all services..."
        docker compose $COMPOSE_FILES logs -f
    fi
}

open_shell() {
    local service=${1:-}
    
    if [[ -z "$service" ]]; then
        error "Please specify a service name"
    fi
    
    log "Opening shell in $service..."
    docker compose $COMPOSE_FILES exec "$service" bash
}

show_status() {
    log "Service status:"
    docker compose $COMPOSE_FILES ps
    
    echo ""
    log "Resource usage:"
    docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.NetIO}}\t{{.BlockIO}}"
}

clean_up() {
    log "Cleaning up containers and images..."
    
    # Stop services
    docker compose $COMPOSE_FILES down
    
    # Remove unused containers, networks, images
    docker system prune -f
    
    log "Cleanup completed."
}

reset_everything() {
    warn "This will remove all containers, volumes, and data!"
    read -p "Are you sure? (yes/no): " confirmation
    
    if [[ "$confirmation" == "yes" ]]; then
        log "Resetting everything..."
        
        # Stop and remove everything
        docker compose $COMPOSE_FILES down -v --remove-orphans
        
        # Remove custom images
        docker rmi $(docker images | grep sonarqube-mcp | awk '{print $3}') 2>/dev/null || true
        
        # Clean up system
        docker system prune -a -f --volumes
        
        log "Reset completed."
    else
        log "Reset cancelled."
    fi
}

backup_volumes() {
    log "Backing up volumes..."
    
    local backup_dir="backups/$(date +%Y%m%d_%H%M%S)"
    mkdir -p "$backup_dir"
    
    # Backup PostgreSQL data
    docker run --rm -v postgres_data:/data -v "$(pwd)/$backup_dir":/backup alpine \
        tar czf /backup/postgres_data.tar.gz -C /data .
    
    # Backup SonarQube data
    docker run --rm -v sonarqube_data:/data -v "$(pwd)/$backup_dir":/backup alpine \
        tar czf /backup/sonarqube_data.tar.gz -C /data .
    
    # Backup Redis data
    docker run --rm -v redis_data:/data -v "$(pwd)/$backup_dir":/backup alpine \
        tar czf /backup/redis_data.tar.gz -C /data .
    
    log "Backup completed: $backup_dir"
}

restore_volumes() {
    local backup_dir=${1:-}
    
    if [[ -z "$backup_dir" ]]; then
        error "Please specify backup directory"
    fi
    
    if [[ ! -d "$backup_dir" ]]; then
        error "Backup directory not found: $backup_dir"
    fi
    
    warn "This will overwrite existing data!"
    read -p "Are you sure? (yes/no): " confirmation
    
    if [[ "$confirmation" == "yes" ]]; then
        log "Restoring volumes from $backup_dir..."
        
        # Stop services
        docker compose $COMPOSE_FILES down
        
        # Restore PostgreSQL data
        if [[ -f "$backup_dir/postgres_data.tar.gz" ]]; then
            docker run --rm -v postgres_data:/data -v "$(pwd)/$backup_dir":/backup alpine \
                tar xzf /backup/postgres_data.tar.gz -C /data
        fi
        
        # Restore SonarQube data
        if [[ -f "$backup_dir/sonarqube_data.tar.gz" ]]; then
            docker run --rm -v sonarqube_data:/data -v "$(pwd)/$backup_dir":/backup alpine \
                tar xzf /backup/sonarqube_data.tar.gz -C /data
        fi
        
        # Restore Redis data
        if [[ -f "$backup_dir/redis_data.tar.gz" ]]; then
            docker run --rm -v redis_data:/data -v "$(pwd)/$backup_dir":/backup alpine \
                tar xzf /backup/redis_data.tar.gz -C /data
        fi
        
        log "Restore completed."
    else
        log "Restore cancelled."
    fi
}

check_health() {
    log "Checking service health..."
    
    local services=("mcp-server:8000/health" "streamlit-app:8501/_stcore/health" "sonarqube:9000/sonarqube/api/system/status")
    
    for service_url in "${services[@]}"; do
        local service=$(echo "$service_url" | cut -d: -f1)
        local url="http://localhost:${service_url#*:}"
        
        if curl -f -s "$url" > /dev/null 2>&1; then
            echo "✅ $service - Healthy"
        else
            echo "❌ $service - Unhealthy"
        fi
    done
    
    # Check database connections
    if docker compose $COMPOSE_FILES exec -T postgres pg_isready -U sonarqube > /dev/null 2>&1; then
        echo "✅ PostgreSQL - Connected"
    else
        echo "❌ PostgreSQL - Connection failed"
    fi
    
    if docker compose $COMPOSE_FILES exec -T redis redis-cli ping > /dev/null 2>&1; then
        echo "✅ Redis - Connected"
    else
        echo "❌ Redis - Connection failed"
    fi
}

show_ports() {
    log "Port Mapping Reference:"
    echo ""
    echo "🔌 PORT MAPPING TABLE:"
    echo "┌─────────────────┬──────────────┬───────────────┬─────────────────────────────────┐"
    echo "│ Service         │ Host Port    │ Container Port│ Purpose                         │"
    echo "├─────────────────┼──────────────┼───────────────┼─────────────────────────────────┤"
    echo "│ Streamlit App   │ 8501         │ 8501          │ Web UI Access                   │"
    echo "│ SonarQube       │ 9000         │ 9000          │ Code Analysis Dashboard         │"
    echo "│ MCP Server      │ 8000         │ 8000          │ MCP API Endpoints               │"
    echo "│ pgAdmin         │ 8082         │ 80            │ Database Administration         │"
    echo "│ Redis Commander │ 8081         │ 8081          │ Cache Management                │"
    echo "│ Mailhog Web     │ 8025         │ 8025          │ Email Testing Interface         │"
    echo "│ PostgreSQL      │ 5432         │ 5432          │ Database Connections            │"
    echo "│ Redis           │ 6379         │ 6379          │ Cache Connections               │"
    echo "│ Mailhog SMTP    │ 1025         │ 1025          │ Email Testing SMTP              │"
    echo "└─────────────────┴──────────────┴───────────────┴─────────────────────────────────┘"
    echo ""
    echo "💡 Tips:"
    echo "   • All services are accessible from localhost"
    echo "   • Internal communication uses container names (e.g., postgres:5432)"
    echo "   • Change host ports in development.yml if conflicts occur"
    echo "   • Use 'docker port <container_name>' to check specific mappings"
}

show_urls() {
    log "Service URLs and Ports:"
    echo ""
    echo "🌐 MAIN SERVICES:"
    echo "┌─────────────────┬─────────────────────────────────────┬──────┬─────────────────────┐"
    echo "│ Service         │ URL                                 │ Port │ Credentials         │"
    echo "├─────────────────┼─────────────────────────────────────┼──────┼─────────────────────┤"
    echo "│ Streamlit App   │ http://localhost:8501               │ 8501 │ -                   │"
    echo "│ SonarQube       │ http://localhost:9000/sonarqube     │ 9000 │ admin / admin       │"
    echo "│ MCP Server      │ http://localhost:8000               │ 8000 │ -                   │"
    echo "└─────────────────┴─────────────────────────────────────┴──────┴─────────────────────┘"
    echo ""
    echo "🛠️ DEVELOPMENT TOOLS:"
    echo "┌─────────────────┬─────────────────────────────────────┬──────┬─────────────────────┐"
    echo "│ Service         │ URL                                 │ Port │ Credentials         │"
    echo "├─────────────────┼─────────────────────────────────────┼──────┼─────────────────────┤"
    echo "│ pgAdmin         │ http://localhost:8082               │ 8082 │ admin@example.com   │"
    echo "│                 │                                     │      │ / admin             │"
    echo "│ Redis Commander │ http://localhost:8081               │ 8081 │ -                   │"
    echo "│ Mailhog         │ http://localhost:8025               │ 8025 │ -                   │"
    echo "└─────────────────┴─────────────────────────────────────┴──────┴─────────────────────┘"
    echo ""
    echo "🔌 DATABASE CONNECTIONS:"
    echo "┌─────────────────┬─────────────────────────────────────┬──────┬─────────────────────┐"
    echo "│ Service         │ Connection                          │ Port │ Credentials         │"
    echo "├─────────────────┼─────────────────────────────────────┼──────┼─────────────────────┤"
    echo "│ PostgreSQL      │ localhost:5432                      │ 5432 │ sonarqube /         │"
    echo "│                 │ Database: sonarqube                 │      │ sonarqube_dev_pass  │"
    echo "│ Redis           │ localhost:6379                      │ 6379 │ redis_dev_password  │"
    echo "│ Mailhog SMTP    │ localhost:1025                      │ 1025 │ -                   │"
    echo "└─────────────────┴─────────────────────────────────────┴──────┴─────────────────────┘"
    echo ""
    echo "🔍 HEALTH CHECKS:"
    echo "   • MCP Server Health: http://localhost:8000/health"
    echo "   • Streamlit Health: http://localhost:8501/_stcore/health"
    echo "   • SonarQube Status: http://localhost:9000/sonarqube/api/system/status"
}

main() {
    if [[ $# -eq 0 ]]; then
        usage
    fi
    
    check_prerequisites
    
    case "$1" in
        setup)
            setup
            ;;
        start)
            start_services
            ;;
        stop)
            stop_services
            ;;
        restart)
            restart_services
            ;;
        build)
            build_images
            ;;
        rebuild)
            rebuild_services
            ;;
        logs)
            show_logs "${2:-}"
            ;;
        shell)
            open_shell "${2:-}"
            ;;
        status)
            show_status
            ;;
        clean)
            clean_up
            ;;
        reset)
            reset_everything
            ;;
        backup)
            backup_volumes
            ;;
        restore)
            restore_volumes "${2:-}"
            ;;
        health)
            check_health
            ;;
        urls)
            show_urls
            ;;
        ports)
            show_ports
            ;;
        *)
            error "Unknown command: $1"
            ;;
    esac
}

main "$@"