#!/bin/bash

# Docker Compose Backup Script for SonarQube MCP
# This script creates backups of Docker volumes and configurations

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
BACKUP_DIR="$PROJECT_ROOT/backups/$(date +%Y%m%d_%H%M%S)"
COMPOSE_FILES="-f docker/compose/base/docker-compose.yml -f docker/compose/environments/development.yml"
ENV_FILE="--env-file docker/environments/.env.development"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
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

usage() {
    echo "Usage: $0 [OPTIONS]"
    echo "Options:"
    echo "  -d, --backup-dir DIR    Custom backup directory"
    echo "  -c, --compress          Compress backup files"
    echo "  -s, --stop-services     Stop services during backup"
    echo "  -h, --help              Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 --compress"
    echo "  $0 --backup-dir /custom/backup/path"
    exit 1
}

# Parse command line arguments
parse_args() {
    COMPRESS_BACKUP=false
    STOP_SERVICES=false
    
    while [[ $# -gt 0 ]]; do
        case $1 in
            -d|--backup-dir)
                BACKUP_DIR="$2"
                shift 2
                ;;
            -c|--compress)
                COMPRESS_BACKUP=true
                shift
                ;;
            -s|--stop-services)
                STOP_SERVICES=true
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

# Check prerequisites
check_prerequisites() {
    log "Checking prerequisites..."
    
    if ! command -v docker &> /dev/null; then
        error "Docker is not installed or not in PATH"
    fi
    
    if ! docker compose version &> /dev/null; then
        error "Docker Compose is not available"
    fi
    
    cd "$PROJECT_ROOT"
    
    log "Prerequisites check passed"
}

# Create backup directory
create_backup_dir() {
    log "Creating backup directory: $BACKUP_DIR"
    mkdir -p "$BACKUP_DIR"/{volumes,configs,logs}
}

# Stop services if requested
stop_services() {
    if [[ "$STOP_SERVICES" == "true" ]]; then
        log "Stopping services for backup..."
        docker compose $COMPOSE_FILES $ENV_FILE stop
    fi
}

# Start services if they were stopped
start_services() {
    if [[ "$STOP_SERVICES" == "true" ]]; then
        log "Starting services after backup..."
        docker compose $COMPOSE_FILES $ENV_FILE start
    fi
}

# Backup Docker volumes
backup_volumes() {
    log "Backing up Docker volumes..."
    
    # Get list of volumes used by the project
    local volumes=$(docker compose $COMPOSE_FILES config --volumes)
    
    for volume in $volumes; do
        log "Backing up volume: $volume"
        
        # Create a temporary container to access the volume
        docker run --rm \
            -v "${volume}:/source:ro" \
            -v "$BACKUP_DIR/volumes:/backup" \
            alpine \
            tar czf "/backup/${volume}.tar.gz" -C /source .
        
        if [[ $? -eq 0 ]]; then
            log "Volume $volume backed up successfully"
        else
            warn "Failed to backup volume $volume"
        fi
    done
}

# Backup configurations
backup_configurations() {
    log "Backing up configurations..."
    
    # Backup Docker Compose files
    cp -r docker/ "$BACKUP_DIR/configs/"
    
    # Backup environment files (without sensitive data)
    if [[ -d "docker/environments" ]]; then
        mkdir -p "$BACKUP_DIR/configs/environments"
        
        # Copy environment files but mask sensitive values
        for env_file in docker/environments/*.env*; do
            if [[ -f "$env_file" ]]; then
                local filename=$(basename "$env_file")
                sed 's/\(TOKEN\|PASSWORD\|SECRET\|KEY\)=.*/\1=***MASKED***/g' "$env_file" > "$BACKUP_DIR/configs/environments/$filename"
            fi
        done
    fi
    
    # Backup application source (optional)
    if [[ -d "src" ]]; then
        tar czf "$BACKUP_DIR/configs/source-code.tar.gz" src/
    fi
    
    log "Configurations backed up successfully"
}

