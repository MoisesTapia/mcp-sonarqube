#!/bin/bash

# SonarQube MCP Restore Script
# This script restores data from backups

set -euo pipefail

# Configuration
NAMESPACE="sonarqube-mcp"
BACKUP_PATH=""
S3_BUCKET="${S3_BACKUP_BUCKET:-sonarqube-mcp-backups}"

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
    echo "  -b, --backup-path PATH    Local backup directory path"
    echo "  -s, --s3-backup NAME      S3 backup name (without .tar.gz extension)"
    echo "  -l, --list-backups        List available S3 backups"
    echo "  -f, --force               Force restore without confirmation"
    echo "  -h, --help                Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 --backup-path /backups/20231022_143000"
    echo "  $0 --s3-backup 20231022_143000"
    echo "  $0 --list-backups"
    exit 1
}

# Parse command line arguments
parse_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            -b|--backup-path)
                BACKUP_PATH="$2"
                shift 2
                ;;
            -s|--s3-backup)
                S3_BACKUP_NAME="$2"
                shift 2
                ;;
            -l|--list-backups)
                list_s3_backups
                exit 0
                ;;
            -f|--force)
                FORCE_RESTORE=true
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

# List available S3 backups
list_s3_backups() {
    log "Available S3 backups:"
    aws s3 ls "s3://$S3_BUCKET/backups/" | grep "\.tar\.gz$" | awk '{print $4}' | sed 's/\.tar\.gz$//'
}

# Download backup from S3
download_from_s3() {
    local backup_name="$1"
    local temp_dir="/tmp/restore_$(date +%s)"
    
    log "Downloading backup from S3: $backup_name"
    
    mkdir -p "$temp_dir"
    aws s3 cp "s3://$S3_BUCKET/backups/${backup_name}.tar.gz" "$temp_dir/"
    
    # Extract the backup
    tar xzf "$temp_dir/${backup_name}.tar.gz" -C "$temp_dir"
    
    BACKUP_PATH="$temp_dir/$backup_name"
    log "Backup downloaded and extracted to: $BACKUP_PATH"
}

# Check prerequisites
check_prerequisites() {
    log "Checking prerequisites..."
    
    if ! command -v kubectl &> /dev/null; then
        error "kubectl is not installed or not in PATH"
    fi
    
    if [[ -n "${S3_BACKUP_NAME:-}" ]] && ! command -v aws &> /dev/null; then
        error "AWS CLI is not installed or not in PATH"
    fi
    
    if ! kubectl get namespace "$NAMESPACE" &> /dev/null; then
        error "Namespace $NAMESPACE does not exist"
    fi
    
    log "Prerequisites check passed"
}

# Validate backup directory
validate_backup() {
    log "Validating backup directory: $BACKUP_PATH"
    
    if [[ ! -d "$BACKUP_PATH" ]]; then
        error "Backup directory does not exist: $BACKUP_PATH"
    fi
    
    # Check for required backup files
    local required_files=(
        "$BACKUP_PATH/postgres/sonarqube_dump.sql.gz"
        "$BACKUP_PATH/sonarqube/data.tar.gz"
        "$BACKUP_PATH/sonarqube/extensions.tar.gz"
        "$BACKUP_PATH/redis/dump.rdb.gz"
        "$BACKUP_PATH/configs/resources.yaml"
    )
    
    for file in "${required_files[@]}"; do
        if [[ ! -f "$file" ]]; then
            error "Required backup file not found: $file"
        fi
    done
    
    log "Backup validation completed"
}

# Confirm restore operation
confirm_restore() {
    if [[ "${FORCE_RESTORE:-false}" == "true" ]]; then
        return 0
    fi
    
    warn "This operation will restore data from backup and may overwrite existing data."
    warn "Current data will be lost. Are you sure you want to continue?"
    
    read -p "Type 'yes' to confirm: " confirmation
    
    if [[ "$confirmation" != "yes" ]]; then
        log "Restore operation cancelled"
        exit 0
    fi
}

