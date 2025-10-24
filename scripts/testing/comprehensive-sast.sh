#!/bin/bash

# Comprehensive SAST (Static Application Security Testing) Script
# This script runs all security analysis tools locally

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
RESULTS_DIR="$PROJECT_ROOT/sast-results"
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
    echo "  -a, --all           Run all SAST tools (default)"
    echo "  -s, --safety        Run Safety dependency scan only"
    echo "  -b, --bandit        Run Bandit security linting only"
    echo "  -g, --semgrep       Run Semgrep SAST only"
    echo "  -d, --dependencies  Run dependency analysis only"
    echo "  -r, --report        Generate comprehensive report"
    echo "  -h, --help          Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 --all --report"
    echo "  $0 --safety --bandit"
    exit 1
}

# Parse command line arguments
parse_args() {
    RUN_ALL=true
    RUN_SAFETY=false
    RUN_BANDIT=false
    RUN_SEMGREP=false
    RUN_DEPENDENCIES=false
    GENERATE_REPORT=false
    
    while [[ $# -gt 0 ]]; do
        case $1 in
            -a|--all)
                RUN_ALL=true
                shift
                ;;
            -s|--safety)
                RUN_SAFETY=true
                RUN_ALL=false
                shift
                ;;
            -b|--bandit)
                RUN_BANDIT=true
                RUN_ALL=false
                shift
                ;;
            -g|--semgrep)
                RUN_SEMGREP=true
                RUN_ALL=false
                shift
                ;;
            -d|--dependencies)
                RUN_DEPENDENCIES=true
                RUN_ALL=false
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
    
    # Set individual flags if running all
    if [[ "$RUN_ALL" == "true" ]]; then
        RUN_SAFETY=true
        RUN_BANDIT=true
        RUN_SEMGREP=true
        RUN_DEPENDENCIES=true
        GENERATE_REPORT=true
    fi
}

# Setup SAST environment
setup_sast_environment() {
    log "Setting up SAST environment..."
    
    # Create results directory
    mkdir -p "$RESULTS_DIR"
    
    # Change to project root
    cd "$PROJECT_ROOT"
    
    # Check if virtual environment exists and activate it
    if [[ -d "venv" ]]; then
        source venv/bin/activate
    elif [[ -d ".venv" ]]; then
        source .venv/bin/activate
    fi
    
    # Install SAST tools
    log "Installing SAST tools..."
    pip install --upgrade pip
    pip install safety bandit semgrep pip-audit pipdeptree
    
    log "SAST environment setup completed"
}

# Run Safety dependency vulnerability scan
run_safety_scan() {
    if [[ "$RUN_SAFETY" != "true" ]]; then
        return 0
    fi
    
    log "Running Safety dependency vulnerability scan..."
    
    # Install project dependencies first
    if [[ -f "requirements.txt" ]]; then
        pip install -r requirements.txt
    fi
    
    # Run Safety with different configurations
    info "Running Safety with JSON output..."
    safety check --json --output "$RESULTS_DIR/safety-report-${TIMESTAMP}.json" || true
    
    info "Running Safety with text output..."
    safety check --output "$RESULTS_DIR/safety-report-${TIMESTAMP}.txt" || true
    
    info "Running Safety with full report..."
    safety check --full-report --output "$RESULTS_DIR/safety-full-report-${TIMESTAMP}.txt" || true
    
    # Run with policy file if it exists
    if [[ -f ".safety-policy.yml" ]]; then
        info "Running Safety with policy file..."
        safety check --policy-file .safety-policy.yml --output "$RESULTS_DIR/safety-policy-report-${TIMESTAMP}.txt" || true
    fi
    
    log "Safety scan completed"
}

# Run Bandit security linting
run_bandit_scan() {
    if [[ "$RUN_BANDIT" != "true" ]]; then
        return 0
    fi
    
    log "Running Bandit security linting..."
    
    # Run Bandit with different output formats
    info "Running Bandit with JSON output..."
    bandit -r src/ -f json -o "$RESULTS_DIR/bandit-report-${TIMESTAMP}.json" || true
    
    info "Running Bandit with text output..."
    bandit -r src/ -f txt -o "$RESULTS_DIR/bandit-report-${TIMESTAMP}.txt" || true
    
    info "Running Bandit with HTML output..."
    bandit -r src/ -f html -o "$RESULTS_DIR/bandit-report-${TIMESTAMP}.html" || true
    
    # Run with configuration file if it exists
    if [[ -f ".bandit" ]]; then
        info "Running Bandit with configuration file..."
        bandit -r src/ -f json -o "$RESULTS_DIR/bandit-config-report-${TIMESTAMP}.json" || true
    fi
    
    log "Bandit scan completed"
}

