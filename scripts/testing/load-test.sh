#!/bin/bash

# Load Testing Script for SonarQube MCP
# This script performs load testing and performance validation

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
LOAD_TEST_RESULTS_DIR="$PROJECT_ROOT/load-test-results"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# Default test parameters
DEFAULT_CONCURRENT_USERS=10
DEFAULT_DURATION=60
DEFAULT_RAMP_UP=10
DEFAULT_TARGET_URL="http://localhost:8000"

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
    echo "  -u, --users NUM         Number of concurrent users (default: $DEFAULT_CONCURRENT_USERS)"
    echo "  -d, --duration SEC      Test duration in seconds (default: $DEFAULT_DURATION)"
    echo "  -r, --ramp-up SEC       Ramp-up time in seconds (default: $DEFAULT_RAMP_UP)"
    echo "  -t, --target URL        Target URL (default: $DEFAULT_TARGET_URL)"
    echo "  -s, --scenario NAME     Test scenario (basic|full|stress|spike)"
    echo "  -m, --monitoring        Enable system monitoring during test"
    echo "  -p, --profile           Enable profiling"
    echo "  -h, --help              Show this help message"
    echo ""
    echo "Test Scenarios:"
    echo "  basic   - Basic load test with default parameters"
    echo "  full    - Comprehensive test covering all endpoints"
    echo "  stress  - Stress test with high load"
    echo "  spike   - Spike test with sudden load increases"
    echo ""
    echo "Examples:"
    echo "  $0 --scenario basic"
    echo "  $0 --users 50 --duration 300 --monitoring"
    echo "  $0 --scenario stress --profile"
    exit 1
}

# Parse command line arguments
parse_args() {
    CONCURRENT_USERS=$DEFAULT_CONCURRENT_USERS
    DURATION=$DEFAULT_DURATION
    RAMP_UP=$DEFAULT_RAMP_UP
    TARGET_URL=$DEFAULT_TARGET_URL
    SCENARIO="basic"
    ENABLE_MONITORING=false
    ENABLE_PROFILING=false
    
    while [[ $# -gt 0 ]]; do
        case $1 in
            -u|--users)
                CONCURRENT_USERS="$2"
                shift 2
                ;;
            -d|--duration)
                DURATION="$2"
                shift 2
                ;;
            -r|--ramp-up)
                RAMP_UP="$2"
                shift 2
                ;;
            -t|--target)
                TARGET_URL="$2"
                shift 2
                ;;
            -s|--scenario)
                SCENARIO="$2"
                shift 2
                ;;
            -m|--monitoring)
                ENABLE_MONITORING=true
                shift
                ;;
            -p|--profile)
                ENABLE_PROFILING=true
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
    
    # Validate scenario
    case "$SCENARIO" in
        basic|full|stress|spike)
            ;;
        *)
            error "Invalid scenario: $SCENARIO"
            ;;
    esac
}

# Setup load test environment
setup_load_test_environment() {
    log "Setting up load test environment..."
    
    # Create results directory
    mkdir -p "$LOAD_TEST_RESULTS_DIR"
    
    # Check if target service is available
    if ! curl -f "$TARGET_URL/health" &> /dev/null; then
        warn "Target service not available at $TARGET_URL"
        info "Starting services..."
        
        cd "$PROJECT_ROOT"
        docker-compose -f docker/compose/base/docker-compose.yml up -d
        
        # Wait for services to be ready
        local max_wait=120
        local wait_time=0
        
        while ! curl -f "$TARGET_URL/health" &> /dev/null; do
            if [[ $wait_time -ge $max_wait ]]; then
                error "Services failed to start within ${max_wait} seconds"
            fi
            sleep 5
            wait_time=$((wait_time + 5))
            info "Waiting for services to be ready... (${wait_time}s)"
        done
    fi
    
    # Install load testing tools if not present
    if ! command -v ab &> /dev/null && ! command -v wrk &> /dev/null && ! command -v hey &> /dev/null; then
        info "Installing load testing tools..."
        
        # Try to install hey (Go-based HTTP load testing tool)
        if command -v go &> /dev/null; then
            go install github.com/rakyll/hey@latest
        else
            warn "No suitable load testing tool found. Please install 'ab', 'wrk', or 'hey'"
        fi
    fi
    
    log "Load test environment setup completed"
}

