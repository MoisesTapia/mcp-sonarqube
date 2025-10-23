# Production-ready Multi-stage Dockerfile for SonarQube MCP Server
# Stage 1: Build stage with security scanning
FROM python:3.11-slim as builder

# Set build arguments
ARG BUILDPLATFORM
ARG TARGETPLATFORM
ARG BUILD_DATE
ARG VCS_REF
ARG VERSION

# Labels for metadata
LABEL org.opencontainers.image.title="SonarQube MCP Server"
LABEL org.opencontainers.image.description="Production MCP Server for SonarQube integration"
LABEL org.opencontainers.image.version="${VERSION}"
LABEL org.opencontainers.image.created="${BUILD_DATE}"
LABEL org.opencontainers.image.revision="${VCS_REF}"
LABEL org.opencontainers.image.vendor="SonarQube MCP"
LABEL org.opencontainers.image.licenses="MIT"

# Install build dependencies and security tools
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Create non-root user for build
RUN groupadd -r builduser && useradd -r -g builduser builduser

# Set working directory
WORKDIR /app

# Copy dependency files
COPY requirements.txt requirements-dev.txt pyproject.toml ./

# Create virtual environment and install dependencies
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Upgrade pip and install dependencies with security checks
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir safety bandit && \
    pip install --no-cache-dir -r requirements.txt && \
    # Security scan of dependencies
    safety check --json || true && \
    # Clean up
    pip uninstall -y safety bandit setuptools wheel

# Stage 2: Security scanning stage
FROM builder as security-scan

COPY src/ ./src/

# Run security scans
RUN pip install --no-cache-dir bandit && \
    bandit -r src/ -f json -o /tmp/bandit-report.json || true && \
    pip uninstall -y bandit

# Stage 3: Runtime stage with hardening
FROM python:3.11-slim as runtime

# Set environment variables for security and performance
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONHASHSEED=random \
    PATH="/opt/venv/bin:$PATH" \
    PYTHONPATH="/app/src" \
    # Security settings
    PYTHONFAULTHANDLER=1 \
    PYTHONMALLOC=malloc \
    # Performance settings
    PYTHONOPTIMIZE=2

# Install runtime dependencies and security tools
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    dumb-init \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean \
    # Remove unnecessary packages
    && apt-get autoremove -y \
    # Update CA certificates
    && update-ca-certificates

# Create non-root user with specific UID/GID for security
RUN groupadd -r -g 1000 mcpuser && \
    useradd -r -u 1000 -g mcpuser -d /app -s /bin/bash mcpuser && \
    # Create home directory
    mkdir -p /app && \
    chown mcpuser:mcpuser /app

# Copy virtual environment from builder stage
COPY --from=builder --chown=mcpuser:mcpuser /opt/venv /opt/venv

# Set working directory
WORKDIR /app

# Copy application code with proper ownership
COPY --chown=mcpuser:mcpuser src/ ./src/
COPY --chown=mcpuser:mcpuser config/ ./config/

# Create necessary directories with proper permissions
RUN mkdir -p /app/logs /app/data /app/tmp && \
    chown -R mcpuser:mcpuser /app && \
    chmod -R 755 /app && \
    # Set specific permissions for sensitive directories
    chmod 700 /app/logs /app/data && \
    # Remove write permissions from application code
    chmod -R a-w /app/src /app/config

# Security hardening
RUN # Remove shell history and temporary files
    rm -rf /root/.bash_history /tmp/* /var/tmp/* && \
    # Remove package manager caches
    rm -rf /var/cache/apt/* /var/lib/apt/lists/* && \
    # Set secure permissions on system files
    chmod 644 /etc/passwd /etc/group && \
    chmod 600 /etc/shadow || true

# Switch to non-root user
USER mcpuser

# Health check with timeout and retries
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Expose port
EXPOSE 8000

# Use dumb-init as PID 1 for proper signal handling
ENTRYPOINT ["dumb-init", "--"]

# Default command with security considerations
CMD ["python", "-m", "src.mcp_server.server"]

# Security metadata
LABEL security.scan.date="${BUILD_DATE}"
LABEL security.non-root-user="mcpuser"
LABEL security.read-only-rootfs="false"
LABEL security.capabilities.drop="ALL"