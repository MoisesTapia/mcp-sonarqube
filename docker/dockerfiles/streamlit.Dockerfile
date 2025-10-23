# Multi-stage Dockerfile for SonarQube Streamlit Application
# Stage 1: Build stage
FROM python:3.11-slim as builder

# Set build arguments
ARG BUILDPLATFORM
ARG TARGETPLATFORM

# Install build dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy dependency files
COPY requirements.txt requirements-dev.txt pyproject.toml ./

# Create virtual environment and install dependencies
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Upgrade pip and install dependencies
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -r requirements.txt

# Stage 2: Runtime stage
FROM python:3.11-slim as runtime

# Set environment variables for Streamlit production
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/opt/venv/bin:$PATH" \
    PYTHONPATH="/app/src" \
    STREAMLIT_SERVER_PORT=8501 \
    STREAMLIT_SERVER_ADDRESS=0.0.0.0 \
    STREAMLIT_SERVER_HEADLESS=true \
    STREAMLIT_BROWSER_GATHER_USAGE_STATS=false \
    STREAMLIT_SERVER_ENABLE_CORS=false \
    STREAMLIT_SERVER_ENABLE_XSRF_PROTECTION=true

# Create non-root user for security
RUN groupadd -r streamlituser && useradd -r -g streamlituser streamlituser

# Install runtime dependencies only
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Copy virtual environment from builder stage
COPY --from=builder /opt/venv /opt/venv

# Set working directory
WORKDIR /app

# Copy application code
COPY src/ ./src/
COPY config/ ./config/

# Create Streamlit config directory and config file
RUN mkdir -p /app/.streamlit && \
    echo '[server]' > /app/.streamlit/config.toml && \
    echo 'port = 8501' >> /app/.streamlit/config.toml && \
    echo 'address = "0.0.0.0"' >> /app/.streamlit/config.toml && \
    echo 'headless = true' >> /app/.streamlit/config.toml && \
    echo 'enableCORS = false' >> /app/.streamlit/config.toml && \
    echo 'enableXsrfProtection = true' >> /app/.streamlit/config.toml && \
    echo '[browser]' >> /app/.streamlit/config.toml && \
    echo 'gatherUsageStats = false' >> /app/.streamlit/config.toml

# Create necessary directories and set permissions
RUN mkdir -p /app/logs /app/data /app/.streamlit && \
    chown -R streamlituser:streamlituser /app

# Switch to non-root user
USER streamlituser

# Health check endpoint
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8501/_stcore/health || exit 1

# Expose port
EXPOSE 8501

# Default command
CMD ["streamlit", "run", "src/streamlit_app/app.py", "--server.port=8501", "--server.address=0.0.0.0"]