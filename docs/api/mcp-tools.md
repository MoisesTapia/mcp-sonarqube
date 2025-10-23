# SonarQube MCP Tools API Documentation

## Overview

The SonarQube MCP server provides a comprehensive set of tools for interacting with SonarQube through the Model Context Protocol (MCP). This document describes all available tools, their parameters, and expected responses.

## Authentication

All tools require authentication through SonarQube user tokens. Configure the `SONARQUBE_TOKEN` environment variable with a valid SonarQube user token.

## Base URL Configuration

Set the `SONARQUBE_URL` environment variable to your SonarQube instance URL (e.g., `https://sonarqube.company.com`).

## Tool Categories

### Project Management Tools

#### list_projects

Lists all projects accessible to the authenticated user.

**Parameters:**
- `search` (optional): Filter projects by name or key
- `page` (optional): Page number for pagination (default: 1)
- `page_size` (optional): Number of items per page (default: 100, max: 500)

**Example Request:**
```json
{
  "name": "list_projects",
  "arguments": {
    "search": "my-project",
    "page": 1,
    "page_size": 50
  }
}
```

**Example Response:**
```json
{
  "success": true,
  "data": {
    "projects": [
      {
        "key": "my-project",
        "name": "My Project",
        "visibility": "public",
        "lastAnalysisDate": "2023-10-22T14:30:00Z",
        "revision": "abc123"
      }
    ],
    "paging": {
      "pageIndex": 1,
      "pageSize": 50,
      "total": 1
    }
  },
  "message": "Projects retrieved successfully"
}
```

#### get_project_details

Retrieves detailed information about a specific project.

**Parameters:**
- `project_key` (required): The project key

**Example Request:**
```json
{
  "name": "get_project_details",
  "arguments": {
    "project_key": "my-project"
  }
}
```

**Example Response:**
```json
{
  "success": true,
  "data": {
    "key": "my-project",
    "name": "My Project",
    "description": "Project description",
    "visibility": "public",
    "lastAnalysisDate": "2023-10-22T14:30:00Z",
    "revision": "abc123",
    "qualityGate": {
      "status": "OK",
      "name": "Sonar way"
    },
    "metrics": {
      "coverage": "85.2",
      "bugs": "0",
      "vulnerabilities": "1",
      "code_smells": "15"
    }
  },
  "message": "Project details retrieved successfully"
}
```

#### create_project

Creates a new project in SonarQube.

**Parameters:**
- `project_key` (required): Unique project key
- `name` (required): Project display name
- `visibility` (optional): Project visibility ("public" or "private", default: "private")

**Example Request:**
```json
{
  "name": "create_project",
  "arguments": {
    "project_key": "new-project",
    "name": "New Project",
    "visibility": "private"
  }
}
```

**Example Response:**
```json
{
  "success": true,
  "data": {
    "key": "new-project",
    "name": "New Project",
    "visibility": "private"
  },
  "message": "Project created successfully"
}
```

#### delete_project

Deletes a project from SonarQube.

**Parameters:**
- `project_key` (required): The project key to delete

**Example Request:**
```json
{
  "name": "delete_project",
  "arguments": {
    "project_key": "old-project"
  }
}
```

**Example Response:**
```json
{
  "success": true,
  "data": null,
  "message": "Project deleted successfully"
}
```

### Metrics and Quality Analysis Tools

#### get_measures

Retrieves metrics for a project or component.

**Parameters:**
- `component` (required): Component key (project key or file path)
- `metric_keys` (required): Comma-separated list of metric keys
- `additional_fields` (optional): Additional fields to include

**Available Metrics:**
- `coverage`: Test coverage percentage
- `bugs`: Number of bugs
- `vulnerabilities`: Number of vulnerabilities
- `code_smells`: Number of code smells
- `duplicated_lines_density`: Duplicated lines percentage
- `ncloc`: Number of lines of code
- `complexity`: Cyclomatic complexity
- `security_hotspots`: Number of security hotspots

