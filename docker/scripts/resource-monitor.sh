#!/bin/bash
# Resource monitoring script for SonarQube MCP containers

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
REFRESH_INTERVAL=5
LOG_FILE="logs/resource-monitor.log"

# Logging function
log() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $1" >> "$LOG_FILE"
}

# Check if Docker Compose is available
check_docker_compose() {
    if ! command -v docker-compose > /dev/null 2>&1; then
        if ! docker compose version > /dev/null 2>&1; then
            echo -e "${RED}Docker Compose is not available${NC}"
            exit 1
        fi
        DOCKER_COMPOSE_CMD="docker compose"
    else
        DOCKER_COMPOSE_CMD="docker-compose"
    fi
}

# Get container stats
get_container_stats() {
    docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.MemPerc}}\t{{.NetIO}}\t{{.BlockIO}}" \
        $(docker-compose ps -q) 2>/dev/null || echo "No running containers"
}

# Check resource limits and alerts
check_resource_alerts() {
    local alerts=()
    
    # Get container stats in parseable format
    while IFS= read -r line; do
        if [[ $line == *"%"* ]]; then
            container=$(echo "$line" | awk '{print $1}')
            cpu_percent=$(echo "$line" | awk '{print $2}' | sed 's/%//')
            mem_percent=$(echo "$line" | awk '{print $4}' | sed 's/%//')
            
            # CPU alerts
            if (( $(echo "$cpu_percent > 80" | bc -l) )); then
                alerts+=("${RED}HIGH CPU${NC}: $container using ${cpu_percent}% CPU")
            fi
            
            # Memory alerts
            if (( $(echo "$mem_percent > 85" | bc -l) )); then
                alerts+=("${RED}HIGH MEMORY${NC}: $container using ${mem_percent}% memory")
            fi
        fi
    done < <(docker stats --no-stream --format "{{.Container}} {{.CPUPerc}} {{.MemUsage}} {{.MemPerc}}" $(docker-compose ps -q) 2>/dev/null)
    
    # Display alerts
    if [ ${#alerts[@]} -gt 0 ]; then
        echo -e "\n${YELLOW}⚠️  RESOURCE ALERTS:${NC}"
        for alert in "${alerts[@]}"; do
            echo -e "  $alert"
            log "ALERT: $(echo "$alert" | sed 's/\x1b\[[0-9;]*m//g')"
        done
    fi
}

# Get disk usage
get_disk_usage() {
    echo -e "\n${BLUE}📁 Docker Volume Usage:${NC}"
    docker system df -v | grep -E "(VOLUME NAME|sonarqube-mcp)" || echo "No volumes found"
    
    echo -e "\n${BLUE}💾 Host Disk Usage:${NC}"
    df -h / | tail -1 | awk '{print "Root filesystem: " $3 " used / " $2 " total (" $5 " used)"}'
}

# Get network stats
get_network_stats() {
    echo -e "\n${BLUE}🌐 Network Usage:${NC}"
    docker network ls | grep sonarqube-mcp || echo "No custom networks found"
}

# Monitor container health
monitor_health() {
    echo -e "\n${BLUE}🏥 Container Health Status:${NC}"
    
    containers=$(docker-compose ps --format "table {{.Name}}\t{{.State}}\t{{.Status}}")
    echo "$containers"
    
    # Check for unhealthy containers
    unhealthy=$(docker ps --filter "health=unhealthy" --format "{{.Names}}" | grep -E "(sonarqube|mcp|streamlit|postgres|redis|nginx)" || true)
    
    if [ -n "$unhealthy" ]; then
        echo -e "\n${RED}🚨 Unhealthy Containers:${NC}"
        echo "$unhealthy"
        log "ALERT: Unhealthy containers detected: $unhealthy"
    fi
}

# Display system overview
display_overview() {
    clear
    echo -e "${BLUE}╔══════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║                    SonarQube MCP Monitor                     ║${NC}"
    echo -e "${BLUE}║                  $(date +'%Y-%m-%d %H:%M:%S')                    ║${NC}"
    echo -e "${BLUE}╚══════════════════════════════════════════════════════════════╝${NC}"
    
    echo -e "\n${BLUE}📊 Container Resource Usage:${NC}"
    get_container_stats
    
    check_resource_alerts
    monitor_health
    get_disk_usage
    get_network_stats
    
    echo -e "\n${BLUE}Press Ctrl+C to stop monitoring${NC}"
    echo -e "${BLUE}Refresh interval: ${REFRESH_INTERVAL}s${NC}"
}

# Continuous monitoring mode
continuous_monitor() {
    log "Starting continuous resource monitoring"
    
    while true; do
        display_overview
        sleep "$REFRESH_INTERVAL"
    done
}

# One-time report
generate_report() {
    local report_file="logs/resource-report-$(date +%Y%m%d_%H%M%S).txt"
    
    {
        echo "SonarQube MCP Resource Report"
        echo "Generated: $(date)"
        echo "================================"
        echo
        
        echo "Container Stats:"
        get_container_stats
        echo
        
        echo "Health Status:"
        docker-compose ps
        echo
        
        echo "Disk Usage:"
        get_disk_usage
        echo
        
        echo "System Resources:"
        free -h
        echo
        df -h
        
    } > "$report_file"
    
    echo -e "${GREEN}Report generated: $report_file${NC}"
}

# Usage information
usage() {
    echo "Usage: $0 [OPTIONS]"
    echo
    echo "Options:"
    echo "  -c, --continuous    Start continuous monitoring (default)"
    echo "  -r, --report        Generate one-time report"
    echo "  -i, --interval N    Set refresh interval in seconds (default: 5)"
    echo "  -h, --help          Show this help message"
    echo
    echo "Examples:"
    echo "  $0                  # Start continuous monitoring"
    echo "  $0 -r               # Generate one-time report"
    echo "  $0 -c -i 10         # Monitor with 10-second intervals"
}

# Main function
main() {
    local mode="continuous"
    
    # Parse command line arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            -c|--continuous)
                mode="continuous"
                shift
                ;;
            -r|--report)
                mode="report"
                shift
                ;;
            -i|--interval)
                REFRESH_INTERVAL="$2"
                shift 2
                ;;
            -h|--help)
                usage
                exit 0
                ;;
            *)
                echo "Unknown option: $1"
                usage
                exit 1
                ;;
        esac
    done
    
    # Create logs directory if it doesn't exist
    mkdir -p logs
    
    check_docker_compose
    
    case $mode in
        continuous)
            continuous_monitor
            ;;
        report)
            generate_report
            ;;
    esac
}

# Handle Ctrl+C gracefully
trap 'echo -e "\n${GREEN}Monitoring stopped${NC}"; exit 0' SIGINT SIGTERM

# Run main function
main "$@"