# Start system monitoring
start_monitoring() {
    if [[ "$ENABLE_MONITORING" != "true" ]]; then
        return 0
    fi
    
    log "Starting system monitoring..."
    
    # Start resource monitoring
    {
        echo "timestamp,cpu_percent,memory_percent,disk_io_read,disk_io_write,network_rx,network_tx"
        while true; do
            local timestamp=$(date +%s)
            local cpu_percent=$(top -bn1 | grep "Cpu(s)" | awk '{print $2}' | cut -d'%' -f1)
            local memory_info=$(free | grep Mem)
            local memory_total=$(echo $memory_info | awk '{print $2}')
            local memory_used=$(echo $memory_info | awk '{print $3}')
            local memory_percent=$(( memory_used * 100 / memory_total ))
            
            echo "$timestamp,$cpu_percent,$memory_percent,0,0,0,0"
            sleep 1
        done
    } > "$LOAD_TEST_RESULTS_DIR/system-metrics-${TIMESTAMP}.csv" &
    
    MONITORING_PID=$!
    
    # Monitor Docker containers if available
    if command -v docker &> /dev/null; then
        docker stats --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.NetIO}}\t{{.BlockIO}}" --no-stream > "$LOAD_TEST_RESULTS_DIR/docker-stats-${TIMESTAMP}.txt" &
        DOCKER_MONITORING_PID=$!
    fi
}

# Stop system monitoring
stop_monitoring() {
    if [[ "$ENABLE_MONITORING" != "true" ]]; then
        return 0
    fi
    
    log "Stopping system monitoring..."
    
    if [[ -n "${MONITORING_PID:-}" ]]; then
        kill $MONITORING_PID 2>/dev/null || true
    fi
    
    if [[ -n "${DOCKER_MONITORING_PID:-}" ]]; then
        kill $DOCKER_MONITORING_PID 2>/dev/null || true
    fi
}

# Create test scenarios
create_test_scenarios() {
    log "Creating test scenarios..."
    
    # Create URL list for testing
    cat > "$LOAD_TEST_RESULTS_DIR/test-urls.txt" << EOF
$TARGET_URL/health
EOF
    
    # Add scenario-specific URLs
    case "$SCENARIO" in
        basic)
            # Basic health check only
            ;;
        full)
            # Add more comprehensive endpoints
            cat >> "$LOAD_TEST_RESULTS_DIR/test-urls.txt" << EOF
$TARGET_URL/tools
$TARGET_URL/resources
EOF
            ;;
        stress|spike)
            # Add all available endpoints for stress testing
            cat >> "$LOAD_TEST_RESULTS_DIR/test-urls.txt" << EOF
$TARGET_URL/tools
$TARGET_URL/resources
EOF
            ;;
    esac
    
    # Create test data for POST requests
    cat > "$LOAD_TEST_RESULTS_DIR/test-data.json" << EOF
{
  "name": "list_projects",
  "arguments": {
    "page": 1,
    "page_size": 10
  }
}
EOF
}

# Run load test with Apache Bench (ab)
run_ab_test() {
    if ! command -v ab &> /dev/null; then
        return 1
    fi
    
    info "Running load test with Apache Bench..."
    
    local total_requests=$((CONCURRENT_USERS * DURATION / 10))  # Rough calculation
    
    ab -n $total_requests -c $CONCURRENT_USERS -g "$LOAD_TEST_RESULTS_DIR/ab-gnuplot-${TIMESTAMP}.dat" "$TARGET_URL/health" > "$LOAD_TEST_RESULTS_DIR/ab-results-${TIMESTAMP}.txt" 2>&1
    
    return 0
}