**Example Request:**
```json
{
  "name": "get_measures",
  "arguments": {
    "component": "my-project",
    "metric_keys": "coverage,bugs,vulnerabilities,code_smells"
  }
}
```

**Example Response:**
```json
{
  "success": true,
  "data": {
    "component": {
      "key": "my-project",
      "name": "My Project",
      "measures": [
        {
          "metric": "coverage",
          "value": "85.2",
          "bestValue": false
        },
        {
          "metric": "bugs",
          "value": "0",
          "bestValue": true
        },
        {
          "metric": "vulnerabilities",
          "value": "1",
          "bestValue": false
        },
        {
          "metric": "code_smells",
          "value": "15",
          "bestValue": false
        }
      ]
    }
  },
  "message": "Measures retrieved successfully"
}
```

#### get_quality_gate_status

Retrieves the Quality Gate status for a project.

**Parameters:**
- `project_key` (required): The project key

**Example Request:**
```json
{
  "name": "get_quality_gate_status",
  "arguments": {
    "project_key": "my-project"
  }
}
```

**Example Response:**
```json
{
  "success": true,
  "data": {
    "projectStatus": {
      "status": "OK",
      "conditions": [
        {
          "status": "OK",
          "metricKey": "coverage",
          "comparator": "LT",
          "errorThreshold": "80",
          "actualValue": "85.2"
        }
      ],
      "periods": [],
      "ignoredConditions": false
    }
  },
  "message": "Quality Gate status retrieved successfully"
}
```

#### get_project_history

Retrieves historical metrics data for a project.

**Parameters:**
- `component` (required): Component key (project key)
- `metrics` (required): Comma-separated list of metric keys
- `from` (optional): Start date (YYYY-MM-DD format)
- `to` (optional): End date (YYYY-MM-DD format)

**Example Request:**
```json
{
  "name": "get_project_history",
  "arguments": {
    "component": "my-project",
    "metrics": "coverage,bugs",
    "from": "2023-01-01",
    "to": "2023-10-22"
  }
}
```

**Example Response:**
```json
{
  "success": true,
  "data": {
    "measures": [
      {
        "metric": "coverage",
        "history": [
          {
            "date": "2023-10-22T14:30:00Z",
            "value": "85.2"
          },
          {
            "date": "2023-10-21T14:30:00Z",
            "value": "84.8"
          }
        ]
      }
    ]
  },
  "message": "Project history retrieved successfully"
}
```

### Issue Management Tools

#### search_issues

Searches for issues in SonarQube.

**Parameters:**
- `componentKeys` (optional): Comma-separated list of component keys
- `severities` (optional): Comma-separated list of severities (INFO, MINOR, MAJOR, CRITICAL, BLOCKER)
- `statuses` (optional): Comma-separated list of statuses (OPEN, CONFIRMED, REOPENED, RESOLVED, CLOSED)
- `types` (optional): Comma-separated list of types (CODE_SMELL, BUG, VULNERABILITY)
- `assignees` (optional): Comma-separated list of assignee logins
- `page` (optional): Page number (default: 1)
- `page_size` (optional): Page size (default: 100, max: 500)

**Example Request:**
```json
{
  "name": "search_issues",
  "arguments": {
    "componentKeys": "my-project",
    "severities": "MAJOR,CRITICAL",
    "statuses": "OPEN",
    "page": 1,
    "page_size": 50
  }
}
```

**Example Response:**
```json
{
  "success": true,
  "data": {
    "issues": [
      {
        "key": "issue-123",
        "rule": "java:S1234",
        "severity": "MAJOR",
        "component": "my-project:src/main/java/Example.java",
        "status": "OPEN",
        "message": "Issue description",
        "assignee": "john.doe",
        "creationDate": "2023-10-22T14:30:00Z",
        "type": "CODE_SMELL"
      }
    ],
    "paging": {
      "pageIndex": 1,
      "pageSize": 50,
      "total": 1
    }
  },
  "message": "Issues retrieved successfully"
}
```

#### get_issue_details

Retrieves detailed information about a specific issue.

**Parameters:**
- `issue_key` (required): The issue key