# Scale down deployments
scale_down_deployments() {
    log "Scaling down deployments..."
    
    kubectl scale deployment mcp-server --replicas=0 -n "$NAMESPACE" || true
    kubectl scale deployment streamlit-app --replicas=0 -n "$NAMESPACE" || true
    kubectl scale deployment sonarqube --replicas=0 -n "$NAMESPACE" || true
    
    # Wait for pods to terminate
    kubectl wait --for=delete pod -l app=mcp-server -n "$NAMESPACE" --timeout=300s || true
    kubectl wait --for=delete pod -l app=streamlit-app -n "$NAMESPACE" --timeout=300s || true
    kubectl wait --for=delete pod -l app=sonarqube -n "$NAMESPACE" --timeout=300s || true
    
    log "Deployments scaled down"
}

# Scale up deployments
scale_up_deployments() {
    log "Scaling up deployments..."
    
    kubectl scale deployment postgres --replicas=1 -n "$NAMESPACE"
    kubectl scale deployment redis --replicas=1 -n "$NAMESPACE"
    
    # Wait for database services to be ready
    kubectl wait --for=condition=ready pod -l app=postgres -n "$NAMESPACE" --timeout=300s
    kubectl wait --for=condition=ready pod -l app=redis -n "$NAMESPACE" --timeout=300s
    
    kubectl scale deployment sonarqube --replicas=1 -n "$NAMESPACE"
    kubectl wait --for=condition=ready pod -l app=sonarqube -n "$NAMESPACE" --timeout=600s
    
    kubectl scale deployment mcp-server --replicas=3 -n "$NAMESPACE"
    kubectl scale deployment streamlit-app --replicas=2 -n "$NAMESPACE"
    
    kubectl wait --for=condition=ready pod -l app=mcp-server -n "$NAMESPACE" --timeout=300s
    kubectl wait --for=condition=ready pod -l app=streamlit-app -n "$NAMESPACE" --timeout=300s
    
    log "Deployments scaled up"
}

# Restore PostgreSQL database
restore_postgres() {
    log "Restoring PostgreSQL database..."
    
    local pod_name=$(kubectl get pods -n "$NAMESPACE" -l app=postgres -o jsonpath='{.items[0].metadata.name}')
    
    if [[ -z "$pod_name" ]]; then
        error "PostgreSQL pod not found"
    fi
    
    # Drop and recreate database
    kubectl exec -n "$NAMESPACE" "$pod_name" -- psql -U sonarqube -d postgres -c "DROP DATABASE IF EXISTS sonarqube;"
    kubectl exec -n "$NAMESPACE" "$pod_name" -- psql -U sonarqube -d postgres -c "CREATE DATABASE sonarqube;"
    
    # Restore database dump
    gunzip -c "$BACKUP_PATH/postgres/sonarqube_dump.sql.gz" | kubectl exec -i -n "$NAMESPACE" "$pod_name" -- psql -U sonarqube -d sonarqube
    
    log "PostgreSQL database restored"
}

