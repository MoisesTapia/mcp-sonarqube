#!/bin/bash
# Configuration validation script for SonarQube MCP

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
ENV_FILE="${1:-.env}"
VALIDATION_ERRORS=0
VALIDATION_WARNINGS=0

# Logging functions
log() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1" >&2
    ((VALIDATION_ERRORS++))
}

warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
    ((VALIDATION_WARNINGS++))
}

success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

# Check if environment file exists
check_env_file() {
    log "Checking environment file: $ENV_FILE"
    
    if [ ! -f "$ENV_FILE" ]; then
        error "Environment file '$ENV_FILE' not found"
        
        if [ -f ".env.example" ]; then
            log "Creating $ENV_FILE from .env.example"
            cp .env.example "$ENV_FILE"
            warning "Please edit $ENV_FILE with your configuration"
        else
            error ".env.example not found. Cannot create default configuration"
            exit 1
        fi
    fi
    
    success "Environment file found"
}

# Load environment variables
load_env_vars() {
    log "Loading environment variables from $ENV_FILE"
    
    # Source the environment file
    set -a  # automatically export all variables
    source "$ENV_FILE" 2>/dev/null || {
        error "Failed to load environment file"
        exit 1
    }
    set +a
    
    success "Environment variables loaded"
}

# Validate required variables
validate_required_vars() {
    log "Validating required environment variables"
    
    # Define required variables for different environments
    local required_vars=(
        "SONARQUBE_URL"
        "SONARQUBE_TOKEN"
        "POSTGRES_PASSWORD"
        "REDIS_PASSWORD"
        "SECRET_KEY"
    )
    
    # Additional production requirements
    if [[ "$ENV_FILE" == *"prod"* ]]; then
        required_vars+=(
            "GRAFANA_USER"
            "GRAFANA_PASSWORD"
            "JWT_SECRET"
            "BACKUP_ENCRYPTION_KEY"
        )
    fi
    
    local missing_vars=()
    
    for var in "${required_vars[@]}"; do
        if [ -z "${!var}" ] || [ "${!var}" = "your_token_here" ] || [ "${!var}" = "change_me" ]; then
            missing_vars+=("$var")
        fi
    done
    
    if [ ${#missing_vars[@]} -gt 0 ]; then
        error "Missing or invalid required environment variables:"
        for var in "${missing_vars[@]}"; do
            error "  - $var"
        done
    else
        success "All required variables are set"
    fi
}

# Validate SonarQube configuration
validate_sonarqube_config() {
    log "Validating SonarQube configuration"
    
    # Check URL format
    if [[ ! "$SONARQUBE_URL" =~ ^https?:// ]]; then
        error "SONARQUBE_URL must start with http:// or https://"
    fi
    
    # Check token format (SonarQube tokens are typically 40 characters)
    if [ ${#SONARQUBE_TOKEN} -lt 20 ]; then
        warning "SONARQUBE_TOKEN seems too short (expected at least 20 characters)"
    fi
    
    # Test SonarQube connectivity (if not using Docker internal URLs)
    if [[ ! "$SONARQUBE_URL" =~ sonarqube: ]]; then
        log "Testing SonarQube connectivity..."
        if command -v curl > /dev/null 2>&1; then
            if curl -s -f "$SONARQUBE_URL/api/system/status" > /dev/null; then
                success "SonarQube server is reachable"
            else
                warning "Cannot reach SonarQube server (this is normal if using Docker internal URLs)"
            fi
        fi
    fi
}

# Validate database configuration
validate_database_config() {
    log "Validating database configuration"
    
    # Check password strength
    if [ ${#POSTGRES_PASSWORD} -lt 8 ]; then
        warning "POSTGRES_PASSWORD should be at least 8 characters long"
    fi
    
    # Check for common weak passwords
    local weak_passwords=("password" "123456" "admin" "postgres" "dev_password")
    for weak_pass in "${weak_passwords[@]}"; do
        if [ "$POSTGRES_PASSWORD" = "$weak_pass" ]; then
            if [[ "$ENV_FILE" == *"prod"* ]]; then
                error "Using weak password '$weak_pass' in production environment"
            else
                warning "Using weak password '$weak_pass' (acceptable for development)"
            fi
            break
        fi
    done
    
    success "Database configuration validated"
}

# Validate Redis configuration
validate_redis_config() {
    log "Validating Redis configuration"
    
    # Check password strength
    if [ ${#REDIS_PASSWORD} -lt 8 ]; then
        warning "REDIS_PASSWORD should be at least 8 characters long"
    fi
    
    # Validate Redis URL format
    if [[ -n "$REDIS_URL" && ! "$REDIS_URL" =~ ^redis:// ]]; then
        error "REDIS_URL must start with redis://"
    fi
    
    success "Redis configuration validated"
}

# Validate security configuration
validate_security_config() {
    log "Validating security configuration"
    
    # Check secret key strength
    if [ ${#SECRET_KEY} -lt 32 ]; then
        error "SECRET_KEY must be at least 32 characters long"
    fi
    
    # Production-specific security checks
    if [[ "$ENV_FILE" == *"prod"* ]]; then
        if [ "$HTTPS_ONLY" != "true" ]; then
            error "HTTPS_ONLY must be true in production"
        fi
        
        if [ "$SECURE_COOKIES" != "true" ]; then
            error "SECURE_COOKIES must be true in production"
        fi
        
        if [ "$DEBUG" = "true" ]; then
            error "DEBUG must be false in production"
        fi
        
        if [ "$DEVELOPMENT_MODE" = "true" ]; then
            error "DEVELOPMENT_MODE must be false in production"
        fi
    fi
    
    success "Security configuration validated"
}

# Validate resource limits
validate_resource_limits() {
    log "Validating resource limits"
    
    # Check memory limits format
    local memory_vars=(
        "POSTGRES_MEMORY_LIMIT"
        "REDIS_MEMORY_LIMIT"
        "SONARQUBE_MEMORY_LIMIT"
        "MCP_SERVER_MEMORY_LIMIT"
        "STREAMLIT_MEMORY_LIMIT"
    )
    
    for var in "${memory_vars[@]}"; do
        if [ -n "${!var}" ]; then
            if [[ ! "${!var}" =~ ^[0-9]+[kmgKMG]?$ ]]; then
                warning "$var format should be like '512m' or '2g'"
            fi
        fi
    done
    
    success "Resource limits validated"
}

# Validate monitoring configuration
validate_monitoring_config() {
    log "Validating monitoring configuration"
    
    # Check Grafana credentials
    if [ -n "$GRAFANA_USER" ] && [ -n "$GRAFANA_PASSWORD" ]; then
        if [ "$GRAFANA_PASSWORD" = "admin" ] && [[ "$ENV_FILE" == *"prod"* ]]; then
            error "Change default Grafana password in production"
        fi
    fi
    
    # Check alert configuration
    if [ "$ALERTMANAGER_ENABLED" = "true" ]; then
        if [ -z "$ALERT_EMAIL_TO" ]; then
            warning "ALERT_EMAIL_TO should be set when alerting is enabled"
        fi
    fi
    
    success "Monitoring configuration validated"
}

# Validate backup configuration
validate_backup_config() {
    log "Validating backup configuration"
    
    if [ "$BACKUP_ENABLED" = "true" ]; then
        if [ -z "$BACKUP_SCHEDULE" ]; then
            warning "BACKUP_SCHEDULE should be set when backup is enabled"
        fi
        
        if [ "$BACKUP_S3_ENABLED" = "true" ]; then
            local s3_vars=("BACKUP_S3_BUCKET" "BACKUP_S3_REGION" "BACKUP_S3_ACCESS_KEY" "BACKUP_S3_SECRET_KEY")
            for var in "${s3_vars[@]}"; do
                if [ -z "${!var}" ]; then
                    error "$var is required when S3 backup is enabled"
                fi
            done
        fi
    fi
    
    success "Backup configuration validated"
}

# Generate configuration report
generate_report() {
    local report_file="config-validation-report-$(date +%Y%m%d_%H%M%S).txt"
    
    {
        echo "SonarQube MCP Configuration Validation Report"
        echo "Generated: $(date)"
        echo "Environment File: $ENV_FILE"
        echo "=============================================="
        echo
        
        echo "Validation Summary:"
        echo "- Errors: $VALIDATION_ERRORS"
        echo "- Warnings: $VALIDATION_WARNINGS"
        echo
        
        if [ $VALIDATION_ERRORS -eq 0 ] && [ $VALIDATION_WARNINGS -eq 0 ]; then
            echo "✅ Configuration is valid and ready for deployment"
        elif [ $VALIDATION_ERRORS -eq 0 ]; then
            echo "⚠️  Configuration is valid but has warnings"
        else
            echo "❌ Configuration has errors that must be fixed"
        fi
        
        echo
        echo "Environment Variables (sensitive values masked):"
        env | grep -E "^(SONARQUBE|POSTGRES|REDIS|MCP|STREAMLIT|GRAFANA|PROMETHEUS)" | \
        sed 's/\(PASSWORD\|TOKEN\|SECRET\|KEY\)=.*/\1=***MASKED***/' | sort
        
    } > "$report_file"
    
    log "Configuration report generated: $report_file"
}

# Main validation function
main() {
    log "Starting configuration validation for: $ENV_FILE"
    
    check_env_file
    load_env_vars
    validate_required_vars
    validate_sonarqube_config
    validate_database_config
    validate_redis_config
    validate_security_config
    validate_resource_limits
    validate_monitoring_config
    validate_backup_config
    
    echo
    echo "=================================="
    echo "Validation Summary:"
    echo "- Errors: $VALIDATION_ERRORS"
    echo "- Warnings: $VALIDATION_WARNINGS"
    echo "=================================="
    
    if [ $VALIDATION_ERRORS -eq 0 ] && [ $VALIDATION_WARNINGS -eq 0 ]; then
        success "✅ Configuration is valid and ready for deployment!"
        generate_report
        exit 0
    elif [ $VALIDATION_ERRORS -eq 0 ]; then
        warning "⚠️  Configuration is valid but has warnings"
        generate_report
        exit 0
    else
        error "❌ Configuration has $VALIDATION_ERRORS error(s) that must be fixed"
        generate_report
        exit 1
    fi
}

# Usage information
usage() {
    echo "Usage: $0 [ENV_FILE]"
    echo
    echo "Validate SonarQube MCP configuration file"
    echo
    echo "Arguments:"
    echo "  ENV_FILE    Path to environment file (default: .env)"
    echo
    echo "Examples:"
    echo "  $0                  # Validate .env"
    echo "  $0 .env.prod        # Validate production config"
    echo "  $0 .env.dev         # Validate development config"
}

# Check for help flag
if [ "$1" = "-h" ] || [ "$1" = "--help" ]; then
    usage
    exit 0
fi

# Run main function
main "$@"