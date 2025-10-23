#!/bin/bash

# SonarQube MCP Backup Script
# This script creates backups of all persistent data

set -euo pipefail

# Configuration
NAMESPACE="sonarqube-mcp"
BACKUP_DIR="/backups/$(date +%Y%m%d_%H%M%S)"
S3_BUCKET="${S3_BACKUP_BUCKET:-sonarqube-mcp-backups}"
RETENTION_DAYS="${BACKUP_RETENTION_DAYS:-30}"

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

# Check prerequisites
check_prerequisites() {
    log "Checking prerequisites..."
    
    if ! command -v kubectl &> /dev/null; then
        error "kubectl is not installed or not in PATH"
    fi
    
    if ! command -v aws &> /dev/null; then
        error "AWS CLI is not installed or not in PATH"
    fi
    
    if ! kubectl get namespace "$NAMESPACE" &> /dev/null; then
        error "Namespace $NAMESPACE does not exist"
    fi
    
    log "Prerequisites check passed"
}

# Create backup directory
create_backup_dir() {
    log "Creating backup directory: $BACKUP_DIR"
    mkdir -p "$BACKUP_DIR"/{postgres,sonarqube,redis,configs}
}

# Backup PostgreSQL database
backup_postgres() {
    log "Starting PostgreSQL backup..."
    
    local pod_name=$(kubectl get pods -n "$NAMESPACE" -l app=postgres -o jsonpath='{.items[0].metadata.name}')
    
    if [[ -z "$pod_name" ]]; then
        error "PostgreSQL pod not found"
    fi
    
    log "Found PostgreSQL pod: $pod_name"
    
    # Create database dump
    kubectl exec -n "$NAMESPACE" "$pod_name" -- pg_dump -U sonarqube -d sonarqube --no-password > "$BACKUP_DIR/postgres/sonarqube_dump.sql"
    
    # Backup PostgreSQL configuration
    kubectl exec -n "$NAMESPACE" "$pod_name" -- cat /var/lib/postgresql/data/postgresql.conf > "$BACKUP_DIR/postgres/postgresql.conf" 2>/dev/null || true
    
    # Compress the backup
    gzip "$BACKUP_DIR/postgres/sonarqube_dump.sql"
    
    log "PostgreSQL backup completed"
}

# Backup SonarQube data
backup_sonarqube() {
    log "Starting SonarQube data backup..."
    
    local pod_name=$(kubectl get pods -n "$NAMESPACE" -l app=sonarqube -o jsonpath='{.items[0].metadata.name}')
    
    if [[ -z "$pod_name" ]]; then
        error "SonarQube pod not found"
    fi
    
    log "Found SonarQube pod: $pod_name"
    
    # Backup SonarQube data directory
    kubectl exec -n "$NAMESPACE" "$pod_name" -- tar czf - /opt/sonarqube/data > "$BACKUP_DIR/sonarqube/data.tar.gz"
    
    # Backup SonarQube extensions
    kubectl exec -n "$NAMESPACE" "$pod_name" -- tar czf - /opt/sonarqube/extensions > "$BACKUP_DIR/sonarqube/extensions.tar.gz"
    
    # Backup SonarQube logs (last 7 days)
    kubectl exec -n "$NAMESPACE" "$pod_name" -- find /opt/sonarqube/logs -name "*.log" -mtime -7 -exec tar czf - {} + > "$BACKUP_DIR/sonarqube/logs.tar.gz" 2>/dev/null || true
    
    log "SonarQube data backup completed"
}

# Backup Redis data
backup_redis() {
    log "Starting Redis backup..."
    
    local pod_name=$(kubectl get pods -n "$NAMESPACE" -l app=redis -o jsonpath='{.items[0].metadata.name}')
    
    if [[ -z "$pod_name" ]]; then
        error "Redis pod not found"
    fi
    
    log "Found Redis pod: $pod_name"
    
    # Create Redis backup
    kubectl exec -n "$NAMESPACE" "$pod_name" -- redis-cli --rdb /tmp/dump.rdb
    kubectl exec -n "$NAMESPACE" "$pod_name" -- cat /tmp/dump.rdb > "$BACKUP_DIR/redis/dump.rdb"
    
    # Backup Redis configuration
    kubectl exec -n "$NAMESPACE" "$pod_name" -- cat /usr/local/etc/redis/redis.conf > "$BACKUP_DIR/redis/redis.conf"
    
    # Compress the backup
    gzip "$BACKUP_DIR/redis/dump.rdb"
    
    log "Redis backup completed"
}

