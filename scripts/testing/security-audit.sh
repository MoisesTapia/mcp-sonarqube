#!/bin/bash

# Security Audit Script for SonarQube MCP
# This script performs comprehensive security testing and vulnerability assessment

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
AUDIT_RESULTS_DIR="$PROJECT_ROOT/security-audit-results"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

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
    echo "  -c, --code           Run code security analysis"
    echo "  -d, --dependencies   Check dependency vulnerabilities"
    echo "  -i, --infrastructure Check infrastructure security"
    echo "  -n, --network        Run network security tests"
    echo "  -a, --all           Run all security checks (default)"
    echo "  -f, --fix           Attempt to fix issues automatically"
    echo "  -r, --report        Generate detailed security report"
    echo "  -h, --help          Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 --all --report"
    echo "  $0 --code --dependencies"
    echo "  $0 --fix"
    exit 1
}

# Parse command line arguments
parse_args() {
    RUN_CODE=false
    RUN_DEPENDENCIES=false
    RUN_INFRASTRUCTURE=false
    RUN_NETWORK=false
    RUN_ALL=true
    AUTO_FIX=false
    GENERATE_REPORT=false
    
    while [[ $# -gt 0 ]]; do
        case $1 in
            -c|--code)
                RUN_CODE=true
                RUN_ALL=false
                shift
                ;;
            -d|--dependencies)
                RUN_DEPENDENCIES=true
                RUN_ALL=false
                shift
                ;;
            -i|--infrastructure)
                RUN_INFRASTRUCTURE=true
                RUN_ALL=false
                shift
                ;;
            -n|--network)
                RUN_NETWORK=true
                RUN_ALL=false
                shift
                ;;
            -a|--all)
                RUN_ALL=true
                shift
                ;;
            -f|--fix)
                AUTO_FIX=true
                shift
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
    
    # Set individual flags if running all checks
    if [[ "$RUN_ALL" == "true" ]]; then
        RUN_CODE=true
        RUN_DEPENDENCIES=true
        RUN_INFRASTRUCTURE=true
        RUN_NETWORK=true
        GENERATE_REPORT=true
    fi
}

# Setup audit environment
setup_audit_environment() {
    log "Setting up security audit environment..."
    
    # Create audit results directory
    mkdir -p "$AUDIT_RESULTS_DIR"
    
    # Change to project root
    cd "$PROJECT_ROOT"
    
    # Install security tools if not present
    if ! command -v bandit &> /dev/null; then
        pip install bandit
    fi
    
    if ! command -v safety &> /dev/null; then
        pip install safety
    fi
    
    if ! command -v semgrep &> /dev/null; then
        pip install semgrep
    fi
    
    log "Security audit environment setup completed"
}

# Run code security analysis
run_code_security_analysis() {
    if [[ "$RUN_CODE" != "true" ]]; then
        return 0
    fi
    
    log "Running code security analysis..."
    
    # Bandit - Python security linter
    info "Running Bandit security analysis..."
    bandit -r src/ -f json -o "$AUDIT_RESULTS_DIR/bandit-report.json" || true
    bandit -r src/ -f txt -o "$AUDIT_RESULTS_DIR/bandit-report.txt" || true
    
    # Semgrep - Static analysis for security
    info "Running Semgrep security analysis..."
    semgrep --config=auto src/ --json --output="$AUDIT_RESULTS_DIR/semgrep-report.json" || true
    semgrep --config=auto src/ --output="$AUDIT_RESULTS_DIR/semgrep-report.txt" || true
    
    # Custom security checks
    info "Running custom security checks..."
    
    # Check for hardcoded secrets
    grep -r -n -i "password\|secret\|key\|token" src/ --include="*.py" > "$AUDIT_RESULTS_DIR/potential-secrets.txt" || true
    
    # Check for SQL injection patterns
    grep -r -n "execute.*%" src/ --include="*.py" > "$AUDIT_RESULTS_DIR/sql-injection-patterns.txt" || true
    
    # Check for unsafe eval/exec usage
    grep -r -n -E "(eval|exec)\(" src/ --include="*.py" > "$AUDIT_RESULTS_DIR/unsafe-eval-exec.txt" || true
    
    # Check for insecure random usage
    grep -r -n "random\." src/ --include="*.py" > "$AUDIT_RESULTS_DIR/insecure-random.txt" || true
    
    # Check for debug mode in production
    grep -r -n -i "debug.*=.*true" src/ --include="*.py" > "$AUDIT_RESULTS_DIR/debug-mode.txt" || true
    
    log "Code security analysis completed"
}

