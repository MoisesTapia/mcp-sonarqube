# Migration Guide - SonarQube MCP

This guide helps you migrate from previous versions of SonarQube MCP to the latest version.

## 🚀 Migrating to v1.1.0

### Overview of Changes

Version 1.1.0 includes several important fixes and improvements that require configuration updates:

- **MCP Server Port**: Changed from 8000 to 8001
- **Streamlit Compatibility**: Updated for Streamlit 1.50+
- **Docker Configuration**: Improved production configurations
- **Error Handling**: Enhanced session state management

### 📋 Migration Steps

#### 1. Update Environment Files

**Before (v1.0.0)**:
```env
MCP_SERVER_PORT=8000
MCP_SERVER_URL=http://mcp-server:8000
```

**After (v1.1.0)**:
```env
MCP_SERVER_PORT=8001
MCP_SERVER_URL=http://mcp-server:8001
```

**Automatic Update**:
```bash
# Update development environment
sed -i 's/8000/8001/g' docker/environments/.env.development

# Update production environment (if you have one)
sed -i 's/8000/8001/g' docker/environments/.env.production
```

#### 2. Update Docker Compose Overrides

If you have custom Docker Compose overrides, update port mappings:

**Before**:
```yaml
services:
  mcp-server:
    ports:
      - "8000:8000"
```

**After**:
```yaml
services:
  mcp-server:
    ports:
      - "8001:8001"
```

#### 3. Update Client Configurations

If you have external clients connecting to the MCP server, update their configurations:

**Before**:
```python
mcp_client = MCPClient("http://localhost:8000")
```

**After**:
```python
mcp_client = MCPClient("http://localhost:8001")
```

#### 4. Rebuild and Restart Services

```bash
# Stop current services
docker compose down

# Remove old images (optional, but recommended)
docker compose down --rmi all

# Rebuild with latest changes
docker compose -f docker/compose/base/docker-compose.yml \
                -f docker/compose/environments/development.yml \
                --env-file docker/environments/.env.development \
                up --build -d

# Verify services are healthy
docker compose ps
```

#### 5. Verify Migration

Check that all services are running on correct ports:

```bash
# Test MCP Server (new port)
curl -f http://localhost:8001/health

# Test Streamlit App
curl -f http://localhost:8501/_stcore/health

# Test SonarQube
curl -f http://localhost:9000/sonarqube/api/system/status

# Check all services status
docker compose ps
```

### 🔧 Configuration Changes

#### Environment Variables

| Variable | Old Value | New Value | Action Required |
|----------|-----------|-----------|-----------------|
| `MCP_SERVER_PORT` | 8000 | 8001 | Update in .env files |
| `MCP_SERVER_URL` | http://mcp-server:8000 | http://mcp-server:8001 | Update in .env files |

#### Docker Compose

- Removed obsolete `version: '3.8'` from production.yml
- Updated port mappings for MCP server
- Commented out unused services in production configuration

#### Streamlit Code

If you have custom Streamlit code, update deprecated parameters:

**Before**:
```python
st.plotly_chart(fig, use_container_width=True)
st.dataframe(df, use_container_width=True)
st.button("Click me", use_container_width=True)
```

**After**:
```python
st.plotly_chart(fig, width="stretch")
st.dataframe(df, width="stretch")
st.button("Click me", width="stretch")
```

### 🐛 Troubleshooting Migration Issues

#### Port Conflicts

If you encounter port conflicts after migration:

```bash
# Check what's using port 8001
netstat -tulpn | grep :8001

# If something else is using 8001, you can change it in development.yml:
# ports:
#   - "8002:8001"  # Use 8002 on host, 8001 in container
```

#### Service Not Starting

```bash
# Check logs for errors
docker compose logs mcp-server

# Common issues and solutions:
# 1. Port already in use - change host port mapping
# 2. Environment variables not updated - check .env files
# 3. Old containers still running - run `docker compose down` first
```

#### Connection Errors

```bash
# Test connectivity between services
docker compose exec streamlit-app curl http://mcp-server:8001/health

# If this fails, check:
# 1. Both containers are on the same network
# 2. MCP server is actually listening on port 8001
# 3. No firewall rules blocking internal communication
```

### 📊 Verification Checklist

After migration, verify these items:

- [ ] All services start without errors
- [ ] MCP Server responds on port 8001
- [ ] Streamlit app loads without deprecation warnings
- [ ] SonarQube connection works in Streamlit UI
- [ ] No session state errors in Streamlit logs
- [ ] Health checks pass for all services
- [ ] External clients can connect to new MCP port

### 🔄 Rollback Procedure

If you need to rollback to v1.0.0:

```bash
# Stop current services
docker compose down

# Checkout previous version
git checkout v1.0.0

# Restore old environment files
git checkout HEAD -- docker/environments/.env.development

# Start with old configuration
docker compose up --build -d
```

### 📞 Getting Help

If you encounter issues during migration:

1. **Check the logs**: `docker compose logs`
2. **Review troubleshooting**: See [docker/README.md](docker/README.md#troubleshooting)
3. **Open an issue**: [GitHub Issues](https://github.com/your-org/sonarqube-mcp/issues)
4. **Join discussions**: [GitHub Discussions](https://github.com/your-org/sonarqube-mcp/discussions)

### 🎯 Benefits of v1.1.0

After successful migration, you'll benefit from:

- **Improved Stability**: Better error handling and session management
- **Future Compatibility**: Updated for latest Streamlit versions
- **Cleaner Configuration**: Simplified Docker and environment setup
- **Better Monitoring**: Enhanced health checks and logging
- **Production Ready**: Improved production configuration templates

---

**Migration completed successfully? Great! You're now running SonarQube MCP v1.1.0 🎉**