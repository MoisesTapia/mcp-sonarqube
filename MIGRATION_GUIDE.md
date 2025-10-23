# Migration Guide: API Endpoint and Configuration Updates

This guide helps you migrate from the previous configuration to the corrected setup.

## 🚨 Critical Changes

### 1. SonarQube API Endpoint Correction

**What Changed:**
- ❌ **Old**: `/web_api/api` (incorrect)
- ✅ **New**: `/api` (correct SonarQube standard)

**Impact:**
- All API calls now work correctly
- Faster response times
- Proper SonarQube integration

### 2. MCP Server Port Correction

**What Changed:**
- ❌ **Old**: Port 8000
- ✅ **New**: Port 8001

**Impact:**
- MCP server connections now work properly
- Chat and tool execution functions correctly

### 3. Docker Compose Updates

**What Changed:**
- Updated service ports and health checks
- Corrected environment variables
- Added proper port mappings

## 📋 Migration Steps

### Step 1: Update Docker Compose

If you have an existing `docker-compose.yml`, update it with the new configuration:

```yaml
# MCP Server - Updated port and health check
mcp-server:
  ports:
    - "8001:8001"  # Changed from 8000 to 8001
  healthcheck:
    test: ["CMD", "curl", "-f", "http://localhost:8001/health"]

# Streamlit App - Updated environment variables
streamlit-app:
  environment:
    MCP_SERVER_URL: http://mcp-server:8001  # Updated port
  ports:
    - "8501:8501"
```

### Step 2: Update Environment Files

Update your `.env` files:

```bash
# Old configuration (remove these)
# MCP_SERVER_URL=http://mcp-server:8000

# New configuration (add these)
MCP_SERVER_URL=http://mcp-server:8001
SONARQUBE_URL=http://sonarqube:9000/sonarqube
```

### Step 3: Clear Old Containers

```bash
# Stop and remove old containers
docker-compose down

# Remove old images (optional, to force rebuild)
docker rmi $(docker images -q sonarqube-mcp*)

# Start with new configuration
docker-compose up -d
```

### Step 4: Update Streamlit Configuration

In the Streamlit app configuration page:

1. **Clear old configuration**: Click "Clear Configuration"
2. **Enter new URL**: `http://localhost:9000/sonarqube`
3. **Re-enter your token**: Use the same SonarQube token
4. **Test connection**: Should now work correctly

## 🔍 Verification

### Check API Endpoints

```bash
# Test SonarQube API (should return JSON)
curl http://localhost:9000/sonarqube/api/system/status

# Expected response:
# {"id":"...","version":"10.3.0.82913","status":"UP"}

# Test MCP Server (should return health status)
curl http://localhost:8001/health

# Expected response:
# {"status":"healthy","timestamp":...,"service":"sonarqube-mcp-server","sonarqube_connected":true}
```

### Check Service Logs

```bash
# Check for successful API calls in logs
docker logs sonarqube-streamlit-app | grep "API GET"

# Should see entries like:
# INFO - API GET system/status - 200 - 10.23ms
# INFO - API GET authentication/validate - 200 - 5.84ms
```

### Verify Streamlit Connection

1. Open http://localhost:8501
2. Go to Configuration page
3. Should show "✅ SonarQube is configured" and "✅ Connected to SonarQube"
4. No more "Server is not responding or is down" errors

## 🐛 Troubleshooting Migration Issues

### Issue: "Connection failed" after migration

**Solution:**
```bash
# 1. Check if services are running on correct ports
docker ps

# 2. Verify network connectivity
docker exec sonarqube-streamlit-app curl http://sonarqube-server:9000/sonarqube/api/system/status

# 3. Check environment variables
docker exec sonarqube-streamlit-app env | grep SONARQUBE
```

### Issue: MCP tools not working

**Solution:**
```bash
# 1. Verify MCP server is on port 8001
curl http://localhost:8001/health

# 2. Check MCP server logs
docker logs sonarqube-mcp-server

# 3. Restart Streamlit app
docker restart sonarqube-streamlit-app
```

### Issue: Old configuration persists

**Solution:**
```bash
# 1. Clear Docker volumes (WARNING: This removes data)
docker-compose down -v

# 2. Remove old configuration files
rm -rf data/.sonarqube_mcp/

# 3. Start fresh
docker-compose up -d
```

## 📊 Before vs After Comparison

### API Response Times

| Endpoint | Before (Incorrect) | After (Correct) |
|----------|-------------------|-----------------|
| System Status | ❌ HTML response | ✅ JSON, ~10ms |
| Authentication | ❌ Failed | ✅ Success, ~5ms |
| Projects List | ❌ Failed | ✅ Success, ~15ms |

### Service Connectivity

| Service | Before | After |
|---------|--------|-------|
| MCP Server | ❌ Port 8000 (failed) | ✅ Port 8001 (working) |
| SonarQube API | ❌ /web_api/api (404) | ✅ /api (200) |
| Streamlit UI | ⚠️ Connection errors | ✅ Fully functional |

## 📝 Configuration Checklist

After migration, verify these configurations:

- [ ] SonarQube accessible at http://localhost:9000/sonarqube
- [ ] MCP Server responding at http://localhost:8001/health
- [ ] Streamlit app working at http://localhost:8501
- [ ] API calls returning 200 status codes
- [ ] No "Server is not responding" errors
- [ ] MCP tools working in chat interface
- [ ] Project data loading correctly
- [ ] Quality metrics displaying properly

## 🔄 Rollback Plan

If you need to rollback (not recommended):

1. **Stop current services**:
   ```bash
   docker-compose down
   ```

2. **Checkout previous version**:
   ```bash
   git checkout previous-version-tag
   ```

3. **Restore old configuration**:
   ```bash
   # Use your backed up configuration files
   ```

**Note**: The old configuration had known issues and is not recommended.

## 📞 Support

If you encounter issues during migration:

1. **Check logs**: `docker logs <container-name>`
2. **Verify configuration**: Use the verification commands above
3. **Clear and restart**: Follow the troubleshooting steps
4. **Create an issue**: Include logs and configuration details

---

**Migration completed successfully?** 🎉  
You should now have a fully functional SonarQube MCP integration with correct API endpoints and service connectivity!