**Example Request:**
```json
{
  "name": "get_issue_details",
  "arguments": {
    "issue_key": "issue-123"
  }
}
```

**Example Response:**
```json
{
  "success": true,
  "data": {
    "issue": {
      "key": "issue-123",
      "rule": "java:S1234",
      "severity": "MAJOR",
      "component": "my-project:src/main/java/Example.java",
      "status": "OPEN",
      "message": "Issue description",
      "assignee": "john.doe",
      "creationDate": "2023-10-22T14:30:00Z",
      "type": "CODE_SMELL",
      "textRange": {
        "startLine": 42,
        "endLine": 42,
        "startOffset": 10,
        "endOffset": 20
      },
      "flows": [],
      "comments": []
    }
  },
  "message": "Issue details retrieved successfully"
}
```

#### update_issue

Updates an issue (assign, change status, etc.).

**Parameters:**
- `issue_key` (required): The issue key
- `assign` (optional): Assignee login
- `set_severity` (optional): New severity
- `do_transition` (optional): Transition to apply (confirm, resolve, reopen, etc.)

**Example Request:**
```json
{
  "name": "update_issue",
  "arguments": {
    "issue_key": "issue-123",
    "assign": "jane.doe",
    "do_transition": "confirm"
  }
}
```

**Example Response:**
```json
{
  "success": true,
  "data": {
    "issue": {
      "key": "issue-123",
      "assignee": "jane.doe",
      "status": "CONFIRMED"
    }
  },
  "message": "Issue updated successfully"
}
```

#### add_issue_comment

Adds a comment to an issue.

**Parameters:**
- `issue_key` (required): The issue key
- `text` (required): Comment text

**Example Request:**
```json
{
  "name": "add_issue_comment",
  "arguments": {
    "issue_key": "issue-123",
    "text": "This issue needs immediate attention."
  }
}
```

**Example Response:**
```json
{
  "success": true,
  "data": {
    "comment": {
      "key": "comment-456",
      "login": "current.user",
      "htmlText": "This issue needs immediate attention.",
      "createdAt": "2023-10-22T14:30:00Z"
    }
  },
  "message": "Comment added successfully"
}
```

### Security Analysis Tools

#### search_hotspots

Searches for security hotspots.

**Parameters:**
- `projectKey` (required): Project key
- `status` (optional): Hotspot status (TO_REVIEW, REVIEWED)
- `resolution` (optional): Hotspot resolution (FIXED, SAFE)
- `page` (optional): Page number (default: 1)
- `page_size` (optional): Page size (default: 100, max: 500)

**Example Request:**
```json
{
  "name": "search_hotspots",
  "arguments": {
    "projectKey": "my-project",
    "status": "TO_REVIEW",
    "page": 1,
    "page_size": 50
  }
}
```

**Example Response:**
```json
{
  "success": true,
  "data": {
    "hotspots": [
      {
        "key": "hotspot-789",
        "component": "my-project:src/main/java/Security.java",
        "securityCategory": "sql-injection",
        "vulnerabilityProbability": "HIGH",
        "status": "TO_REVIEW",
        "line": 25,
        "message": "Make sure that executing SQL queries is safe here.",
        "creationDate": "2023-10-22T14:30:00Z"
      }
    ],
    "paging": {
      "pageIndex": 1,
      "pageSize": 50,
      "total": 1
    }
  },
  "message": "Security hotspots retrieved successfully"
}
```

#### get_hotspot_details

Retrieves detailed information about a security hotspot.

**Parameters:**
- `hotspot_key` (required): The hotspot key

**Example Request:**
```json
{
  "name": "get_hotspot_details",
  "arguments": {
    "hotspot_key": "hotspot-789"
  }
}
```