# Run load test with wrk
run_wrk_test() {
    if ! command -v wrk &> /dev/null; then
        return 1
    fi
    
    info "Running load test with wrk..."
    
    wrk -t$CONCURRENT_USERS -c$CONCURRENT_USERS -d${DURATION}s --latency "$TARGET_URL/health" > "$LOAD_TEST_RESULTS_DIR/wrk-results-${TIMESTAMP}.txt" 2>&1
    
    return 0
}

# Run load test with hey
run_hey_test() {
    if ! command -v hey &> /dev/null; then
        return 1
    fi
    
    info "Running load test with hey..."
    
    local total_requests=$((CONCURRENT_USERS * DURATION))
    
    hey -n $total_requests -c $CONCURRENT_USERS -o csv "$TARGET_URL/health" > "$LOAD_TEST_RESULTS_DIR/hey-results-${TIMESTAMP}.csv" 2>&1
    
    return 0
}

# Run custom Python load test
run_python_load_test() {
    info "Running custom Python load test..."
    
    cat > "$LOAD_TEST_RESULTS_DIR/load_test.py" << 'EOF'
import asyncio
import aiohttp
import time
import json
import sys
from datetime import datetime

class LoadTester:
    def __init__(self, target_url, concurrent_users, duration, ramp_up):
        self.target_url = target_url
        self.concurrent_users = concurrent_users
        self.duration = duration
        self.ramp_up = ramp_up
        self.results = []
        self.start_time = None
        
    async def make_request(self, session, url):
        start_time = time.time()
        try:
            async with session.get(url) as response:
                await response.text()
                end_time = time.time()
                return {
                    'timestamp': datetime.now().isoformat(),
                    'url': url,
                    'status_code': response.status,
                    'response_time': end_time - start_time,
                    'success': response.status == 200
                }
        except Exception as e:
            end_time = time.time()
            return {
                'timestamp': datetime.now().isoformat(),
                'url': url,
                'status_code': 0,
                'response_time': end_time - start_time,
                'success': False,
                'error': str(e)
            }
    
    async def worker(self, session, worker_id):
        urls = [f"{self.target_url}/health"]
        
        # Ramp up delay
        await asyncio.sleep(worker_id * (self.ramp_up / self.concurrent_users))
        
        end_time = self.start_time + self.duration
        
        while time.time() < end_time:
            for url in urls:
                if time.time() >= end_time:
                    break
                    
                result = await self.make_request(session, url)
                self.results.append(result)
                
                # Small delay between requests
                await asyncio.sleep(0.1)
    
    async def run_test(self):
        self.start_time = time.time()
        
        connector = aiohttp.TCPConnector(limit=self.concurrent_users * 2)
        timeout = aiohttp.ClientTimeout(total=30)
        
        async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
            tasks = []
            for i in range(self.concurrent_users):
                task = asyncio.create_task(self.worker(session, i))
                tasks.append(task)
            
            await asyncio.gather(*tasks)
        
        return self.analyze_results()
    
    def analyze_results(self):
        if not self.results:
            return {}
        
        successful_requests = [r for r in self.results if r['success']]
        failed_requests = [r for r in self.results if not r['success']]
        
        response_times = [r['response_time'] for r in successful_requests]
        
        if response_times:
            response_times.sort()
            total_requests = len(self.results)
            successful_count = len(successful_requests)
            failed_count = len(failed_requests)
            
            analysis = {
                'total_requests': total_requests,
                'successful_requests': successful_count,
                'failed_requests': failed_count,
                'success_rate': (successful_count / total_requests) * 100,
                'avg_response_time': sum(response_times) / len(response_times),
                'min_response_time': min(response_times),
                'max_response_time': max(response_times),
                'p50_response_time': response_times[int(len(response_times) * 0.5)],
                'p95_response_time': response_times[int(len(response_times) * 0.95)],
                'p99_response_time': response_times[int(len(response_times) * 0.99)],
                'requests_per_second': total_requests / self.duration
            }
        else:
            analysis = {
                'total_requests': len(self.results),
                'successful_requests': 0,
                'failed_requests': len(failed_requests),
                'success_rate': 0,
                'error': 'No successful requests'
            }
        
        return analysis

async def main():
    if len(sys.argv) != 5:
        print("Usage: python load_test.py <target_url> <concurrent_users> <duration> <ramp_up>")
        sys.exit(1)
    
    target_url = sys.argv[1]
    concurrent_users = int(sys.argv[2])
    duration = int(sys.argv[3])
    ramp_up = int(sys.argv[4])
    
    tester = LoadTester(target_url, concurrent_users, duration, ramp_up)
    results = await tester.run_test()
    
    print(json.dumps(results, indent=2))
    
    # Save detailed results
    with open('detailed_results.json', 'w') as f:
        json.dump(tester.results, f, indent=2)

if __name__ == "__main__":
    asyncio.run(main())
EOF
    
    cd "$LOAD_TEST_RESULTS_DIR"
    python load_test.py "$TARGET_URL" "$CONCURRENT_USERS" "$DURATION" "$RAMP_UP" > "python-load-test-${TIMESTAMP}.json" 2>&1
    cd "$PROJECT_ROOT"
}

