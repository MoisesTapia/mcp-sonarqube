# Docker Configuration Files

This directory contains configuration files for various services used in the SonarQube MCP Docker setup.

## 📁 Directory Structure

```
config/
├── README.md                    # This file
├── postgresql/
│   └── init/
│       └── init.sql            # PostgreSQL initialization script
├── redis/
│   └── redis.conf              # Redis server configuration
└── pgadmin/
    └── servers.json            # pgAdmin server definitions
```

## 🐘 PostgreSQL Configuration

### init.sql

**Location**: `postgresql/init/init.sql`

**Purpose**: This script runs when the PostgreSQL container starts for the first time.

**Contents**:
- Database optimization settings
- Performance tuning parameters
- Additional user creation (if needed)
- Custom schema setup (if needed)

**Customization**:
```sql
-- Add custom databases
CREATE DATABASE my_custom_db;

-- Add read-only users
CREATE USER readonly_user WITH PASSWORD 'readonly_pass';
GRANT CONNECT ON DATABASE sonarqube TO readonly_user;
GRANT USAGE ON SCHEMA public TO readonly_user;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO readonly_user;

-- Performance settings
ALTER SYSTEM SET shared_buffers = '256MB';
ALTER SYSTEM SET effective_cache_size = '1GB';
```

## 🔴 Redis Configuration

### redis.conf

**Location**: `redis/redis.conf`

**Purpose**: Redis server configuration optimized for SonarQube MCP caching needs.

**Key Settings**:
- **Memory Management**: `maxmemory-policy allkeys-lru`
- **Persistence**: AOF and RDB snapshots enabled
- **Security**: Password authentication (set via environment)
- **Performance**: Optimized for caching workloads

**Customization Examples**:
```conf
# Increase memory limit
maxmemory 512mb

# Change eviction policy
maxmemory-policy volatile-lru

# Disable persistence for pure cache
save ""
appendonly no

# Enable keyspace notifications
notify-keyspace-events Ex
```

## 🔧 pgAdmin Configuration

### servers.json

**Location**: `pgadmin/servers.json`

**Purpose**: Pre-configure PostgreSQL server connections in pgAdmin.

**Default Configuration**:
- Server Name: "SonarQube MCP PostgreSQL"
- Host: postgres (Docker service name)
- Port: 5432
- Database: postgres
- Username: sonarqube

**Adding Additional Servers**:
```json
{
  "Servers": {
    "1": {
      "Name": "SonarQube MCP PostgreSQL",
      "Group": "Servers",
      "Host": "postgres",
      "Port": 5432,
      "MaintenanceDB": "postgres",
      "Username": "sonarqube"
    },
    "2": {
      "Name": "Production PostgreSQL",
      "Group": "Production",
      "Host": "prod-postgres.example.com",
      "Port": 5432,
      "MaintenanceDB": "postgres",
      "Username": "sonarqube"
    }
  }
}
```

## 🔄 Configuration Updates

### Applying Changes

1. **PostgreSQL**: Restart the postgres container
   ```bash
   docker compose restart postgres
   ```

2. **Redis**: Restart the redis container
   ```bash
   docker compose restart redis
   ```

3. **pgAdmin**: Restart the pgadmin container
   ```bash
   docker compose restart pgadmin
   ```

### Validation

1. **PostgreSQL**:
   ```bash
   # Check if init script ran
   docker compose logs postgres | grep "init.sql"
   
   # Verify settings
   docker compose exec postgres psql -U sonarqube -d sonarqube -c "SHOW shared_preload_libraries;"
   ```

2. **Redis**:
   ```bash
   # Check configuration
   docker compose exec redis redis-cli CONFIG GET "*"
   
   # Test memory policy
   docker compose exec redis redis-cli CONFIG GET maxmemory-policy
   ```

3. **pgAdmin**:
   ```bash
   # Check if servers.json was loaded
   docker compose logs pgadmin | grep "servers.json"
   ```

## 🛠️ Troubleshooting

### Common Issues

1. **PostgreSQL won't start**:
   - Check init.sql syntax
   - Verify file permissions
   - Check logs: `docker compose logs postgres`

2. **Redis configuration not applied**:
   - Verify redis.conf syntax
   - Check file mounting: `docker compose exec redis cat /usr/local/etc/redis/redis.conf`
   - Restart container: `docker compose restart redis`

3. **pgAdmin servers not appearing**:
   - Check servers.json format
   - Verify file permissions
   - Clear pgAdmin data: `docker compose down -v && docker compose up pgadmin`

### Debug Commands

```bash
# Check file contents in containers
docker compose exec postgres cat /docker-entrypoint-initdb.d/init.sql
docker compose exec redis cat /usr/local/etc/redis/redis.conf
docker compose exec pgadmin cat /pgadmin4/servers.json

# Check file permissions
docker compose exec postgres ls -la /docker-entrypoint-initdb.d/
docker compose exec redis ls -la /usr/local/etc/redis/
docker compose exec pgadmin ls -la /pgadmin4/

# Test configurations
docker compose exec postgres psql -U sonarqube -d sonarqube -c "SELECT version();"
docker compose exec redis redis-cli ping
```

## 📝 Best Practices

1. **Version Control**: Keep configuration files in version control
2. **Documentation**: Comment your custom configurations
3. **Testing**: Test configuration changes in development first
4. **Backup**: Backup configurations before major changes
5. **Security**: Don't include passwords in configuration files (use environment variables)

## 🔒 Security Considerations

1. **File Permissions**: Ensure configuration files have appropriate permissions
2. **Sensitive Data**: Use environment variables for passwords and secrets
3. **Network Security**: Configure Redis and PostgreSQL for internal network only
4. **Access Control**: Limit pgAdmin access in production environments

## 🌐 Network Configuration

### Docker Network Details

| Network Name | Driver | Subnet | Services Connected |
|--------------|--------|--------|--------------------|
| **base_sonarqube-mcp** | bridge | 172.20.0.0/16 | All services |

### Internal Service Communication

Services communicate internally using container names:

| From Service | To Service | Internal URL | Purpose |
|--------------|------------|--------------|---------|
| MCP Server | SonarQube | http://sonarqube:9000/sonarqube | API calls |
| MCP Server | PostgreSQL | postgres:5432 | Database queries |
| MCP Server | Redis | redis:6379 | Caching |
| Streamlit App | MCP Server | http://mcp-server:8000 | Tool execution |
| Streamlit App | SonarQube | http://sonarqube:9000/sonarqube | Direct API calls |
| SonarQube | PostgreSQL | postgres:5432 | Data storage |
| Redis Commander | Redis | redis:6379 | Management |
| pgAdmin | PostgreSQL | postgres:5432 | Administration |

## 📚 Additional Resources

- [PostgreSQL Configuration Documentation](https://www.postgresql.org/docs/current/runtime-config.html)
- [Redis Configuration Documentation](https://redis.io/docs/management/config/)
- [pgAdmin Configuration Documentation](https://www.pgadmin.org/docs/pgadmin4/latest/config_py.html)