**Example Response:**
```json
{
  "success": true,
  "data": {
    "key": "hotspot-789",
    "component": "my-project:src/main/java/Security.java",
    "securityCategory": "sql-injection",
    "vulnerabilityProbability": "HIGH",
    "status": "TO_REVIEW",
    "line": 25,
    "message": "Make sure that executing SQL queries is safe here.",
    "creationDate": "2023-10-22T14:30:00Z",
    "textRange": {
      "startLine": 25,
      "endLine": 25,
      "startOffset": 0,
      "endOffset": 50
    },
    "flows": [],
    "rule": {
      "key": "java:S2077",
      "name": "SQL queries should not be vulnerable to injection attacks",
      "securityCategory": "sql-injection",
      "vulnerabilityProbability": "HIGH"
    }
  },
  "message": "Hotspot details retrieved successfully"
}
```

### Quality Gates Management Tools

#### list_quality_gates

Lists all Quality Gates.

**Parameters:** None

**Example Request:**
```json
{
  "name": "list_quality_gates",
  "arguments": {}
}
```

**Example Response:**
```json
{
  "success": true,
  "data": {
    "qualitygates": [
      {
        "id": "1",
        "name": "Sonar way",
        "isDefault": true,
        "isBuiltIn": true
      },
      {
        "id": "2",
        "name": "Custom Gate",
        "isDefault": false,
        "isBuiltIn": false
      }
    ]
  },
  "message": "Quality Gates retrieved successfully"
}
```

#### get_quality_gate_conditions

Retrieves conditions for a specific Quality Gate.

**Parameters:**
- `gate_id` (required): Quality Gate ID

**Example Request:**
```json
{
  "name": "get_quality_gate_conditions",
  "arguments": {
    "gate_id": "1"
  }
}
```

**Example Response:**
```json
{
  "success": true,
  "data": {
    "id": "1",
    "name": "Sonar way",
    "conditions": [
      {
        "id": "1",
        "metric": "coverage",
        "op": "LT",
        "error": "80"
      },
      {
        "id": "2",
        "metric": "bugs",
        "op": "GT",
        "error": "0"
      }
    ]
  },
  "message": "Quality Gate conditions retrieved successfully"
}
```

## Error Handling

All tools return a consistent error format when operations fail:

```json
{
  "success": false,
  "data": null,
  "message": "Error description",
  "metadata": {
    "error_code": "SONARQUBE_API_ERROR",
    "status_code": 404,
    "details": "Additional error details"
  }
}
```

### Common Error Codes

- `AUTHENTICATION_ERROR`: Invalid or missing authentication token
- `AUTHORIZATION_ERROR`: Insufficient permissions for the operation
- `NOT_FOUND`: Requested resource not found
- `VALIDATION_ERROR`: Invalid parameters provided
- `SONARQUBE_API_ERROR`: Error from SonarQube API
- `NETWORK_ERROR`: Network connectivity issues
- `RATE_LIMIT_ERROR`: API rate limit exceeded

## Rate Limiting

The MCP server implements rate limiting to prevent overwhelming the SonarQube API:

- Default: 100 requests per minute per user
- Burst: Up to 10 concurrent requests
- Retry logic: Automatic retry with exponential backoff for rate-limited requests

## Caching

To improve performance, the MCP server implements caching:

- Project lists: 5 minutes TTL
- Metrics: 5 minutes TTL
- Issues: 1 minute TTL
- Quality Gates: 10 minutes TTL
- User permissions: 30 minutes TTL

Cache can be bypassed by setting the `bypass_cache` parameter to `true` in any tool call.

## Pagination

Tools that return lists support pagination:

- Default page size: 100 items
- Maximum page size: 500 items
- Page numbering starts at 1

All paginated responses include a `paging` object with:
- `pageIndex`: Current page number
- `pageSize`: Number of items per page
- `total`: Total number of items available

## Best Practices

1. **Use specific filters**: Always use the most specific filters possible to reduce response size and improve performance.

2. **Handle pagination**: For large datasets, implement proper pagination handling in your client code.

3. **Cache responses**: Cache responses on the client side when appropriate to reduce API calls.

4. **Error handling**: Always check the `success` field and handle errors appropriately.

5. **Rate limiting**: Implement proper rate limiting in your client to avoid hitting API limits.

6. **Security**: Never log or expose authentication tokens in client applications.