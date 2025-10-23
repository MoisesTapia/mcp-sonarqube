#!/bin/bash
# Health check script for all SonarQube MCP services

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Service health check functions
check_postgres() {
    echo -n "PostgreSQL: "
    if docker-compose exec -T postgres pg_isready -U sonarqube > /dev/null 2>&1; then
        echo -e "${GREEN}✓ Healthy${NC}"
        return 0
    else
        echo -e "${RED}✗ Unhealthy${NC}"
        return 1
    fi
}

check_redis() {
    echo -n "Redis: "
    if docker-compose exec -T redis redis-cli ping > /dev/null 2>&1; then
        echo -e "${GREEN}✓ Healthy${NC}"
        return 0
    else
        echo -e "${RED}✗ Unhealthy${NC}"
        return 1
    fi
}

check_sonarqube() {
    echo -n "SonarQube: "
    if curl -s -f http://localhost:9000/sonarqube/api/system/status | grep -q '"status":"UP"' > /dev/null 2>&1; then
        echo -e "${GREEN}✓ Healthy${NC}"
        return 0
    else
        echo -e "${RED}✗ Unhealthy${NC}"
        return 1
    fi
}

check_mcp_server() {
    echo -n "MCP Server: "
    if curl -s -f http://localhost:8000/health > /dev/null 2>&1; then
        echo -e "${GREEN}✓ Healthy${NC}"
        return 0
    else
        echo -e "${RED}✗ Unhealthy${NC}"
        return 1
    fi
}

check_streamlit() {
    echo -n "Streamlit App: "
    if curl -s -f http://localhost:8501/_stcore/health > /dev/null 2>&1; then
        echo -e "${GREEN}✓ Healthy${NC}"
        return 0
    else
        echo -e "${RED}✗ Unhealthy${NC}"
        return 1
    fi
}

check_nginx() {
    echo -n "Nginx: "
    if curl -s -f http://localhost/health > /dev/null 2>&1; then
        echo -e "${GREEN}✓ Healthy${NC}"
        return 0
    else
        echo -e "${RED}✗ Unhealthy${NC}"
        return 1
    fi
}

check_prometheus() {
    echo -n "Prometheus: "
    if curl -s -f http://localhost:9090/-/healthy > /dev/null 2>&1; then
        echo -e "${GREEN}✓ Healthy${NC}"
        return 0
    else
        echo -e "${RED}✗ Unhealthy${NC}"
        return 1
    fi
}

check_grafana() {
    echo -n "Grafana: "
    if curl -s -f http://localhost:3000/api/health > /dev/null 2>&1; then
        echo -e "${GREEN}✓ Healthy${NC}"
        return 0
    else
        echo -e "${RED}✗ Unhealthy${NC}"
        return 1
    fi
}

# Main health check function
main() {
    echo -e "${BLUE}SonarQube MCP Health Check${NC}"
    echo "=========================="
    
    failed_services=0
    
    # Core services
    echo -e "\n${BLUE}Core Services:${NC}"
    check_postgres || ((failed_services++))
    check_redis || ((failed_services++))
    check_sonarqube || ((failed_services++))
    
    # Application services
    echo -e "\n${BLUE}Application Services:${NC}"
    check_mcp_server || ((failed_services++))
    check_streamlit || ((failed_services++))
    
    # Infrastructure services
    echo -e "\n${BLUE}Infrastructure Services:${NC}"
    check_nginx || ((failed_services++))
    
    # Monitoring services (optional)
    echo -e "\n${BLUE}Monitoring Services:${NC}"
    check_prometheus || ((failed_services++))
    check_grafana || ((failed_services++))
    
    # Summary
    echo -e "\n=========================="
    if [ $failed_services -eq 0 ]; then
        echo -e "${GREEN}All services are healthy!${NC}"
        exit 0
    else
        echo -e "${RED}$failed_services service(s) are unhealthy${NC}"
        exit 1
    fi
}

# Check if Docker Compose is available
if ! command -v docker-compose > /dev/null 2>&1; then
    if ! docker compose version > /dev/null 2>&1; then
        echo -e "${RED}Docker Compose is not available${NC}"
        exit 1
    fi
    # Use docker compose instead of docker-compose
    alias docker-compose='docker compose'
fi

# Run main function
main "$@"