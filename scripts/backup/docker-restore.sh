#!/bin/bash

# Docker Compose Restore Script for SonarQube MCP
# This script restores data from Docker volume backups

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
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
    echo "  -b, --backup-path PATH    Path to backup directory or compressed file"
    echo "  -f, --force               Force restore without confirmation"
    echo "  -v, --volumes-only        Restore volumes only (skip configs)"
    echo "  -c, --configs-only        Restore configurations only (skip volumes)"
    echo "  -h, --help                Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 --backup-path /path/to/backup"
    echo "  $0 --backup-path backup.tar.gz --force"
    echo "  $0 --backup-path /backup --volumes-only"
    exit 1
}

# Parse command line arguments
parse_args() {
    BACKUP_PATH=""
    FORCE_RESTORE=false
    VOLUMES_ONLY=false
    CONFIGS_ONLY=false
    
    while [[ $# -gt 0 ]]; do
        case $1 in
            -b|--backup-path)
                BACKUP_PATH="$2"
                shift 2
                ;;
            -f|--force)
                FORCE_RESTORE=true
                shift
                ;;
            -v|--volumes-only)
                VOLUMES_ONLY=true
                shift
                ;;
            -c|--configs-only)
                CONFIGS_ONLY=true
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
    
    if [[ -z "$BACKUP_PATH" ]]; then
        error "Backup path is required. Use --backup-path option."
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
    
    cd "$PROJECT_ROOT"
    
    log "Prerequisites check passed"
}

# Extract compressed backup if needed
extract_backup() {
    if [[ "$BACKUP_PATH" == *.tar.gz ]]; then
        log "Extracting compressed backup..."
        
        local extract_dir="/tmp/sonarqube-mcp-restore-$(date +%s)"
        mkdir -p "$extract_dir"
        
        tar xzf "$BACKUP_PATH" -C "$extract_dir"
        
        # Find the backup directory inside the extracted content
        local backup_dir=$(find "$extract_dir" -maxdepth 1 -type d -name "20*" | head -1)
        
        if [[ -z "$backup_dir" ]]; then
            error "Could not find backup directory in extracted archive"
        fi
        
        BACKUP_PATH="$backup_dir"
        EXTRACTED_BACKUP=true
        
        log "Backup extracted to: $BACKUP_PATH"
    fi
}

# Validate backup directory
validate_backup() {
    log "Validating backup directory: $BACKUP_PATH"
    
    if [[ ! -d "$BACKUP_PATH" ]]; then
        error "Backup directory does not exist: $BACKUP_PATH"
    fi
    
    # Check for manifest file
    if [[ ! -f "$BACKUP_PATH/manifest.txt" ]]; then
        warn "Backup manifest not found. This may not be a valid backup."
    else
        log "Backup manifest found:"
        head -10 "$BACKUP_PATH/manifest.txt"
    fi
    
    # Check for expected directories
    if [[ "$VOLUMES_ONLY" != "true" && "$CONFIGS_ONLY" != "true" ]]; then
        if [[ ! -d "$BACKUP_PATH/volumes" ]] && [[ ! -d "$BACKUP_PATH/configs" ]]; then
            error "Backup directory does not contain expected volumes or configs directories"
        fi
    elif [[ "$VOLUMES_ONLY" == "true" && ! -d "$BACKUP_PATH/volumes" ]]; then
        error "Backup directory does not contain volumes directory"
    elif [[ "$CONFIGS_ONLY" == "true" && ! -d "$BACKUP_PATH/configs" ]]; then
        error "Backup directory does not contain configs directory"
    fi
    
    log "Backup validation completed"
}

# Confirm restore operation
confirm_restore() {
    if [[ "$FORCE_RESTORE" == "true" ]]; then
        return 0
    fi
    
    warn "This operation will restore data from backup and may overwrite existing data."
    warn "Current data will be lost. Are you sure you want to continue?"
    
    echo ""
    echo "Restore Summary:"
    echo "  Backup Path: $BACKUP_PATH"
    echo "  Volumes Only: $VOLUMES_ONLY"
    echo "  Configs Only: $CONFIGS_ONLY"
    echo ""
    
    read -p "Type 'yes' to confirm: " confirmation
    
    if [[ "$confirmation" != "yes" ]]; then
        log "Restore operation cancelled"
        exit 0
    fi
}

# Stop services
stop_services() {
    log "Stopping services..."
    docker compose $COMPOSE_FILES $ENV_FILE down
    log "Services stopped"
}

# Start services
start_services() {
    log "Starting services..."
    docker compose $COMPOSE_FILES $ENV_FILE up -d
    
    # Wait for services to be ready
    log "Waiting for services to be ready..."
    sleep 10
    
    # Check if MCP server is responding
    local max_wait=60
    local wait_time=0
    
    while ! curl -f http://localhost:8001/health &> /dev/null; do
        if [[ $wait_time -ge $max_wait ]]; then
            warn "Services may not be fully ready yet"
            break
        fi
        sleep 5
        wait_time=$((wait_time + 5))
    done
    
    log "Services started"
}