# Run Semgrep SAST
run_semgrep_scan() {
    if [[ "$RUN_SEMGREP" != "true" ]]; then
        return 0
    fi
    
    log "Running Semgrep static analysis..."
    
    # Run Semgrep with different rule sets
    info "Running Semgrep with auto configuration..."
    semgrep --config=auto src/ --json --output="$RESULTS_DIR/semgrep-auto-${TIMESTAMP}.json" || true
    semgrep --config=auto src/ --output="$RESULTS_DIR/semgrep-auto-${TIMESTAMP}.txt" || true
    
    info "Running Semgrep with security rules..."
    semgrep --config=p/security-audit src/ --json --output="$RESULTS_DIR/semgrep-security-${TIMESTAMP}.json" || true
    
    info "Running Semgrep with Python-specific rules..."
    semgrep --config=p/python src/ --json --output="$RESULTS_DIR/semgrep-python-${TIMESTAMP}.json" || true
    
    info "Running Semgrep with OWASP Top 10 rules..."
    semgrep --config=p/owasp-top-ten src/ --json --output="$RESULTS_DIR/semgrep-owasp-${TIMESTAMP}.json" || true
    
    info "Running Semgrep with secrets detection..."
    semgrep --config=p/secrets src/ --json --output="$RESULTS_DIR/semgrep-secrets-${TIMESTAMP}.json" || true
    
    log "Semgrep scan completed"
}

# Run dependency analysis
run_dependency_analysis() {
    if [[ "$RUN_DEPENDENCIES" != "true" ]]; then
        return 0
    fi
    
    log "Running dependency analysis..."
    
    # Generate dependency tree
    info "Generating dependency tree..."
    pipdeptree --json-tree > "$RESULTS_DIR/dependency-tree-${TIMESTAMP}.json" || true
    pipdeptree > "$RESULTS_DIR/dependency-tree-${TIMESTAMP}.txt" || true
    
    # Run pip-audit
    info "Running pip-audit vulnerability scan..."
    pip-audit --format=json --output="$RESULTS_DIR/pip-audit-${TIMESTAMP}.json" || true
    pip-audit --output="$RESULTS_DIR/pip-audit-${TIMESTAMP}.txt" || true
    
    # Check for outdated packages
    info "Checking for outdated packages..."
    pip list --outdated --format=json > "$RESULTS_DIR/outdated-packages-${TIMESTAMP}.json" || true
    pip list --outdated > "$RESULTS_DIR/outdated-packages-${TIMESTAMP}.txt" || true
    
    # Generate requirements analysis
    info "Analyzing requirements files..."
    if [[ -f "requirements.txt" ]]; then
        safety check --file requirements.txt --json --output "$RESULTS_DIR/requirements-safety-${TIMESTAMP}.json" || true
    fi
    
    log "Dependency analysis completed"
}

