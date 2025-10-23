# SonarQube MCP Troubleshooting Guide

## Overview

This guide covers common issues you might encounter when using the SonarQube MCP system and provides step-by-step solutions to resolve them.

## Quick Diagnostic Commands

Before diving into specific issues, run these commands to get an overview of system health:

```bash
# Check MCP server health
curl -f http://localhost:8000/health

# Check Streamlit application health
curl -f http://localhost:8501/_stcore/health

# Check SonarQube connectivity
curl -u your_token: https://your-sonarqube-instance.com/api/system/status

# Check Docker containers (if using Docker)
docker-compose ps

# Check Kubernetes pods (if using Kubernetes)
kubectl get pods -n sonarqube-mcp
```

## Connection Issues

### Issue: Cannot Connect to SonarQube

**Symptoms:**
- Error messages about connection timeouts
- "Connection refused" errors
- MCP tools returning network errors

**Diagnostic Steps:**

1. **Verify SonarQube URL**:
   ```bash
   curl -I https://your-sonarqube-instance.com
   ```

2. **Check network connectivity**:
   ```bash
   ping your-sonarqube-instance.com
   telnet your-sonarqube-instance.com 443  # For HTTPS
   telnet your-sonarqube-instance.com 80   # For HTTP
   ```

3. **Test SonarQube API directly**:
   ```bash
   curl -u your_token: https://your-sonarqube-instance.com/api/system/status
   ```

**Solutions:**

1. **Incorrect URL**: Ensure the SonarQube URL is correct and includes the proper protocol (http/https)
2. **Firewall/Network**: Check firewall rules and network policies
3. **SonarQube Down**: Verify SonarQube server is running and healthy
4. **SSL Issues**: For HTTPS, ensure SSL certificates are valid
5. **Proxy Settings**: Configure proxy settings if behind a corporate proxy

**Example Fix:**
```bash
# Update environment variable with correct URL
export SONARQUBE_URL="https://sonarqube.company.com"

# Or update in .env file
echo "SONARQUBE_URL=https://sonarqube.company.com" >> .env
```

### Issue: SSL Certificate Errors

**Symptoms:**
- SSL verification errors
- Certificate validation failures
- HTTPS connection issues

**Solutions:**

1. **Update CA certificates**:
   ```bash
   # On Ubuntu/Debian
   sudo apt-get update && sudo apt-get install ca-certificates
   
   # On CentOS/RHEL
   sudo yum update ca-certificates
   ```

2. **Disable SSL verification (not recommended for production)**:
   ```bash
   export PYTHONHTTPSVERIFY=0
   ```

3. **Add custom CA certificate**:
   ```bash
   # Copy certificate to system store
   sudo cp your-ca-cert.crt /usr/local/share/ca-certificates/
   sudo update-ca-certificates
   ```

## Authentication Issues

### Issue: Authentication Failed

**Symptoms:**
- 401 Unauthorized errors
- "Invalid token" messages
- Permission denied errors

**Diagnostic Steps:**

1. **Validate token format**:
   ```bash
   echo "Token length: ${#SONARQUBE_TOKEN}"
   echo "Token starts with: ${SONARQUBE_TOKEN:0:4}"
   ```

2. **Test token directly**:
   ```bash
   curl -u $SONARQUBE_TOKEN: https://your-sonarqube-instance.com/api/authentication/validate
   ```

3. **Check token permissions**:
   ```bash
   curl -u $SONARQUBE_TOKEN: https://your-sonarqube-instance.com/api/permissions/users
   ```

**Solutions:**

1. **Regenerate Token**:
   - Log into SonarQube
   - Go to My Account → Security
   - Revoke old token and generate new one

2. **Check Token Permissions**:
   - Ensure token has required permissions:
     - Browse projects
     - Execute analysis
     - Administer issues
     - Administer security hotspots

3. **Update Token in Configuration**:
   ```bash
   # Update environment variable
   export SONARQUBE_TOKEN="new_token_here"
   
   # Or update in .env file
   sed -i 's/SONARQUBE_TOKEN=.*/SONARQUBE_TOKEN=new_token_here/' .env
   ```