# Backup application logs
backup_logs() {
    log "Backing up application logs..."
    
    # Backup container logs
    local containers=$(docker compose $COMPOSE_FILES ps -q)
    
    for container in $containers; do
        if [[ -n "$container" ]]; then
            local container_name=$(docker inspect --format='{{.Name}}' "$container" | sed 's/\///')
            docker logs "$container" > "$BACKUP_DIR/logs/${container_name}.log" 2>&1 || true
        fi
    done
    
    # Backup application log files if they exist
    if [[ -d "logs" ]]; then
        cp -r logs/ "$BACKUP_DIR/logs/application-logs/"
    fi
    
    log "Logs backed up successfully"
}

# Create backup manifest
create_manifest() {
    log "Creating backup manifest..."
    
    cat > "$BACKUP_DIR/manifest.txt" << EOF
SonarQube MCP Backup Manifest
============================
Backup Date: $(date)
Backup Directory: $BACKUP_DIR
Project Root: $PROJECT_ROOT
Docker Compose Version: $(docker compose version)
Docker Version: $(docker --version)

Backup Contents:
- Docker volumes: $(ls -1 "$BACKUP_DIR/volumes/" | wc -l) files
- Configuration files: $(find "$BACKUP_DIR/configs/" -type f | wc -l) files
- Log files: $(find "$BACKUP_DIR/logs/" -type f | wc -l) files

Volume Sizes:
$(du -sh "$BACKUP_DIR/volumes/"* 2>/dev/null || echo "No volumes backed up")

Total Backup Size: $(du -sh "$BACKUP_DIR" | cut -f1)

Restore Instructions:
1. Stop services: docker compose $COMPOSE_FILES $ENV_FILE down
2. Restore volumes using docker-restore.sh script
3. Restore configurations from configs/ directory
4. Start services: docker compose $COMPOSE_FILES $ENV_FILE up -d
EOF
    
    log "Backup manifest created"
}

# Compress backup if requested
compress_backup() {
    if [[ "$COMPRESS_BACKUP" == "true" ]]; then
        log "Compressing backup..."
        
        local backup_name=$(basename "$BACKUP_DIR")
        local compressed_file="${BACKUP_DIR}.tar.gz"
        
        tar czf "$compressed_file" -C "$(dirname "$BACKUP_DIR")" "$backup_name"
        
        if [[ $? -eq 0 ]]; then
            log "Backup compressed to: $compressed_file"
            
            # Remove uncompressed backup
            rm -rf "$BACKUP_DIR"
            
            log "Uncompressed backup removed"
        else
            error "Failed to compress backup"
        fi
    fi
}

# Verify backup integrity
verify_backup() {
    log "Verifying backup integrity..."
    
    local backup_path="$BACKUP_DIR"
    
    if [[ "$COMPRESS_BACKUP" == "true" ]]; then
        backup_path="${BACKUP_DIR}.tar.gz"
        
        # Test compressed file
        if ! tar tzf "$backup_path" > /dev/null 2>&1; then
            error "Compressed backup file is corrupted"
        fi
    else
        # Check if backup directory exists and has content
        if [[ ! -d "$backup_path" ]]; then
            error "Backup directory not found"
        fi
        
        if [[ -z "$(ls -A "$backup_path")" ]]; then
            error "Backup directory is empty"
        fi
    fi
    
    log "Backup integrity verification passed"
}

# Main backup function
main() {
    log "Starting SonarQube MCP backup process..."
    
    trap 'start_services; error "Backup failed due to an error"' ERR
    
    parse_args "$@"
    check_prerequisites
    create_backup_dir
    
    stop_services
    
    backup_volumes
    backup_configurations
    backup_logs
    
    start_services
    
    create_manifest
    compress_backup
    verify_backup
    
    log "Backup process completed successfully!"
    
    if [[ "$COMPRESS_BACKUP" == "true" ]]; then
        log "Backup location: ${BACKUP_DIR}.tar.gz"
    else
        log "Backup location: $BACKUP_DIR"
    fi
    
    # Show backup size
    if [[ "$COMPRESS_BACKUP" == "true" ]]; then
        local size=$(du -sh "${BACKUP_DIR}.tar.gz" | cut -f1)
        log "Backup size: $size"
    else
        local size=$(du -sh "$BACKUP_DIR" | cut -f1)
        log "Backup size: $size"
    fi
}

# Run main function
main "$@"