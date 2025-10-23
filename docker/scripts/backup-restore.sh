#!/bin/bash
# Backup and restore script for SonarQube MCP

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
BACKUP_DIR="backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_NAME="sonarqube-mcp-backup-$TIMESTAMP"

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

# Create backup directory
setup_backup_dir() {
    if [ ! -d "$BACKUP_DIR" ]; then
        mkdir -p "$BACKUP_DIR"
        log "Created backup directory: $BACKUP_DIR"
    fi
}

# Backup PostgreSQL database
backup_postgres() {
    log "Backing up PostgreSQL database..."
    
    local backup_file="$BACKUP_DIR/${BACKUP_NAME}_postgres.sql"
    
    # Check if PostgreSQL container is running
    if ! $DOCKER_COMPOSE_CMD ps postgres | grep -q "Up"; then
        error "PostgreSQL container is not running"
        return 1
    fi
    
    # Create database backup
    $DOCKER_COMPOSE_CMD exec -T postgres pg_dumpall -U sonarqube > "$backup_file"
    
    if [ -f "$backup_file" ] && [ -s "$backup_file" ]; then
        # Compress backup
        gzip "$backup_file"
        success "PostgreSQL backup created: ${backup_file}.gz"
    else
        error "Failed to create PostgreSQL backup"
        return 1
    fi
}

# Backup Redis data
backup_redis() {
    log "Backing up Redis data..."
    
    local backup_file="$BACKUP_DIR/${BACKUP_NAME}_redis.rdb"
    
    # Check if Redis container is running
    if ! $DOCKER_COMPOSE_CMD ps redis | grep -q "Up"; then
        error "Redis container is not running"
        return 1
    fi
    
    # Create Redis backup
    $DOCKER_COMPOSE_CMD exec -T redis redis-cli --rdb - > "$backup_file"
    
    if [ -f "$backup_file" ] && [ -s "$backup_file" ]; then
        # Compress backup
        gzip "$backup_file"
        success "Redis backup created: ${backup_file}.gz"
    else
        error "Failed to create Redis backup"
        return 1
    fi
}

# Backup SonarQube data
backup_sonarqube() {
    log "Backing up SonarQube data..."
    
    local backup_dir="$BACKUP_DIR/${BACKUP_NAME}_sonarqube"
    
    # Check if SonarQube container is running
    if ! $DOCKER_COMPOSE_CMD ps sonarqube | grep -q "Up"; then
        warning "SonarQube container is not running, backing up volumes only"
    fi
    
    # Create backup directory
    mkdir -p "$backup_dir"
    
    # Backup SonarQube data volume
    docker run --rm \
        -v sonarqube-mcp_sonarqube_data:/source:ro \
        -v "$(pwd)/$backup_dir":/backup \
        alpine \
        tar czf /backup/sonarqube_data.tar.gz -C /source .
    
    # Backup SonarQube logs volume
    docker run --rm \
        -v sonarqube-mcp_sonarqube_logs:/source:ro \
        -v "$(pwd)/$backup_dir":/backup \
        alpine \
        tar czf /backup/sonarqube_logs.tar.gz -C /source .
    
    # Backup SonarQube extensions volume
    docker run --rm \
        -v sonarqube-mcp_sonarqube_extensions:/source:ro \
        -v "$(pwd)/$backup_dir":/backup \
        alpine \
        tar czf /backup/sonarqube_extensions.tar.gz -C /source .
    
    success "SonarQube data backup created: $backup_dir"
}

# Backup configuration files
backup_config() {
    log "Backing up configuration files..."
    
    local config_backup="$BACKUP_DIR/${BACKUP_NAME}_config.tar.gz"
    
    # Create list of files to backup
    local config_files=(
        ".env"
        "docker-compose.yml"
        "docker-compose.dev.yml"
        "docker-compose.prod.yml"
        "config/"
        "docker/"
    )
    
    # Create config backup
    tar czf "$config_backup" "${config_files[@]}" 2>/dev/null || {
        warning "Some configuration files may be missing"
    }
    
    if [ -f "$config_backup" ]; then
        success "Configuration backup created: $config_backup"
    else
        error "Failed to create configuration backup"
        return 1
    fi
}

# Create full backup
create_backup() {
    log "Creating full backup: $BACKUP_NAME"
    
    setup_backup_dir
    
    local backup_success=true
    
    # Backup each component
    backup_postgres || backup_success=false
    backup_redis || backup_success=false
    backup_sonarqube || backup_success=false
    backup_config || backup_success=false
    
    # Create backup manifest
    local manifest_file="$BACKUP_DIR/${BACKUP_NAME}_manifest.txt"
    cat > "$manifest_file" << EOF
SonarQube MCP Backup Manifest
=============================
Backup Name: $BACKUP_NAME
Created: $(date)
Components:
- PostgreSQL Database
- Redis Data
- SonarQube Data
- Configuration Files

Files:
$(ls -la "$BACKUP_DIR"/${BACKUP_NAME}_* 2>/dev/null || echo "No backup files found")
EOF
    
    if [ "$backup_success" = true ]; then
        success "Full backup completed successfully: $BACKUP_NAME"
        log "Backup manifest: $manifest_file"
    else
        error "Backup completed with errors"
        return 1
    fi
}