### Issue: Token Expired

**Symptoms:**
- Authentication worked before but now fails
- Token validation returns expired status

**Solutions:**

1. **Check token expiration in SonarQube**:
   - Go to My Account → Security
   - Check token expiration date

2. **Generate new token with longer expiration**:
   - Create new token with appropriate expiration
   - Update configuration with new token

3. **Implement token rotation**:
   ```bash
   # Script to rotate tokens
   #!/bin/bash
   OLD_TOKEN=$SONARQUBE_TOKEN
   NEW_TOKEN="new_generated_token"
   
   # Update configuration
   export SONARQUBE_TOKEN=$NEW_TOKEN
   
   # Restart services
   docker-compose restart mcp-server streamlit-app
   ```

## Performance Issues

### Issue: Slow Response Times

**Symptoms:**
- API calls taking longer than expected
- Timeouts on large requests
- UI feels sluggish

**Diagnostic Steps:**

1. **Check response times**:
   ```bash
   time curl -u $SONARQUBE_TOKEN: https://your-sonarqube-instance.com/api/projects/search
   ```

2. **Monitor resource usage**:
   ```bash
   # Docker containers
   docker stats
   
   # System resources
   top
   htop
   ```

3. **Check network latency**:
   ```bash
   ping -c 10 your-sonarqube-instance.com
   ```

**Solutions:**

1. **Enable Caching**:
   ```bash
   # Configure Redis for caching
   export REDIS_URL="redis://localhost:6379/0"
   export CACHE_TTL=300
   ```

2. **Increase Timeout Values**:
   ```bash
   export REQUEST_TIMEOUT=60
   export MAX_RETRIES=5
   ```

3. **Optimize Queries**:
   - Use specific filters in API calls
   - Implement pagination for large datasets
   - Cache frequently accessed data

4. **Scale Resources**:
   ```yaml
   # In docker-compose.yml
   services:
     mcp-server:
       deploy:
         resources:
           limits:
             memory: 2G
             cpus: '1.0'
   ```

### Issue: High Memory Usage

**Symptoms:**
- Out of memory errors
- System becoming unresponsive
- Container restarts due to memory limits

**Solutions:**

1. **Increase Memory Limits**:
   ```yaml
   # Docker Compose
   services:
     mcp-server:
       mem_limit: 2g
   ```

   ```yaml
   # Kubernetes
   resources:
     limits:
       memory: "2Gi"
     requests:
       memory: "1Gi"
   ```

2. **Optimize Cache Settings**:
   ```bash
   export CACHE_TTL=60  # Reduce cache time
   export MAX_CACHE_SIZE=100  # Limit cache size
   ```

3. **Enable Garbage Collection**:
   ```bash
   export PYTHONOPTIMIZE=2
   export PYTHONUNBUFFERED=1
   ```

## Docker Issues

### Issue: Containers Not Starting

**Symptoms:**
- Docker containers exit immediately
- Services fail to start
- Port binding errors

**Diagnostic Steps:**

1. **Check container logs**:
   ```bash
   docker-compose logs mcp-server
   docker-compose logs streamlit-app
   docker-compose logs postgres
   ```

2. **Check port availability**:
   ```bash
   netstat -tulpn | grep :8000
   netstat -tulpn | grep :8501
   ```

3. **Verify environment variables**:
   ```bash
   docker-compose config
   ```

**Solutions:**

1. **Port Conflicts**:
   ```yaml
   # Change ports in docker-compose.yml
   services:
     mcp-server:
       ports:
         - "8001:8000"  # Use different host port
   ```

2. **Missing Environment Variables**:
   ```bash
   # Check .env file exists and has required variables
   cat .env
   
   # Add missing variables
   echo "SONARQUBE_TOKEN=your_token" >> .env
   ```

3. **Permission Issues**:
   ```bash
   # Fix file permissions
   sudo chown -R $USER:$USER .
   chmod +x scripts/*.sh
   ```

