#!/bin/bash

# Simple Load Testing Script for SonarQube MCP
# This script performs basic load testing using curl and built-in tools

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
RESULTS_DIR="$PROJECT_ROOT/load-test-results"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# Default test parameters
DEFAULT_CONCURRENT_USERS=5
DEFAULT_DURATION=30
DEFAULT_TARGET_URL="http://localhost:8001"

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
    echo "  -t, --target URL        Target URL (default: $DEFAULT_TARGET_URL)"
    echo "  -e, --endpoint PATH     Specific endpoint to test (default: /health)"
    echo "  -r, --report            Generate HTML report"
    echo "  -h, --help              Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 --users 10 --duration 60"
    echo "  $0 --endpoint /tools --report"
    exit 1
}

# Parse command line arguments
parse_args() {
    CONCURRENT_USERS=$DEFAULT_CONCURRENT_USERS
    DURATION=$DEFAULT_DURATION
    TARGET_URL=$DEFAULT_TARGET_URL
    ENDPOINT="/health"
    GENERATE_REPORT=false
    
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
            -t|--target)
                TARGET_URL="$2"
                shift 2
                ;;
            -e|--endpoint)
                ENDPOINT="$2"
                shift 2
                ;;
            -r|--report)
                GENERATE_REPORT=true
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

# Setup test environment
setup_test_environment() {
    log "Setting up load test environment..."
    
    # Create results directory
    mkdir -p "$RESULTS_DIR"
    
    # Check if target service is available
    local test_url="${TARGET_URL}${ENDPOINT}"
    
    if ! curl -f -s "$test_url" > /dev/null 2>&1; then
        warn "Target service not available at $test_url"
        
        # Try to start services if we're testing localhost
        if [[ "$TARGET_URL" == "http://localhost:"* ]]; then
            info "Attempting to start local services..."
            
            cd "$PROJECT_ROOT"
            
            if [[ -f "docker/compose/base/docker-compose.yml" ]]; then
                docker compose -f docker/compose/base/docker-compose.yml \
                              -f docker/compose/environments/development.yml \
                              --env-file docker/environments/.env.development \
                              up -d
                
                # Wait for services to be ready
                local max_wait=60
                local wait_time=0
                
                while ! curl -f -s "$test_url" > /dev/null 2>&1; do
                    if [[ $wait_time -ge $max_wait ]]; then
                        error "Services failed to start within ${max_wait} seconds"
                    fi
                    sleep 5
                    wait_time=$((wait_time + 5))
                    info "Waiting for services... (${wait_time}s)"
                done
                
                log "Services are ready"
            else
                error "Cannot start services - Docker Compose files not found"
            fi
        else
            error "Target service is not available"
        fi
    else
        log "Target service is available"
    fi
}

# Run simple load test using curl
run_curl_load_test() {
    log "Running load test with curl..."
    
    local test_url="${TARGET_URL}${ENDPOINT}"
    local results_file="$RESULTS_DIR/curl-results-${TIMESTAMP}.csv"
    
    # Create CSV header
    echo "timestamp,response_time,status_code,success" > "$results_file"
    
    # Function to run a single test
    run_single_test() {
        local user_id=$1
        local end_time=$2
        local user_results_file="$RESULTS_DIR/user-${user_id}-${TIMESTAMP}.csv"
        
        while [[ $(date +%s) -lt $end_time ]]; do
            local start_time=$(date +%s%3N)
            local timestamp=$(date -Iseconds)
            
            # Make request and capture response
            local status_code=$(curl -s -o /dev/null -w "%{http_code}" "$test_url" 2>/dev/null || echo "000")
            local end_request_time=$(date +%s%3N)
            local response_time=$((end_request_time - start_time))
            
            # Determine success
            local success="false"
            if [[ "$status_code" == "200" ]]; then
                success="true"
            fi
            
            # Log result
            echo "$timestamp,$response_time,$status_code,$success" >> "$user_results_file"
            
            # Small delay between requests
            sleep 0.1
        done
    }
    
    # Start concurrent users
    local end_time=$(($(date +%s) + DURATION))
    local pids=()
    
    info "Starting $CONCURRENT_USERS concurrent users for ${DURATION} seconds..."
    
    for ((i=1; i<=CONCURRENT_USERS; i++)); do
        run_single_test "$i" "$end_time" &
        pids+=($!)
    done
    
    # Wait for all background processes to complete
    for pid in "${pids[@]}"; do
        wait "$pid"
    done
    
    # Combine results from all users
    for ((i=1; i<=CONCURRENT_USERS; i++)); do
        local user_file="$RESULTS_DIR/user-${i}-${TIMESTAMP}.csv"
        if [[ -f "$user_file" ]]; then
            cat "$user_file" >> "$results_file"
            rm "$user_file"
        fi
    done
    
    log "Load test completed"
}

