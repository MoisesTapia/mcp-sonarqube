#!/bin/bash

# SonarQube MCP Deployment Script
# This script handles deployment to different environments

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
ENVIRONMENT="${ENVIRONMENT:-staging}"
NAMESPACE="sonarqube-mcp"
REGISTRY="${REGISTRY:-ghcr.io}"
IMAGE_TAG="${IMAGE_TAG:-latest}"

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
    echo "  -e, --environment ENV     Target environment (staging|production) [default: staging]"
    echo "  -t, --tag TAG            Docker image tag [default: latest]"
    echo "  -r, --registry REGISTRY  Container registry [default: ghcr.io]"
    echo "  -n, --namespace NS       Kubernetes namespace [default: sonarqube-mcp]"
    echo "  -f, --force              Force deployment without confirmation"
    echo "  -d, --dry-run            Show what would be deployed without applying"
    echo "  -h, --help               Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 --environment production --tag v1.0.0"
    echo "  $0 --dry-run --environment staging"
    exit 1
}

# Parse command line arguments
parse_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            -e|--environment)
                ENVIRONMENT="$2"
                shift 2
                ;;
            -t|--tag)
                IMAGE_TAG="$2"
                shift 2
                ;;
            -r|--registry)
                REGISTRY="$2"
                shift 2
                ;;
            -n|--namespace)
                NAMESPACE="$2"
                shift 2
                ;;
            -f|--force)
                FORCE_DEPLOY=true
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
        staging|production)
            log "Deploying to $ENVIRONMENT environment"
            ;;
        *)
            error "Invalid environment: $ENVIRONMENT. Must be 'staging' or 'production'"
            ;;
    esac
}

# Check prerequisites
check_prerequisites() {
    log "Checking prerequisites..."
    
    if ! command -v kubectl &> /dev/null; then
        error "kubectl is not installed or not in PATH"
    fi
    
    if ! command -v helm &> /dev/null; then
        warn "helm is not installed. Some features may not be available"
    fi
    
    # Check kubectl context
    local current_context=$(kubectl config current-context)
    info "Current kubectl context: $current_context"
    
    if [[ "$ENVIRONMENT" == "production" ]] && [[ "$current_context" != *"prod"* ]]; then
        warn "Current context doesn't appear to be production. Please verify."
    fi
    
    # Check cluster connectivity
    if ! kubectl cluster-info &> /dev/null; then
        error "Cannot connect to Kubernetes cluster"
    fi
    
    log "Prerequisites check passed"
}