# Run scenario-specific tests
run_scenario_tests() {
    log "Running $SCENARIO scenario tests..."
    
    case "$SCENARIO" in
        basic)
            # Basic load test
            run_load_tests
            ;;
        full)
            # Comprehensive test with multiple endpoints
            run_load_tests
            run_endpoint_specific_tests
            ;;
        stress)
            # Stress test with high load
            local original_users=$CONCURRENT_USERS
            local original_duration=$DURATION
            
            CONCURRENT_USERS=$((original_users * 3))
            DURATION=$((original_duration * 2))
            
            info "Running stress test with $CONCURRENT_USERS users for ${DURATION}s"
            run_load_tests
            
            CONCURRENT_USERS=$original_users
            DURATION=$original_duration
            ;;
        spike)
            # Spike test with sudden load increases
            info "Running spike test..."
            
            # Normal load
            run_load_tests
            
            # Sudden spike
            local spike_users=$((CONCURRENT_USERS * 5))
            local spike_duration=30
            
            info "Running spike with $spike_users users for ${spike_duration}s"
            CONCURRENT_USERS=$spike_users
            DURATION=$spike_duration
            run_load_tests
            ;;
    esac
}

# Run load tests with available tools
run_load_tests() {
    local test_run=false
    
    # Try different load testing tools
    if run_hey_test; then
        test_run=true
    elif run_wrk_test; then
        test_run=true
    elif run_ab_test; then
        test_run=true
    fi
    
    # Always run Python load test as fallback
    run_python_load_test
    test_run=true
    
    if [[ "$test_run" != "true" ]]; then
        error "No load testing tools available"
    fi
}

# Run endpoint-specific tests
run_endpoint_specific_tests() {
    info "Running endpoint-specific tests..."
    
    # Test different MCP endpoints if available
    local endpoints=(
        "/health"
        "/tools"
        "/resources"
    )
    
    for endpoint in "${endpoints[@]}"; do
        local url="${TARGET_URL}${endpoint}"
        
        # Check if endpoint exists
        if curl -f "$url" &> /dev/null; then
            info "Testing endpoint: $endpoint"
            
            # Run a quick test on this endpoint
            if command -v hey &> /dev/null; then
                hey -n 100 -c 10 "$url" > "$LOAD_TEST_RESULTS_DIR/endpoint-${endpoint//\//-}-${TIMESTAMP}.txt" 2>&1
            fi
        fi
    done
}