# Analyze test results
analyze_results() {
    log "Analyzing test results..."
    
    local results_file="$RESULTS_DIR/curl-results-${TIMESTAMP}.csv"
    local analysis_file="$RESULTS_DIR/analysis-${TIMESTAMP}.txt"
    
    if [[ ! -f "$results_file" ]]; then
        error "Results file not found: $results_file"
    fi
    
    # Use awk to analyze the CSV data
    awk -F',' '
    BEGIN {
        total_requests = 0
        successful_requests = 0
        failed_requests = 0
        total_response_time = 0
        min_response_time = 999999
        max_response_time = 0
    }
    NR > 1 {  # Skip header
        total_requests++
        response_time = $2
        success = $4
        
        total_response_time += response_time
        
        if (response_time < min_response_time) min_response_time = response_time
        if (response_time > max_response_time) max_response_time = response_time
        
        if (success == "true") {
            successful_requests++
        } else {
            failed_requests++
        }
        
        # Store response times for percentile calculation
        response_times[NR-1] = response_time
    }
    END {
        if (total_requests > 0) {
            avg_response_time = total_response_time / total_requests
            success_rate = (successful_requests / total_requests) * 100
            requests_per_second = total_requests / '$DURATION'
            
            print "Load Test Analysis Report"
            print "========================"
            print "Test Duration: '$DURATION' seconds"
            print "Concurrent Users: '$CONCURRENT_USERS'"
            print "Target URL: '$TARGET_URL$ENDPOINT'"
            print ""
            print "Results Summary:"
            print "  Total Requests: " total_requests
            print "  Successful Requests: " successful_requests
            print "  Failed Requests: " failed_requests
            print "  Success Rate: " success_rate "%"
            print "  Requests per Second: " requests_per_second
            print ""
            print "Response Time Statistics (ms):"
            print "  Average: " avg_response_time
            print "  Minimum: " min_response_time
            print "  Maximum: " max_response_time
            print ""
            
            # Simple performance assessment
            if (success_rate >= 95 && avg_response_time <= 1000) {
                print "Performance Assessment: GOOD ✅"
            } else if (success_rate >= 90 && avg_response_time <= 2000) {
                print "Performance Assessment: ACCEPTABLE ⚠️"
            } else {
                print "Performance Assessment: NEEDS IMPROVEMENT ❌"
            }
        } else {
            print "No valid test data found"
        }
    }' "$results_file" > "$analysis_file"
    
    # Display analysis
    cat "$analysis_file"
    
    info "Analysis saved to: $analysis_file"
}