# Generate comprehensive report
generate_comprehensive_report() {
    if [[ "$GENERATE_REPORT" != "true" ]]; then
        return 0
    fi
    
    log "Generating comprehensive SAST report..."
    
    local report_file="$RESULTS_DIR/comprehensive-sast-report-${TIMESTAMP}.md"
    
    cat > "$report_file" << EOF
# 🔒 Comprehensive SAST Report

**Generated:** $(date)
**Project:** SonarQube MCP
**Scan ID:** ${TIMESTAMP}
**Tools Used:** Safety, Bandit, Semgrep, pip-audit

## 📊 Executive Summary

This report contains the results of comprehensive Static Application Security Testing (SAST) analysis.

### 🎯 Scan Coverage
- **Dependency Vulnerabilities:** Safety, pip-audit
- **Security Linting:** Bandit
- **Static Analysis:** Semgrep (multiple rule sets)
- **Dependency Analysis:** pipdeptree, outdated packages

## 🔍 Vulnerability Analysis

### Safety (Dependency Vulnerabilities)
EOF
    
    # Analyze Safety results
    if [[ -f "$RESULTS_DIR/safety-report-${TIMESTAMP}.json" ]]; then
        local safety_vulns=$(jq '.vulnerabilities | length' "$RESULTS_DIR/safety-report-${TIMESTAMP}.json" 2>/dev/null || echo "0")
        echo "- **Vulnerabilities Found:** $safety_vulns" >> "$report_file"
        
        if [[ "$safety_vulns" -gt "0" ]]; then
            echo "- **Status:** ⚠️ Action Required" >> "$report_file"
            echo "" >> "$report_file"
            echo "#### Critical Vulnerabilities:" >> "$report_file"
            jq -r '.vulnerabilities[] | "- **\(.package_name)** \(.installed_version): \(.vulnerability_id) - \(.advisory)"' "$RESULTS_DIR/safety-report-${TIMESTAMP}.json" 2>/dev/null | head -10 >> "$report_file" || true
        else
            echo "- **Status:** ✅ No vulnerabilities found" >> "$report_file"
        fi
    else
        echo "- **Status:** ❌ Scan failed or no report generated" >> "$report_file"
    fi
    
    echo "" >> "$report_file"
    echo "### Bandit (Security Linting)" >> "$report_file"
    
    # Analyze Bandit results
    if [[ -f "$RESULTS_DIR/bandit-report-${TIMESTAMP}.json" ]]; then
        local bandit_issues=$(jq '.results | length' "$RESULTS_DIR/bandit-report-${TIMESTAMP}.json" 2>/dev/null || echo "0")
        echo "- **Security Issues:** $bandit_issues" >> "$report_file"
        
        if [[ "$bandit_issues" -gt "0" ]]; then
            local high_severity=$(jq '[.results[] | select(.issue_severity == "HIGH")] | length' "$RESULTS_DIR/bandit-report-${TIMESTAMP}.json" 2>/dev/null || echo "0")
            local medium_severity=$(jq '[.results[] | select(.issue_severity == "MEDIUM")] | length' "$RESULTS_DIR/bandit-report-${TIMESTAMP}.json" 2>/dev/null || echo "0")
            local low_severity=$(jq '[.results[] | select(.issue_severity == "LOW")] | length' "$RESULTS_DIR/bandit-report-${TIMESTAMP}.json" 2>/dev/null || echo "0")
            
            echo "- **High Severity:** $high_severity" >> "$report_file"
            echo "- **Medium Severity:** $medium_severity" >> "$report_file"
            echo "- **Low Severity:** $low_severity" >> "$report_file"
            
            if [[ "$high_severity" -gt "0" ]]; then
                echo "- **Status:** 🚨 Critical - Immediate Action Required" >> "$report_file"
            elif [[ "$medium_severity" -gt "0" ]]; then
                echo "- **Status:** ⚠️ Review Required" >> "$report_file"
            else
                echo "- **Status:** ℹ️ Low Priority Issues" >> "$report_file"
            fi
        else
            echo "- **Status:** ✅ No security issues found" >> "$report_file"
        fi
    else
        echo "- **Status:** ❌ Scan failed or no report generated" >> "$report_file"
    fi
    
    echo "" >> "$report_file"
    echo "### Semgrep (Static Analysis)" >> "$report_file"
    
    # Analyze Semgrep results
    local total_semgrep_findings=0
    for semgrep_file in "$RESULTS_DIR"/semgrep-*-"${TIMESTAMP}".json; do
        if [[ -f "$semgrep_file" ]]; then
            local findings=$(jq '.results | length' "$semgrep_file" 2>/dev/null || echo "0")
            total_semgrep_findings=$((total_semgrep_findings + findings))
        fi
    done
    
    echo "- **Total Findings:** $total_semgrep_findings" >> "$report_file"
    
    if [[ "$total_semgrep_findings" -gt "0" ]]; then
        echo "- **Status:** ⚠️ Review Required" >> "$report_file"
    else
        echo "- **Status:** ✅ No issues found" >> "$report_file"
    fi
    
    echo "" >> "$report_file"
    echo "## 📦 Dependency Analysis" >> "$report_file"
    
    # Analyze dependency results
    if [[ -f "$RESULTS_DIR/outdated-packages-${TIMESTAMP}.json" ]]; then
        local outdated_count=$(jq '. | length' "$RESULTS_DIR/outdated-packages-${TIMESTAMP}.json" 2>/dev/null || echo "0")
        echo "- **Outdated Packages:** $outdated_count" >> "$report_file"
    fi
    
    if [[ -f "$RESULTS_DIR/pip-audit-${TIMESTAMP}.json" ]]; then
        local pip_audit_vulns=$(jq '. | length' "$RESULTS_DIR/pip-audit-${TIMESTAMP}.json" 2>/dev/null || echo "0")
        echo "- **pip-audit Vulnerabilities:** $pip_audit_vulns" >> "$report_file"
    fi
    
    echo "" >> "$report_file"
    echo "## 🎯 Recommendations" >> "$report_file"
    echo "" >> "$report_file"
    echo "### Immediate Actions" >> "$report_file"
    echo "1. **High Severity Issues:** Address all high severity findings from Bandit" >> "$report_file"
    echo "2. **Critical Vulnerabilities:** Update packages with known vulnerabilities" >> "$report_file"
    echo "3. **Security Review:** Conduct code review for flagged security patterns" >> "$report_file"
    echo "" >> "$report_file"
    echo "### Long-term Improvements" >> "$report_file"
    echo "1. **Dependency Management:** Implement automated dependency updates" >> "$report_file"
    echo "2. **Security Training:** Provide secure coding training for development team" >> "$report_file"
    echo "3. **Continuous Monitoring:** Integrate SAST tools into CI/CD pipeline" >> "$report_file"
    echo "4. **Security Policies:** Establish and enforce security coding standards" >> "$report_file"
    echo "" >> "$report_file"
    echo "## 📁 Detailed Reports" >> "$report_file"
    echo "" >> "$report_file"
    echo "Detailed reports are available in the following files:" >> "$report_file"
    echo "" >> "$report_file"
    
    # List all generated reports
    for report in "$RESULTS_DIR"/*-"${TIMESTAMP}".*; do
        if [[ -f "$report" ]]; then
            local filename=$(basename "$report")
            echo "- \`$filename\`" >> "$report_file"
        fi
    done
    
    info "Comprehensive report generated: $report_file"
}

# Display results summary
display_summary() {
    log "SAST Analysis Summary"
    echo ""
    echo "📁 Results Directory: $RESULTS_DIR"
    echo "🕒 Scan Timestamp: $TIMESTAMP"
    echo ""
    
    if [[ "$RUN_SAFETY" == "true" ]]; then
        echo "🔍 Safety Scan: ✅ Completed"
    fi
    
    if [[ "$RUN_BANDIT" == "true" ]]; then
        echo "🛡️ Bandit Scan: ✅ Completed"
    fi
    
    if [[ "$RUN_SEMGREP" == "true" ]]; then
        echo "🔎 Semgrep Scan: ✅ Completed"
    fi
    
    if [[ "$RUN_DEPENDENCIES" == "true" ]]; then
        echo "📦 Dependency Analysis: ✅ Completed"
    fi
    
    if [[ "$GENERATE_REPORT" == "true" ]]; then
        echo "📋 Comprehensive Report: ✅ Generated"
    fi
    
    echo ""
    echo "📊 Quick Stats:"
    
    # Quick stats from results
    if [[ -f "$RESULTS_DIR/safety-report-${TIMESTAMP}.json" ]]; then
        local safety_vulns=$(jq '.vulnerabilities | length' "$RESULTS_DIR/safety-report-${TIMESTAMP}.json" 2>/dev/null || echo "0")
        echo "   Safety Vulnerabilities: $safety_vulns"
    fi
    
    if [[ -f "$RESULTS_DIR/bandit-report-${TIMESTAMP}.json" ]]; then
        local bandit_issues=$(jq '.results | length' "$RESULTS_DIR/bandit-report-${TIMESTAMP}.json" 2>/dev/null || echo "0")
        echo "   Bandit Security Issues: $bandit_issues"
    fi
    
    echo ""
    echo "🎯 Next Steps:"
    echo "   1. Review generated reports in $RESULTS_DIR"
    echo "   2. Address high/critical severity findings"
    echo "   3. Update vulnerable dependencies"
    echo "   4. Integrate fixes and re-run analysis"
}

# Main function
main() {
    log "Starting comprehensive SAST analysis..."
    
    parse_args "$@"
    setup_sast_environment
    
    run_safety_scan
    run_bandit_scan
    run_semgrep_scan
    run_dependency_analysis
    
    generate_comprehensive_report
    display_summary
    
    log "Comprehensive SAST analysis completed! 🔒"
}

# Run main function
main "$@"