### Issue: Database Connection Errors

**Symptoms:**
- PostgreSQL connection failures
- Database initialization errors
- Data persistence issues

**Solutions:**

1. **Check PostgreSQL Status**:
   ```bash
   docker-compose logs postgres
   docker-compose exec postgres pg_isready -U sonarqube
   ```

2. **Reset Database**:
   ```bash
   # Stop services
   docker-compose down
   
   # Remove volumes
   docker-compose down -v
   
   # Restart
   docker-compose up -d
   ```

3. **Check Database Configuration**:
   ```bash
   # Verify environment variables
   echo $POSTGRES_DB
   echo $POSTGRES_USER
   # Don't echo password for security
   ```

## Kubernetes Issues

### Issue: Pods Not Starting

**Symptoms:**
- Pods stuck in Pending or CrashLoopBackOff state
- ImagePullBackOff errors
- Resource constraints

**Diagnostic Steps:**

1. **Check pod status**:
   ```bash
   kubectl get pods -n sonarqube-mcp
   kubectl describe pod <pod-name> -n sonarqube-mcp
   ```

2. **Check logs**:
   ```bash
   kubectl logs <pod-name> -n sonarqube-mcp
   kubectl logs <pod-name> -n sonarqube-mcp --previous
   ```

3. **Check events**:
   ```bash
   kubectl get events -n sonarqube-mcp --sort-by='.lastTimestamp'
   ```

**Solutions:**

1. **Image Pull Issues**:
   ```bash
   # Check image exists
   docker pull your-registry/mcp-server:latest
   
   # Update image pull policy
   kubectl patch deployment mcp-server -n sonarqube-mcp -p '{"spec":{"template":{"spec":{"containers":[{"name":"mcp-server","imagePullPolicy":"Always"}]}}}}'
   ```

2. **Resource Constraints**:
   ```bash
   # Check node resources
   kubectl top nodes
   kubectl describe nodes
   
   # Adjust resource requests
   kubectl patch deployment mcp-server -n sonarqube-mcp -p '{"spec":{"template":{"spec":{"containers":[{"name":"mcp-server","resources":{"requests":{"memory":"256Mi","cpu":"100m"}}}]}}}}'
   ```

3. **Secret Issues**:
   ```bash
   # Check secrets exist
   kubectl get secrets -n sonarqube-mcp
   
   # Recreate secrets
   kubectl delete secret sonarqube-mcp-secrets -n sonarqube-mcp
   kubectl create secret generic sonarqube-mcp-secrets \
     --from-literal=sonarqube-token=your_token \
     -n sonarqube-mcp
   ```

### Issue: Service Discovery Problems

**Symptoms:**
- Services cannot reach each other
- DNS resolution failures
- Network connectivity issues

**Solutions:**

1. **Check Service Configuration**:
   ```bash
   kubectl get services -n sonarqube-mcp
   kubectl describe service mcp-server-service -n sonarqube-mcp
   ```

2. **Test Network Connectivity**:
   ```bash
   # Test from one pod to another
   kubectl exec -it <pod-name> -n sonarqube-mcp -- nslookup mcp-server-service
   kubectl exec -it <pod-name> -n sonarqube-mcp -- curl http://mcp-server-service:8000/health
   ```

3. **Check Network Policies**:
   ```bash
   kubectl get networkpolicies -n sonarqube-mcp
   kubectl describe networkpolicy sonarqube-mcp-network-policy -n sonarqube-mcp
   ```

## Application-Specific Issues

### Issue: MCP Tools Not Working

**Symptoms:**
- Tool calls return errors
- Unexpected responses from tools
- Missing data in responses

**Diagnostic Steps:**

1. **Test individual tools**:
   ```bash
   # Test with curl
   curl -X POST http://localhost:8000/tools/list_projects \
     -H "Content-Type: application/json" \
     -d '{"arguments": {}}'
   ```

2. **Check MCP server logs**:
   ```bash
   # Docker
   docker-compose logs mcp-server
   
   # Kubernetes
   kubectl logs -l app=mcp-server -n sonarqube-mcp
   ```

