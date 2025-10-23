# 🚀 SonarQube MCP Production Deployment Guide

Esta guía completa cubre todo lo necesario para desplegar el sistema SonarQube MCP en entornos de producción, desde la configuración inicial hasta el mantenimiento continuo.

## 📋 Tabla de Contenidos

1. [Prerrequisitos](#prerrequisitos)
2. [Requisitos de Infraestructura](#requisitos-de-infraestructura)
3. [Configuración de Seguridad](#configuración-de-seguridad)
4. [Configuración del Entorno de Producción](#configuración-del-entorno-de-producción)
5. [Despliegue con Kubernetes](#despliegue-con-kubernetes)
6. [Despliegue con Docker Compose](#despliegue-con-docker-compose)
7. [Configuración SSL/TLS](#configuración-ssltls)
8. [Monitoreo y Logging](#monitoreo-y-logging)
9. [Backup y Recuperación](#backup-y-recuperación)
10. [Optimización de Performance](#optimización-de-performance)
11. [Troubleshooting](#troubleshooting)
12. [Mantenimiento y Actualizaciones](#mantenimiento-y-actualizaciones)
13. [Hardening de Seguridad](#hardening-de-seguridad)
14. [Estrategias de Escalado](#estrategias-de-escalado)

## Prerrequisitos

### Requisitos del Sistema

#### Requisitos Mínimos
- **CPU**: 4 cores (8 recomendados)
- **RAM**: 8GB (16GB recomendados)
- **Storage**: 100GB SSD (500GB+ recomendados)
- **Red**: Conexión 1Gbps
- **OS**: Linux (Ubuntu 20.04+, CentOS 8+, RHEL 8+)

#### Configuración Recomendada para Producción
- **CPU**: 8+ cores
- **RAM**: 32GB+
- **Storage**: 1TB+ NVMe SSD
- **Red**: Conexión 10Gbps
- **Load Balancer**: Nginx, HAProxy, o cloud LB
- **Base de Datos**: Cluster PostgreSQL externo
- **Cache**: Cluster Redis externo

### Dependencias de Software

```bash
# Docker y Docker Compose
Docker Engine 20.10+
Docker Compose 2.0+

# Kubernetes (si se usa K8s)
Kubernetes 1.25+
kubectl
Helm 3.0+

# SSL/TLS
Certbot (Let's Encrypt)
OpenSSL

# Monitoreo
Prometheus
Grafana
Alertmanager

# Herramientas de Backup
PostgreSQL client tools
AWS CLI (si se usa S3)
```

## Requisitos de Infraestructura

### Arquitectura de Red

```
┌─────────────────────────────────────────────────────────────────┐
│                          INTERNET                               │
└─────────────────────┬───────────────────────────────────────────┘
                      │
┌─────────────────────┴───────────────────────────────────────────┐
│                      DMZ ZONE                                   │
│  ┌─────────────────┐    ┌─────────────────┐                    │
│  │  Load Balancer  │    │      WAF        │                    │
│  │   (Nginx/HAProxy)│    │                 │                    │
│  └─────────────────┘    └─────────────────┘                    │
└─────────────────────┬───────────────────────────────────────────┘
                      │
┌─────────────────────┴───────────────────────────────────────────┐
│                 APPLICATION TIER                                │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐             │
│  │ Streamlit 1 │  │ Streamlit 2 │  │ Streamlit 3 │             │
│  └─────────────┘  └─────────────┘  └─────────────┘             │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐             │
│  │ MCP Server 1│  │ MCP Server 2│  │ MCP Server 3│             │
│  └─────────────┘  └─────────────┘  └─────────────┘             │
└─────────────────────┬───────────────────────────────────────────┘
                      │
┌─────────────────────┴───────────────────────────────────────────┐
│                    DATA TIER                                    │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐             │
│  │ PostgreSQL  │  │    Redis    │  │  SonarQube  │             │
│  │   Primary   │  │   Cluster   │  │   Server    │             │
│  └─────────────┘  └─────────────┘  └─────────────┘             │
│  ┌─────────────┐                                               │
│  │ PostgreSQL  │                                               │
│  │   Replica   │                                               │
│  └─────────────┘                                               │
└─────────────────────────────────────────────────────────────────┘
```

### Configuración de Puertos

| Servicio | Puerto Interno | Puerto Externo | Protocolo | Acceso |
|----------|----------------|----------------|-----------|--------|
| Streamlit App | 8501 | 443 (HTTPS) | HTTP/HTTPS | Público |
| MCP Server | 8000 | 443 (HTTPS) | HTTP/HTTPS | API Only |
| SonarQube | 9000 | 443 (HTTPS) | HTTP/HTTPS | Interno |
| PostgreSQL | 5432 | - | TCP | Interno |
| Redis | 6379 | - | TCP | Interno |
| Prometheus | 9090 | - | HTTP | Interno |
| Grafana | 3000 | 443 (HTTPS) | HTTP/HTTPS | Admin Only |

## Configuración de Seguridad

### 1. Variables de Entorno

Crear archivos de entorno seguros:

```bash
# Crear directorio de configuración de producción
sudo mkdir -p /opt/sonarqube-mcp/config
sudo touch /opt/sonarqube-mcp/config/.env.production
sudo chmod 600 /opt/sonarqube-mcp/config/.env.production
```

**Variables de Entorno de Producción** (`/opt/sonarqube-mcp/config/.env.production`):

```env
# =============================================================================
# CONFIGURACIÓN DE PRODUCCIÓN - MANTENER SEGURO
# =============================================================================

# Configuración SonarQube
SONARQUBE_URL=https://sonarqube.internal.company.com
SONARQUBE_TOKEN=squ_production_token_here_64_chars_long
SONARQUBE_ORGANIZATION=your_organization

# Configuración Base de Datos (PostgreSQL Externo)
POSTGRES_HOST=postgres-primary.internal.company.com
POSTGRES_PORT=5432
POSTGRES_DB=sonarqube_prod
POSTGRES_USER=sonarqube_prod
POSTGRES_PASSWORD=very_secure_password_32_chars_min
POSTGRES_SSL_MODE=require

# Configuración Redis (Cluster Redis Externo)
REDIS_HOST=redis-cluster.internal.company.com
REDIS_PORT=6379
REDIS_PASSWORD=very_secure_redis_password_32_chars
REDIS_SSL=true
REDIS_CLUSTER_MODE=true

# Configuración de Aplicación
CACHE_TTL=300
LOG_LEVEL=INFO
SERVER_DEBUG=false
MAX_WORKERS=4
REQUEST_TIMEOUT=30
MAX_RETRIES=3

# Configuración de Seguridad
SECRET_KEY=your_secret_key_64_chars_long_random_string_here
JWT_SECRET=your_jwt_secret_64_chars_long_random_string_here
ENCRYPTION_KEY=your_encryption_key_32_chars_long

# Configuración SSL/TLS
SSL_CERT_PATH=/etc/ssl/certs/sonarqube-mcp.crt
SSL_KEY_PATH=/etc/ssl/private/sonarqube-mcp.key
SSL_CA_PATH=/etc/ssl/certs/ca-bundle.crt

# Configuración de Monitoreo
PROMETHEUS_ENABLED=true
METRICS_PORT=9090
HEALTH_CHECK_INTERVAL=30

# Configuración de Backup
BACKUP_S3_BUCKET=sonarqube-mcp-backups-prod
BACKUP_RETENTION_DAYS=30
AWS_ACCESS_KEY_ID=your_aws_access_key
AWS_SECRET_ACCESS_KEY=your_aws_secret_key
AWS_REGION=us-east-1

# Configuración de Email (para notificaciones)
SMTP_HOST=smtp.company.com
SMTP_PORT=587
SMTP_USER=notifications@company.com
SMTP_PASSWORD=smtp_password_here
SMTP_TLS=true

# Configuración Streamlit Producción
STREAMLIT_SERVER_HEADLESS=true
STREAMLIT_BROWSER_GATHER_USAGE_STATS=false
STREAMLIT_SERVER_ENABLE_CORS=false
STREAMLIT_SERVER_ENABLE_XSRF_PROTECTION=true
STREAMLIT_SERVER_MAX_UPLOAD_SIZE=50
STREAMLIT_GLOBAL_DEVELOPMENT_MODE=false
```

### 2. Gestión de Secretos

#### Usando Kubernetes Secrets

```bash
# Crear namespace
kubectl create namespace sonarqube-mcp-prod

# Crear secrets desde archivos
kubectl create secret generic sonarqube-mcp-secrets \
  --from-env-file=/opt/sonarqube-mcp/config/.env.production \
  -n sonarqube-mcp-prod

# Crear TLS secrets
kubectl create secret tls sonarqube-mcp-tls \
  --cert=/etc/ssl/certs/sonarqube-mcp.crt \
  --key=/etc/ssl/private/sonarqube-mcp.key \
  -n sonarqube-mcp-prod
```

#### Usando Docker Secrets

```bash
# Inicializar Docker Swarm (si no está hecho)
docker swarm init

# Crear secrets
echo "your_postgres_password" | docker secret create postgres_password -
echo "your_redis_password" | docker secret create redis_password -
echo "your_sonarqube_token" | docker secret create sonarqube_token -
```

## Configuración del Entorno de Producción

### 1. Estructura de Directorios

```bash
# Crear estructura de directorios de producción
sudo mkdir -p /opt/sonarqube-mcp/{config,data,logs,backups,ssl}
sudo mkdir -p /opt/sonarqube-mcp/data/{postgres,redis,sonarqube}
sudo mkdir -p /opt/sonarqube-mcp/logs/{mcp-server,streamlit,nginx}

# Establecer permisos apropiados
sudo chown -R root:docker /opt/sonarqube-mcp
sudo chmod -R 750 /opt/sonarqube-mcp
sudo chmod 600 /opt/sonarqube-mcp/config/.env.production
```

### 2. Docker Compose de Producción

Crear `/opt/sonarqube-mcp/docker-compose.prod.yml`:

```yaml
version: '3.8'

services:
  # Nginx Load Balancer
  nginx:
    image: nginx:1.25-alpine
    container_name: sonarqube-mcp-nginx
    restart: unless-stopped
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./config/nginx.conf:/etc/nginx/nginx.conf:ro
      - ./ssl:/etc/ssl/certs:ro
      - ./logs/nginx:/var/log/nginx
    depends_on:
      - streamlit-app-1
      - streamlit-app-2
      - mcp-server-1
      - mcp-server-2
    networks:
      - sonarqube-mcp-prod
    healthcheck:
      test: ["CMD", "nginx", "-t"]
      interval: 30s
      timeout: 10s
      retries: 3

  # Streamlit Applications (Múltiples instancias)
  streamlit-app-1:
    image: sonarqube-mcp/streamlit-app:${VERSION:-latest}
    container_name: sonarqube-mcp-streamlit-1
    restart: unless-stopped
    env_file:
      - ./config/.env.production
    volumes:
      - ./logs/streamlit:/app/logs
    networks:
      - sonarqube-mcp-prod
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8501/_stcore/health"]
      interval: 30s
      timeout: 10s
      retries: 3
    deploy:
      resources:
        limits:
          memory: 2G
          cpus: '1.0'
        reservations:
          memory: 1G
          cpus: '0.5'

  streamlit-app-2:
    image: sonarqube-mcp/streamlit-app:${VERSION:-latest}
    container_name: sonarqube-mcp-streamlit-2
    restart: unless-stopped
    env_file:
      - ./config/.env.production
    volumes:
      - ./logs/streamlit:/app/logs
    networks:
      - sonarqube-mcp-prod
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8501/_stcore/health"]
      interval: 30s
      timeout: 10s
      retries: 3
    deploy:
      resources:
        limits:
          memory: 2G
          cpus: '1.0'
        reservations:
          memory: 1G
          cpus: '0.5'

  # MCP Servers (Múltiples instancias)
  mcp-server-1:
    image: sonarqube-mcp/mcp-server:${VERSION:-latest}
    container_name: sonarqube-mcp-server-1
    restart: unless-stopped
    env_file:
      - ./config/.env.production
    volumes:
      - ./logs/mcp-server:/app/logs
    networks:
      - sonarqube-mcp-prod
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
    deploy:
      resources:
        limits:
          memory: 2G
          cpus: '1.0'
        reservations:
          memory: 1G
          cpus: '0.5'

  mcp-server-2:
    image: sonarqube-mcp/mcp-server:${VERSION:-latest}
    container_name: sonarqube-mcp-server-2
    restart: unless-stopped
    env_file:
      - ./config/.env.production
    volumes:
      - ./logs/mcp-server:/app/logs
    networks:
      - sonarqube-mcp-prod
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
    deploy:
      resources:
        limits:
          memory: 2G
          cpus: '1.0'
        reservations:
          memory: 1G
          cpus: '0.5'

  # Monitoreo
  prometheus:
    image: prom/prometheus:v2.45.0
    container_name: sonarqube-mcp-prometheus
    restart: unless-stopped
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
      - '--web.console.libraries=/etc/prometheus/console_libraries'
      - '--web.console.templates=/etc/prometheus/consoles'
      - '--storage.tsdb.retention.time=30d'
      - '--web.enable-lifecycle'
    volumes:
      - ./config/prometheus.yml:/etc/prometheus/prometheus.yml:ro
      - prometheus_data:/prometheus
    networks:
      - sonarqube-mcp-prod
    deploy:
      resources:
        limits:
          memory: 1G
          cpus: '0.5'

  grafana:
    image: grafana/grafana:10.1.0
    container_name: sonarqube-mcp-grafana
    restart: unless-stopped
    environment:
      - GF_SECURITY_ADMIN_USER=${GRAFANA_ADMIN_USER:-admin}
      - GF_SECURITY_ADMIN_PASSWORD=${GRAFANA_ADMIN_PASSWORD}
      - GF_USERS_ALLOW_SIGN_UP=false
      - GF_INSTALL_PLUGINS=grafana-piechart-panel
    volumes:
      - grafana_data:/var/lib/grafana
      - ./config/grafana:/etc/grafana/provisioning
    networks:
      - sonarqube-mcp-prod
    deploy:
      resources:
        limits:
          memory: 512M
          cpus: '0.5'

volumes:
  prometheus_data:
    driver: local
  grafana_data:
    driver: local

networks:
  sonarqube-mcp-prod:
    driver: bridge
    ipam:
      config:
        - subnet: 172.30.0.0/16
```

## Despliegue con Kubernetes

### 1. Namespace y RBAC de Producción

```yaml
# k8s/production/namespace.yaml
apiVersion: v1
kind: Namespace
metadata:
  name: sonarqube-mcp-prod
  labels:
    name: sonarqube-mcp-prod
    environment: production
---
apiVersion: v1
kind: ResourceQuota
metadata:
  name: sonarqube-mcp-quota
  namespace: sonarqube-mcp-prod
spec:
  hard:
    requests.cpu: "8"
    requests.memory: 16Gi
    limits.cpu: "16"
    limits.memory: 32Gi
    persistentvolumeclaims: "20"
    services: "20"
    secrets: "20"
    configmaps: "20"
---
apiVersion: v1
kind: LimitRange
metadata:
  name: sonarqube-mcp-limits
  namespace: sonarqube-mcp-prod
spec:
  limits:
  - default:
      cpu: "2"
      memory: "4Gi"
    defaultRequest:
      cpu: "500m"
      memory: "1Gi"
    type: Container
```

### 2. Secrets de Producción

```yaml
# k8s/production/secrets.yaml
apiVersion: v1
kind: Secret
metadata:
  name: sonarqube-mcp-secrets
  namespace: sonarqube-mcp-prod
type: Opaque
data:
  # Todos los valores deben estar codificados en base64
  postgres-password: <base64-encoded-password>
  redis-password: <base64-encoded-password>
  sonarqube-token: <base64-encoded-token>
  secret-key: <base64-encoded-secret>
  jwt-secret: <base64-encoded-jwt-secret>
  encryption-key: <base64-encoded-encryption-key>
---
apiVersion: v1
kind: Secret
metadata:
  name: tls-secret
  namespace: sonarqube-mcp-prod
type: kubernetes.io/tls
data:
  tls.crt: <base64-encoded-certificate>
  tls.key: <base64-encoded-private-key>
```

### 3. ConfigMap de Producción

```yaml
# k8s/production/configmap.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: sonarqube-mcp-config
  namespace: sonarqube-mcp-prod
data:
  # Configuración no sensible
  CACHE_TTL: "300"
  LOG_LEVEL: "INFO"
  SERVER_DEBUG: "false"
  MAX_WORKERS: "4"
  REQUEST_TIMEOUT: "30"
  MAX_RETRIES: "3"
  PROMETHEUS_ENABLED: "true"
  METRICS_PORT: "9090"
  HEALTH_CHECK_INTERVAL: "30"
  STREAMLIT_SERVER_HEADLESS: "true"
  STREAMLIT_BROWSER_GATHER_USAGE_STATS: "false"
  STREAMLIT_SERVER_ENABLE_CORS: "false"
  STREAMLIT_SERVER_ENABLE_XSRF_PROTECTION: "true"
  STREAMLIT_GLOBAL_DEVELOPMENT_MODE: "false"
```
### 4. Deployments de Producción

```yaml
# k8s/production/mcp-server.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: mcp-server
  namespace: sonarqube-mcp-prod
  labels:
    app: mcp-server
    version: v1
spec:
  replicas: 3
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 1
      maxUnavailable: 1
  selector:
    matchLabels:
      app: mcp-server
  template:
    metadata:
      labels:
        app: mcp-server
        version: v1
      annotations:
        prometheus.io/scrape: "true"
        prometheus.io/port: "9090"
        prometheus.io/path: "/metrics"
    spec:
      securityContext:
        runAsNonRoot: true
        runAsUser: 1000
        fsGroup: 1000
      containers:
      - name: mcp-server
        image: sonarqube-mcp/mcp-server:v1.0.0
        imagePullPolicy: Always
        ports:
        - containerPort: 8000
          name: http
        - containerPort: 9090
          name: metrics
        env:
        - name: SONARQUBE_TOKEN
          valueFrom:
            secretKeyRef:
              name: sonarqube-mcp-secrets
              key: sonarqube-token
        - name: POSTGRES_PASSWORD
          valueFrom:
            secretKeyRef:
              name: sonarqube-mcp-secrets
              key: postgres-password
        - name: REDIS_PASSWORD
          valueFrom:
            secretKeyRef:
              name: sonarqube-mcp-secrets
              key: redis-password
        envFrom:
        - configMapRef:
            name: sonarqube-mcp-config
        resources:
          requests:
            memory: "1Gi"
            cpu: "500m"
          limits:
            memory: "2Gi"
            cpu: "1"
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 30
          timeoutSeconds: 10
          failureThreshold: 3
        readinessProbe:
          httpGet:
            path: /ready
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 10
          timeoutSeconds: 5
          failureThreshold: 3
        securityContext:
          allowPrivilegeEscalation: false
          readOnlyRootFilesystem: true
          capabilities:
            drop:
            - ALL
        volumeMounts:
        - name: tmp
          mountPath: /tmp
        - name: logs
          mountPath: /app/logs
      volumes:
      - name: tmp
        emptyDir: {}
      - name: logs
        emptyDir: {}
---
apiVersion: v1
kind: Service
metadata:
  name: mcp-server-service
  namespace: sonarqube-mcp-prod
  labels:
    app: mcp-server
spec:
  type: ClusterIP
  ports:
  - port: 8000
    targetPort: 8000
    name: http
  - port: 9090
    targetPort: 9090
    name: metrics
  selector:
    app: mcp-server
---
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: mcp-server-hpa
  namespace: sonarqube-mcp-prod
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: mcp-server
  minReplicas: 3
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
```

### 5. Ingress de Producción

```yaml
# k8s/production/ingress.yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: sonarqube-mcp-ingress
  namespace: sonarqube-mcp-prod
  annotations:
    kubernetes.io/ingress.class: "nginx"
    nginx.ingress.kubernetes.io/ssl-redirect: "true"
    nginx.ingress.kubernetes.io/force-ssl-redirect: "true"
    nginx.ingress.kubernetes.io/proxy-body-size: "50m"
    nginx.ingress.kubernetes.io/rate-limit: "100"
    nginx.ingress.kubernetes.io/rate-limit-window: "1m"
    cert-manager.io/cluster-issuer: "letsencrypt-prod"
    nginx.ingress.kubernetes.io/configuration-snippet: |
      more_set_headers "X-Frame-Options: DENY";
      more_set_headers "X-Content-Type-Options: nosniff";
      more_set_headers "X-XSS-Protection: 1; mode=block";
      more_set_headers "Referrer-Policy: strict-origin-when-cross-origin";
spec:
  tls:
  - hosts:
    - sonarqube-mcp.company.com
    - api.sonarqube-mcp.company.com
    secretName: sonarqube-mcp-tls
  rules:
  - host: sonarqube-mcp.company.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: streamlit-service
            port:
              number: 8501
  - host: api.sonarqube-mcp.company.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: mcp-server-service
            port:
              number: 8000
```

## Configuración SSL/TLS

### 1. Certificados Let's Encrypt

```bash
# Instalar Certbot
sudo apt-get update
sudo apt-get install certbot python3-certbot-nginx

# Obtener certificados
sudo certbot --nginx -d sonarqube-mcp.company.com -d api.sonarqube-mcp.company.com

# Configurar renovación automática
sudo crontab -e
# Agregar línea:
0 12 * * * /usr/bin/certbot renew --quiet
```

### 2. Configuración Nginx SSL

```nginx
# /opt/sonarqube-mcp/config/nginx.conf
events {
    worker_connections 1024;
}

http {
    upstream streamlit_backend {
        least_conn;
        server streamlit-app-1:8501 max_fails=3 fail_timeout=30s;
        server streamlit-app-2:8501 max_fails=3 fail_timeout=30s;
    }

    upstream mcp_backend {
        least_conn;
        server mcp-server-1:8000 max_fails=3 fail_timeout=30s;
        server mcp-server-2:8000 max_fails=3 fail_timeout=30s;
    }

    # Rate limiting
    limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;
    limit_req_zone $binary_remote_addr zone=web:10m rate=5r/s;

    # SSL Configuration
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512:ECDHE-RSA-AES256-GCM-SHA384:DHE-RSA-AES256-GCM-SHA384;
    ssl_prefer_server_ciphers off;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;

    # Security Headers
    add_header X-Frame-Options DENY always;
    add_header X-Content-Type-Options nosniff always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;
    add_header Content-Security-Policy "default-src 'self'; script-src 'self' 'unsafe-inline' 'unsafe-eval'; style-src 'self' 'unsafe-inline';" always;

    # Redirect HTTP to HTTPS
    server {
        listen 80;
        server_name sonarqube-mcp.company.com api.sonarqube-mcp.company.com;
        return 301 https://$server_name$request_uri;
    }

    # Streamlit Frontend
    server {
        listen 443 ssl http2;
        server_name sonarqube-mcp.company.com;

        ssl_certificate /etc/ssl/certs/sonarqube-mcp.crt;
        ssl_certificate_key /etc/ssl/private/sonarqube-mcp.key;

        client_max_body_size 50M;

        location / {
            limit_req zone=web burst=20 nodelay;
            proxy_pass http://streamlit_backend;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
            
            # WebSocket support for Streamlit
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection "upgrade";
            proxy_read_timeout 86400;
        }

        location /_stcore/stream {
            limit_req zone=web burst=20 nodelay;
            proxy_pass http://streamlit_backend;
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection "upgrade";
            proxy_set_header Host $host;
            proxy_cache_bypass $http_upgrade;
        }
    }

    # MCP API Backend
    server {
        listen 443 ssl http2;
        server_name api.sonarqube-mcp.company.com;

        ssl_certificate /etc/ssl/certs/sonarqube-mcp.crt;
        ssl_certificate_key /etc/ssl/private/sonarqube-mcp.key;

        location / {
            limit_req zone=api burst=50 nodelay;
            proxy_pass http://mcp_backend;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
            proxy_connect_timeout 30s;
            proxy_send_timeout 30s;
            proxy_read_timeout 30s;
        }

        location /health {
            access_log off;
            proxy_pass http://mcp_backend;
            proxy_set_header Host $host;
        }
    }
}
```

## Monitoreo y Logging

### 1. Configuración Prometheus

```yaml
# /opt/sonarqube-mcp/config/prometheus.yml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

rule_files:
  - "alert_rules.yml"

alerting:
  alertmanagers:
    - static_configs:
        - targets:
          - alertmanager:9093

scrape_configs:
  - job_name: 'prometheus'
    static_configs:
      - targets: ['localhost:9090']

  - job_name: 'mcp-server'
    static_configs:
      - targets: ['mcp-server-1:9090', 'mcp-server-2:9090']
    metrics_path: '/metrics'
    scrape_interval: 30s

  - job_name: 'streamlit-app'
    static_configs:
      - targets: ['streamlit-app-1:8501', 'streamlit-app-2:8501']
    metrics_path: '/_stcore/metrics'
    scrape_interval: 30s

  - job_name: 'nginx'
    static_configs:
      - targets: ['nginx:9113']
    scrape_interval: 30s

  - job_name: 'node-exporter'
    static_configs:
      - targets: ['node-exporter:9100']
    scrape_interval: 30s
```

### 2. Reglas de Alertas

```yaml
# /opt/sonarqube-mcp/config/alert_rules.yml
groups:
- name: sonarqube-mcp-alerts
  rules:
  - alert: HighCPUUsage
    expr: 100 - (avg by(instance) (irate(node_cpu_seconds_total{mode="idle"}[5m])) * 100) > 80
    for: 5m
    labels:
      severity: warning
    annotations:
      summary: "High CPU usage detected"
      description: "CPU usage is above 80% for more than 5 minutes"

  - alert: HighMemoryUsage
    expr: (node_memory_MemTotal_bytes - node_memory_MemAvailable_bytes) / node_memory_MemTotal_bytes * 100 > 85
    for: 5m
    labels:
      severity: warning
    annotations:
      summary: "High memory usage detected"
      description: "Memory usage is above 85% for more than 5 minutes"

  - alert: ServiceDown
    expr: up == 0
    for: 1m
    labels:
      severity: critical
    annotations:
      summary: "Service is down"
      description: "{{ $labels.instance }} of job {{ $labels.job }} has been down for more than 1 minute"

  - alert: HighResponseTime
    expr: histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m])) > 2
    for: 5m
    labels:
      severity: warning
    annotations:
      summary: "High response time detected"
      description: "95th percentile response time is above 2 seconds"

  - alert: DatabaseConnectionFailure
    expr: increase(database_connection_errors_total[5m]) > 5
    for: 2m
    labels:
      severity: critical
    annotations:
      summary: "Database connection failures"
      description: "More than 5 database connection failures in the last 5 minutes"
```

### 3. Configuración de Logging

```yaml
# /opt/sonarqube-mcp/config/logging.yml
version: 1
disable_existing_loggers: false

formatters:
  standard:
    format: '%(asctime)s [%(levelname)s] %(name)s: %(message)s'
  json:
    format: '{"timestamp": "%(asctime)s", "level": "%(levelname)s", "logger": "%(name)s", "message": "%(message)s", "module": "%(module)s", "function": "%(funcName)s", "line": %(lineno)d}'

handlers:
  console:
    class: logging.StreamHandler
    level: INFO
    formatter: standard
    stream: ext://sys.stdout

  file:
    class: logging.handlers.RotatingFileHandler
    level: INFO
    formatter: json
    filename: /app/logs/app.log
    maxBytes: 10485760  # 10MB
    backupCount: 5

  error_file:
    class: logging.handlers.RotatingFileHandler
    level: ERROR
    formatter: json
    filename: /app/logs/error.log
    maxBytes: 10485760  # 10MB
    backupCount: 5

loggers:
  sonarqube_mcp:
    level: INFO
    handlers: [console, file, error_file]
    propagate: false

  uvicorn:
    level: INFO
    handlers: [console, file]
    propagate: false

  sqlalchemy:
    level: WARNING
    handlers: [console, file]
    propagate: false

root:
  level: INFO
  handlers: [console, file]
```

## Backup y Recuperación

### 1. Script de Backup Automatizado

```bash
#!/bin/bash
# /opt/sonarqube-mcp/scripts/backup.sh

set -euo pipefail

# Configuración
BACKUP_DIR="/opt/sonarqube-mcp/backups"
S3_BUCKET="sonarqube-mcp-backups-prod"
RETENTION_DAYS=30
DATE=$(date +%Y%m%d_%H%M%S)

# Crear directorio de backup
mkdir -p "$BACKUP_DIR/$DATE"

echo "🔄 Iniciando backup de SonarQube MCP - $DATE"

# 1. Backup de Base de Datos PostgreSQL
echo "📊 Respaldando base de datos PostgreSQL..."
docker exec sonarqube-mcp-postgres pg_dump -U $POSTGRES_USER -d $POSTGRES_DB > "$BACKUP_DIR/$DATE/postgres_backup.sql"

# 2. Backup de Redis (si es necesario)
echo "🔴 Respaldando Redis..."
docker exec sonarqube-mcp-redis redis-cli --rdb /data/dump.rdb
docker cp sonarqube-mcp-redis:/data/dump.rdb "$BACKUP_DIR/$DATE/redis_backup.rdb"

# 3. Backup de configuraciones
echo "⚙️ Respaldando configuraciones..."
cp -r /opt/sonarqube-mcp/config "$BACKUP_DIR/$DATE/"

# 4. Backup de logs importantes
echo "📝 Respaldando logs..."
cp -r /opt/sonarqube-mcp/logs "$BACKUP_DIR/$DATE/"

# 5. Crear archivo comprimido
echo "🗜️ Comprimiendo backup..."
cd "$BACKUP_DIR"
tar -czf "sonarqube_mcp_backup_$DATE.tar.gz" "$DATE"
rm -rf "$DATE"

# 6. Subir a S3 (si está configurado)
if [ ! -z "${AWS_ACCESS_KEY_ID:-}" ]; then
    echo "☁️ Subiendo backup a S3..."
    aws s3 cp "sonarqube_mcp_backup_$DATE.tar.gz" "s3://$S3_BUCKET/"
fi

# 7. Limpiar backups antiguos
echo "🧹 Limpiando backups antiguos..."
find "$BACKUP_DIR" -name "sonarqube_mcp_backup_*.tar.gz" -mtime +$RETENTION_DAYS -delete

# 8. Limpiar backups antiguos en S3
if [ ! -z "${AWS_ACCESS_KEY_ID:-}" ]; then
    aws s3 ls "s3://$S3_BUCKET/" | while read -r line; do
        createDate=$(echo $line | awk '{print $1" "$2}')
        createDate=$(date -d "$createDate" +%s)
        olderThan=$(date -d "$RETENTION_DAYS days ago" +%s)
        if [[ $createDate -lt $olderThan ]]; then
            fileName=$(echo $line | awk '{print $4}')
            if [[ $fileName != "" ]]; then
                aws s3 rm "s3://$S3_BUCKET/$fileName"
            fi
        fi
    done
fi

echo "✅ Backup completado exitosamente: sonarqube_mcp_backup_$DATE.tar.gz"
```

### 2. Script de Restauración

```bash
#!/bin/bash
# /opt/sonarqube-mcp/scripts/restore.sh

set -euo pipefail

if [ $# -eq 0 ]; then
    echo "❌ Error: Debe especificar el archivo de backup"
    echo "Uso: $0 <backup_file.tar.gz>"
    exit 1
fi

BACKUP_FILE="$1"
RESTORE_DIR="/tmp/sonarqube_mcp_restore_$(date +%s)"

echo "🔄 Iniciando restauración desde: $BACKUP_FILE"

# 1. Extraer backup
echo "📦 Extrayendo backup..."
mkdir -p "$RESTORE_DIR"
tar -xzf "$BACKUP_FILE" -C "$RESTORE_DIR"

# 2. Detener servicios
echo "⏹️ Deteniendo servicios..."
docker-compose -f /opt/sonarqube-mcp/docker-compose.prod.yml down

# 3. Restaurar base de datos
echo "📊 Restaurando base de datos PostgreSQL..."
docker-compose -f /opt/sonarqube-mcp/docker-compose.prod.yml up -d postgres
sleep 30
docker exec -i sonarqube-mcp-postgres psql -U $POSTGRES_USER -d $POSTGRES_DB < "$RESTORE_DIR"/*/postgres_backup.sql

# 4. Restaurar Redis
echo "🔴 Restaurando Redis..."
docker-compose -f /opt/sonarqube-mcp/docker-compose.prod.yml up -d redis
sleep 10
docker cp "$RESTORE_DIR"/*/redis_backup.rdb sonarqube-mcp-redis:/data/dump.rdb
docker restart sonarqube-mcp-redis

# 5. Restaurar configuraciones
echo "⚙️ Restaurando configuraciones..."
cp -r "$RESTORE_DIR"/*/config/* /opt/sonarqube-mcp/config/

# 6. Iniciar todos los servicios
echo "🚀 Iniciando todos los servicios..."
docker-compose -f /opt/sonarqube-mcp/docker-compose.prod.yml up -d

# 7. Limpiar archivos temporales
echo "🧹 Limpiando archivos temporales..."
rm -rf "$RESTORE_DIR"

echo "✅ Restauración completada exitosamente"
```

### 3. Configuración de Backup Automático

```bash
# Agregar al crontab del sistema
sudo crontab -e

# Backup diario a las 2:00 AM
0 2 * * * /opt/sonarqube-mcp/scripts/backup.sh >> /opt/sonarqube-mcp/logs/backup.log 2>&1

# Backup semanal completo los domingos a las 1:00 AM
0 1 * * 0 /opt/sonarqube-mcp/scripts/backup_full.sh >> /opt/sonarqube-mcp/logs/backup_full.log 2>&1
```

## Optimización de Performance

### 1. Configuración de PostgreSQL para Producción

```sql
-- /opt/sonarqube-mcp/config/postgresql.conf

# Configuración de memoria
shared_buffers = 4GB                    # 25% de RAM total
effective_cache_size = 12GB             # 75% de RAM total
work_mem = 256MB                        # Para operaciones complejas
maintenance_work_mem = 1GB              # Para mantenimiento

# Configuración de conexiones
max_connections = 200                   # Ajustar según necesidades
superuser_reserved_connections = 3

# Configuración de WAL
wal_buffers = 64MB
checkpoint_completion_target = 0.9
checkpoint_timeout = 15min
max_wal_size = 4GB
min_wal_size = 1GB

# Configuración de logging
log_destination = 'stderr'
logging_collector = on
log_directory = '/var/log/postgresql'
log_filename = 'postgresql-%Y-%m-%d_%H%M%S.log'
log_rotation_age = 1d
log_rotation_size = 100MB
log_min_duration_statement = 1000       # Log queries > 1 segundo

# Configuración de performance
random_page_cost = 1.1                  # Para SSD
effective_io_concurrency = 200          # Para SSD
max_worker_processes = 8
max_parallel_workers_per_gather = 4
max_parallel_workers = 8
```

### 2. Configuración de Redis para Producción

```conf
# /opt/sonarqube-mcp/config/redis.conf

# Configuración de memoria
maxmemory 2gb
maxmemory-policy allkeys-lru

# Configuración de persistencia
save 900 1
save 300 10
save 60 10000

# Configuración de red
tcp-keepalive 300
timeout 0

# Configuración de seguridad
requirepass your_secure_redis_password
rename-command FLUSHDB ""
rename-command FLUSHALL ""
rename-command DEBUG ""

# Configuración de logging
loglevel notice
logfile /var/log/redis/redis-server.log

# Configuración de performance
tcp-backlog 511
databases 16
```

### 3. Optimización de Aplicación

```python
# /opt/sonarqube-mcp/config/performance.py

# Configuración de conexión a base de datos
DATABASE_CONFIG = {
    'pool_size': 20,
    'max_overflow': 30,
    'pool_timeout': 30,
    'pool_recycle': 3600,
    'pool_pre_ping': True
}

# Configuración de cache
CACHE_CONFIG = {
    'default_timeout': 300,
    'key_prefix': 'sonarqube_mcp:',
    'connection_pool_kwargs': {
        'max_connections': 50,
        'retry_on_timeout': True
    }
}

# Configuración de workers
WORKER_CONFIG = {
    'workers': 4,
    'worker_class': 'uvicorn.workers.UvicornWorker',
    'worker_connections': 1000,
    'max_requests': 1000,
    'max_requests_jitter': 100,
    'timeout': 30,
    'keepalive': 2
}
```

## Troubleshooting

### 1. Problemas Comunes y Soluciones

#### Error de Conexión a Base de Datos

```bash
# Verificar estado de PostgreSQL
docker logs sonarqube-mcp-postgres

# Verificar conectividad
docker exec sonarqube-mcp-postgres pg_isready -U $POSTGRES_USER

# Verificar configuración de red
docker network ls
docker network inspect sonarqube-mcp-prod

# Solución: Reiniciar servicios en orden
docker-compose -f docker-compose.prod.yml restart postgres
sleep 30
docker-compose -f docker-compose.prod.yml restart mcp-server-1 mcp-server-2
```

#### Problemas de Performance

```bash
# Monitorear recursos del sistema
htop
iotop
nethogs

# Verificar logs de aplicación
tail -f /opt/sonarqube-mcp/logs/mcp-server/app.log

# Verificar métricas de Prometheus
curl http://localhost:9090/metrics

# Optimizar base de datos
docker exec sonarqube-mcp-postgres psql -U $POSTGRES_USER -d $POSTGRES_DB -c "VACUUM ANALYZE;"
```

#### Problemas de SSL/TLS

```bash
# Verificar certificados
openssl x509 -in /etc/ssl/certs/sonarqube-mcp.crt -text -noout

# Verificar configuración Nginx
docker exec sonarqube-mcp-nginx nginx -t

# Renovar certificados Let's Encrypt
sudo certbot renew --dry-run
```

### 2. Scripts de Diagnóstico

```bash
#!/bin/bash
# /opt/sonarqube-mcp/scripts/health_check.sh

echo "🔍 SonarQube MCP Health Check"
echo "================================"

# 1. Verificar servicios Docker
echo "📦 Estado de contenedores:"
docker-compose -f /opt/sonarqube-mcp/docker-compose.prod.yml ps

# 2. Verificar conectividad de red
echo -e "\n🌐 Conectividad de red:"
curl -s -o /dev/null -w "%{http_code}" http://localhost/health || echo "❌ Streamlit no responde"
curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/health || echo "❌ MCP Server no responde"

# 3. Verificar base de datos
echo -e "\n📊 Estado de base de datos:"
docker exec sonarqube-mcp-postgres pg_isready -U $POSTGRES_USER && echo "✅ PostgreSQL OK" || echo "❌ PostgreSQL ERROR"

# 4. Verificar Redis
echo -e "\n🔴 Estado de Redis:"
docker exec sonarqube-mcp-redis redis-cli ping && echo "✅ Redis OK" || echo "❌ Redis ERROR"

# 5. Verificar espacio en disco
echo -e "\n💾 Espacio en disco:"
df -h /opt/sonarqube-mcp

# 6. Verificar memoria
echo -e "\n🧠 Uso de memoria:"
free -h

# 7. Verificar CPU
echo -e "\n⚡ Carga de CPU:"
uptime
```

## Mantenimiento y Actualizaciones

### 1. Proceso de Actualización

```bash
#!/bin/bash
# /opt/sonarqube-mcp/scripts/update.sh

set -euo pipefail

NEW_VERSION="$1"
BACKUP_DIR="/opt/sonarqube-mcp/backups/pre_update_$(date +%Y%m%d_%H%M%S)"

echo "🔄 Iniciando actualización a versión: $NEW_VERSION"

# 1. Crear backup pre-actualización
echo "💾 Creando backup pre-actualización..."
/opt/sonarqube-mcp/scripts/backup.sh

# 2. Descargar nuevas imágenes
echo "📥 Descargando nuevas imágenes..."
docker pull sonarqube-mcp/mcp-server:$NEW_VERSION
docker pull sonarqube-mcp/streamlit-app:$NEW_VERSION

# 3. Actualizar variables de entorno
echo "⚙️ Actualizando configuración..."
export VERSION=$NEW_VERSION

# 4. Actualización rolling (sin downtime)
echo "🔄 Realizando actualización rolling..."

# Actualizar MCP servers uno por uno
docker-compose -f /opt/sonarqube-mcp/docker-compose.prod.yml up -d --no-deps mcp-server-1
sleep 30
docker-compose -f /opt/sonarqube-mcp/docker-compose.prod.yml up -d --no-deps mcp-server-2
sleep 30

# Actualizar Streamlit apps uno por uno
docker-compose -f /opt/sonarqube-mcp/docker-compose.prod.yml up -d --no-deps streamlit-app-1
sleep 30
docker-compose -f /opt/sonarqube-mcp/docker-compose.prod.yml up -d --no-deps streamlit-app-2

# 5. Verificar salud del sistema
echo "🔍 Verificando salud del sistema..."
sleep 60
/opt/sonarqube-mcp/scripts/health_check.sh

echo "✅ Actualización completada exitosamente"
```

### 2. Mantenimiento de Base de Datos

```bash
#!/bin/bash
# /opt/sonarqube-mcp/scripts/db_maintenance.sh

echo "🔧 Iniciando mantenimiento de base de datos"

# 1. VACUUM y ANALYZE
echo "🧹 Ejecutando VACUUM ANALYZE..."
docker exec sonarqube-mcp-postgres psql -U $POSTGRES_USER -d $POSTGRES_DB -c "VACUUM ANALYZE;"

# 2. Reindexar tablas importantes
echo "📊 Reindexando tablas..."
docker exec sonarqube-mcp-postgres psql -U $POSTGRES_USER -d $POSTGRES_DB -c "REINDEX DATABASE $POSTGRES_DB;"

# 3. Actualizar estadísticas
echo "📈 Actualizando estadísticas..."
docker exec sonarqube-mcp-postgres psql -U $POSTGRES_USER -d $POSTGRES_DB -c "ANALYZE;"

# 4. Limpiar logs antiguos
echo "🗑️ Limpiando logs antiguos..."
docker exec sonarqube-mcp-postgres find /var/log/postgresql -name "*.log" -mtime +7 -delete

echo "✅ Mantenimiento de base de datos completado"
```

## Hardening de Seguridad

### 1. Configuración de Firewall

```bash
#!/bin/bash
# /opt/sonarqube-mcp/scripts/setup_firewall.sh

# Configurar UFW (Ubuntu Firewall)
sudo ufw --force reset
sudo ufw default deny incoming
sudo ufw default allow outgoing

# Permitir SSH (cambiar puerto si es necesario)
sudo ufw allow 22/tcp

# Permitir HTTP/HTTPS
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# Permitir acceso interno entre servicios
sudo ufw allow from 172.30.0.0/16

# Activar firewall
sudo ufw --force enable

echo "✅ Firewall configurado correctamente"
```

### 2. Configuración de Fail2Ban

```ini
# /etc/fail2ban/jail.local
[DEFAULT]
bantime = 3600
findtime = 600
maxretry = 5
backend = systemd

[nginx-http-auth]
enabled = true
port = http,https
logpath = /opt/sonarqube-mcp/logs/nginx/error.log

[nginx-limit-req]
enabled = true
port = http,https
logpath = /opt/sonarqube-mcp/logs/nginx/error.log
maxretry = 10

[sshd]
enabled = true
port = ssh
logpath = /var/log/auth.log
maxretry = 3
```

### 3. Configuración de Auditoría

```bash
# /opt/sonarqube-mcp/scripts/setup_audit.sh

# Instalar auditd
sudo apt-get install auditd audispd-plugins

# Configurar reglas de auditoría
sudo tee /etc/audit/rules.d/sonarqube-mcp.rules << EOF
# Monitorear acceso a archivos de configuración
-w /opt/sonarqube-mcp/config/ -p wa -k sonarqube_config

# Monitorear cambios en Docker
-w /var/lib/docker/ -p wa -k docker_changes

# Monitorear comandos de administración
-w /usr/bin/docker -p x -k docker_commands
-w /usr/local/bin/docker-compose -p x -k docker_compose_commands

# Monitorear acceso a logs
-w /opt/sonarqube-mcp/logs/ -p r -k log_access
EOF

# Reiniciar auditd
sudo systemctl restart auditd

echo "✅ Auditoría configurada correctamente"
```

## Estrategias de Escalado

### 1. Escalado Horizontal

```yaml
# k8s/production/hpa-advanced.yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: mcp-server-hpa-advanced
  namespace: sonarqube-mcp-prod
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: mcp-server
  minReplicas: 3
  maxReplicas: 20
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
  - type: Pods
    pods:
      metric:
        name: http_requests_per_second
      target:
        type: AverageValue
        averageValue: "100"
  behavior:
    scaleDown:
      stabilizationWindowSeconds: 300
      policies:
      - type: Percent
        value: 10
        periodSeconds: 60
    scaleUp:
      stabilizationWindowSeconds: 60
      policies:
      - type: Percent
        value: 50
        periodSeconds: 60
      - type: Pods
        value: 2
        periodSeconds: 60
      selectPolicy: Max
```

### 2. Configuración de Load Balancer Avanzado

```nginx
# /opt/sonarqube-mcp/config/nginx-advanced.conf
upstream mcp_backend {
    least_conn;
    
    # Servidores principales
    server mcp-server-1:8000 max_fails=3 fail_timeout=30s weight=3;
    server mcp-server-2:8000 max_fails=3 fail_timeout=30s weight=3;
    server mcp-server-3:8000 max_fails=3 fail_timeout=30s weight=3;
    
    # Servidores de respaldo
    server mcp-server-4:8000 max_fails=3 fail_timeout=30s weight=1 backup;
    server mcp-server-5:8000 max_fails=3 fail_timeout=30s weight=1 backup;
    
    # Health check
    keepalive 32;
}

# Configuración de cache
proxy_cache_path /var/cache/nginx levels=1:2 keys_zone=api_cache:10m max_size=1g inactive=60m use_temp_path=off;

server {
    listen 443 ssl http2;
    server_name api.sonarqube-mcp.company.com;

    # Cache para endpoints específicos
    location ~* ^/api/v1/(projects|metrics|reports) {
        proxy_cache api_cache;
        proxy_cache_valid 200 5m;
        proxy_cache_use_stale error timeout updating http_500 http_502 http_503 http_504;
        proxy_cache_lock on;
        add_header X-Cache-Status $upstream_cache_status;
        
        proxy_pass http://mcp_backend;
    }
    
    # Sin cache para endpoints dinámicos
    location / {
        proxy_pass http://mcp_backend;
        proxy_no_cache 1;
        proxy_cache_bypass 1;
    }
}
```

---

## 📞 Soporte y Contacto

Para soporte técnico o consultas sobre el despliegue:

- **Documentación**: Consultar README.md y archivos en `/docker/`
- **Logs**: Revisar `/opt/sonarqube-mcp/logs/`
- **Monitoreo**: Acceder a Grafana en `https://monitoring.company.com`
- **Alertas**: Configuradas vía Prometheus Alertmanager

## 📚 Referencias Adicionales

- [Docker Production Best Practices](https://docs.docker.com/develop/dev-best-practices/)
- [Kubernetes Production Best Practices](https://kubernetes.io/docs/setup/best-practices/)
- [Nginx Security Best Practices](https://nginx.org/en/docs/http/securing_http.html)
- [PostgreSQL Performance Tuning](https://wiki.postgresql.org/wiki/Performance_Optimization)
- [Redis Production Deployment](https://redis.io/docs/manual/admin/)

---

**⚠️ Importante**: Este documento debe mantenerse actualizado con cada cambio en la infraestructura de producción. Revisar y actualizar trimestralmente.