# Restore Docker volumes
restore_volumes() {
    if [[ "$CONFIGS_ONLY" == "true" ]]; then
        return 0
    fi
    
    log "Restoring Docker volumes..."
    
    if [[ ! -d "$BACKUP_PATH/volumes" ]]; then
        warn "No volumes directory found in backup"
        return 0
    fi
    
    # Get list of volume backup files
    local volume_backups=$(find "$BACKUP_PATH/volumes" -name "*.tar.gz" -type f)
    
    if [[ -z "$volume_backups" ]]; then
        warn "No volume backup files found"
        return 0
    fi
    
    for volume_backup in $volume_backups; do
        local volume_name=$(basename "$volume_backup" .tar.gz)
        
        log "Restoring volume: $volume_name"
        
        # Create volume if it doesn't exist
        docker volume create "$volume_name" > /dev/null 2>&1 || true
        
        # Restore volume data
        docker run --rm \
            -v "${volume_name}:/target" \
            -v "$BACKUP_PATH/volumes:/backup:ro" \
            alpine \
            sh -c "cd /target && tar xzf /backup/${volume_name}.tar.gz"
        
        if [[ $? -eq 0 ]]; then
            log "Volume $volume_name restored successfully"
        else
            warn "Failed to restore volume $volume_name"
        fi
    done
    
    log "Volume restoration completed"
}

# Restore configurations
restore_configurations() {
    if [[ "$VOLUMES_ONLY" == "true" ]]; then
        return 0
    fi
    
    log "Restoring configurations..."
    
    if [[ ! -d "$BACKUP_PATH/configs" ]]; then
        warn "No configs directory found in backup"
        return 0
    fi
    
    # Restore Docker Compose files
    if [[ -d "$BACKUP_PATH/configs/docker" ]]; then
        log "Restoring Docker Compose configurations..."
        
        # Backup current configs
        if [[ -d "docker" ]]; then
            mv docker docker.backup.$(date +%s)
        fi
        
        cp -r "$BACKUP_PATH/configs/docker" .
        log "Docker configurations restored"
    fi
    
    # Restore environment files
    if [[ -d "$BACKUP_PATH/configs/environments" ]]; then
        log "Restoring environment configurations..."
        
        mkdir -p docker/environments
        
        # Copy environment files but warn about masked values
        for env_file in "$BACKUP_PATH/configs/environments"/*; do
            if [[ -f "$env_file" ]]; then
                local filename=$(basename "$env_file")
                cp "$env_file" "docker/environments/$filename"
                
                # Check if file contains masked values
                if grep -q "***MASKED***" "$env_file"; then
                    warn "Environment file $filename contains masked sensitive values"
                    warn "Please update docker/environments/$filename with actual values"
                fi
            fi
        done
        
        log "Environment configurations restored"
    fi
    
    # Restore source code if available
    if [[ -f "$BACKUP_PATH/configs/source-code.tar.gz" ]]; then
        log "Source code backup found. Restore manually if needed:"
        log "  tar xzf $BACKUP_PATH/configs/source-code.tar.gz"
    fi
    
    log "Configuration restoration completed"
}

# Verify restore
verify_restore() {
    log "Verifying restore..."
    
    # Check if services are running
    local running_containers=$(docker compose $COMPOSE_FILES ps -q | wc -l)
    log "Running containers: $running_containers"
    
    # Check service health
    if curl -f http://localhost:8001/health &> /dev/null; then
        log "MCP server is responding"
    else
        warn "MCP server is not responding"
    fi
    
    if curl -f http://localhost:8501/_stcore/health &> /dev/null; then
        log "Streamlit app is responding"
    else
        warn "Streamlit app is not responding"
    fi
    
    log "Restore verification completed"
}

# Cleanup function
cleanup() {
    if [[ "${EXTRACTED_BACKUP:-false}" == "true" ]]; then
        log "Cleaning up extracted backup..."
        rm -rf "$(dirname "$BACKUP_PATH")"
    fi
}

# Main restore function
main() {
    log "Starting SonarQube MCP restore process..."
    
    trap cleanup EXIT
    trap 'error "Restore failed due to an error"' ERR
    
    parse_args "$@"
    check_prerequisites
    extract_backup
    validate_backup
    confirm_restore
    
    stop_services
    
    restore_volumes
    restore_configurations
    
    start_services
    verify_restore
    
    log "Restore process completed successfully!"
    
    if grep -q "***MASKED***" docker/environments/*.env* 2>/dev/null; then
        warn "Some environment files contain masked values"
        warn "Please update the following files with actual values:"
        grep -l "***MASKED***" docker/environments/*.env* 2>/dev/null || true
    fi
    
    log "Services should be accessible at:"
    echo "  - Streamlit App: http://localhost:8501"
    echo "  - MCP Server: http://localhost:8001"
    echo "  - SonarQube: http://localhost:9000/sonarqube"
}

# Run main function
main "$@"