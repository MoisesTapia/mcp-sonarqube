#!/bin/bash

# Comprehensive Test Suite Runner
# This script runs all tests and quality checks for the SonarQube MCP system

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
TEST_RESULTS_DIR="$PROJECT_ROOT/test-results"
COVERAGE_THRESHOLD=80
PERFORMANCE_THRESHOLD=2000  # milliseconds

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
    echo "  -u, --unit           Run unit tests only"
    echo "  -i, --integration    Run integration tests only"
    echo "  -e, --e2e           Run end-to-end tests only"
    echo "  -p, --performance   Run performance tests only"
    echo "  -s, --security      Run security tests only"
    echo "  -l, --lint          Run linting only"
    echo "  -c, --coverage      Generate coverage report"
    echo "  -a, --all           Run all tests (default)"
    echo "  -f, --fast          Skip slow tests"
    echo "  -v, --verbose       Verbose output"
    echo "  -h, --help          Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 --unit --coverage"
    echo "  $0 --all --verbose"
    echo "  $0 --fast"
    exit 1
}

# Parse command line arguments
parse_args() {
    RUN_UNIT=false
    RUN_INTEGRATION=false
    RUN_E2E=false
    RUN_PERFORMANCE=false
    RUN_SECURITY=false
    RUN_LINT=false
    RUN_COVERAGE=false
    RUN_ALL=true
    FAST_MODE=false
    VERBOSE=false
    
    while [[ $# -gt 0 ]]; do
        case $1 in
            -u|--unit)
                RUN_UNIT=true
                RUN_ALL=false
                shift
                ;;
            -i|--integration)
                RUN_INTEGRATION=true
                RUN_ALL=false
                shift
                ;;
            -e|--e2e)
                RUN_E2E=true
                RUN_ALL=false
                shift
                ;;
            -p|--performance)
                RUN_PERFORMANCE=true
                RUN_ALL=false
                shift
                ;;
            -s|--security)
                RUN_SECURITY=true
                RUN_ALL=false
                shift
                ;;
            -l|--lint)
                RUN_LINT=true
                RUN_ALL=false
                shift
                ;;
            -c|--coverage)
                RUN_COVERAGE=true
                shift
                ;;
            -a|--all)
                RUN_ALL=true
                shift
                ;;
            -f|--fast)
                FAST_MODE=true
                shift
                ;;
            -v|--verbose)
                VERBOSE=true
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
    
    # Set individual flags if running all tests
    if [[ "$RUN_ALL" == "true" ]]; then
        RUN_UNIT=true
        RUN_INTEGRATION=true
        RUN_E2E=true
        RUN_PERFORMANCE=true
        RUN_SECURITY=true
        RUN_LINT=true
        RUN_COVERAGE=true
    fi
}

# Setup test environment
setup_test_environment() {
    log "Setting up test environment..."
    
    # Create test results directory
    mkdir -p "$TEST_RESULTS_DIR"
    
    # Change to project root
    cd "$PROJECT_ROOT"
    
    # Check if virtual environment exists
    if [[ ! -d "venv" ]]; then
        log "Creating virtual environment..."
        python -m venv venv
    fi
    
    # Activate virtual environment
    source venv/bin/activate
    
    # Install dependencies
    log "Installing dependencies..."
    pip install -q --upgrade pip
    pip install -q -r requirements.txt
    pip install -q -r requirements-dev.txt
    
    # Set test environment variables
    export PYTHONPATH="$PROJECT_ROOT/src"
    export TESTING=true
    export LOG_LEVEL=WARNING
    
    log "Test environment setup completed"
}

# Check prerequisites
check_prerequisites() {
    log "Checking prerequisites..."
    
    # Check Python version
    python_version=$(python --version 2>&1 | cut -d' ' -f2)
    if [[ $(echo "$python_version" | cut -d'.' -f1-2) < "3.11" ]]; then
        error "Python 3.11+ required, found $python_version"
    fi
    
    # Check required tools
    local required_tools=("pytest" "black" "ruff" "mypy" "bandit")
    for tool in "${required_tools[@]}"; do
        if ! command -v "$tool" &> /dev/null; then
            error "$tool is not installed"
        fi
    done
    
    log "Prerequisites check passed"
}