# Analyze results
analyze_results() {
    log "Analyzing load test results..."
    
    local analysis_file="$LOAD_TEST_RESULTS_DIR/analysis-${TIMESTAMP}.txt"
    
    {
        echo "Load Test Analysis Report"
        echo "========================"
        echo "Generated: $(date)"
        echo "Scenario: $SCENARIO"
        echo "Concurrent Users: $CONCURRENT_USERS"
        echo "Duration: ${DURATION}s"
        echo "Target URL: $TARGET_URL"
        echo ""
        
        # Analyze Python test results if available
        if [[ -f "$LOAD_TEST_RESULTS_DIR/python-load-test-${TIMESTAMP}.json" ]]; then
            echo "Python Load Test Results:"
            echo "------------------------"
            cat "$LOAD_TEST_RESULTS_DIR/python-load-test-${TIMESTAMP}.json"
            echo ""
        fi
        
        # Analyze hey results if available
        if [[ -f "$LOAD_TEST_RESULTS_DIR/hey-results-${TIMESTAMP}.csv" ]]; then
            echo "Hey Load Test Summary:"
            echo "---------------------"
            tail -10 "$LOAD_TEST_RESULTS_DIR/hey-results-${TIMESTAMP}.csv"
            echo ""
        fi
        
        # Analyze wrk results if available
        if [[ -f "$LOAD_TEST_RESULTS_DIR/wrk-results-${TIMESTAMP}.txt" ]]; then
            echo "Wrk Load Test Results:"
            echo "---------------------"
            cat "$LOAD_TEST_RESULTS_DIR/wrk-results-${TIMESTAMP}.txt"
            echo ""
        fi
        
        # System resource analysis
        if [[ -f "$LOAD_TEST_RESULTS_DIR/system-metrics-${TIMESTAMP}.csv" ]]; then
            echo "System Resource Usage:"
            echo "---------------------"
            echo "Average CPU usage during test:"
            awk -F',' 'NR>1 {sum+=$2; count++} END {if(count>0) print sum/count "%"}' "$LOAD_TEST_RESULTS_DIR/system-metrics-${TIMESTAMP}.csv"
            
            echo "Average Memory usage during test:"
            awk -F',' 'NR>1 {sum+=$3; count++} END {if(count>0) print sum/count "%"}' "$LOAD_TEST_RESULTS_DIR/system-metrics-${TIMESTAMP}.csv"
            echo ""
        fi
        
    } > "$analysis_file"
    
    info "Analysis completed: $analysis_file"
}

