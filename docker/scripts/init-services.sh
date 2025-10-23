#!/bin/bash
# Service initialization script for SonarQube MCP

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

# Check if Docker is running
check_docker() {
    log "Checking Docker status..."
    if ! docker info > /dev/null 2>&1; then
        error "Docker is not running. Please start Docker and try again."
        exit 1
    fi
    success "Docker is running"
}

# Check if Docker Compose is available
check_docker_compose() {
    log "Checking Docker Compose..."
    if ! command -v docker-compose > /dev/null 2>&1; then
        if ! docker compose version > /dev/null 2>&1; then
            error "Docker Compose is not available. Please install Docker Compose."
            exit 1
        fi
        DOCKER_COMPOSE_CMD="docker compose"
    else
        DOCKER_COMPOSE_CMD="docker-compose"
    fi
    success "Docker Compose is available"
}

# Create necessary directories
create_directories() {
    log "Creating necessary directories..."
    
    directories=(
        "logs"
        "logs/nginx"
        "data"
        "docker/nginx/ssl"
    )
    
    for dir in "${directories[@]}"; do
        if [ ! -d "$dir" ]; then
            mkdir -p "$dir"
            log "Created directory: $dir"
        fi
    done
    
    success "Directories created"
}

# Generate SSL certificates for Nginx
generate_ssl_certificates() {
    log "Generating SSL certificates..."
    
    if [ ! -f "docker/nginx/ssl/nginx.crt" ] || [ ! -f "docker/nginx/ssl/nginx.key" ]; then
        # Make the script executable
        chmod +x docker/nginx/generate-ssl.sh
        
        # Run the SSL generation script
        docker run --rm \
            -v "$(pwd)/docker/nginx/ssl:/etc/nginx/ssl" \
            -v "$(pwd)/docker/nginx/generate-ssl.sh:/generate-ssl.sh" \
            alpine/openssl \
            sh /generate-ssl.sh
        
        success "SSL certificates generated"
    else
        log "SSL certificates already exist"
    fi
}

# Validate environment file
validate_environment() {
    log "Validating environment configuration..."
    
    if [ ! -f ".env" ]; then
        warning ".env file not found. Creating from .env.example..."
        if [ -f ".env.example" ]; then
            cp .env.example .env
            warning "Please edit .env file with your configuration before starting services"
        else
            error ".env.example file not found. Please create .env file manually."
            exit 1
        fi
    fi
    
    # Check required environment variables
    required_vars=(
        "SONARQUBE_TOKEN"
        "POSTGRES_PASSWORD"
        "REDIS_PASSWORD"
    )
    
    missing_vars=()
    for var in "${required_vars[@]}"; do
        if ! grep -q "^${var}=" .env || grep -q "^${var}=$" .env; then
            missing_vars+=("$var")
        fi
    done
    
    if [ ${#missing_vars[@]} -gt 0 ]; then
        error "Missing required environment variables:"
        for var in "${missing_vars[@]}"; do
            error "  - $var"
        done
        error "Please set these variables in your .env file"
        exit 1
    fi
    
    success "Environment configuration validated"
}

# Initialize database
init_database() {
    log "Initializing database..."
    
    # Start only PostgreSQL first
    $DOCKER_COMPOSE_CMD up -d postgres
    
    # Wait for PostgreSQL to be ready
    log "Waiting for PostgreSQL to be ready..."
    timeout=60
    while [ $timeout -gt 0 ]; do
        if $DOCKER_COMPOSE_CMD exec -T postgres pg_isready -U sonarqube > /dev/null 2>&1; then
            success "PostgreSQL is ready"
            break
        fi
        sleep 2
        timeout=$((timeout - 2))
    done
    
    if [ $timeout -le 0 ]; then
        error "PostgreSQL failed to start within 60 seconds"
        exit 1
    fi
}

# Initialize Redis
init_redis() {
    log "Initializing Redis..."
    
    # Start Redis
    $DOCKER_COMPOSE_CMD up -d redis
    
    # Wait for Redis to be ready
    log "Waiting for Redis to be ready..."
    timeout=30
    while [ $timeout -gt 0 ]; do
        if $DOCKER_COMPOSE_CMD exec -T redis redis-cli ping > /dev/null 2>&1; then
            success "Redis is ready"
            break
        fi
        sleep 2
        timeout=$((timeout - 2))
    done
    
    if [ $timeout -le 0 ]; then
        error "Redis failed to start within 30 seconds"
        exit 1
    fi
}

# Initialize SonarQube
init_sonarqube() {
    log "Initializing SonarQube..."
    
    # Start SonarQube
    $DOCKER_COMPOSE_CMD up -d sonarqube
    
    # Wait for SonarQube to be ready (this can take a while)
    log "Waiting for SonarQube to be ready (this may take several minutes)..."
    timeout=300  # 5 minutes
    while [ $timeout -gt 0 ]; do
        if curl -s -f http://localhost:9000/sonarqube/api/system/status | grep -q '"status":"UP"'; then
            success "SonarQube is ready"
            break
        fi
        sleep 10
        timeout=$((timeout - 10))
        log "Still waiting for SonarQube... ($timeout seconds remaining)"
    done
    
    if [ $timeout -le 0 ]; then
        error "SonarQube failed to start within 5 minutes"
        exit 1
    fi
}

# Main initialization function
main() {
    log "Starting SonarQube MCP service initialization..."
    
    check_docker
    check_docker_compose
    create_directories
    generate_ssl_certificates
    validate_environment
    init_database
    init_redis
    init_sonarqube
    
    success "Service initialization completed successfully!"
    log "You can now start all services with: $DOCKER_COMPOSE_CMD up -d"
}

# Run main function
main "$@"