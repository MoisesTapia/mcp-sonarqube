# Multi-stage Dockerfile for SonarQube Streamlit Application
# ----------------------------------------------------------
# Stage 1: Builder
FROM python:3.11-slim AS builder

ARG BUILDPLATFORM
ARG TARGETPLATFORM

ENV PIP_NO_CACHE_DIR=1 \
    VIRTUAL_ENV=/opt/venv \
    PATH="/opt/venv/bin:$PATH"

# System deps for building wheels
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
  && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copia sólo los archivos necesarios para resolver deps
COPY requirements.txt requirements-dev.txt pyproject.toml ./

# Venv + deps
RUN python -m venv "$VIRTUAL_ENV" \
 && pip install --upgrade pip setuptools wheel \
 && pip install -r requirements.txt

# ----------------------------------------------------------
# Stage 2: Runtime
FROM python:3.11-slim AS runtime

# ===== Runtime defaults (puedes sobrescribir en docker-compose) =====
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    VIRTUAL_ENV=/opt/venv \
    PATH="/opt/venv/bin:$PATH" \
    PYTHONPATH="/app/src" \
    # Streamlit sane defaults
    STREAMLIT_SERVER_PORT=8501 \
    STREAMLIT_SERVER_ADDRESS=0.0.0.0 \
    STREAMLIT_SERVER_HEADLESS=true \
    STREAMLIT_BROWSER_GATHER_USAGE_STATS=false \
    # Por defecto SIN CORS y SIN XSRF (evita el warning):
    STREAMLIT_SERVER_ENABLE_CORS=false \
    STREAMLIT_SERVER_ENABLE_XSRF_PROTECTION=false

# UID/GID configurables (útil para volúmenes host)
ARG APP_UID=1000
ARG APP_GID=1000

# Paquetes runtime mínimos + tini
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    curl \
    tini \
  && rm -rf /var/lib/apt/lists/*

# Usuario no-root
RUN groupadd -g ${APP_GID} streamlituser \
 && useradd  -u ${APP_UID} -g ${APP_GID} -m -d /app -s /bin/bash streamlituser

# Copia venv desde builder
COPY --from=builder /opt/venv /opt/venv

WORKDIR /app

# Copia código de la app
COPY src/ ./src/
COPY config/ ./config/
# (Opcional) scripts de arranque si los usas:
# COPY docker/scripts/start-streamlit.sh ./start-streamlit.sh
# RUN chmod +x ./start-streamlit.sh

# Create Streamlit config directory and config file
RUN mkdir -p /app/.streamlit && \
    echo '[server]' > /app/.streamlit/config.toml && \
    echo 'headless = true' >> /app/.streamlit/config.toml && \
    echo 'address = "0.0.0.0"' >> /app/.streamlit/config.toml && \
    echo 'port = 8501' >> /app/.streamlit/config.toml && \
    echo '' >> /app/.streamlit/config.toml && \
    echo '[browser]' >> /app/.streamlit/config.toml && \
    echo 'gatherUsageStats = false' >> /app/.streamlit/config.toml && \
    echo '' >> /app/.streamlit/config.toml && \
    echo '[global]' >> /app/.streamlit/config.toml && \
    echo 'showWarningOnDirectExecution = false' >> /app/.streamlit/config.toml && \
    echo '[general]' > /app/.streamlit/credentials.toml && \
    echo 'email = ""' >> /app/.streamlit/credentials.toml

# Create directories and set permissions
RUN mkdir -p /app/logs /app/data /app/.streamlit && \
    chown -R streamlituser:streamlituser /app && \
    chmod -R 755 /app/logs /app/data

USER streamlituser

# Healthcheck
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD curl -fsS http://localhost:8501/_stcore/health || exit 1

EXPOSE 8501

# tini como PID 1 para señalización correcta
ENTRYPOINT ["/usr/bin/tini","--"]

# Ejecuta Streamlit (ajusta el path del entrypoint si cambia)
CMD ["streamlit","run","src/streamlit_app/app.py","--server.port=8501","--server.address=0.0.0.0"]