# Check dependency vulnerabilities
check_dependency_vulnerabilities() {
    if [[ "$RUN_DEPENDENCIES" != "true" ]]; then
        return 0
    fi
    
    log "Checking dependency vulnerabilities..."
    
    # Safety - Check for known security vulnerabilities
    info "Running Safety vulnerability check..."
    safety check --json --output "$AUDIT_RESULTS_DIR/safety-report.json" || true
    safety check --output "$AUDIT_RESULTS_DIR/safety-report.txt" || true
    
    # pip-audit - Alternative vulnerability scanner
    if command -v pip-audit &> /dev/null; then
        info "Running pip-audit vulnerability check..."
        pip-audit --format=json --output="$AUDIT_RESULTS_DIR/pip-audit-report.json" || true
        pip-audit --output="$AUDIT_RESULTS_DIR/pip-audit-report.txt" || true
    fi
    
    # Check for outdated packages
    info "Checking for outdated packages..."
    pip list --outdated --format=json > "$AUDIT_RESULTS_DIR/outdated-packages.json" || true
    
    # Generate dependency tree
    info "Generating dependency tree..."
    pip freeze > "$AUDIT_RESULTS_DIR/current-dependencies.txt"
    
    log "Dependency vulnerability check completed"
}

# Check infrastructure security
check_infrastructure_security() {
    if [[ "$RUN_INFRASTRUCTURE" != "true" ]]; then
        return 0
    fi
    
    log "Checking infrastructure security..."
    
    # Docker security analysis
    if command -v docker &> /dev/null; then
        info "Running Docker security analysis..."
        
        # Check Dockerfile security
        if command -v hadolint &> /dev/null; then
            find . -name "Dockerfile*" -exec hadolint {} \; > "$AUDIT_RESULTS_DIR/dockerfile-security.txt" 2>&1 || true
        fi
        
        # Check for running containers with security issues
        docker ps --format "table {{.Names}}\t{{.Image}}\t{{.Status}}" > "$AUDIT_RESULTS_DIR/running-containers.txt" || true
        
        # Scan Docker images for vulnerabilities
        if command -v trivy &> /dev/null; then
            info "Scanning Docker images with Trivy..."
            for image in $(docker images --format "{{.Repository}}:{{.Tag}}" | grep -E "(mcp-server|streamlit)"); do
                trivy image --format json --output "$AUDIT_RESULTS_DIR/trivy-${image//[\/:]/-}.json" "$image" || true
            done
        fi
    fi
    
    # Kubernetes security analysis
    if command -v kubectl &> /dev/null && kubectl cluster-info &> /dev/null; then
        info "Running Kubernetes security analysis..."
        
        # Check for security policies
        kubectl get networkpolicies --all-namespaces -o json > "$AUDIT_RESULTS_DIR/network-policies.json" 2>/dev/null || true
        kubectl get podsecuritypolicies -o json > "$AUDIT_RESULTS_DIR/pod-security-policies.json" 2>/dev/null || true
        
        # Check for privileged containers
        kubectl get pods --all-namespaces -o json | jq '.items[] | select(.spec.containers[]?.securityContext?.privileged == true)' > "$AUDIT_RESULTS_DIR/privileged-pods.json" || true
        
        # Check for containers running as root
        kubectl get pods --all-namespaces -o json | jq '.items[] | select(.spec.containers[]?.securityContext?.runAsUser == 0 or (.spec.containers[]?.securityContext?.runAsUser == null))' > "$AUDIT_RESULTS_DIR/root-containers.json" || true
    fi
    
    # Check file permissions
    info "Checking file permissions..."
    find . -type f -perm /o+w -not -path "./venv/*" -not -path "./.git/*" > "$AUDIT_RESULTS_DIR/world-writable-files.txt" || true
    find . -type f -name "*.py" -perm /o+x > "$AUDIT_RESULTS_DIR/executable-python-files.txt" || true
    
    log "Infrastructure security check completed"
}

