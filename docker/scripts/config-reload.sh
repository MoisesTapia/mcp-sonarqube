#!/bin/bash
# Configuration hot-reloading script for SonarQube MCP

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
WATCH_FILES=(".env" "config/config.yaml" "docker-compose.yml")
RELOAD_SERVICES=("mcp-server" "streamlit-app")
CHECK_INTERVAL=5

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

# Get file modification time
get_file_mtime() {
    local file="$1"
    if [ -f "$file" ]; then
        stat -f%m "$file" 2>/dev/null || stat -c%Y "$file" 2>/dev/null || echo "0"
    else
        echo "0"
    fi
}

# Store initial modification times
store_initial_mtimes() {
    log "Storing initial file modification times"
    
    declare -gA file_mtimes
    
    for file in "${WATCH_FILES[@]}"; do
        file_mtimes["$file"]=$(get_file_mtime "$file")
        log "Watching: $file (mtime: ${file_mtimes[$file]})"
    done
}

# Check for file changes
check_file_changes() {
    local changed_files=()
    
    for file in "${WATCH_FILES[@]}"; do
        local current_mtime=$(get_file_mtime "$file")
        local stored_mtime=${file_mtimes["$file"]}
        
        if [ "$current_mtime" != "$stored_mtime" ]; then
            changed_files+=("$file")
            file_mtimes["$file"]=$current_mtime
        fi
    done
    
    if [ ${#changed_files[@]} -gt 0 ]; then
        log "Detected changes in: ${changed_files[*]}"
        return 0
    else
        return 1
    fi
}

# Validate configuration before reload
validate_config() {
    log "Validating configuration before reload"
    
    # Run configuration validation script
    if [ -f "scripts/docker/validate-config.sh" ]; then
        if bash scripts/docker/validate-config.sh > /dev/null 2>&1; then
            success "Configuration validation passed"
            return 0
        else
            error "Configuration validation failed"
            return 1
        fi
    else
        warning "Configuration validation script not found, skipping validation"
        return 0
    fi
}

# Reload specific service
reload_service() {
    local service="$1"
    
    log "Reloading service: $service"
    
    # Check if service is running
    if ! $DOCKER_COMPOSE_CMD ps -q "$service" > /dev/null 2>&1; then
        warning "Service $service is not running, skipping reload"
        return
    fi
    
    # Send SIGHUP for graceful reload (if supported)
    if $DOCKER_COMPOSE_CMD kill -s SIGHUP "$service" 2>/dev/null; then
        log "Sent SIGHUP to $service for graceful reload"
        sleep 2
        
        # Check if service is still healthy
        if $DOCKER_COMPOSE_CMD ps "$service" | grep -q "Up"; then
            success "Service $service reloaded successfully"
        else
            warning "Service $service may have issues after reload"
        fi
    else
        # Fallback to restart
        warning "Graceful reload not supported, restarting $service"
        $DOCKER_COMPOSE_CMD restart "$service"
        success "Service $service restarted"
    fi
}

# Reload all affected services
reload_services() {
    log "Reloading affected services"
    
    for service in "${RELOAD_SERVICES[@]}"; do
        reload_service "$service"
    done
    
    # Wait for services to stabilize
    sleep 5
    
    # Check service health
    check_service_health
}

# Check service health after reload
check_service_health() {
    log "Checking service health after reload"
    
    local unhealthy_services=()
    
    for service in "${RELOAD_SERVICES[@]}"; do
        # Check if service is running
        if $DOCKER_COMPOSE_CMD ps -q "$service" > /dev/null 2>&1; then
            # Check health status
            local health_status=$($DOCKER_COMPOSE_CMD ps "$service" | tail -1 | awk '{print $4}')
            
            if [[ "$health_status" =~ Up.*healthy ]]; then
                success "Service $service is healthy"
            else
                unhealthy_services+=("$service")
                warning "Service $service may be unhealthy: $health_status"
            fi
        else
            unhealthy_services+=("$service")
            error "Service $service is not running"
        fi
    done
    
    if [ ${#unhealthy_services[@]} -gt 0 ]; then
        error "Unhealthy services detected: ${unhealthy_services[*]}"
        return 1
    else
        success "All services are healthy"
        return 0
    fi
}

# Send reload signal to running containers
send_reload_signal() {
    local service="$1"
    local signal="${2:-SIGHUP}"
    
    log "Sending $signal to $service"
    
    # Get container ID
    local container_id=$($DOCKER_COMPOSE_CMD ps -q "$service")
    
    if [ -n "$container_id" ]; then
        docker kill --signal="$signal" "$container_id"
        log "Signal $signal sent to $service ($container_id)"
    else
        warning "Container for $service not found"
    fi
}

# Watch for configuration changes
watch_config_changes() {
    log "Starting configuration file watcher"
    log "Watching files: ${WATCH_FILES[*]}"
    log "Will reload services: ${RELOAD_SERVICES[*]}"
    log "Check interval: ${CHECK_INTERVAL}s"
    
    store_initial_mtimes
    
    while true; do
        if check_file_changes; then
            log "Configuration changes detected, initiating reload"
            
            if validate_config; then
                reload_services
                
                if check_service_health; then
                    success "Configuration reload completed successfully"
                else
                    error "Some services are unhealthy after reload"
                fi
            else
                error "Configuration validation failed, skipping reload"
            fi
        fi
        
        sleep "$CHECK_INTERVAL"
    done
}

# Manual reload trigger
manual_reload() {
    log "Manual configuration reload triggered"
    
    if validate_config; then
        reload_services
        
        if check_service_health; then
            success "Manual reload completed successfully"
        else
            error "Some services are unhealthy after reload"
            exit 1
        fi
    else
        error "Configuration validation failed"
        exit 1
    fi
}

# Test reload functionality
test_reload() {
    log "Testing reload functionality"
    
    # Create a temporary config change
    local test_file=".env.test"
    echo "# Test configuration change" > "$test_file"
    
    # Add test file to watch list temporarily
    WATCH_FILES+=("$test_file")
    
    # Store initial mtimes
    store_initial_mtimes
    
    # Modify test file
    sleep 1
    echo "# Modified test configuration" >> "$test_file"
    
    # Check for changes
    if check_file_changes; then
        success "File change detection is working"
    else
        error "File change detection failed"
    fi
    
    # Clean up
    rm -f "$test_file"
    
    success "Reload functionality test completed"
}

# Usage information
usage() {
    echo "Usage: $0 COMMAND [OPTIONS]"
    echo
    echo "Configuration hot-reloading for SonarQube MCP"
    echo
    echo "Commands:"
    echo "  watch                 Start watching for configuration changes"
    echo "  reload                Manually trigger configuration reload"
    echo "  test                  Test reload functionality"
    echo "  signal SERVICE SIG    Send signal to specific service"
    echo
    echo "Options:"
    echo "  --interval N          Set check interval in seconds (default: 5)"
    echo "  --files FILE1,FILE2   Override files to watch"
    echo "  --services SVC1,SVC2  Override services to reload"
    echo
    echo "Examples:"
    echo "  $0 watch              # Start watching for changes"
    echo "  $0 reload             # Manual reload"
    echo "  $0 signal mcp-server SIGHUP  # Send SIGHUP to MCP server"
}

# Parse command line options
parse_options() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            --interval)
                CHECK_INTERVAL="$2"
                shift 2
                ;;
            --files)
                IFS=',' read -ra WATCH_FILES <<< "$2"
                shift 2
                ;;
            --services)
                IFS=',' read -ra RELOAD_SERVICES <<< "$2"
                shift 2
                ;;
            *)
                break
                ;;
        esac
    done
}

# Signal handler for graceful shutdown
cleanup() {
    log "Received shutdown signal, stopping configuration watcher"
    exit 0
}

# Main function
main() {
    local command="$1"
    shift || true
    
    # Parse options
    parse_options "$@"
    
    check_docker_compose
    
    case $command in
        watch)
            trap cleanup SIGTERM SIGINT
            watch_config_changes
            ;;
        reload)
            manual_reload
            ;;
        test)
            test_reload
            ;;
        signal)
            local service="$1"
            local signal="${2:-SIGHUP}"
            if [ -z "$service" ]; then
                error "Service name is required for signal command"
                exit 1
            fi
            send_reload_signal "$service" "$signal"
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