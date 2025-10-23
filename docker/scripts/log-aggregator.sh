#!/bin/bash
# Log aggregation and management script for SonarQube MCP

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
LOG_DIR="logs"
ARCHIVE_DIR="logs/archive"
MAX_LOG_SIZE="100M"
MAX_LOG_DAYS=30

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

# Create log directories
setup_log_directories() {
    log "Setting up log directories..."
    
    directories=(
        "$LOG_DIR"
        "$ARCHIVE_DIR"
        "$LOG_DIR/nginx"
        "$LOG_DIR/containers"
        "$LOG_DIR/application"
    )
    
    for dir in "${directories[@]}"; do
        if [ ! -d "$dir" ]; then
            mkdir -p "$dir"
            log "Created directory: $dir"
        fi
    done
    
    success "Log directories created"
}

# Collect container logs
collect_container_logs() {
    log "Collecting container logs..."
    
    # Get list of running containers
    containers=$($DOCKER_COMPOSE_CMD ps --format "{{.Name}}")
    
    if [ -z "$containers" ]; then
        warning "No running containers found"
        return
    fi
    
    # Collect logs for each container
    while IFS= read -r container; do
        if [ -n "$container" ]; then
            log "Collecting logs for: $container"
            
            # Create container-specific log file
            log_file="$LOG_DIR/containers/${container}_$(date +%Y%m%d_%H%M%S).log"
            
            # Get container logs (last 1000 lines)
            docker logs --tail 1000 "$container" > "$log_file" 2>&1
            
            # Compress if file is large
            if [ -f "$log_file" ] && [ $(stat -f%z "$log_file" 2>/dev/null || stat -c%s "$log_file") -gt 10485760 ]; then
                gzip "$log_file"
                log_file="${log_file}.gz"
            fi
            
            log "Saved: $log_file"
        fi
    done <<< "$containers"
    
    success "Container logs collected"
}

# Aggregate application logs
aggregate_application_logs() {
    log "Aggregating application logs..."
    
    # Aggregate MCP server logs
    if [ -d "src/mcp_server" ]; then
        find . -name "*.log" -path "*/mcp_server/*" -exec cp {} "$LOG_DIR/application/" \; 2>/dev/null || true
    fi
    
    # Aggregate Streamlit logs
    if [ -d "src/streamlit_app" ]; then
        find . -name "*.log" -path "*/streamlit_app/*" -exec cp {} "$LOG_DIR/application/" \; 2>/dev/null || true
    fi
    
    success "Application logs aggregated"
}

# Rotate logs
rotate_logs() {
    log "Rotating logs..."
    
    # Find and rotate large log files
    find "$LOG_DIR" -name "*.log" -size +$MAX_LOG_SIZE -exec gzip {} \;
    
    # Move old logs to archive
    find "$LOG_DIR" -name "*.log.gz" -mtime +7 -exec mv {} "$ARCHIVE_DIR/" \;
    
    # Clean up very old archives
    find "$ARCHIVE_DIR" -name "*.log.gz" -mtime +$MAX_LOG_DAYS -delete
    
    success "Log rotation completed"
}