# Run linting and code quality checks
run_linting() {
    if [[ "$RUN_LINT" != "true" ]]; then
        return 0
    fi
    
    log "Running linting and code quality checks..."
    
    local lint_failed=false
    
    # Black formatting check
    info "Checking code formatting with Black..."
    if ! black --check src/ tests/ --diff; then
        error "Code formatting issues found. Run 'black src/ tests/' to fix."
        lint_failed=true
    fi
    
    # Ruff linting
    info "Running Ruff linter..."
    if ! ruff check src/ tests/ --output-format=json > "$TEST_RESULTS_DIR/ruff-report.json"; then
        error "Ruff linting issues found"
        lint_failed=true
    fi
    
    # MyPy type checking
    info "Running MyPy type checking..."
    if ! mypy src/ --json-report "$TEST_RESULTS_DIR/mypy-report"; then
        warn "MyPy type checking issues found"
        # Don't fail on type checking issues, just warn
    fi
    
    # Import sorting check
    info "Checking import sorting..."
    if ! isort --check-only src/ tests/; then
        warn "Import sorting issues found. Run 'isort src/ tests/' to fix."
    fi
    
    if [[ "$lint_failed" == "true" ]]; then
        error "Linting checks failed"
    fi
    
    log "Linting checks completed successfully"
}

