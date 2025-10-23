"""Test fixtures for SonarQube API responses."""

from datetime import datetime
from typing import Any, Dict, List


class SonarQubeFixtures:
    """Collection of SonarQube API response fixtures."""

    @staticmethod
    def system_status() -> Dict[str, Any]:
        """System status response."""
        return {
            "id": "test-server-id",
            "version": "10.2.1",
            "status": "UP"
        }

    @staticmethod
    def authentication_validate() -> Dict[str, Any]:
        """Authentication validation response."""
        return {
            "valid": True
        }

    @staticmethod
    def project_list() -> Dict[str, Any]:
        """Projects list response."""
        return {
            "paging": {
                "pageIndex": 1,
                "pageSize": 100,
                "total": 2
            },
            "components": [
                {
                    "key": "project-1",
                    "name": "Test Project 1",
                    "qualifier": "TRK",
                    "visibility": "public",
                    "lastAnalysisDate": "2025-10-22T10:00:00+0000"
                },
                {
                    "key": "project-2",
                    "name": "Test Project 2",
                    "qualifier": "TRK",
                    "visibility": "private",
                    "lastAnalysisDate": "2025-10-21T15:30:00+0000"
                }
            ]
        }

    @staticmethod
    def project_details() -> Dict[str, Any]:
        """Single project details response."""
        return {
            "component": {
                "key": "project-1",
                "name": "Test Project 1",
                "qualifier": "TRK",
                "visibility": "public",
                "lastAnalysisDate": "2025-10-22T10:00:00+0000",
                "revision": "abc123def456"
            }
        }

    @staticmethod
    def project_measures() -> Dict[str, Any]:
        """Project measures response."""
        return {
            "component": {
                "key": "project-1",
                "name": "Test Project 1",
                "qualifier": "TRK"
            },
            "metrics": [
                {
                    "key": "coverage",
                    "value": "85.5"
                },
                {
                    "key": "bugs",
                    "value": "3"
                },
                {
                    "key": "vulnerabilities",
                    "value": "1"
                },
                {
                    "key": "code_smells",
                    "value": "12"
                }
            ]
        }

    @staticmethod
    def quality_gate_status() -> Dict[str, Any]:
        """Quality gate status response."""
        return {
            "projectStatus": {
                "status": "OK",
                "conditions": [
                    {
                        "status": "OK",
                        "metricKey": "coverage",
                        "comparator": "LT",
                        "errorThreshold": "80",
                        "actualValue": "85.5"
                    },
                    {
                        "status": "OK",
                        "metricKey": "bugs",
                        "comparator": "GT",
                        "errorThreshold": "0",
                        "actualValue": "3"
                    }
                ],
                "ignoredConditions": False
            }
        }

    @staticmethod
    def issues_search() -> Dict[str, Any]:
        """Issues search response."""
        return {
            "total": 2,
            "p": 1,
            "ps": 100,
            "paging": {
                "pageIndex": 1,
                "pageSize": 100,
                "total": 2
            },
            "issues": [
                {
                    "key": "issue-1",
                    "rule": "java:S1234",
                    "severity": "MAJOR",
                    "component": "project-1:src/main/java/Test.java",
                    "project": "project-1",
                    "line": 42,
                    "status": "OPEN",
                    "message": "This is a test issue",
                    "type": "BUG",
                    "creationDate": "2025-10-22T09:00:00+0000",
                    "updateDate": "2025-10-22T09:00:00+0000"
                },
                {
                    "key": "issue-2",
                    "rule": "java:S5678",
                    "severity": "CRITICAL",
                    "component": "project-1:src/main/java/Another.java",
                    "project": "project-1",
                    "line": 15,
                    "status": "CONFIRMED",
                    "message": "Critical security issue",
                    "type": "VULNERABILITY",
                    "assignee": "john.doe",
                    "creationDate": "2025-10-21T14:30:00+0000",
                    "updateDate": "2025-10-22T08:15:00+0000"
                }
            ],
            "components": [
                {
                    "key": "project-1:src/main/java/Test.java",
                    "name": "Test.java",
                    "qualifier": "FIL",
                    "path": "src/main/java/Test.java",
                    "language": "java"
                }
            ],
            "rules": [
                {
                    "key": "java:S1234",
                    "name": "Test Rule",
                    "lang": "java",
                    "langName": "Java",
                    "type": "BUG",
                    "severity": "MAJOR",
                    "status": "READY"
                }
            ]
        }

    @staticmethod
    def security_hotspots() -> Dict[str, Any]:
        """Security hotspots response."""
        return {
            "paging": {
                "pageIndex": 1,
                "pageSize": 100,
                "total": 1
            },
            "hotspots": [
                {
                    "key": "hotspot-1",
                    "component": "project-1:src/main/java/Security.java",
                    "project": "project-1",
                    "securityCategory": "sql-injection",
                    "vulnerabilityProbability": "HIGH",
                    "status": "TO_REVIEW",
                    "line": 25,
                    "message": "Potential SQL injection vulnerability",
                    "assignee": "security.team",
                    "creationDate": "2025-10-22T11:00:00+0000",
                    "updateDate": "2025-10-22T11:00:00+0000"
                }
            ]
        }

    @staticmethod
    def users_search() -> Dict[str, Any]:
        """Users search response."""
        return {
            "paging": {
                "pageIndex": 1,
                "pageSize": 50,
                "total": 2
            },
            "users": [
                {
                    "login": "john.doe",
                    "name": "John Doe",
                    "email": "john.doe@example.com",
                    "active": True,
                    "local": True,
                    "groups": ["developers", "users"]
                },
                {
                    "login": "jane.smith",
                    "name": "Jane Smith",
                    "email": "jane.smith@example.com",
                    "active": True,
                    "local": False,
                    "externalIdentity": "jane.smith@ldap",
                    "externalProvider": "LDAP",
                    "groups": ["admins", "users"]
                }
            ]
        }

    @staticmethod
    def quality_gates_list() -> Dict[str, Any]:
        """Quality gates list response."""
        return {
            "qualitygates": [
                {
                    "id": "1",
                    "name": "Sonar way",
                    "isDefault": True,
                    "isBuiltIn": True
                },
                {
                    "id": "2",
                    "name": "Custom Gate",
                    "isDefault": False,
                    "isBuiltIn": False
                }
            ]
        }

    @staticmethod
    def error_response(status_code: int, message: str) -> Dict[str, Any]:
        """Generic error response."""
        return {
            "errors": [
                {
                    "msg": message
                }
            ]
        }

    @staticmethod
    def authentication_error() -> Dict[str, Any]:
        """Authentication error response."""
        return {
            "errors": [
                {
                    "msg": "Authentication failed. Please check your token."
                }
            ]
        }

    @staticmethod
    def authorization_error() -> Dict[str, Any]:
        """Authorization error response."""
        return {
            "errors": [
                {
                    "msg": "Insufficient privileges"
                }
            ]
        }

    @staticmethod
    def rate_limit_error() -> Dict[str, Any]:
        """Rate limit error response."""
        return {
            "errors": [
                {
                    "msg": "Rate limit exceeded. Please try again later."
                }
            ]
        }

    @staticmethod
    def server_error() -> Dict[str, Any]:
        """Server error response."""
        return {
            "errors": [
                {
                    "msg": "Internal server error"
                }
            ]
        }