# Confirm deployment
confirm_deployment() {
    if [[ "${FORCE_DEPLOY:-false}" == "true" ]] || [[ "${DRY_RUN:-false}" == "true" ]]; then
        return 0
    fi
    
    info "Deployment Summary:"
    echo "  Environment: $ENVIRONMENT"
    echo "  Namespace: $NAMESPACE"
    echo "  Registry: $REGISTRY"
    echo "  Image Tag: $IMAGE_TAG"
    echo "  Kubectl Context: $(kubectl config current-context)"
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

# Create namespace if it doesn't exist
create_namespace() {
    log "Ensuring namespace exists: $NAMESPACE"
    
    if [[ "${DRY_RUN:-false}" == "true" ]]; then
        info "[DRY RUN] Would create namespace: $NAMESPACE"
        return 0
    fi
    
    kubectl create namespace "$NAMESPACE" --dry-run=client -o yaml | kubectl apply -f -
}

# Update image tags in manifests
update_image_tags() {
    log "Updating image tags in manifests..."
    
    local temp_dir="/tmp/sonarqube-mcp-deploy-$$"
    mkdir -p "$temp_dir"
    
    # Copy manifests to temp directory
    cp -r "$PROJECT_ROOT/k8s" "$temp_dir/"
    
    # Update image tags
    find "$temp_dir/k8s" -name "*.yaml" -type f -exec sed -i \
        "s|sonarqube-mcp/mcp-server:latest|$REGISTRY/sonarqube-mcp/mcp-server:$IMAGE_TAG|g" {} \;
    
    find "$temp_dir/k8s" -name "*.yaml" -type f -exec sed -i \
        "s|sonarqube-mcp/streamlit-app:latest|$REGISTRY/sonarqube-mcp/streamlit-app:$IMAGE_TAG|g" {} \;
    
    # Update namespace if different from default
    if [[ "$NAMESPACE" != "sonarqube-mcp" ]]; then
        find "$temp_dir/k8s" -name "*.yaml" -type f -exec sed -i \
            "s|namespace: sonarqube-mcp|namespace: $NAMESPACE|g" {} \;
    fi
    
    # Environment-specific configurations
    if [[ "$ENVIRONMENT" == "production" ]]; then
        # Update resource limits for production
        find "$temp_dir/k8s" -name "*.yaml" -type f -exec sed -i \
            's|replicas: 2|replicas: 3|g' {} \;
        find "$temp_dir/k8s" -name "*.yaml" -type f -exec sed -i \
            's|replicas: 3|replicas: 5|g' {} \;
    fi
    
    MANIFEST_DIR="$temp_dir/k8s"
    log "Manifests updated in: $MANIFEST_DIR"
}

# Deploy infrastructure components
deploy_infrastructure() {
    log "Deploying infrastructure components..."
    
    local manifests=(
        "$MANIFEST_DIR/namespace.yaml"
        "$MANIFEST_DIR/secrets.yaml"
        "$MANIFEST_DIR/postgres.yaml"
        "$MANIFEST_DIR/redis.yaml"
    )
    
    for manifest in "${manifests[@]}"; do
        if [[ -f "$manifest" ]]; then
            info "Applying: $(basename "$manifest")"
            if [[ "${DRY_RUN:-false}" == "true" ]]; then
                kubectl apply -f "$manifest" --dry-run=client
            else
                kubectl apply -f "$manifest"
            fi
        fi
    done
    
    if [[ "${DRY_RUN:-false}" != "true" ]]; then
        # Wait for infrastructure to be ready
        log "Waiting for infrastructure to be ready..."
        kubectl wait --for=condition=ready pod -l app=postgres -n "$NAMESPACE" --timeout=300s || true
        kubectl wait --for=condition=ready pod -l app=redis -n "$NAMESPACE" --timeout=300s || true
    fi
}

# Deploy SonarQube
deploy_sonarqube() {
    log "Deploying SonarQube..."
    
    if [[ "${DRY_RUN:-false}" == "true" ]]; then
        kubectl apply -f "$MANIFEST_DIR/sonarqube.yaml" --dry-run=client
    else
        kubectl apply -f "$MANIFEST_DIR/sonarqube.yaml"
        
        # Wait for SonarQube to be ready
        log "Waiting for SonarQube to be ready..."
        kubectl wait --for=condition=ready pod -l app=sonarqube -n "$NAMESPACE" --timeout=600s || true
    fi
}

# Deploy application components
deploy_applications() {
    log "Deploying application components..."
    
    local manifests=(
        "$MANIFEST_DIR/mcp-server.yaml"
        "$MANIFEST_DIR/streamlit-app.yaml"
    )
    
    for manifest in "${manifests[@]}"; do
        if [[ -f "$manifest" ]]; then
            info "Applying: $(basename "$manifest")"
            if [[ "${DRY_RUN:-false}" == "true" ]]; then
                kubectl apply -f "$manifest" --dry-run=client
            else
                kubectl apply -f "$manifest"
            fi
        fi
    done
    
    if [[ "${DRY_RUN:-false}" != "true" ]]; then
        # Wait for applications to be ready
        log "Waiting for applications to be ready..."
        kubectl wait --for=condition=ready pod -l app=mcp-server -n "$NAMESPACE" --timeout=300s || true
        kubectl wait --for=condition=ready pod -l app=streamlit-app -n "$NAMESPACE" --timeout=300s || true
    fi
}

# Deploy networking and ingress
deploy_networking() {
    log "Deploying networking and ingress..."
    
    if [[ -f "$MANIFEST_DIR/ingress.yaml" ]]; then
        if [[ "${DRY_RUN:-false}" == "true" ]]; then
            kubectl apply -f "$MANIFEST_DIR/ingress.yaml" --dry-run=client
        else
            kubectl apply -f "$MANIFEST_DIR/ingress.yaml"
        fi
    fi
}

# Deploy monitoring
deploy_monitoring() {
    log "Deploying monitoring stack..."
    
    if [[ -d "$MANIFEST_DIR/monitoring" ]]; then
        if [[ "${DRY_RUN:-false}" == "true" ]]; then
            kubectl apply -f "$MANIFEST_DIR/monitoring/" --dry-run=client
        else
            kubectl apply -f "$MANIFEST_DIR/monitoring/"
            
            # Wait for monitoring to be ready
            log "Waiting for monitoring to be ready..."
            kubectl wait --for=condition=ready pod -l app=prometheus -n "$NAMESPACE" --timeout=300s || true
            kubectl wait --for=condition=ready pod -l app=grafana -n "$NAMESPACE" --timeout=300s || true
        fi
    fi
}

# Run health checks
run_health_checks() {
    if [[ "${DRY_RUN:-false}" == "true" ]]; then
        info "[DRY RUN] Would run health checks"
        return 0
    fi
    
    log "Running health checks..."
    
    # Check pod status
    kubectl get pods -n "$NAMESPACE"
    
    # Check service endpoints
    local services=("mcp-server-service" "streamlit-app-service" "sonarqube-service")
    
    for service in "${services[@]}"; do
        if kubectl get service "$service" -n "$NAMESPACE" &> /dev/null; then
            info "Service $service is available"
        else
            warn "Service $service is not available"
        fi
    done
    
    # Run application health checks
    local mcp_pod=$(kubectl get pods -n "$NAMESPACE" -l app=mcp-server -o jsonpath='{.items[0].metadata.name}' 2>/dev/null || echo "")
    local streamlit_pod=$(kubectl get pods -n "$NAMESPACE" -l app=streamlit-app -o jsonpath='{.items[0].metadata.name}' 2>/dev/null || echo "")
    
    if [[ -n "$mcp_pod" ]]; then
        if kubectl exec -n "$NAMESPACE" "$mcp_pod" -- curl -f http://localhost:8000/health &> /dev/null; then
            log "MCP server health check passed"
        else
            warn "MCP server health check failed"
        fi
    fi
    
    if [[ -n "$streamlit_pod" ]]; then
        if kubectl exec -n "$NAMESPACE" "$streamlit_pod" -- curl -f http://localhost:8501/_stcore/health &> /dev/null; then
            log "Streamlit app health check passed"
        else
            warn "Streamlit app health check failed"
        fi
    fi
}

# Send deployment notification
send_notification() {
    local status=$1
    local message="Deployment to $ENVIRONMENT $status at $(date)"
    
    if [[ -n "${SLACK_WEBHOOK_URL:-}" ]]; then
        curl -X POST -H 'Content-type: application/json' \
            --data "{\"text\":\"$message\"}" \
            "$SLACK_WEBHOOK_URL" || true
    fi
    
    if [[ -n "${EMAIL_RECIPIENT:-}" ]]; then
        echo "$message" | mail -s "SonarQube MCP Deployment $status" "$EMAIL_RECIPIENT" || true
    fi
}

# Cleanup function
cleanup() {
    if [[ -n "${MANIFEST_DIR:-}" ]] && [[ "$MANIFEST_DIR" == "/tmp/"* ]]; then
        rm -rf "$(dirname "$MANIFEST_DIR")"
    fi
}

# Main deployment function
main() {
    log "Starting SonarQube MCP deployment..."
    
    trap cleanup EXIT
    trap 'error "Deployment failed due to an error"' ERR
    
    parse_args "$@"
    validate_environment
    check_prerequisites
    confirm_deployment
    
    create_namespace
    update_image_tags
    
    deploy_infrastructure
    deploy_sonarqube
    deploy_applications
    deploy_networking
    
    if [[ "$ENVIRONMENT" == "production" ]]; then
        deploy_monitoring
    fi
    
    run_health_checks
    
    if [[ "${DRY_RUN:-false}" == "true" ]]; then
        log "Dry run completed successfully!"
    else
        log "Deployment completed successfully!"
        send_notification "SUCCESS"
    fi
    
    info "Deployment summary:"
    echo "  Environment: $ENVIRONMENT"
    echo "  Namespace: $NAMESPACE"
    echo "  Image Tag: $IMAGE_TAG"
    
    if [[ "${DRY_RUN:-false}" != "true" ]]; then
        echo ""
        echo "Access URLs:"
        if [[ "$ENVIRONMENT" == "production" ]]; then
            echo "  Streamlit UI: https://sonarqube-mcp.yourdomain.com"
            echo "  MCP API: https://api.sonarqube-mcp.yourdomain.com"
            echo "  SonarQube: https://sonarqube-mcp.yourdomain.com/sonarqube"
        else
            echo "  Use kubectl port-forward to access services locally"
        fi
    fi
}

# Run main function
main "$@"