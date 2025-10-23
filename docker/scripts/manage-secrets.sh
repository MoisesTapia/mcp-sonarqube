#!/bin/bash
# Docker secrets management script for SonarQube MCP

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
SECRETS_DIR="docker/secrets"
SECRETS_FILE="$SECRETS_DIR/secrets.env"

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

# Generate secure random string
generate_secret() {
    local length=${1:-32}
    openssl rand -base64 $length | tr -d "=+/" | cut -c1-$length
}

# Create secrets directory
setup_secrets_directory() {
    log "Setting up secrets directory"
    
    if [ ! -d "$SECRETS_DIR" ]; then
        mkdir -p "$SECRETS_DIR"
        chmod 700 "$SECRETS_DIR"
        log "Created secrets directory: $SECRETS_DIR"
    fi
    
    # Create .gitignore to prevent secrets from being committed
    if [ ! -f "$SECRETS_DIR/.gitignore" ]; then
        cat > "$SECRETS_DIR/.gitignore" << EOF
# Ignore all secrets
*
!.gitignore
!README.md
EOF
        log "Created .gitignore for secrets directory"
    fi
    
    success "Secrets directory setup complete"
}

# Generate all required secrets
generate_secrets() {
    log "Generating secrets for SonarQube MCP"
    
    setup_secrets_directory
    
    # Create secrets file
    cat > "$SECRETS_FILE" << EOF
# Generated secrets for SonarQube MCP
# Generated on: $(date)
# WARNING: Keep this file secure and never commit to version control

# Database secrets
POSTGRES_PASSWORD=$(generate_secret 24)
POSTGRES_ADMIN_PASSWORD=$(generate_secret 24)

# Redis secrets
REDIS_PASSWORD=$(generate_secret 24)

# Application secrets
SECRET_KEY=$(generate_secret 64)
JWT_SECRET=$(generate_secret 48)

# Monitoring secrets
GRAFANA_USER=admin
GRAFANA_PASSWORD=$(generate_secret 16)

# Backup secrets
BACKUP_ENCRYPTION_KEY=$(generate_secret 32)

# Webhook secrets
WEBHOOK_SECRET=$(generate_secret 32)

# SMTP secrets (set these manually)
SMTP_USER=your_smtp_user
SMTP_PASSWORD=your_smtp_password

# S3 backup secrets (set these manually)
BACKUP_S3_ACCESS_KEY=your_s3_access_key
BACKUP_S3_SECRET_KEY=your_s3_secret_key

# SonarQube token (set this manually)
SONARQUBE_TOKEN=your_sonarqube_token_here
EOF
    
    chmod 600 "$SECRETS_FILE"
    success "Secrets generated and saved to: $SECRETS_FILE"
    
    warning "Please update the following secrets manually:"
    warning "  - SONARQUBE_TOKEN"
    warning "  - SMTP_USER and SMTP_PASSWORD (if using email alerts)"
    warning "  - BACKUP_S3_ACCESS_KEY and BACKUP_S3_SECRET_KEY (if using S3 backup)"
}

# Create individual secret files for Docker Swarm
create_docker_secrets() {
    log "Creating individual secret files for Docker Swarm"
    
    if [ ! -f "$SECRETS_FILE" ]; then
        error "Secrets file not found. Run 'generate' command first."
        exit 1
    fi
    
    # Source the secrets file
    source "$SECRETS_FILE"
    
    # Create individual secret files
    local secrets=(
        "POSTGRES_PASSWORD"
        "REDIS_PASSWORD"
        "SECRET_KEY"
        "JWT_SECRET"
        "GRAFANA_PASSWORD"
        "BACKUP_ENCRYPTION_KEY"
        "WEBHOOK_SECRET"
        "SONARQUBE_TOKEN"
    )
    
    for secret in "${secrets[@]}"; do
        local secret_file="$SECRETS_DIR/${secret,,}.txt"  # Convert to lowercase
        echo "${!secret}" > "$secret_file"
        chmod 600 "$secret_file"
        log "Created secret file: $secret_file"
    done
    
    success "Docker secret files created"
}