# Restore SonarQube data
restore_sonarqube() {
    log "Restoring SonarQube data..."
    
    local pod_name=$(kubectl get pods -n "$NAMESPACE" -l app=sonarqube -o jsonpath='{.items[0].metadata.name}')
    
    if [[ -z "$pod_name" ]]; then
        error "SonarQube pod not found"
    fi
    
    # Clear existing data
    kubectl exec -n "$NAMESPACE" "$pod_name" -- rm -rf /opt/sonarqube/data/* || true
    kubectl exec -n "$NAMESPACE" "$pod_name" -- rm -rf /opt/sonarqube/extensions/* || true
    
    # Restore data directory
    kubectl exec -i -n "$NAMESPACE" "$pod_name" -- tar xzf - -C / < "$BACKUP_PATH/sonarqube/data.tar.gz"
    
    # Restore extensions
    kubectl exec -i -n "$NAMESPACE" "$pod_name" -- tar xzf - -C / < "$BACKUP_PATH/sonarqube/extensions.tar.gz"
    
    # Fix permissions
    kubectl exec -n "$NAMESPACE" "$pod_name" -- chown -R sonarqube:sonarqube /opt/sonarqube/data /opt/sonarqube/extensions
    
    log "SonarQube data restored"
}

# Restore Redis data
restore_redis() {
    log "Restoring Redis data..."
    
    local pod_name=$(kubectl get pods -n "$NAMESPACE" -l app=redis -o jsonpath='{.items[0].metadata.name}')
    
    if [[ -z "$pod_name" ]]; then
        error "Redis pod not found"
    fi
    
    # Stop Redis temporarily
    kubectl exec -n "$NAMESPACE" "$pod_name" -- redis-cli SHUTDOWN NOSAVE || true
    
    # Restore Redis dump
    gunzip -c "$BACKUP_PATH/redis/dump.rdb.gz" | kubectl exec -i -n "$NAMESPACE" "$pod_name" -- tee /data/dump.rdb > /dev/null
    
    # Restart Redis
    kubectl delete pod "$pod_name" -n "$NAMESPACE"
    kubectl wait --for=condition=ready pod -l app=redis -n "$NAMESPACE" --timeout=300s
    
    log "Redis data restored"
}

# Verify restore
verify_restore() {
    log "Verifying restore..."
    
    # Check if all services are running
    kubectl get pods -n "$NAMESPACE"
    
    # Check service health
    local mcp_pod=$(kubectl get pods -n "$NAMESPACE" -l app=mcp-server -o jsonpath='{.items[0].metadata.name}')
    local streamlit_pod=$(kubectl get pods -n "$NAMESPACE" -l app=streamlit-app -o jsonpath='{.items[0].metadata.name}')
    
    if [[ -n "$mcp_pod" ]]; then
        kubectl exec -n "$NAMESPACE" "$mcp_pod" -- curl -f http://localhost:8000/health || warn "MCP server health check failed"
    fi
    
    if [[ -n "$streamlit_pod" ]]; then
        kubectl exec -n "$NAMESPACE" "$streamlit_pod" -- curl -f http://localhost:8501/_stcore/health || warn "Streamlit app health check failed"
    fi
    
    log "Restore verification completed"
}

# Send notification
send_notification() {
    local status=$1
    local message=$2
    
    if [[ -n "${SLACK_WEBHOOK_URL:-}" ]]; then
        curl -X POST -H 'Content-type: application/json' \
            --data "{\"text\":\"Restore $status: $message\"}" \
            "$SLACK_WEBHOOK_URL" || true
    fi
    
    if [[ -n "${EMAIL_RECIPIENT:-}" ]]; then
        echo "$message" | mail -s "SonarQube MCP Restore $status" "$EMAIL_RECIPIENT" || true
    fi
}

# Main restore function
main() {
    log "Starting SonarQube MCP restore process..."
    
    trap 'error "Restore failed due to an error"' ERR
    
    parse_args "$@"
    
    if [[ -z "$BACKUP_PATH" && -z "${S3_BACKUP_NAME:-}" ]]; then
        error "Either --backup-path or --s3-backup must be specified"
    fi
    
    check_prerequisites
    
    if [[ -n "${S3_BACKUP_NAME:-}" ]]; then
        download_from_s3 "$S3_BACKUP_NAME"
    fi
    
    validate_backup
    confirm_restore
    
    scale_down_deployments
    
    restore_postgres
    restore_redis
    restore_sonarqube
    
    scale_up_deployments
    verify_restore
    
    log "Restore process completed successfully!"
    
    send_notification "SUCCESS" "Restore completed successfully at $(date)"
}

# Run main function
main "$@"