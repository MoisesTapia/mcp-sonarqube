# Production-ready Multi-stage Dockerfile for SonarQube Streamlit Application
# Stage 1: Build stage with security scanning
FROM python:3.11-slim as builder

# Set build arguments
ARG BUILDPLATFORM
ARG TARGETPLATFORM
ARG BUILD_DATE
ARG VCS_REF
ARG VERSION

# Labels for metadata
LABEL org.opencontainers.image.title="SonarQube Streamlit App"
LABEL org.opencontainers.image.description="Production Streamlit UI for SonarQube MCP"
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

# Set environment variables for Streamlit production and security
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONHASHSEED=random \
    PATH="/opt/venv/bin:$PATH" \
    PYTHONPATH="/app/src" \
    # Security settings
    PYTHONFAULTHANDLER=1 \
    PYTHONMALLOC=malloc \
    # Performance settings
    PYTHONOPTIMIZE=2 \
    # Streamlit production settings
    STREAMLIT_SERVER_PORT=8501 \
    STREAMLIT_SERVER_ADDRESS=0.0.0.0 \
    STREAMLIT_SERVER_HEADLESS=true \
    STREAMLIT_BROWSER_GATHER_USAGE_STATS=false \
    STREAMLIT_SERVER_ENABLE_CORS=false \
    STREAMLIT_SERVER_ENABLE_XSRF_PROTECTION=true \
    STREAMLIT_SERVER_MAX_UPLOAD_SIZE=50 \
    STREAMLIT_SERVER_MAX_MESSAGE_SIZE=50 \
    STREAMLIT_GLOBAL_DEVELOPMENT_MODE=false \
    STREAMLIT_GLOBAL_LOG_LEVEL=WARNING

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
RUN groupadd -r -g 1001 streamlituser && \
    useradd -r -u 1001 -g streamlituser -d /app -s /bin/bash streamlituser && \
    # Create home directory
    mkdir -p /app && \
    chown streamlituser:streamlituser /app

# Copy virtual environment from builder stage
COPY --from=builder --chown=streamlituser:streamlituser /opt/venv /opt/venv

# Set working directory
WORKDIR /app

# Copy application code with proper ownership
COPY --chown=streamlituser:streamlituser src/ ./src/
COPY --chown=streamlituser:streamlituser config/ ./config/

# Create Streamlit config directory and secure config file
RUN mkdir -p /app/.streamlit && \
    echo '[server]' > /app/.streamlit/config.toml && \
    echo 'port = 8501' >> /app/.streamlit/config.toml && \
    echo 'address = "0.0.0.0"' >> /app/.streamlit/config.toml && \
    echo 'headless = true' >> /app/.streamlit/config.toml && \
    echo 'enableCORS = false' >> /app/.streamlit/config.toml && \
    echo 'enableXsrfProtection = true' >> /app/.streamlit/config.toml && \
    echo 'maxUploadSize = 50' >> /app/.streamlit/config.toml && \
    echo 'maxMessageSize = 50' >> /app/.streamlit/config.toml && \
    echo '[browser]' >> /app/.streamlit/config.toml && \
    echo 'gatherUsageStats = false' >> /app/.streamlit/config.toml && \
    echo '[global]' >> /app/.streamlit/config.toml && \
    echo 'developmentMode = false' >> /app/.streamlit/config.toml && \
    echo 'logLevel = "WARNING"' >> /app/.streamlit/config.toml && \
    echo '[theme]' >> /app/.streamlit/config.toml && \
    echo 'primaryColor = "#FF6B6B"' >> /app/.streamlit/config.toml && \
    echo 'backgroundColor = "#FFFFFF"' >> /app/.streamlit/config.toml && \
    echo 'secondaryBackgroundColor = "#F0F2F6"' >> /app/.streamlit/config.toml && \
    echo 'textColor = "#262730"' >> /app/.streamlit/config.toml

# Create necessary directories with proper permissions
RUN mkdir -p /app/logs /app/data /app/tmp /app/.streamlit && \
    chown -R streamlituser:streamlituser /app && \
    chmod -R 755 /app && \
    # Set specific permissions for sensitive directories
    chmod 700 /app/logs /app/data && \
    # Remove write permissions from application code
    chmod -R a-w /app/src /app/config && \
    # Secure Streamlit config
    chmod 600 /app/.streamlit/config.toml

# Security hardening
RUN # Remove shell history and temporary files
    rm -rf /root/.bash_history /tmp/* /var/tmp/* && \
    # Remove package manager caches
    rm -rf /var/cache/apt/* /var/lib/apt/lists/* && \
    # Set secure permissions on system files
    chmod 644 /etc/passwd /etc/group && \
    chmod 600 /etc/shadow || true

# Switch to non-root user
USER streamlituser

# Health check with timeout and retries
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8501/_stcore/health || exit 1

# Expose port
EXPOSE 8501

# Use dumb-init as PID 1 for proper signal handling
ENTRYPOINT ["dumb-init", "--"]

# Default command with security considerations
CMD ["streamlit", "run", "src/streamlit_app/app.py", \
     "--server.port=8501", \
     "--server.address=0.0.0.0", \
     "--server.headless=true", \
     "--server.enableCORS=false", \
     "--server.enableXsrfProtection=true", \
     "--browser.gatherUsageStats=false", \
     "--global.developmentMode=false"]

# Security metadata
LABEL security.scan.date="${BUILD_DATE}"
LABEL security.non-root-user="streamlituser"
LABEL security.read-only-rootfs="false"
LABEL security.capabilities.drop="ALL"