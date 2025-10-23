# SonarQube MCP Tools Documentation

Comprehensive documentation for all available MCP tools for SonarQube integration

## Table of Contents

- [System Tools](#system-tools)
- [Project Management Tools](#project-management-tools)
- [Metrics and Quality Tools](#metrics-and-quality-tools)
- [Cache Management Tools](#cache-management-tools)

---

## System Tools

### health_check

Check server health and SonarQube connectivity.

**Parameters:** None

**Returns:** `Dict[str, Any]`

**Example:**
```python
result = await health_check()
# Returns: {"status": "healthy", "sonarqube_connected": true, "cache_status": "enabled"}
```

---

### get_server_info

Get SonarQube server information including version and status.

**Parameters:** None

**Returns:** `Dict[str, Any]`

**Example:**
```python
result = await get_server_info()
# Returns: {"server_id": "...", "version": "10.2.1", "status": "UP"}
```

---

### get_rate_limit_status

Get current rate limiting status for SonarQube API calls.

**Parameters:** None

**Returns:** `Dict[str, Any]`

**Example:**
```python
result = await get_rate_limit_status()
# Returns: {"available_tokens": 95, "utilization_percent": 5.0}
```

---

## Project Management Tools

### list_projects

List all accessible SonarQube projects with optional filtering and pagination.

**Parameters:**

- `search` (str) - optional: Search query to filter projects by name or key
- `organization` (str) - optional: Organization key to filter projects
- `visibility` (str) - optional: Project visibility (public, private)
- `page` (int) - optional (default: 1): Page number (1-based)
- `page_size` (int) - optional (default: 100): Number of projects per page (max 500)

**Returns:** `Dict[str, Any]`

**Example:**
```python
result = await list_projects(search="backend", page=1, page_size=50)
```

---

### get_project_details

Get detailed information about a specific project including metrics and Quality Gate status.

**Parameters:**

- `project_key` (str) - **required**: Unique project key

**Returns:** `Dict[str, Any]`

**Example:**
```python
result = await get_project_details("my-project-key")
```

---

### create_project

Create a new SonarQube project with validation.

**Parameters:**

- `name` (str) - **required**: Project name
- `project_key` (str) - **required**: Unique project key
- `visibility` (str) - optional (default: "private"): Project visibility (public, private)
- `main_branch` (str) - optional: Main branch name

**Returns:** `Dict[str, Any]`

**Example:**
```python
result = await create_project("My New Project", "my-new-project", visibility="private")
```

---

### delete_project

Delete a SonarQube project with confirmation.

**Parameters:**

- `project_key` (str) - **required**: Unique project key to delete

**Returns:** `Dict[str, Any]`

**Example:**
```python
result = await delete_project("project-to-delete")
```

---

### get_project_branches

Get branches for a specific project.

**Parameters:**

- `project_key` (str) - **required**: Unique project key

**Returns:** `Dict[str, Any]`

**Example:**
```python
result = await get_project_branches("my-project")
```

---

### get_project_analyses

Get analysis history for a specific project.

**Parameters:**

- `project_key` (str) - **required**: Unique project key
- `page` (int) - optional (default: 1): Page number (1-based)
- `page_size` (int) - optional (default: 100): Number of analyses per page

**Returns:** `Dict[str, Any]`

**Example:**
```python
result = await get_project_analyses("my-project", page=1, page_size=50)
```

---

## Metrics and Quality Tools

### get_measures

Get metrics for a specific project with intelligent caching.

**Parameters:**

- `project_key` (str) - **required**: Unique project key
- `metric_keys` (List[str]) - optional: List of metric keys to retrieve (defaults to core metrics)
- `additional_fields` (List[str]) - optional: Additional fields to include (periods, metrics)

**Returns:** `Dict[str, Any]`

**Example:**
```python
result = await get_measures("my-project", metric_keys=["coverage", "bugs", "vulnerabilities"])
```

---

### get_quality_gate_status

Get Quality Gate status for a specific project with detailed conditions.

**Parameters:**

- `project_key` (str) - **required**: Unique project key

**Returns:** `Dict[str, Any]`

**Example:**
```python
result = await get_quality_gate_status("my-project")
```

---

### get_project_history

Get historical metrics data for a project with date filtering.

**Parameters:**

- `project_key` (str) - **required**: Unique project key
- `metrics` (List[str]) - optional: List of metrics to retrieve history for
- `from_date` (str) - optional: Start date (YYYY-MM-DD format)
- `to_date` (str) - optional: End date (YYYY-MM-DD format)
- `page` (int) - optional (default: 1): Page number (1-based)
- `page_size` (int) - optional (default: 1000): Number of records per page

**Returns:** `Dict[str, Any]`

**Example:**
```python
result = await get_project_history("my-project", metrics=["coverage"], from_date="2025-01-01")
```

---

### get_metrics_definitions

Get definitions of all available SonarQube metrics.

**Parameters:** None

**Returns:** `Dict[str, Any]`

**Example:**
```python
result = await get_metrics_definitions()
```

---

### analyze_project_quality

Perform comprehensive quality analysis of a project with recommendations.

**Parameters:**

- `project_key` (str) - **required**: Unique project key

**Returns:** `Dict[str, Any]`

**Example:**
```python
result = await analyze_project_quality("my-project")
# Returns comprehensive analysis with recommendations and risk assessment
```

---

## Cache Management Tools

### get_cache_info

Get comprehensive cache information and statistics.

**Parameters:** None

**Returns:** `Dict[str, Any]`

**Example:**
```python
result = await get_cache_info()
```

---

### clear_all_caches

Clear all cache entries across all data types.

**Parameters:** None

**Returns:** `Dict[str, Any]`

**Example:**
```python
result = await clear_all_caches()
```

---

### clear_cache_by_type

Clear cache entries of a specific type.

**Parameters:**

- `cache_type` (str) - **required**: Type of cache to clear (projects, metrics, quality_gates, issues, security)

**Returns:** `Dict[str, Any]`

**Example:**
```python
result = await clear_cache_by_type("projects")
```

---

### invalidate_project_caches

Invalidate all caches related to a specific project.

**Parameters:**

- `project_key` (str) - **required**: Project key to invalidate caches for

**Returns:** `Dict[str, Any]`

**Example:**
```python
result = await invalidate_project_caches("my-project")
```

---

### optimize_cache_performance

Perform cache optimization operations including cleanup of expired entries.

**Parameters:** None

**Returns:** `Dict[str, Any]`

**Example:**
```python
result = await optimize_cache_performance()
```

---

## Error Handling

All tools follow consistent error handling patterns:

- **Success Response**: `{"success": true, "data": {...}}`
- **Error Response**: `{"success": false, "error": "Error message"}`
- **Validation Errors**: Thrown for invalid parameters
- **Network Errors**: Handled with automatic retries
- **Rate Limiting**: Automatic throttling with exponential backoff

## Authentication

All tools require proper SonarQube authentication:

- Set `SONARQUBE_URL` environment variable
- Set `SONARQUBE_TOKEN` environment variable  
- Optionally set `SONARQUBE_ORGANIZATION` for organization-specific access

## Performance Features

- **Intelligent Caching**: Automatic caching with configurable TTL by data type
- **Rate Limiting**: Built-in rate limiting to prevent API overload
- **Connection Pooling**: Efficient HTTP connection reuse
- **Retry Logic**: Automatic retry with exponential backoff for transient failures
- **Pagination**: Automatic handling of large datasets