# Run network security tests
run_network_security_tests() {
    if [[ "$RUN_NETWORK" != "true" ]]; then
        return 0
    fi
    
    log "Running network security tests..."
    
    # Check if services are running
    local services_running=false
    if curl -f http://localhost:8000/health &> /dev/null; then
        services_running=true
    fi
    
    if [[ "$services_running" == "false" ]]; then
        warn "Services not running, starting them for network tests..."
        docker-compose -f docker/compose/base/docker-compose.yml up -d
        
        # Wait for services to be ready
        local max_wait=60
        local wait_time=0
        
        while ! curl -f http://localhost:8000/health &> /dev/null; do
            if [[ $wait_time -ge $max_wait ]]; then
                error "Services failed to start within ${max_wait} seconds"
            fi
            sleep 5
            wait_time=$((wait_time + 5))
        done
    fi
    
    # Test SSL/TLS configuration
    info "Testing SSL/TLS configuration..."
    
    # Check for HTTP services that should be HTTPS
    if curl -f http://localhost:8000/health &> /dev/null; then
        echo "HTTP service detected on port 8000" >> "$AUDIT_RESULTS_DIR/http-services.txt"
    fi
    
    if curl -f http://localhost:8501/_stcore/health &> /dev/null; then
        echo "HTTP service detected on port 8501" >> "$AUDIT_RESULTS_DIR/http-services.txt"
    fi
    
    # Test for common security headers
    info "Testing security headers..."
    
    curl -I http://localhost:8000/health 2>/dev/null | grep -i "x-frame-options\|x-content-type-options\|x-xss-protection\|strict-transport-security\|content-security-policy" > "$AUDIT_RESULTS_DIR/security-headers-8000.txt" || true
    
    curl -I http://localhost:8501/_stcore/health 2>/dev/null | grep -i "x-frame-options\|x-content-type-options\|x-xss-protection\|strict-transport-security\|content-security-policy" > "$AUDIT_RESULTS_DIR/security-headers-8501.txt" || true
    
    # Port scanning
    info "Checking open ports..."
    netstat -tulpn | grep LISTEN > "$AUDIT_RESULTS_DIR/open-ports.txt" || true
    
    # Test for default credentials
    info "Testing for default credentials..."
    
    # Test common default credentials (this is safe as we're testing our own service)
    echo "Testing default credentials..." > "$AUDIT_RESULTS_DIR/credential-tests.txt"
    
    # Test weak authentication
    curl -f -u admin:admin http://localhost:8000/health &> /dev/null && echo "Weak credentials accepted" >> "$AUDIT_RESULTS_DIR/credential-tests.txt" || true
    curl -f -u test:test http://localhost:8000/health &> /dev/null && echo "Test credentials accepted" >> "$AUDIT_RESULTS_DIR/credential-tests.txt" || true
    
    log "Network security tests completed"
}

