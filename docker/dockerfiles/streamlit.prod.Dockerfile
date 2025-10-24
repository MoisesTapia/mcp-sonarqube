# Production-ready Multi-stage Dockerfile for SonarQube Streamlit Application
# ==========================================================================

# ----------------------------
# Stage 1: Build + dep checks
# ----------------------------
FROM python:3.11-slim as builder

ARG BUILDPLATFORM
ARG TARGETPLATFORM
ARG BUILD_DATE
ARG VCS_REF
ARG VERSION

# OCI labels
LABEL org.opencontainers.image.title="SonarQube Streamlit App"
LABEL org.opencontainers.image.description="Production Streamlit UI for SonarQube MCP"
LABEL org.opencontainers.image.version="${VERSION}"
LABEL org.opencontainers.image.created="${BUILD_DATE}"
LABEL org.opencontainers.image.revision="${VCS_REF}"
LABEL org.opencontainers.image.vendor="SonarQube MCP"
LABEL org.opencontainers.image.licenses="MIT"

ENV PIP_NO_CACHE_DIR=1 \
    VIRTUAL_ENV=/opt/venv \
    PATH="/opt/venv/bin:$PATH"

# Build deps + tools usados SOLO en build
RUN apt-get update && apt-get install -y --no-install-recommends \
      build-essential \
      curl \
      git \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Usuario de build (no root)
RUN groupadd -r builduser && useradd -r -g builduser builduser
USER builduser

WORKDIR /app

# Sólo lo mínimo para resolver deps
COPY --chown=builduser:builduser requirements.txt requirements-dev.txt pyproject.toml ./

# Venv + deps + escaneo de dependencias
RUN python -m venv "$VIRTUAL_ENV" \
 && pip install --upgrade pip setuptools wheel \
 && pip install safety bandit \
 && pip install -r requirements.txt \
 && safety check --json || true \
 && pip uninstall -y safety bandit setuptools wheel

# ----------------------------
# Stage 2: Código + bandit
# ----------------------------
FROM builder as security-scan
USER builduser
WORKDIR /app
COPY --chown=builduser:builduser src/ ./src/
# Reporte opcional (no falla el build)
RUN python -m venv "$VIRTUAL_ENV" \
 && pip install bandit \
 && bandit -r src/ -f json -o /tmp/bandit-report.json || true

# ----------------------------
# Stage 3: Runtime endurecido
# ----------------------------
FROM python:3.11-slim as runtime

# Seguridad/rendimiento + defaults de Streamlit
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONHASHSEED=random \
    PYTHONFAULTHANDLER=1 \
    PYTHONMALLOC=malloc \
    PYTHONOPTIMIZE=2 \
    VIRTUAL_ENV=/opt/venv \
    PATH="/opt/venv/bin:$PATH" \
    PYTHONPATH="/app/src" \
    # Streamlit defaults (puedes override en compose)
    STREAMLIT_SERVER_PORT=8501 \
    STREAMLIT_SERVER_ADDRESS=0.0.0.0 \
    STREAMLIT_SERVER_HEADLESS=true \
    STREAMLIT_BROWSER_GATHER_USAGE_STATS=false \
    # Evita warning y mantiene protección CSRF
    STREAMLIT_SERVER_ENABLE_CORS=true \
    STREAMLIT_SERVER_ENABLE_XSRF_PROTECTION=true \
    STREAMLIT_SERVER_MAX_UPLOAD_SIZE=50 \
    STREAMLIT_SERVER_MAX_MESSAGE_SIZE=50 \
    STREAMLIT_GLOBAL_DEVELOPMENT_MODE=false \
    STREAMLIT_GLOBAL_LOG_LEVEL=WARNING

# Runtime deps mínimos + dumb-init
RUN apt-get update && apt-get install -y --no-install-recommends \
      curl \
      ca-certificates \
      dumb-init \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean \
    && apt-get autoremove -y \
    && update-ca-certificates

# Usuario no-root fijo
RUN groupadd -r -g 1001 streamlituser \
 && useradd  -r -u 1001 -g streamlituser -d /app -s /bin/bash streamlituser \
 && mkdir -p /app \
 && chown streamlituser:streamlituser /app

# Copia venv desde builder (propiedad segura)
COPY --from=builder --chown=streamlituser:streamlituser /opt/venv /opt/venv

WORKDIR /app

# Código de la app (propiedad segura)
COPY --chown=streamlituser:streamlituser src/ ./src/
COPY --chown=streamlituser:streamlituser config/ ./config/

# Configuración Streamlit:
# - config.toml coherente con ENV (CORS & XSRF en true)
# - credentials.toml con email vacío => NO banner de onboarding
RUN mkdir -p /app/.streamlit \
 && /bin/sh -lc 'cat > /app/.streamlit/config.toml << "EOF"\n\
[server]\n\
port = 8501\n\
address = "0.0.0.0"\n\
headless = true\n\
enableCORS = true\n\
enableXsrfProtection = true\n\
maxUploadSize = 50\n\
maxMessageSize = 50\n\
\n\
[browser]\n\
gatherUsageStats = false\n\
\n\
[global]\n\
developmentMode = false\n\
logLevel = "WARNING"\n\
\n\
[theme]\n\
primaryColor = "#FF6B6B"\n\
backgroundColor = "#FFFFFF"\n\
secondaryBackgroundColor = "#F0F2F6"\n\
textColor = "#262730"\n\
EOF' \
 && /bin/sh -lc 'cat > /app/.streamlit/credentials.toml << "EOF"\n\
[general]\n\
email = \"\"\n\
EOF' \
 && mkdir -p /app/logs /app/data /app/tmp \
 && chown -R streamlituser:streamlituser /app \
 && chmod -R 755 /app \
 && chmod 700 /app/logs /app/data \
 && chmod -R a-w /app/src /app/config \
 && chmod 600 /app/.streamlit/config.toml

# Hardening final
RUN rm -rf /root/.bash_history /tmp/* /var/tmp/* /var/cache/apt/* /var/lib/apt/lists/* \
 && chmod 644 /etc/passwd /etc/group \
 || true

USER streamlituser

# Healthcheck
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8501/_stcore/health || exit 1

EXPOSE 8501

# dumb-init como PID 1
ENTRYPOINT ["dumb-init", "--"]

# Ejecuta Streamlit (sin flags duplicadas de CORS/XSRF)
CMD ["streamlit", "run", "src/streamlit_app/app.py", "--server.port=8501", "--server.address=0.0.0.0"]

# Metadata de seguridad
LABEL security.scan.date="${BUILD_DATE}"
LABEL security.non-root-user="streamlituser"
LABEL security.read-only-rootfs="false"
LABEL security.capabilities.drop="ALL"