**Solutions:**

1. **Restart MCP Server**:
   ```bash
   # Docker
   docker-compose restart mcp-server
   
   # Kubernetes
   kubectl rollout restart deployment/mcp-server -n sonarqube-mcp
   ```

2. **Clear Cache**:
   ```bash
   # Connect to Redis and clear cache
   redis-cli FLUSHALL
   ```

3. **Update Configuration**:
   ```bash
   # Check and update environment variables
   kubectl edit configmap sonarqube-mcp-config -n sonarqube-mcp
   ```

### Issue: Streamlit Application Errors

**Symptoms:**
- White screen or error page
- Configuration not saving
- UI components not loading

**Solutions:**

1. **Clear Browser Cache**:
   - Clear browser cache and cookies
   - Try incognito/private browsing mode

2. **Restart Streamlit Application**:
   ```bash
   # Docker
   docker-compose restart streamlit-app
   
   # Kubernetes
   kubectl rollout restart deployment/streamlit-app -n sonarqube-mcp
   ```

3. **Check Streamlit Configuration**:
   ```bash
   # Verify Streamlit config
   cat .streamlit/config.toml
   ```

## Monitoring and Logging

### Enable Debug Logging

1. **MCP Server**:
   ```bash
   export LOG_LEVEL=DEBUG
   export SERVER_DEBUG=true
   ```

2. **Streamlit Application**:
   ```bash
   export STREAMLIT_LOGGER_LEVEL=debug
   ```

### Collect Diagnostic Information

Create a diagnostic script:

```bash
#!/bin/bash
# diagnostic.sh

echo "=== System Information ==="
uname -a
docker --version
kubectl version --client

echo "=== Environment Variables ==="
env | grep SONARQUBE
env | grep REDIS
env | grep LOG_LEVEL

echo "=== Service Status ==="
if command -v docker-compose &> /dev/null; then
    docker-compose ps
fi

if command -v kubectl &> /dev/null; then
    kubectl get pods -n sonarqube-mcp
fi

echo "=== Health Checks ==="
curl -f http://localhost:8000/health || echo "MCP server health check failed"
curl -f http://localhost:8501/_stcore/health || echo "Streamlit health check failed"

echo "=== Recent Logs ==="
if command -v docker-compose &> /dev/null; then
    docker-compose logs --tail=50 mcp-server
fi
```

## Getting Help

### Before Seeking Help

1. **Check this troubleshooting guide**
2. **Review application logs**
3. **Verify configuration**
4. **Test with minimal setup**

### Information to Provide

When reporting issues, include:

1. **System Information**:
   - Operating system and version
   - Docker/Kubernetes version
   - Python version

2. **Configuration**:
   - Environment variables (redact sensitive data)
   - Configuration files
   - Deployment method used

3. **Error Details**:
   - Complete error messages
   - Steps to reproduce
   - Expected vs actual behavior

4. **Logs**:
   - Application logs
   - System logs
   - Network traces (if relevant)

### Support Channels

1. **GitHub Issues**: For bug reports and feature requests
2. **Documentation**: Check the latest documentation
3. **Community Forums**: For general questions and discussions
4. **Stack Overflow**: Tag questions with `sonarqube-mcp`

## Prevention and Best Practices

### Regular Maintenance

1. **Update Dependencies**:
   ```bash
   pip install --upgrade -r requirements.txt
   docker-compose pull
   ```

2. **Monitor Resource Usage**:
   - Set up monitoring and alerting
   - Regular health checks
   - Capacity planning

3. **Backup Configuration**:
   - Regular backups of configuration
   - Version control for manifests
   - Document custom changes

### Security Best Practices

1. **Token Management**:
   - Regular token rotation
   - Principle of least privilege
   - Secure storage of credentials

2. **Network Security**:
   - Use HTTPS where possible
   - Implement network policies
   - Regular security updates

3. **Access Control**:
   - Implement proper RBAC
   - Regular access reviews
   - Audit logging