# Restore PostgreSQL database
restore_postgres() {
    local backup_file="$1"
    
    log "Restoring PostgreSQL database from: $backup_file"
    
    # Check if backup file exists
    if [ ! -f "$backup_file" ]; then
        error "PostgreSQL backup file not found: $backup_file"
        return 1
    fi
    
    # Stop services that depend on database
    log "Stopping dependent services..."
    $DOCKER_COMPOSE_CMD stop sonarqube mcp-server streamlit-app
    
    # Restore database
    if [[ "$backup_file" == *.gz ]]; then
        gunzip -c "$backup_file" | $DOCKER_COMPOSE_CMD exec -T postgres psql -U sonarqube
    else
        $DOCKER_COMPOSE_CMD exec -T postgres psql -U sonarqube < "$backup_file"
    fi
    
    success "PostgreSQL database restored"
}

# Restore Redis data
restore_redis() {
    local backup_file="$1"
    
    log "Restoring Redis data from: $backup_file"
    
    # Check if backup file exists
    if [ ! -f "$backup_file" ]; then
        error "Redis backup file not found: $backup_file"
        return 1
    fi
    
    # Stop Redis
    $DOCKER_COMPOSE_CMD stop redis
    
    # Restore Redis data
    if [[ "$backup_file" == *.gz ]]; then
        gunzip -c "$backup_file" | $DOCKER_COMPOSE_CMD exec -T redis redis-cli --pipe
    else
        $DOCKER_COMPOSE_CMD exec -T redis redis-cli --pipe < "$backup_file"
    fi
    
    # Restart Redis
    $DOCKER_COMPOSE_CMD start redis
    
    success "Redis data restored"
}

# Restore SonarQube data
restore_sonarqube() {
    local backup_dir="$1"
    
    log "Restoring SonarQube data from: $backup_dir"
    
    # Check if backup directory exists
    if [ ! -d "$backup_dir" ]; then
        error "SonarQube backup directory not found: $backup_dir"
        return 1
    fi
    
    # Stop SonarQube
    $DOCKER_COMPOSE_CMD stop sonarqube
    
    # Restore data volume
    if [ -f "$backup_dir/sonarqube_data.tar.gz" ]; then
        docker run --rm \
            -v sonarqube-mcp_sonarqube_data:/target \
            -v "$(pwd)/$backup_dir":/backup \
            alpine \
            sh -c "cd /target && tar xzf /backup/sonarqube_data.tar.gz"
    fi
    
    # Restore logs volume
    if [ -f "$backup_dir/sonarqube_logs.tar.gz" ]; then
        docker run --rm \
            -v sonarqube-mcp_sonarqube_logs:/target \
            -v "$(pwd)/$backup_dir":/backup \
            alpine \
            sh -c "cd /target && tar xzf /backup/sonarqube_logs.tar.gz"
    fi
    
    # Restore extensions volume
    if [ -f "$backup_dir/sonarqube_extensions.tar.gz" ]; then
        docker run --rm \
            -v sonarqube-mcp_sonarqube_extensions:/target \
            -v "$(pwd)/$backup_dir":/backup \
            alpine \
            sh -c "cd /target && tar xzf /backup/sonarqube_extensions.tar.gz"
    fi
    
    success "SonarQube data restored"
}

# Restore configuration files
restore_config() {
    local config_backup="$1"
    
    log "Restoring configuration from: $config_backup"
    
    # Check if backup file exists
    if [ ! -f "$config_backup" ]; then
        error "Configuration backup file not found: $config_backup"
        return 1
    fi
    
    # Create backup of current config
    local current_backup="config_backup_$(date +%Y%m%d_%H%M%S).tar.gz"
    tar czf "$current_backup" .env docker-compose*.yml config/ docker/ 2>/dev/null || true
    log "Current configuration backed up to: $current_backup"
    
    # Restore configuration
    tar xzf "$config_backup"
    
    success "Configuration restored"
}