# Generate log summary
generate_log_summary() {
    local summary_file="$LOG_DIR/log-summary-$(date +%Y%m%d_%H%M%S).txt"
    
    log "Generating log summary..."
    
    {
        echo "SonarQube MCP Log Summary"
        echo "Generated: $(date)"
        echo "========================="
        echo
        
        echo "Log Directory Structure:"
        tree "$LOG_DIR" 2>/dev/null || find "$LOG_DIR" -type f | sort
        echo
        
        echo "Log File Sizes:"
        find "$LOG_DIR" -name "*.log" -exec ls -lh {} \; | awk '{print $5 "\t" $9}'
        echo
        
        echo "Recent Error Patterns:"
        find "$LOG_DIR" -name "*.log" -exec grep -l -i "error\|exception\|failed" {} \; | head -10
        echo
        
        echo "Container Status:"
        $DOCKER_COMPOSE_CMD ps
        echo
        
        echo "Disk Usage:"
        du -sh "$LOG_DIR"/* 2>/dev/null || echo "No log files found"
        
    } > "$summary_file"
    
    success "Log summary generated: $summary_file"
}

# Search logs for patterns
search_logs() {
    local pattern="$1"
    local time_range="${2:-1h}"
    
    if [ -z "$pattern" ]; then
        error "Search pattern is required"
        return 1
    fi
    
    log "Searching logs for pattern: $pattern (last $time_range)"
    
    # Search in container logs
    echo -e "\n${BLUE}Container Logs:${NC}"
    find "$LOG_DIR/containers" -name "*.log" -newermt "-$time_range" -exec grep -l -i "$pattern" {} \; | while read -r file; do
        echo -e "${YELLOW}Found in: $file${NC}"
        grep -i --color=always "$pattern" "$file" | head -5
        echo
    done
    
    # Search in application logs
    echo -e "\n${BLUE}Application Logs:${NC}"
    find "$LOG_DIR/application" -name "*.log" -newermt "-$time_range" -exec grep -l -i "$pattern" {} \; | while read -r file; do
        echo -e "${YELLOW}Found in: $file${NC}"
        grep -i --color=always "$pattern" "$file" | head -5
        echo
    done
}

# Follow logs in real-time
follow_logs() {
    local service="$1"
    
    if [ -n "$service" ]; then
        log "Following logs for service: $service"
        $DOCKER_COMPOSE_CMD logs -f "$service"
    else
        log "Following logs for all services"
        $DOCKER_COMPOSE_CMD logs -f
    fi
}

# Export logs
export_logs() {
    local export_file="sonarqube-mcp-logs-$(date +%Y%m%d_%H%M%S).tar.gz"
    
    log "Exporting logs to: $export_file"
    
    # Create temporary directory for export
    temp_dir=$(mktemp -d)
    
    # Copy logs to temp directory
    cp -r "$LOG_DIR" "$temp_dir/"
    
    # Add container information
    $DOCKER_COMPOSE_CMD ps > "$temp_dir/container-status.txt"
    docker system df > "$temp_dir/docker-system-info.txt"
    
    # Create archive
    tar -czf "$export_file" -C "$temp_dir" .
    
    # Clean up
    rm -rf "$temp_dir"
    
    success "Logs exported to: $export_file"
}

# Usage information
usage() {
    echo "Usage: $0 [COMMAND] [OPTIONS]"
    echo
    echo "Commands:"
    echo "  collect             Collect all container and application logs"
    echo "  rotate              Rotate and archive old logs"
    echo "  summary             Generate log summary report"
    echo "  search PATTERN      Search logs for pattern"
    echo "  follow [SERVICE]    Follow logs in real-time"
    echo "  export              Export all logs to archive"
    echo "  cleanup             Clean up old logs and archives"
    echo
    echo "Options:"
    echo "  --time-range TIME   Time range for search (default: 1h)"
    echo "  --help              Show this help message"
    echo
    echo "Examples:"
    echo "  $0 collect          # Collect all logs"
    echo "  $0 search error     # Search for errors in logs"
    echo "  $0 follow nginx     # Follow nginx logs"
    echo "  $0 export           # Export all logs"
}

# Clean up old logs
cleanup_logs() {
    log "Cleaning up old logs..."
    
    # Remove logs older than MAX_LOG_DAYS
    find "$LOG_DIR" -name "*.log" -mtime +$MAX_LOG_DAYS -delete
    find "$ARCHIVE_DIR" -name "*.log.gz" -mtime +$MAX_LOG_DAYS -delete
    
    # Remove empty directories
    find "$LOG_DIR" -type d -empty -delete 2>/dev/null || true
    
    success "Log cleanup completed"
}

# Main function
main() {
    local command="$1"
    shift || true
    
    # Parse options
    while [[ $# -gt 0 ]]; do
        case $1 in
            --time-range)
                TIME_RANGE="$2"
                shift 2
                ;;
            --help)
                usage
                exit 0
                ;;
            *)
                break
                ;;
        esac
    done
    
    check_docker_compose
    setup_log_directories
    
    case $command in
        collect)
            collect_container_logs
            aggregate_application_logs
            ;;
        rotate)
            rotate_logs
            ;;
        summary)
            generate_log_summary
            ;;
        search)
            search_logs "$1" "${TIME_RANGE:-1h}"
            ;;
        follow)
            follow_logs "$1"
            ;;
        export)
            export_logs
            ;;
        cleanup)
            cleanup_logs
            ;;
        "")
            # Default action
            collect_container_logs
            aggregate_application_logs
            generate_log_summary
            ;;
        *)
            error "Unknown command: $command"
            usage
            exit 1
            ;;
    esac
}

# Run main function
main "$@"