# Run unit tests
run_unit_tests() {
    if [[ "$RUN_UNIT" != "true" ]]; then
        return 0
    fi
    
    log "Running unit tests..."
    
    local pytest_args=("tests/unit/")
    
    if [[ "$VERBOSE" == "true" ]]; then
        pytest_args+=("-v")
    fi
    
    if [[ "$RUN_COVERAGE" == "true" ]]; then
        pytest_args+=("--cov=src" "--cov-report=html:$TEST_RESULTS_DIR/coverage-html" "--cov-report=xml:$TEST_RESULTS_DIR/coverage.xml" "--cov-report=term-missing")
    fi
    
    if [[ "$FAST_MODE" == "true" ]]; then
        pytest_args+=("-m" "not slow")
    fi
    
    pytest_args+=("--junit-xml=$TEST_RESULTS_DIR/unit-test-results.xml")
    
    if ! pytest "${pytest_args[@]}"; then
        error "Unit tests failed"
    fi
    
    # Check coverage threshold
    if [[ "$RUN_COVERAGE" == "true" ]]; then
        local coverage_percent=$(python -c "
import xml.etree.ElementTree as ET
tree = ET.parse('$TEST_RESULTS_DIR/coverage.xml')
root = tree.getroot()
coverage = float(root.attrib['line-rate']) * 100
print(f'{coverage:.1f}')
")
        
        info "Code coverage: ${coverage_percent}%"
        
        if (( $(echo "$coverage_percent < $COVERAGE_THRESHOLD" | bc -l) )); then
            error "Coverage ${coverage_percent}% is below threshold ${COVERAGE_THRESHOLD}%"
        fi
    fi
    
    log "Unit tests completed successfully"
}

# Run integration tests
run_integration_tests() {
    if [[ "$RUN_INTEGRATION" != "true" ]]; then
        return 0
    fi
    
    log "Running integration tests..."
    
    # Check if test SonarQube instance is available
    if [[ -z "${TEST_SONARQUBE_URL:-}" ]] || [[ -z "${TEST_SONARQUBE_TOKEN:-}" ]]; then
        warn "Test SonarQube credentials not configured, skipping integration tests"
        return 0
    fi
    
    local pytest_args=("tests/integration/")
    
    if [[ "$VERBOSE" == "true" ]]; then
        pytest_args+=("-v")
    fi
    
    if [[ "$FAST_MODE" == "true" ]]; then
        pytest_args+=("-m" "not slow")
    fi
    
    pytest_args+=("--junit-xml=$TEST_RESULTS_DIR/integration-test-results.xml")
    
    # Set integration test environment
    export SONARQUBE_URL="$TEST_SONARQUBE_URL"
    export SONARQUBE_TOKEN="$TEST_SONARQUBE_TOKEN"
    
    if ! pytest "${pytest_args[@]}"; then
        error "Integration tests failed"
    fi
    
    log "Integration tests completed successfully"
}

# Run end-to-end tests
run_e2e_tests() {
    if [[ "$RUN_E2E" != "true" ]]; then
        return 0
    fi
    
    if [[ "$FAST_MODE" == "true" ]]; then
        warn "Skipping E2E tests in fast mode"
        return 0
    fi
    
    log "Running end-to-end tests..."
    
    # Start test services if not already running
    if ! curl -f http://localhost:8000/health &> /dev/null; then
        info "Starting test services..."
        docker-compose -f docker/compose/base/docker-compose.yml up -d
        
        # Wait for services to be ready
        local max_wait=120
        local wait_time=0
        
        while ! curl -f http://localhost:8000/health &> /dev/null; do
            if [[ $wait_time -ge $max_wait ]]; then
                error "Services failed to start within ${max_wait} seconds"
            fi
            sleep 5
            wait_time=$((wait_time + 5))
        done
        
        info "Services are ready"
    fi
    
    local pytest_args=("tests/e2e/")
    
    if [[ "$VERBOSE" == "true" ]]; then
        pytest_args+=("-v")
    fi
    
    pytest_args+=("--junit-xml=$TEST_RESULTS_DIR/e2e-test-results.xml")
    
    if ! pytest "${pytest_args[@]}"; then
        error "End-to-end tests failed"
    fi
    
    log "End-to-end tests completed successfully"
}

# Run performance tests
run_performance_tests() {
    if [[ "$RUN_PERFORMANCE" != "true" ]]; then
        return 0
    fi
    
    if [[ "$FAST_MODE" == "true" ]]; then
        warn "Skipping performance tests in fast mode"
        return 0
    fi
    
    log "Running performance tests..."
    
    # Ensure services are running
    if ! curl -f http://localhost:8000/health &> /dev/null; then
        warn "MCP server not running, skipping performance tests"
        return 0
    fi
    
    # Run performance benchmarks
    info "Running API performance benchmarks..."
    
    # Simple performance test using curl and time
    local start_time=$(date +%s%3N)
    
    for i in {1..10}; do
        if ! curl -f -s http://localhost:8000/health > /dev/null; then
            error "Performance test failed on request $i"
        fi
    done
    
    local end_time=$(date +%s%3N)
    local avg_response_time=$(( (end_time - start_time) / 10 ))
    
    info "Average response time: ${avg_response_time}ms"
    
    if [[ $avg_response_time -gt $PERFORMANCE_THRESHOLD ]]; then
        error "Average response time ${avg_response_time}ms exceeds threshold ${PERFORMANCE_THRESHOLD}ms"
    fi
    
    # Run pytest performance tests
    local pytest_args=("tests/performance/")
    
    if [[ "$VERBOSE" == "true" ]]; then
        pytest_args+=("-v")
    fi
    
    pytest_args+=("--junit-xml=$TEST_RESULTS_DIR/performance-test-results.xml")
    
    if ! pytest "${pytest_args[@]}"; then
        error "Performance tests failed"
    fi
    
    log "Performance tests completed successfully"
}

# Run security tests
run_security_tests() {
    if [[ "$RUN_SECURITY" != "true" ]]; then
        return 0
    fi
    
    log "Running security tests..."
    
    # Bandit security linting
    info "Running Bandit security analysis..."
    if ! bandit -r src/ -f json -o "$TEST_RESULTS_DIR/bandit-report.json"; then
        warn "Bandit found potential security issues"
        # Don't fail on security warnings, just report them
    fi
    
    # Safety check for known vulnerabilities
    info "Checking for known vulnerabilities..."
    if ! safety check --json --output "$TEST_RESULTS_DIR/safety-report.json"; then
        warn "Safety found known vulnerabilities in dependencies"
        # Don't fail on vulnerability warnings, just report them
    fi
    
    # Run security-focused tests
    local pytest_args=("tests/security/")
    
    if [[ "$VERBOSE" == "true" ]]; then
        pytest_args+=("-v")
    fi
    
    pytest_args+=("--junit-xml=$TEST_RESULTS_DIR/security-test-results.xml")
    
    if [[ -d "tests/security" ]]; then
        if ! pytest "${pytest_args[@]}"; then
            error "Security tests failed"
        fi
    else
        info "No security tests directory found, skipping pytest security tests"
    fi
    
    log "Security tests completed successfully"
}

# Generate test report
generate_test_report() {
    log "Generating test report..."
    
    local report_file="$TEST_RESULTS_DIR/test-report.html"
    
    cat > "$report_file" << EOF
<!DOCTYPE html>
<html>
<head>
    <title>SonarQube MCP Test Report</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        .header { background-color: #f0f0f0; padding: 20px; border-radius: 5px; }
        .section { margin: 20px 0; padding: 15px; border: 1px solid #ddd; border-radius: 5px; }
        .success { background-color: #d4edda; border-color: #c3e6cb; }
        .warning { background-color: #fff3cd; border-color: #ffeaa7; }
        .error { background-color: #f8d7da; border-color: #f5c6cb; }
        .metric { display: inline-block; margin: 10px; padding: 10px; background-color: #e9ecef; border-radius: 3px; }
    </style>
</head>
<body>
    <div class="header">
        <h1>SonarQube MCP Test Report</h1>
        <p>Generated on: $(date)</p>
        <p>Test Environment: $(uname -a)</p>
    </div>
EOF
    
    # Add test results sections
    if [[ -f "$TEST_RESULTS_DIR/unit-test-results.xml" ]]; then
        local unit_tests=$(grep -o 'tests="[0-9]*"' "$TEST_RESULTS_DIR/unit-test-results.xml" | cut -d'"' -f2)
        local unit_failures=$(grep -o 'failures="[0-9]*"' "$TEST_RESULTS_DIR/unit-test-results.xml" | cut -d'"' -f2)
        
        echo "    <div class=\"section success\">" >> "$report_file"
        echo "        <h2>Unit Tests</h2>" >> "$report_file"
        echo "        <div class=\"metric\">Tests: $unit_tests</div>" >> "$report_file"
        echo "        <div class=\"metric\">Failures: $unit_failures</div>" >> "$report_file"
        echo "    </div>" >> "$report_file"
    fi
    
    if [[ -f "$TEST_RESULTS_DIR/coverage.xml" ]]; then
        local coverage=$(python -c "
import xml.etree.ElementTree as ET
tree = ET.parse('$TEST_RESULTS_DIR/coverage.xml')
root = tree.getroot()
coverage = float(root.attrib['line-rate']) * 100
print(f'{coverage:.1f}')
")
        
        echo "    <div class=\"section success\">" >> "$report_file"
        echo "        <h2>Code Coverage</h2>" >> "$report_file"
        echo "        <div class=\"metric\">Coverage: ${coverage}%</div>" >> "$report_file"
        echo "    </div>" >> "$report_file"
    fi
    
    echo "</body></html>" >> "$report_file"
    
    info "Test report generated: $report_file"
}

# Cleanup function
cleanup() {
    log "Cleaning up test environment..."
    
    # Stop test services if we started them
    if [[ "${STARTED_SERVICES:-false}" == "true" ]]; then
        docker-compose -f docker/compose/base/docker-compose.yml down
    fi
    
    # Deactivate virtual environment
    if [[ -n "${VIRTUAL_ENV:-}" ]]; then
        deactivate
    fi
}

# Main function
main() {
    log "Starting SonarQube MCP test suite..."
    
    trap cleanup EXIT
    trap 'error "Test suite failed due to an error"' ERR
    
    parse_args "$@"
    setup_test_environment
    check_prerequisites
    
    # Run test suites
    run_linting
    run_unit_tests
    run_integration_tests
    run_e2e_tests
    run_performance_tests
    run_security_tests
    
    generate_test_report
    
    log "All tests completed successfully! 🎉"
    
    info "Test Results Summary:"
    echo "  - Test results directory: $TEST_RESULTS_DIR"
    echo "  - Test report: $TEST_RESULTS_DIR/test-report.html"
    
    if [[ "$RUN_COVERAGE" == "true" ]]; then
        echo "  - Coverage report: $TEST_RESULTS_DIR/coverage-html/index.html"
    fi
}

# Run main function
main "$@"