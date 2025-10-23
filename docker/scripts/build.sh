#!/bin/bash
# Build script for SonarQube MCP Docker images

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
DOCKER_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

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

# Build Docker images
build_images() {
    local environment="${1:-development}"
    
    log "Building Docker images for environment: $environment"
    
    cd "$PROJECT_ROOT"
    
    # Build MCP Server image
    log "Building MCP Server image..."
    docker build \
        -f docker/dockerfiles/mcp-server.Dockerfile \
        -t sonarqube-mcp-server:latest \
        -t sonarqube-mcp-server:$environment \
        .
    
    if [ $? -eq 0 ]; then
        success "MCP Server image built successfully"
    else
        error "Failed to build MCP Server image"
        exit 1
    fi
    
    # Build Streamlit App image
    log "Building Streamlit App image..."
    docker build \
        -f docker/dockerfiles/streamlit.Dockerfile \
        -t sonarqube-streamlit-app:latest \
        -t sonarqube-streamlit-app:$environment \
        .
    
    if [ $? -eq 0 ]; then
        success "Streamlit App image built successfully"
    else
        error "Failed to build Streamlit App image"
        exit 1
    fi
}

# Build with cache optimization
build_with_cache() {
    local environment="${1:-development}"
    
    log "Building Docker images with cache optimization for environment: $environment"
    
    cd "$PROJECT_ROOT"
    
    # Build MCP Server image with cache
    log "Building MCP Server image with cache..."
    docker build \
        --cache-from sonarqube-mcp-server:latest \
        -f docker/dockerfiles/mcp-server.Dockerfile \
        -t sonarqube-mcp-server:latest \
        -t sonarqube-mcp-server:$environment \
        .
    
    # Build Streamlit App image with cache
    log "Building Streamlit App image with cache..."
    docker build \
        --cache-from sonarqube-streamlit-app:latest \
        -f docker/dockerfiles/streamlit.Dockerfile \
        -t sonarqube-streamlit-app:latest \
        -t sonarqube-streamlit-app:$environment \
        .
}

# Build for multiple architectures
build_multiarch() {
    local environment="${1:-development}"
    
    log "Building multi-architecture Docker images for environment: $environment"
    
    cd "$PROJECT_ROOT"
    
    # Create buildx builder if it doesn't exist
    if ! docker buildx ls | grep -q "sonarqube-mcp-builder"; then
        log "Creating buildx builder..."
        docker buildx create --name sonarqube-mcp-builder --use
    else
        docker buildx use sonarqube-mcp-builder
    fi
    
    # Build MCP Server image for multiple architectures
    log "Building MCP Server image for multiple architectures..."
    docker buildx build \
        --platform linux/amd64,linux/arm64 \
        -f docker/dockerfiles/mcp-server.Dockerfile \
        -t sonarqube-mcp-server:latest \
        -t sonarqube-mcp-server:$environment \
        --push \
        .
    
    # Build Streamlit App image for multiple architectures
    log "Building Streamlit App image for multiple architectures..."
    docker buildx build \
        --platform linux/amd64,linux/arm64 \
        -f docker/dockerfiles/streamlit.Dockerfile \
        -t sonarqube-streamlit-app:latest \
        -t sonarqube-streamlit-app:$environment \
        --push \
        .
}

# Clean build (no cache)
clean_build() {
    local environment="${1:-development}"
    
    log "Performing clean build (no cache) for environment: $environment"
    
    cd "$PROJECT_ROOT"
    
    # Build MCP Server image without cache
    log "Building MCP Server image without cache..."
    docker build \
        --no-cache \
        -f docker/dockerfiles/mcp-server.Dockerfile \
        -t sonarqube-mcp-server:latest \
        -t sonarqube-mcp-server:$environment \
        .
    
    # Build Streamlit App image without cache
    log "Building Streamlit App image without cache..."
    docker build \
        --no-cache \
        -f docker/dockerfiles/streamlit.Dockerfile \
        -t sonarqube-streamlit-app:latest \
        -t sonarqube-streamlit-app:$environment \
        .
}

# List built images
list_images() {
    log "Listing SonarQube MCP Docker images..."
    docker images | grep -E "(sonarqube-mcp-server|sonarqube-streamlit-app)" || echo "No SonarQube MCP images found"
}

# Remove images
remove_images() {
    log "Removing SonarQube MCP Docker images..."
    
    # Remove MCP Server images
    docker images -q sonarqube-mcp-server | xargs -r docker rmi -f
    
    # Remove Streamlit App images
    docker images -q sonarqube-streamlit-app | xargs -r docker rmi -f
    
    success "Images removed successfully"
}

# Tag images for registry
tag_for_registry() {
    local registry="$1"
    local tag="${2:-latest}"
    
    if [ -z "$registry" ]; then
        error "Registry URL is required"
        exit 1
    fi
    
    log "Tagging images for registry: $registry"
    
    # Tag MCP Server image
    docker tag sonarqube-mcp-server:latest "$registry/sonarqube-mcp-server:$tag"
    
    # Tag Streamlit App image
    docker tag sonarqube-streamlit-app:latest "$registry/sonarqube-streamlit-app:$tag"
    
    success "Images tagged for registry: $registry"
}

# Push images to registry
push_to_registry() {
    local registry="$1"
    local tag="${2:-latest}"
    
    if [ -z "$registry" ]; then
        error "Registry URL is required"
        exit 1
    fi
    
    log "Pushing images to registry: $registry"
    
    # Push MCP Server image
    docker push "$registry/sonarqube-mcp-server:$tag"
    
    # Push Streamlit App image
    docker push "$registry/sonarqube-streamlit-app:$tag"
    
    success "Images pushed to registry: $registry"
}

# Usage information
usage() {
    echo "Usage: $0 COMMAND [OPTIONS]"
    echo
    echo "Build Docker images for SonarQube MCP"
    echo
    echo "Commands:"
    echo "  build [ENV]           Build images for environment (default: development)"
    echo "  build-cache [ENV]     Build with cache optimization"
    echo "  build-multiarch [ENV] Build for multiple architectures"
    echo "  clean-build [ENV]     Clean build without cache"
    echo "  list                  List built images"
    echo "  remove                Remove all SonarQube MCP images"
    echo "  tag REGISTRY [TAG]    Tag images for registry"
    echo "  push REGISTRY [TAG]   Push images to registry"
    echo
    echo "Environments:"
    echo "  development           Development environment"
    echo "  staging              Staging environment"
    echo "  production           Production environment"
    echo
    echo "Examples:"
    echo "  $0 build development     # Build for development"
    echo "  $0 build-cache production # Build for production with cache"
    echo "  $0 tag registry.example.com latest"
    echo "  $0 push registry.example.com latest"
}

# Main function
main() {
    local command="$1"
    shift || true
    
    case $command in
        build)
            build_images "$1"
            ;;
        build-cache)
            build_with_cache "$1"
            ;;
        build-multiarch)
            build_multiarch "$1"
            ;;
        clean-build)
            clean_build "$1"
            ;;
        list)
            list_images
            ;;
        remove)
            remove_images
            ;;
        tag)
            tag_for_registry "$1" "$2"
            ;;
        push)
            push_to_registry "$1" "$2"
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