# Generate HTML report
generate_html_report() {
    if [[ "$GENERATE_REPORT" != "true" ]]; then
        return 0
    fi
    
    log "Generating HTML report..."
    
    local report_file="$RESULTS_DIR/load-test-report-${TIMESTAMP}.html"
    local results_file="$RESULTS_DIR/curl-results-${TIMESTAMP}.csv"
    local analysis_file="$RESULTS_DIR/analysis-${TIMESTAMP}.txt"
    
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
        table { width: 100%; border-collapse: collapse; margin: 10px 0; }
        th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
        th { background-color: #f8f9fa; }
    </style>
</head>
<body>
    <div class="header">
        <h1>🚀 SonarQube MCP Load Test Report</h1>
        <p><strong>Generated:</strong> $(date)</p>
        <p><strong>Test ID:</strong> ${TIMESTAMP}</p>
    </div>
    
    <div class="section">
        <h2>📊 Test Configuration</h2>
        <div class="metric">Concurrent Users: $CONCURRENT_USERS</div>
        <div class="metric">Duration: ${DURATION}s</div>
        <div class="metric">Target: ${TARGET_URL}${ENDPOINT}</div>
    </div>
EOF
    
    # Add analysis results
    if [[ -f "$analysis_file" ]]; then
        echo "    <div class=\"section success\">" >> "$report_file"
        echo "        <h2>📈 Test Results</h2>" >> "$report_file"
        echo "        <pre>$(cat "$analysis_file")</pre>" >> "$report_file"
        echo "    </div>" >> "$report_file"
    fi
    
    # Add raw data table (first 100 rows)
    if [[ -f "$results_file" ]]; then
        echo "    <div class=\"section\">" >> "$report_file"
        echo "        <h2>📋 Raw Data (First 100 Requests)</h2>" >> "$report_file"
        echo "        <table>" >> "$report_file"
        
        # Add table header
        echo "            <tr><th>Timestamp</th><th>Response Time (ms)</th><th>Status Code</th><th>Success</th></tr>" >> "$report_file"
        
        # Add data rows (limit to first 100)
        tail -n +2 "$results_file" | head -100 | while IFS=',' read -r timestamp response_time status_code success; do
            local row_class=""
            if [[ "$success" == "false" ]]; then
                row_class=" style=\"background-color: #f8d7da;\""
            fi
            echo "            <tr$row_class><td>$timestamp</td><td>$response_time</td><td>$status_code</td><td>$success</td></tr>" >> "$report_file"
        done
        
        echo "        </table>" >> "$report_file"
        echo "    </div>" >> "$report_file"
    fi
    
    # Add recommendations
    echo "    <div class=\"section warning\">" >> "$report_file"
    echo "        <h2>💡 Recommendations</h2>" >> "$report_file"
    echo "        <ul>" >> "$report_file"
    echo "            <li>Monitor response times under different load conditions</li>" >> "$report_file"
    echo "            <li>Test with realistic data and user scenarios</li>" >> "$report_file"
    echo "            <li>Consider implementing caching for frequently accessed endpoints</li>" >> "$report_file"
    echo "            <li>Set up monitoring and alerting for production environments</li>" >> "$report_file"
    echo "            <li>Run regular performance tests as part of CI/CD pipeline</li>" >> "$report_file"
    echo "        </ul>" >> "$report_file"
    echo "    </div>" >> "$report_file"
    
    echo "</body></html>" >> "$report_file"
    
    info "HTML report generated: $report_file"
}

# Cleanup function
cleanup() {
    # Clean up temporary files
    rm -f "$RESULTS_DIR"/user-*-"$TIMESTAMP".csv 2>/dev/null || true
}

# Main function
main() {
    log "Starting simple load test for SonarQube MCP..."
    
    trap cleanup EXIT
    
    parse_args "$@"
    setup_test_environment
    
    run_curl_load_test
    analyze_results
    generate_html_report
    
    log "Load test completed! 🎯"
    
    info "Results Summary:"
    echo "  - Results directory: $RESULTS_DIR"
    echo "  - Raw data: $RESULTS_DIR/curl-results-${TIMESTAMP}.csv"
    echo "  - Analysis: $RESULTS_DIR/analysis-${TIMESTAMP}.txt"
    
    if [[ "$GENERATE_REPORT" == "true" ]]; then
        echo "  - HTML report: $RESULTS_DIR/load-test-report-${TIMESTAMP}.html"
    fi
}

# Run main function
main "$@"