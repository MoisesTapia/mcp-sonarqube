"""Issue management tools for SonarQube MCP."""

from typing import Any, Dict, List, Optional

import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from sonarqube_client import SonarQubeClient, InputValidator
from utils import CacheManager, get_logger

logger = get_logger(__name__)


class IssueTools:
    """Tools for SonarQube issue management."""

    # Valid issue severities
    VALID_SEVERITIES = ["INFO", "MINOR", "MAJOR", "CRITICAL", "BLOCKER"]
    
    # Valid issue types
    VALID_TYPES = ["CODE_SMELL", "BUG", "VULNERABILITY", "SECURITY_HOTSPOT"]
    
    # Valid issue statuses
    VALID_STATUSES = [
        "OPEN", "CONFIRMED", "REOPENED", "RESOLVED", "CLOSED",
        "TO_REVIEW", "IN_REVIEW", "REVIEWED"
    ]
    
    # Valid issue resolutions
    VALID_RESOLUTIONS = ["FIXED", "WONTFIX", "FALSE_POSITIVE", "REMOVED", "SAFE"]

    def __init__(self, client: SonarQubeClient, cache_manager: Optional[CacheManager] = None):
        """Initialize issue tools."""
        self.client = client
        self.cache = cache_manager
        self.logger = logger

    async def search_issues(
        self,
        project_keys: Optional[List[str]] = None,
        severities: Optional[List[str]] = None,
        types: Optional[List[str]] = None,
        statuses: Optional[List[str]] = None,
        resolutions: Optional[List[str]] = None,
        assignees: Optional[List[str]] = None,
        authors: Optional[List[str]] = None,
        tags: Optional[List[str]] = None,
        created_after: Optional[str] = None,
        created_before: Optional[str] = None,
        page: int = 1,
        page_size: int = 100,
    ) -> Dict[str, Any]:
        """
        Search for issues with comprehensive filtering options.

        Args:
            project_keys: List of project keys to search in
            severities: List of severities to filter by (INFO, MINOR, MAJOR, CRITICAL, BLOCKER)
            types: List of issue types (CODE_SMELL, BUG, VULNERABILITY, SECURITY_HOTSPOT)
            statuses: List of statuses (OPEN, CONFIRMED, REOPENED, RESOLVED, CLOSED, etc.)
            resolutions: List of resolutions (FIXED, WONTFIX, FALSE_POSITIVE, etc.)
            assignees: List of assignee logins
            authors: List of author logins
            tags: List of tags to filter by
            created_after: Created after date (YYYY-MM-DD format)
            created_before: Created before date (YYYY-MM-DD format)
            page: Page number (1-based)
            page_size: Number of issues per page (max 500)

        Returns:
            Dictionary containing issues list and metadata
        """
        try:
            # Validate pagination parameters
            page, page_size = InputValidator.validate_pagination_params(page, page_size)
            
            # Validate project keys if provided
            if project_keys:
                project_keys = [InputValidator.validate_project_key(key) for key in project_keys]
            
            # Validate severities
            if severities:
                severities = [InputValidator.validate_severity(s) for s in severities]
            
            # Validate issue types
            if types:
                types = [InputValidator.validate_issue_type(t) for t in types]
            
            # Validate statuses
            if statuses:
                statuses = [InputValidator.validate_issue_status(s) for s in statuses]
            
            # Build cache key
            cache_key_params = {
                "project_keys": ",".join(sorted(project_keys or [])),
                "severities": ",".join(sorted(severities or [])),
                "types": ",".join(sorted(types or [])),
                "statuses": ",".join(sorted(statuses or [])),
                "resolutions": ",".join(sorted(resolutions or [])),
                "assignees": ",".join(sorted(assignees or [])),
                "authors": ",".join(sorted(authors or [])),
                "tags": ",".join(sorted(tags or [])),
                "created_after": created_after,
                "created_before": created_before,
                "page": page,
                "page_size": page_size,
            }
            
            # Try cache first
            if self.cache:
                cached_result = await self.cache.get("issues", "search", **cache_key_params)
                if cached_result:
                    self.logger.debug("Returning cached issue search results")
                    return cached_result

            # Build API parameters
            params = {
                "p": page,
                "ps": page_size,
            }
            
            if project_keys:
                params["projectKeys"] = ",".join(project_keys)
            if severities:
                params["severities"] = ",".join(severities)
            if types:
                params["types"] = ",".join(types)
            if statuses:
                params["statuses"] = ",".join(statuses)
            if resolutions:
                params["resolutions"] = ",".join(resolutions)
            if assignees:
                params["assignees"] = ",".join(assignees)
            if authors:
                params["authors"] = ",".join(authors)
            if tags:
                params["tags"] = ",".join(tags)
            if created_after:
                params["createdAfter"] = created_after
            if created_before:
                params["createdBefore"] = created_before

            # Make API call
            response = await self.client.get("/issues/search", params=params)
            
            # Format response
            result = {
                "issues": response.get("issues", []),
                "components": response.get("components", []),
                "rules": response.get("rules", []),
                "users": response.get("users", []),
                "paging": response.get("paging", {}),
                "total": response.get("total", 0),
                "facets": response.get("facets", []),
            }
            
            # Add summary statistics
            if result["issues"]:
                result["summary"] = self._generate_issue_summary(result["issues"])
            
            # Cache result with shorter TTL (issues change frequently)
            if self.cache:
                await self.cache.set("issues", "search", result, ttl=60, **cache_key_params)
            
            self.logger.info(f"Found {len(result['issues'])} issues")
            return result
            
        except Exception as e:
            self.logger.error(f"Failed to search issues: {e}")
            raise RuntimeError(f"Failed to search issues: {str(e)}")

    async def get_issue_details(self, issue_key: str) -> Dict[str, Any]:
        """
        Get detailed information about a specific issue.

        Args:
            issue_key: Unique issue key

        Returns:
            Dictionary containing detailed issue information
        """
        try:
            # Validate issue key
            issue_key = InputValidator.validate_issue_key(issue_key)
            
            # Try cache first
            if self.cache:
                cached_result = await self.cache.get("issues", "details", issue_key=issue_key)
                if cached_result:
                    self.logger.debug(f"Returning cached issue details for {issue_key}")
                    return cached_result

            # Make API call
            response = await self.client.get(
                "/issues/search",
                params={"issues": issue_key, "additionalFields": "comments,transitions"}
            )
            
            issues = response.get("issues", [])
            if not issues:
                raise RuntimeError(f"Issue not found: {issue_key}")
            
            issue = issues[0]
            
            # Enrich with component and rule information
            components = {comp["key"]: comp for comp in response.get("components", [])}
            rules = {rule["key"]: rule for rule in response.get("rules", [])}
            users = {user["login"]: user for user in response.get("users", [])}
            
            # Add enriched information
            if issue.get("component") and issue["component"] in components:
                issue["component_info"] = components[issue["component"]]
            
            if issue.get("rule") and issue["rule"] in rules:
                issue["rule_info"] = rules[issue["rule"]]
            
            if issue.get("assignee") and issue["assignee"] in users:
                issue["assignee_info"] = users[issue["assignee"]]
            
            if issue.get("author") and issue["author"] in users:
                issue["author_info"] = users[issue["author"]]
            
            # Cache result
            if self.cache:
                await self.cache.set("issues", "details", issue, issue_key=issue_key)
            
            self.logger.info(f"Retrieved details for issue {issue_key}")
            return issue
            
        except Exception as e:
            self.logger.error(f"Failed to get issue details for {issue_key}: {e}")
            raise RuntimeError(f"Failed to get issue details: {str(e)}")

    async def update_issue(
        self,
        issue_key: str,
        assign: Optional[str] = None,
        transition: Optional[str] = None,
        comment: Optional[str] = None,
        severity: Optional[str] = None,
        type: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Update an issue (assign, transition, comment, etc.).

        Args:
            issue_key: Unique issue key
            assign: Login of user to assign issue to
            transition: Transition to apply (confirm, resolve, reopen, etc.)
            comment: Comment to add to the issue
            severity: New severity (INFO, MINOR, MAJOR, CRITICAL, BLOCKER)
            type: New type (CODE_SMELL, BUG, VULNERABILITY)

        Returns:
            Dictionary containing update confirmation
        """
        try:
            # Validate issue key
            issue_key = InputValidator.validate_issue_key(issue_key)
            
            # Validate severity if provided
            if severity:
                severity = InputValidator.validate_severity(severity)
            
            # Validate type if provided
            if type:
                type = InputValidator.validate_issue_type(type)
            
            # Validate assignee if provided
            if assign:
                assign = InputValidator.validate_user_login(assign)
            
            # Sanitize comment if provided
            if comment:
                comment = InputValidator.sanitize_search_query(comment)
            
            updates_made = []
            
            # Assign issue
            if assign:
                await self.client.post(
                    "/issues/assign",
                    data={"issue": issue_key, "assignee": assign}
                )
                updates_made.append(f"assigned to {assign}")
            
            # Apply transition
            if transition:
                await self.client.post(
                    "/issues/do_transition",
                    data={"issue": issue_key, "transition": transition}
                )
                updates_made.append(f"transitioned to {transition}")
            
            # Add comment
            if comment:
                await self.client.post(
                    "/issues/add_comment",
                    data={"issue": issue_key, "text": comment}
                )
                updates_made.append("comment added")
            
            # Update severity
            if severity:
                await self.client.post(
                    "/issues/set_severity",
                    data={"issue": issue_key, "severity": severity}
                )
                updates_made.append(f"severity set to {severity}")
            
            # Update type
            if type:
                await self.client.post(
                    "/issues/set_type",
                    data={"issue": issue_key, "type": type}
                )
                updates_made.append(f"type set to {type}")
            
            # Invalidate caches
            if self.cache:
                await self.cache.delete("issues", "details", issue_key=issue_key)
                await self.cache.invalidate_pattern("issues", "search")
            
            result = {
                "success": True,
                "issue_key": issue_key,
                "updates_made": updates_made,
                "message": f"Issue {issue_key} updated: {', '.join(updates_made)}",
            }
            
            self.logger.info(f"Updated issue {issue_key}: {', '.join(updates_made)}")
            return result
            
        except Exception as e:
            self.logger.error(f"Failed to update issue {issue_key}: {e}")
            raise RuntimeError(f"Failed to update issue: {str(e)}")

    async def add_issue_comment(
        self,
        issue_key: str,
        comment_text: str,
    ) -> Dict[str, Any]:
        """
        Add a comment to an issue.

        Args:
            issue_key: Unique issue key
            comment_text: Comment text to add

        Returns:
            Dictionary containing comment confirmation
        """
        try:
            # Validate issue key
            issue_key = InputValidator.validate_issue_key(issue_key)
            
            # Sanitize comment text
            if not comment_text or not comment_text.strip():
                raise ValueError("Comment text cannot be empty")
            
            comment_text = InputValidator.sanitize_search_query(comment_text.strip())
            
            # Make API call
            await self.client.post(
                "/issues/add_comment",
                data={"issue": issue_key, "text": comment_text}
            )
            
            # Invalidate caches
            if self.cache:
                await self.cache.delete("issues", "details", issue_key=issue_key)
            
            result = {
                "success": True,
                "issue_key": issue_key,
                "comment_added": True,
                "message": f"Comment added to issue {issue_key}",
            }
            
            self.logger.info(f"Added comment to issue {issue_key}")
            return result
            
        except Exception as e:
            self.logger.error(f"Failed to add comment to issue {issue_key}: {e}")
            raise RuntimeError(f"Failed to add comment: {str(e)}")

    async def get_issue_transitions(self, issue_key: str) -> Dict[str, Any]:
        """
        Get available transitions for an issue.

        Args:
            issue_key: Unique issue key

        Returns:
            Dictionary containing available transitions
        """
        try:
            # Validate issue key
            issue_key = InputValidator.validate_issue_key(issue_key)
            
            # Make API call
            response = await self.client.get(
                "/issues/transitions",
                params={"issue": issue_key}
            )
            
            result = {
                "issue_key": issue_key,
                "transitions": response.get("transitions", []),
            }
            
            self.logger.info(f"Retrieved {len(result['transitions'])} transitions for issue {issue_key}")
            return result
            
        except Exception as e:
            self.logger.error(f"Failed to get transitions for issue {issue_key}: {e}")
            raise RuntimeError(f"Failed to get issue transitions: {str(e)}")

    def _generate_issue_summary(self, issues: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate summary statistics for a list of issues."""
        if not issues:
            return {}
        
        summary = {
            "total_count": len(issues),
            "by_severity": {},
            "by_type": {},
            "by_status": {},
            "by_assignee": {},
        }
        
        for issue in issues:
            # Count by severity
            severity = issue.get("severity", "UNKNOWN")
            summary["by_severity"][severity] = summary["by_severity"].get(severity, 0) + 1
            
            # Count by type
            issue_type = issue.get("type", "UNKNOWN")
            summary["by_type"][issue_type] = summary["by_type"].get(issue_type, 0) + 1
            
            # Count by status
            status = issue.get("status", "UNKNOWN")
            summary["by_status"][status] = summary["by_status"].get(status, 0) + 1
            
            # Count by assignee
            assignee = issue.get("assignee", "UNASSIGNED")
            summary["by_assignee"][assignee] = summary["by_assignee"].get(assignee, 0) + 1
        
        return summary