# Validate secrets
validate_secrets() {
    log "Validating secrets"
    
    if [ ! -f "$SECRETS_FILE" ]; then
        error "Secrets file not found: $SECRETS_FILE"
        exit 1
    fi
    
    # Source the secrets file
    source "$SECRETS_FILE"
    
    local validation_errors=0
    
    # Check required secrets
    local required_secrets=(
        "POSTGRES_PASSWORD"
        "REDIS_PASSWORD"
        "SECRET_KEY"
        "JWT_SECRET"
        "GRAFANA_PASSWORD"
    )
    
    for secret in "${required_secrets[@]}"; do
        if [ -z "${!secret}" ] || [ "${!secret}" = "your_token_here" ]; then
            error "Secret $secret is not set or has default value"
            ((validation_errors++))
        elif [ ${#!secret} -lt 8 ]; then
            warning "Secret $secret is shorter than 8 characters"
        fi
    done
    
    # Check SonarQube token
    if [ "$SONARQUBE_TOKEN" = "your_sonarqube_token_here" ]; then
        error "SONARQUBE_TOKEN must be set to a valid SonarQube token"
        ((validation_errors++))
    fi
    
    if [ $validation_errors -eq 0 ]; then
        success "All secrets are valid"
    else
        error "$validation_errors validation error(s) found"
        exit 1
    fi
}

# Rotate secrets
rotate_secrets() {
    log "Rotating secrets"
    
    if [ ! -f "$SECRETS_FILE" ]; then
        error "Secrets file not found. Run 'generate' command first."
        exit 1
    fi
    
    # Backup current secrets
    local backup_file="$SECRETS_DIR/secrets.env.backup.$(date +%Y%m%d_%H%M%S)"
    cp "$SECRETS_FILE" "$backup_file"
    log "Backed up current secrets to: $backup_file"
    
    # Source current secrets
    source "$SECRETS_FILE"
    
    # Generate new secrets (keeping manual ones)
    cat > "$SECRETS_FILE" << EOF
# Rotated secrets for SonarQube MCP
# Generated on: $(date)
# WARNING: Keep this file secure and never commit to version control

# Database secrets
POSTGRES_PASSWORD=$(generate_secret 24)
POSTGRES_ADMIN_PASSWORD=$(generate_secret 24)

# Redis secrets
REDIS_PASSWORD=$(generate_secret 24)

# Application secrets
SECRET_KEY=$(generate_secret 64)
JWT_SECRET=$(generate_secret 48)

# Monitoring secrets
GRAFANA_USER=admin
GRAFANA_PASSWORD=$(generate_secret 16)

# Backup secrets
BACKUP_ENCRYPTION_KEY=$(generate_secret 32)

# Webhook secrets
WEBHOOK_SECRET=$(generate_secret 32)

# SMTP secrets (preserved from previous)
SMTP_USER=${SMTP_USER:-your_smtp_user}
SMTP_PASSWORD=${SMTP_PASSWORD:-your_smtp_password}

# S3 backup secrets (preserved from previous)
BACKUP_S3_ACCESS_KEY=${BACKUP_S3_ACCESS_KEY:-your_s3_access_key}
BACKUP_S3_SECRET_KEY=${BACKUP_S3_SECRET_KEY:-your_s3_secret_key}

# SonarQube token (preserved from previous)
SONARQUBE_TOKEN=${SONARQUBE_TOKEN:-your_sonarqube_token_here}
EOF
    
    chmod 600 "$SECRETS_FILE"
    success "Secrets rotated successfully"
    
    warning "You will need to restart all services for new secrets to take effect"
}

# Export secrets for environment
export_secrets() {
    local env_file="${1:-.env}"
    
    log "Exporting secrets to environment file: $env_file"
    
    if [ ! -f "$SECRETS_FILE" ]; then
        error "Secrets file not found. Run 'generate' command first."
        exit 1
    fi
    
    if [ ! -f "$env_file" ]; then
        error "Environment file not found: $env_file"
        exit 1
    fi
    
    # Create backup of environment file
    cp "$env_file" "${env_file}.backup.$(date +%Y%m%d_%H%M%S)"
    
    # Source secrets
    source "$SECRETS_FILE"
    
    # Update environment file with secrets
    local secrets=(
        "POSTGRES_PASSWORD"
        "REDIS_PASSWORD"
        "SECRET_KEY"
        "JWT_SECRET"
        "GRAFANA_PASSWORD"
        "BACKUP_ENCRYPTION_KEY"
        "WEBHOOK_SECRET"
        "SONARQUBE_TOKEN"
    )
    
    for secret in "${secrets[@]}"; do
        if grep -q "^${secret}=" "$env_file"; then
            # Update existing variable
            sed -i.bak "s|^${secret}=.*|${secret}=${!secret}|" "$env_file"
        else
            # Add new variable
            echo "${secret}=${!secret}" >> "$env_file"
        fi
        log "Updated $secret in $env_file"
    done
    
    success "Secrets exported to $env_file"
}

# Clean up secrets
cleanup_secrets() {
    log "Cleaning up secrets"
    
    if [ -d "$SECRETS_DIR" ]; then
        read -p "Are you sure you want to delete all secrets? (y/N): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            rm -rf "$SECRETS_DIR"
            success "Secrets directory deleted"
        else
            log "Cleanup cancelled"
        fi
    else
        log "No secrets directory found"
    fi
}

# Usage information
usage() {
    echo "Usage: $0 COMMAND [OPTIONS]"
    echo
    echo "Manage Docker secrets for SonarQube MCP"
    echo
    echo "Commands:"
    echo "  generate              Generate new secrets"
    echo "  validate              Validate existing secrets"
    echo "  rotate                Rotate all secrets (except manual ones)"
    echo "  docker-secrets        Create individual secret files for Docker Swarm"
    echo "  export [ENV_FILE]     Export secrets to environment file"
    echo "  cleanup               Delete all secrets (with confirmation)"
    echo
    echo "Examples:"
    echo "  $0 generate           # Generate new secrets"
    echo "  $0 validate           # Validate current secrets"
    echo "  $0 export .env.prod   # Export secrets to production env file"
}

# Main function
main() {
    local command="$1"
    shift || true
    
    case $command in
        generate)
            generate_secrets
            ;;
        validate)
            validate_secrets
            ;;
        rotate)
            rotate_secrets
            ;;
        docker-secrets)
            create_docker_secrets
            ;;
        export)
            export_secrets "$1"
            ;;
        cleanup)
            cleanup_secrets
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