# Attempt to fix security issues automatically
auto_fix_issues() {
    if [[ "$AUTO_FIX" != "true" ]]; then
        return 0
    fi
    
    log "Attempting to fix security issues automatically..."
    
    # Fix file permissions
    info "Fixing file permissions..."
    find . -type f -name "*.py" -perm /o+w -not -path "./venv/*" -not -path "./.git/*" -exec chmod o-w {} \; || true
    find . -type f -name "*.py" -perm /o+x -exec chmod -x {} \; || true
    
    # Update vulnerable dependencies
    info "Updating dependencies..."
    pip install --upgrade pip || true
    
    # Fix common security issues in code
    info "Applying code security fixes..."
    
    # Replace insecure random with secure random
    find src/ -name "*.py" -exec sed -i 's/import random/import secrets as random/g' {} \; || true
    
    # Add security headers to configuration files
    if [[ -f "src/streamlit_app/.streamlit/config.toml" ]]; then
        if ! grep -q "enableXsrfProtection" "src/streamlit_app/.streamlit/config.toml"; then
            echo "enableXsrfProtection = true" >> "src/streamlit_app/.streamlit/config.toml"
        fi
    fi
    
    log "Automatic fixes applied"
}

# Generate security report
generate_security_report() {
    if [[ "$GENERATE_REPORT" != "true" ]]; then
        return 0
    fi
    
    log "Generating security report..."
    
    local report_file="$AUDIT_RESULTS_DIR/security-report-${TIMESTAMP}.html"
    
    cat > "$report_file" << EOF
<!DOCTYPE html>
<html>
<head>
    <title>SonarQube MCP Security Audit Report</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; line-height: 1.6; }
        .header { background-color: #f8f9fa; padding: 20px; border-radius: 5px; margin-bottom: 20px; }
        .section { margin: 20px 0; padding: 15px; border: 1px solid #ddd; border-radius: 5px; }
        .critical { background-color: #f8d7da; border-color: #f5c6cb; }
        .high { background-color: #fff3cd; border-color: #ffeaa7; }
        .medium { background-color: #d1ecf1; border-color: #bee5eb; }
        .low { background-color: #d4edda; border-color: #c3e6cb; }
        .info { background-color: #e2e3e5; border-color: #d6d8db; }
        .metric { display: inline-block; margin: 10px; padding: 10px; background-color: #e9ecef; border-radius: 3px; }
        pre { background-color: #f8f9fa; padding: 10px; border-radius: 3px; overflow-x: auto; }
        .toc { background-color: #f8f9fa; padding: 15px; border-radius: 5px; margin-bottom: 20px; }
        .toc ul { list-style-type: none; padding-left: 0; }
        .toc li { margin: 5px 0; }
        .toc a { text-decoration: none; color: #007bff; }
    </style>
</head>
<body>
    <div class="header">
        <h1>🔒 SonarQube MCP Security Audit Report</h1>
        <p><strong>Generated:</strong> $(date)</p>
        <p><strong>Audit ID:</strong> ${TIMESTAMP}</p>
        <p><strong>System:</strong> $(uname -a)</p>
    </div>
    
    <div class="toc">
        <h2>Table of Contents</h2>
        <ul>
            <li><a href="#executive-summary">Executive Summary</a></li>
            <li><a href="#code-security">Code Security Analysis</a></li>
            <li><a href="#dependency-vulnerabilities">Dependency Vulnerabilities</a></li>
            <li><a href="#infrastructure-security">Infrastructure Security</a></li>
            <li><a href="#network-security">Network Security</a></li>
            <li><a href="#recommendations">Recommendations</a></li>
        </ul>
    </div>
EOF
    
    # Executive Summary
    echo "    <div id=\"executive-summary\" class=\"section info\">" >> "$report_file"
    echo "        <h2>📊 Executive Summary</h2>" >> "$report_file"
    
    local total_issues=0
    local critical_issues=0
    local high_issues=0
    local medium_issues=0
    local low_issues=0
    
    # Count issues from various reports
    if [[ -f "$AUDIT_RESULTS_DIR/bandit-report.json" ]]; then
        local bandit_issues=$(jq '.results | length' "$AUDIT_RESULTS_DIR/bandit-report.json" 2>/dev/null || echo "0")
        total_issues=$((total_issues + bandit_issues))
    fi
    
    if [[ -f "$AUDIT_RESULTS_DIR/safety-report.json" ]]; then
        local safety_issues=$(jq '.vulnerabilities | length' "$AUDIT_RESULTS_DIR/safety-report.json" 2>/dev/null || echo "0")
        total_issues=$((total_issues + safety_issues))
    fi
    
    echo "        <div class=\"metric\">Total Issues: $total_issues</div>" >> "$report_file"
    echo "        <div class=\"metric\">Critical: $critical_issues</div>" >> "$report_file"
    echo "        <div class=\"metric\">High: $high_issues</div>" >> "$report_file"
    echo "        <div class=\"metric\">Medium: $medium_issues</div>" >> "$report_file"
    echo "        <div class=\"metric\">Low: $low_issues</div>" >> "$report_file"
    echo "    </div>" >> "$report_file"
    
    # Code Security Analysis
    if [[ "$RUN_CODE" == "true" ]]; then
        echo "    <div id=\"code-security\" class=\"section\">" >> "$report_file"
        echo "        <h2>🔍 Code Security Analysis</h2>" >> "$report_file"
        
        if [[ -f "$AUDIT_RESULTS_DIR/bandit-report.txt" ]]; then
            echo "        <h3>Bandit Security Analysis</h3>" >> "$report_file"
            echo "        <pre>$(head -50 "$AUDIT_RESULTS_DIR/bandit-report.txt")</pre>" >> "$report_file"
        fi
        
        if [[ -f "$AUDIT_RESULTS_DIR/semgrep-report.txt" ]]; then
            echo "        <h3>Semgrep Security Analysis</h3>" >> "$report_file"
            echo "        <pre>$(head -50 "$AUDIT_RESULTS_DIR/semgrep-report.txt")</pre>" >> "$report_file"
        fi
        
        echo "    </div>" >> "$report_file"
    fi
    
    # Dependency Vulnerabilities
    if [[ "$RUN_DEPENDENCIES" == "true" ]]; then
        echo "    <div id=\"dependency-vulnerabilities\" class=\"section\">" >> "$report_file"
        echo "        <h2>📦 Dependency Vulnerabilities</h2>" >> "$report_file"
        
        if [[ -f "$AUDIT_RESULTS_DIR/safety-report.txt" ]]; then
            echo "        <h3>Safety Vulnerability Report</h3>" >> "$report_file"
            echo "        <pre>$(cat "$AUDIT_RESULTS_DIR/safety-report.txt")</pre>" >> "$report_file"
        fi
        
        if [[ -f "$AUDIT_RESULTS_DIR/outdated-packages.json" ]]; then
            local outdated_count=$(jq '. | length' "$AUDIT_RESULTS_DIR/outdated-packages.json" 2>/dev/null || echo "0")
            echo "        <h3>Outdated Packages</h3>" >> "$report_file"
            echo "        <p>Found $outdated_count outdated packages</p>" >> "$report_file"
        fi
        
        echo "    </div>" >> "$report_file"
    fi
    
    # Infrastructure Security
    if [[ "$RUN_INFRASTRUCTURE" == "true" ]]; then
        echo "    <div id=\"infrastructure-security\" class=\"section\">" >> "$report_file"
        echo "        <h2>🏗️ Infrastructure Security</h2>" >> "$report_file"
        
        if [[ -f "$AUDIT_RESULTS_DIR/dockerfile-security.txt" ]]; then
            echo "        <h3>Dockerfile Security Issues</h3>" >> "$report_file"
            echo "        <pre>$(cat "$AUDIT_RESULTS_DIR/dockerfile-security.txt")</pre>" >> "$report_file"
        fi
        
        if [[ -f "$AUDIT_RESULTS_DIR/world-writable-files.txt" ]]; then
            local writable_files=$(wc -l < "$AUDIT_RESULTS_DIR/world-writable-files.txt")
            echo "        <h3>File Permissions</h3>" >> "$report_file"
            echo "        <p>Found $writable_files world-writable files</p>" >> "$report_file"
        fi
        
        echo "    </div>" >> "$report_file"
    fi
    
    # Network Security
    if [[ "$RUN_NETWORK" == "true" ]]; then
        echo "    <div id=\"network-security\" class=\"section\">" >> "$report_file"
        echo "        <h2>🌐 Network Security</h2>" >> "$report_file"
        
        if [[ -f "$AUDIT_RESULTS_DIR/open-ports.txt" ]]; then
            echo "        <h3>Open Ports</h3>" >> "$report_file"
            echo "        <pre>$(cat "$AUDIT_RESULTS_DIR/open-ports.txt")</pre>" >> "$report_file"
        fi
        
        if [[ -f "$AUDIT_RESULTS_DIR/security-headers-8000.txt" ]]; then
            echo "        <h3>Security Headers (Port 8000)</h3>" >> "$report_file"
            echo "        <pre>$(cat "$AUDIT_RESULTS_DIR/security-headers-8000.txt")</pre>" >> "$report_file"
        fi
        
        echo "    </div>" >> "$report_file"
    fi
    
    # Recommendations
    echo "    <div id=\"recommendations\" class=\"section high\">" >> "$report_file"
    echo "        <h2>💡 Recommendations</h2>" >> "$report_file"
    echo "        <ul>" >> "$report_file"
    echo "            <li>Regularly update dependencies to patch known vulnerabilities</li>" >> "$report_file"
    echo "            <li>Implement proper security headers in production</li>" >> "$report_file"
    echo "            <li>Use HTTPS for all communications in production</li>" >> "$report_file"
    echo "            <li>Implement proper authentication and authorization</li>" >> "$report_file"
    echo "            <li>Regular security audits and penetration testing</li>" >> "$report_file"
    echo "            <li>Monitor security logs and implement alerting</li>" >> "$report_file"
    echo "            <li>Follow principle of least privilege</li>" >> "$report_file"
    echo "            <li>Implement proper secrets management</li>" >> "$report_file"
    echo "        </ul>" >> "$report_file"
    echo "    </div>" >> "$report_file"
    
    echo "</body></html>" >> "$report_file"
    
    info "Security report generated: $report_file"
}

# Main function
main() {
    log "Starting SonarQube MCP security audit..."
    
    parse_args "$@"
    setup_audit_environment
    
    # Run security checks
    run_code_security_analysis
    check_dependency_vulnerabilities
    check_infrastructure_security
    run_network_security_tests
    
    auto_fix_issues
    generate_security_report
    
    log "Security audit completed! 🔒"
    
    info "Security Audit Results:"
    echo "  - Audit results directory: $AUDIT_RESULTS_DIR"
    
    if [[ "$GENERATE_REPORT" == "true" ]]; then
        echo "  - Security report: $AUDIT_RESULTS_DIR/security-report-${TIMESTAMP}.html"
    fi
    
    # Summary of critical findings
    local critical_findings=0
    
    if [[ -f "$AUDIT_RESULTS_DIR/bandit-report.json" ]]; then
        local bandit_high=$(jq '[.results[] | select(.issue_severity == "HIGH")] | length' "$AUDIT_RESULTS_DIR/bandit-report.json" 2>/dev/null || echo "0")
        critical_findings=$((critical_findings + bandit_high))
    fi
    
    if [[ -f "$AUDIT_RESULTS_DIR/safety-report.json" ]]; then
        local safety_vulns=$(jq '.vulnerabilities | length' "$AUDIT_RESULTS_DIR/safety-report.json" 2>/dev/null || echo "0")
        critical_findings=$((critical_findings + safety_vulns))
    fi
    
    if [[ $critical_findings -gt 0 ]]; then
        warn "Found $critical_findings critical security issues that require attention"
        exit 1
    else
        log "No critical security issues found"
    fi
}

# Run main function
main "$@"