# Generate performance report
generate_performance_report() {
    log "Generating performance report..."
    
    local report_file="$LOAD_TEST_RESULTS_DIR/performance-report-${TIMESTAMP}.html"
    
    cat > "$report_file" << EOF
<!DOCTYPE html>
<html>
<head>
    <title>SonarQube MCP Load Test Report</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; line-height: 1.6; }
        .header { background-color: #f8f9fa; padding: 20px; border-radius: 5px; margin-bottom: 20px; }
        .section { margin: 20px 0; padding: 15px; border: 1px solid #ddd; border-radius: 5px; }
        .metric { display: inline-block; margin: 10px; padding: 10px; background-color: #e9ecef; border-radius: 3px; }
        .success { background-color: #d4edda; border-color: #c3e6cb; }
        .warning { background-color: #fff3cd; border-color: #ffeaa7; }
        .error { background-color: #f8d7da; border-color: #f5c6cb; }
        pre { background-color: #f8f9fa; padding: 10px; border-radius: 3px; overflow-x: auto; }
        .chart { width: 100%; height: 300px; background-color: #f8f9fa; border: 1px solid #ddd; margin: 10px 0; }
    </style>
</head>
<body>
    <div class="header">
        <h1>🚀 SonarQube MCP Load Test Report</h1>
        <p><strong>Generated:</strong> $(date)</p>
        <p><strong>Test ID:</strong> ${TIMESTAMP}</p>
        <p><strong>Scenario:</strong> $SCENARIO</p>
        <p><strong>Target:</strong> $TARGET_URL</p>
    </div>
    
    <div class="section">
        <h2>📊 Test Configuration</h2>
        <div class="metric">Concurrent Users: $CONCURRENT_USERS</div>
        <div class="metric">Duration: ${DURATION}s</div>
        <div class="metric">Ramp-up: ${RAMP_UP}s</div>
        <div class="metric">Scenario: $SCENARIO</div>
    </div>
EOF
    
    # Add results from Python test if available
    if [[ -f "$LOAD_TEST_RESULTS_DIR/python-load-test-${TIMESTAMP}.json" ]]; then
        echo "    <div class=\"section success\">" >> "$report_file"
        echo "        <h2>📈 Performance Metrics</h2>" >> "$report_file"
        
        # Extract key metrics from JSON
        local total_requests=$(jq -r '.total_requests // "N/A"' "$LOAD_TEST_RESULTS_DIR/python-load-test-${TIMESTAMP}.json")
        local success_rate=$(jq -r '.success_rate // "N/A"' "$LOAD_TEST_RESULTS_DIR/python-load-test-${TIMESTAMP}.json")
        local avg_response_time=$(jq -r '.avg_response_time // "N/A"' "$LOAD_TEST_RESULTS_DIR/python-load-test-${TIMESTAMP}.json")
        local requests_per_second=$(jq -r '.requests_per_second // "N/A"' "$LOAD_TEST_RESULTS_DIR/python-load-test-${TIMESTAMP}.json")
        
        echo "        <div class=\"metric\">Total Requests: $total_requests</div>" >> "$report_file"
        echo "        <div class=\"metric\">Success Rate: ${success_rate}%</div>" >> "$report_file"
        echo "        <div class=\"metric\">Avg Response Time: ${avg_response_time}s</div>" >> "$report_file"
        echo "        <div class=\"metric\">Requests/sec: $requests_per_second</div>" >> "$report_file"
        echo "    </div>" >> "$report_file"
    fi
    
    # Add analysis section
    if [[ -f "$LOAD_TEST_RESULTS_DIR/analysis-${TIMESTAMP}.txt" ]]; then
        echo "    <div class=\"section\">" >> "$report_file"
        echo "        <h2>📋 Detailed Analysis</h2>" >> "$report_file"
        echo "        <pre>$(cat "$LOAD_TEST_RESULTS_DIR/analysis-${TIMESTAMP}.txt")</pre>" >> "$report_file"
        echo "    </div>" >> "$report_file"
    fi
    
    echo "</body></html>" >> "$report_file"
    
    info "Performance report generated: $report_file"
}

# Cleanup function
cleanup() {
    log "Cleaning up load test environment..."
    
    stop_monitoring
    
    # Clean up temporary files
    rm -f "$LOAD_TEST_RESULTS_DIR/load_test.py" 2>/dev/null || true
}

# Main function
main() {
    log "Starting SonarQube MCP load testing..."
    
    trap cleanup EXIT
    
    parse_args "$@"
    setup_load_test_environment
    create_test_scenarios
    
    start_monitoring
    
    run_scenario_tests
    
    stop_monitoring
    
    analyze_results
    generate_performance_report
    
    log "Load testing completed! 🎯"
    
    info "Load Test Results:"
    echo "  - Results directory: $LOAD_TEST_RESULTS_DIR"
    echo "  - Performance report: $LOAD_TEST_RESULTS_DIR/performance-report-${TIMESTAMP}.html"
    echo "  - Analysis: $LOAD_TEST_RESULTS_DIR/analysis-${TIMESTAMP}.txt"
    
    # Check if performance meets expectations
    if [[ -f "$LOAD_TEST_RESULTS_DIR/python-load-test-${TIMESTAMP}.json" ]]; then
        local success_rate=$(jq -r '.success_rate // 0' "$LOAD_TEST_RESULTS_DIR/python-load-test-${TIMESTAMP}.json")
        local avg_response_time=$(jq -r '.avg_response_time // 999' "$LOAD_TEST_RESULTS_DIR/python-load-test-${TIMESTAMP}.json")
        
        if (( $(echo "$success_rate < 95" | bc -l) )); then
            warn "Success rate ${success_rate}% is below 95% threshold"
        fi
        
        if (( $(echo "$avg_response_time > 2" | bc -l) )); then
            warn "Average response time ${avg_response_time}s is above 2s threshold"
        fi
        
        if (( $(echo "$success_rate >= 95" | bc -l) )) && (( $(echo "$avg_response_time <= 2" | bc -l) )); then
            log "Performance meets expectations! ✅"
        fi
    fi
}

# Run main function
main "$@"