# Restore from backup
restore_backup() {
    local backup_name="$1"
    
    if [ -z "$backup_name" ]; then
        error "Backup name is required"
        list_backups
        return 1
    fi
    
    log "Restoring from backup: $backup_name"
    
    # Confirm restore operation
    warning "This will overwrite current data!"
    read -p "Are you sure you want to restore from backup '$backup_name'? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        log "Restore cancelled"
        return 0
    fi
    
    local restore_success=true
    
    # Restore each component
    if [ -f "$BACKUP_DIR/${backup_name}_postgres.sql.gz" ]; then
        restore_postgres "$BACKUP_DIR/${backup_name}_postgres.sql.gz" || restore_success=false
    fi
    
    if [ -f "$BACKUP_DIR/${backup_name}_redis.rdb.gz" ]; then
        restore_redis "$BACKUP_DIR/${backup_name}_redis.rdb.gz" || restore_success=false
    fi
    
    if [ -d "$BACKUP_DIR/${backup_name}_sonarqube" ]; then
        restore_sonarqube "$BACKUP_DIR/${backup_name}_sonarqube" || restore_success=false
    fi
    
    if [ -f "$BACKUP_DIR/${backup_name}_config.tar.gz" ]; then
        restore_config "$BACKUP_DIR/${backup_name}_config.tar.gz" || restore_success=false
    fi
    
    # Restart all services
    log "Restarting all services..."
    $DOCKER_COMPOSE_CMD up -d
    
    if [ "$restore_success" = true ]; then
        success "Restore completed successfully"
    else
        error "Restore completed with errors"
        return 1
    fi
}

# List available backups
list_backups() {
    log "Available backups:"
    
    if [ ! -d "$BACKUP_DIR" ] || [ -z "$(ls -A "$BACKUP_DIR" 2>/dev/null)" ]; then
        warning "No backups found"
        return
    fi
    
    # Group backups by name
    local backup_names=($(ls "$BACKUP_DIR" | grep -o 'sonarqube-mcp-backup-[0-9_]*' | sort -u))
    
    for backup_name in "${backup_names[@]}"; do
        echo -e "${GREEN}$backup_name${NC}"
        
        # Show backup components
        local components=()
        [ -f "$BACKUP_DIR/${backup_name}_postgres.sql.gz" ] && components+=("PostgreSQL")
        [ -f "$BACKUP_DIR/${backup_name}_redis.rdb.gz" ] && components+=("Redis")
        [ -d "$BACKUP_DIR/${backup_name}_sonarqube" ] && components+=("SonarQube")
        [ -f "$BACKUP_DIR/${backup_name}_config.tar.gz" ] && components+=("Config")
        
        echo "  Components: ${components[*]}"
        
        # Show backup size
        local total_size=$(du -sh "$BACKUP_DIR"/${backup_name}_* 2>/dev/null | awk '{sum+=$1} END {print sum}' || echo "Unknown")
        echo "  Size: $total_size"
        
        # Show backup date
        if [ -f "$BACKUP_DIR/${backup_name}_manifest.txt" ]; then
            local backup_date=$(grep "Created:" "$BACKUP_DIR/${backup_name}_manifest.txt" | cut -d' ' -f2-)
            echo "  Created: $backup_date"
        fi
        
        echo
    done
}

# Clean old backups
cleanup_backups() {
    local retention_days="${1:-30}"
    
    log "Cleaning up backups older than $retention_days days..."
    
    if [ ! -d "$BACKUP_DIR" ]; then
        log "No backup directory found"
        return
    fi
    
    # Find and delete old backups
    local deleted_count=0
    find "$BACKUP_DIR" -name "sonarqube-mcp-backup-*" -mtime +$retention_days -type f -delete 2>/dev/null || true
    find "$BACKUP_DIR" -name "sonarqube-mcp-backup-*" -mtime +$retention_days -type d -exec rm -rf {} + 2>/dev/null || true
    
    success "Backup cleanup completed"
}

# Usage information
usage() {
    echo "Usage: $0 COMMAND [OPTIONS]"
    echo
    echo "Backup and restore operations for SonarQube MCP"
    echo
    echo "Commands:"
    echo "  backup                Create full backup"
    echo "  restore BACKUP_NAME   Restore from backup"
    echo "  list                  List available backups"
    echo "  cleanup [DAYS]        Clean up old backups (default: 30 days)"
    echo
    echo "Examples:"
    echo "  $0 backup             # Create backup"
    echo "  $0 list               # List backups"
    echo "  $0 restore sonarqube-mcp-backup-20231122_143000"
    echo "  $0 cleanup 7          # Delete backups older than 7 days"
}

# Main function
main() {
    local command="$1"
    shift || true
    
    check_docker_compose
    
    case $command in
        backup)
            create_backup
            ;;
        restore)
            restore_backup "$1"
            ;;
        list)
            list_backups
            ;;
        cleanup)
            cleanup_backups "$1"
            ;;
        "")
            error "Command is required"
            usage
            exit 1
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