# Backup Kubernetes configurations
backup_configs() {
    log "Starting Kubernetes configurations backup..."
    
    # Backup all resources in the namespace
    kubectl get all,pvc,secrets,configmaps,ingress -n "$NAMESPACE" -o yaml > "$BACKUP_DIR/configs/resources.yaml"
    
    # Backup specific manifests
    if [[ -d "k8s" ]]; then
        cp -r k8s "$BACKUP_DIR/configs/"
    fi
    
    # Backup secrets (without sensitive data)
    kubectl get secrets -n "$NAMESPACE" -o yaml | sed 's/data:/data: # REDACTED/g' > "$BACKUP_DIR/configs/secrets_structure.yaml"
    
    log "Kubernetes configurations backup completed"
}

# Upload to S3
upload_to_s3() {
    log "Uploading backup to S3..."
    
    local backup_name=$(basename "$BACKUP_DIR")
    local archive_path="/tmp/${backup_name}.tar.gz"
    
    # Create compressed archive
    tar czf "$archive_path" -C "$(dirname "$BACKUP_DIR")" "$backup_name"
    
    # Upload to S3
    aws s3 cp "$archive_path" "s3://$S3_BUCKET/backups/"
    
    # Clean up local archive
    rm -f "$archive_path"
    
    log "Backup uploaded to S3: s3://$S3_BUCKET/backups/${backup_name}.tar.gz"
}

# Clean up old backups
cleanup_old_backups() {
    log "Cleaning up backups older than $RETENTION_DAYS days..."
    
    # Clean up local backups
    find "$(dirname "$BACKUP_DIR")" -type d -name "20*" -mtime +$RETENTION_DAYS -exec rm -rf {} + 2>/dev/null || true
    
    # Clean up S3 backups
    aws s3 ls "s3://$S3_BUCKET/backups/" | while read -r line; do
        backup_date=$(echo "$line" | awk '{print $1}')
        backup_file=$(echo "$line" | awk '{print $4}')
        
        if [[ -n "$backup_date" && -n "$backup_file" ]]; then
            backup_timestamp=$(date -d "$backup_date" +%s)
            cutoff_timestamp=$(date -d "$RETENTION_DAYS days ago" +%s)
            
            if [[ $backup_timestamp -lt $cutoff_timestamp ]]; then
                log "Deleting old backup: $backup_file"
                aws s3 rm "s3://$S3_BUCKET/backups/$backup_file"
            fi
        fi
    done
    
    log "Cleanup completed"
}

# Verify backup integrity
verify_backup() {
    log "Verifying backup integrity..."
    
    # Check if all expected files exist
    local expected_files=(
        "$BACKUP_DIR/postgres/sonarqube_dump.sql.gz"
        "$BACKUP_DIR/sonarqube/data.tar.gz"
        "$BACKUP_DIR/sonarqube/extensions.tar.gz"
        "$BACKUP_DIR/redis/dump.rdb.gz"
        "$BACKUP_DIR/configs/resources.yaml"
    )
    
    for file in "${expected_files[@]}"; do
        if [[ ! -f "$file" ]]; then
            error "Expected backup file not found: $file"
        fi
    done
    
    # Check file sizes (should not be empty)
    for file in "${expected_files[@]}"; do
        if [[ ! -s "$file" ]]; then
            warn "Backup file is empty: $file"
        fi
    done
    
    log "Backup integrity verification completed"
}

# Send notification
send_notification() {
    local status=$1
    local message=$2
    
    if [[ -n "${SLACK_WEBHOOK_URL:-}" ]]; then
        curl -X POST -H 'Content-type: application/json' \
            --data "{\"text\":\"Backup $status: $message\"}" \
            "$SLACK_WEBHOOK_URL" || true
    fi
    
    if [[ -n "${EMAIL_RECIPIENT:-}" ]]; then
        echo "$message" | mail -s "SonarQube MCP Backup $status" "$EMAIL_RECIPIENT" || true
    fi
}

# Main backup function
main() {
    log "Starting SonarQube MCP backup process..."
    
    trap 'error "Backup failed due to an error"' ERR
    
    check_prerequisites
    create_backup_dir
    
    backup_postgres
    backup_sonarqube
    backup_redis
    backup_configs
    
    verify_backup
    
    if [[ "${UPLOAD_TO_S3:-true}" == "true" ]]; then
        upload_to_s3
    fi
    
    if [[ "${CLEANUP_OLD_BACKUPS:-true}" == "true" ]]; then
        cleanup_old_backups
    fi
    
    log "Backup process completed successfully!"
    log "Backup location: $BACKUP_DIR"
    
    send_notification "SUCCESS" "Backup completed successfully at $(date)"
}

# Run main function
main "$@"