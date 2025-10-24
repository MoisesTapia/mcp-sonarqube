"""Issues resources for MCP."""

from typing import Any, Dict, List, Optional

from ...sonarqube_client import InputValidator
from .base import BaseResource, ResourceURI


class IssuesResource(BaseResource):
    """Resource handler for issues-related URIs."""
    
    def supports_uri(self, uri: ResourceURI) -> bool:
        """Check if this resource supports the URI."""
        return uri.resource_type == "issues"
    
    async def get_resource(self, uri: ResourceURI) -> Dict[str, Any]:
        """Get issues resource data."""
        try:
            if uri.resource_id:
                # Specific project issues: sonarqube://issues/{project_key}
                return await self._get_project_issues(uri)
            else:
                # All issues: sonarqube://issues
                return await self._get_issues_summary(uri)
        except Exception as e:
            self.logger.error(f"Failed to get issues resource {uri}: {e}")
            raise RuntimeError(f"Failed to get issues resource: {str(e)}")
    
    async def _get_project_issues(self, uri: ResourceURI) -> Dict[str, Any]:
        """Get issues for a specific project."""
        project_key = uri.resource_id
        
        async def fetch_project_issues():
            # Validate project key
            project_key_validated = InputValidator.validate_project_key(project_key)
            
            # Parse query parameters
            severities = self._parse_list_param(uri.query_params.get("severities"))
            types = self._parse_list_param(uri.query_params.get("types"))
            statuses = self._parse_list_param(uri.query_params.get("statuses"))
            assignees = self._parse_list_param(uri.query_params.get("assignees"))
            tags = self._parse_list_param(uri.query_params.get("tags"))
            created_after = uri.query_params.get("created_after")
            created_before = uri.query_params.get("created_before")
            page = int(uri.query_params.get("page", 1))
            page_size = int(uri.query_params.get("page_size", 100))
            
            # Validate parameters
            page, page_size = InputValidator.validate_pagination_params(page, page_size)
            
            # Build API parameters
            params = {
                "projectKeys": project_key_validated,
                "p": page,
                "ps": page_size,
                "additionalFields": "comments",
                "facets": "severities,types,statuses,assignees,tags"
            }
            
            if severities:
                params["severities"] = ",".join(severities)
            if types:
                params["types"] = ",".join(types)
            if statuses:
                params["statuses"] = ",".join(statuses)
            if assignees:
                params["assignees"] = ",".join(assignees)
            if tags:
                params["tags"] = ",".join(tags)
            if created_after:
                params["createdAfter"] = created_after
            if created_before:
                params["createdBefore"] = created_before
            
            # Make API call
            response = await self.client.get("/issues/search", params=params)
            
            issues = response.get("issues", [])
            components = response.get("components", [])
            rules = response.get("rules", [])
            users = response.get("users", [])
            facets = response.get("facets", [])
            paging = response.get("paging", {})
            
            # Create lookup dictionaries for enrichment
            components_dict = {comp["key"]: comp for comp in components}
            rules_dict = {rule["key"]: rule for rule in rules}
            users_dict = {user["login"]: user for user in users}
            
            # Enrich issues with additional information
            enriched_issues = []
            for issue in issues:
                enriched_issue = self._enrich_issue(issue, components_dict, rules_dict, users_dict)
                enriched_issues.append(enriched_issue)
            
            # Generate summary statistics
            summary = self._generate_issues_summary(enriched_issues, facets)
            
            return {
                "uri": str(uri),
                "resource_type": "project_issues",
                "project_key": project_key,
                "issues": enriched_issues,
                "summary": summary,
                "facets": self._process_facets(facets),
                "pagination": {
                    "page": page,
                    "page_size": page_size,
                    "total": paging.get("total", len(issues)),
                    "has_more": len(issues) == page_size
                },
                "filters": {
                    "severities": severities,
                    "types": types,
                    "statuses": statuses,
                    "assignees": assignees,
                    "tags": tags,
                    "created_after": created_after,
                    "created_before": created_before,
                },
                "metadata": {
                    "generated_at": self._get_current_timestamp(),
                    "cache_ttl": 60,  # Shorter TTL for issues as they change frequently
                }
            }
        
        return await self._get_cached_or_fetch(uri, fetch_project_issues, ttl=60)
    
    async def _get_issues_summary(self, uri: ResourceURI) -> Dict[str, Any]:
        """Get a summary of issues across all accessible projects."""
        async def fetch_issues_summary():
            # Parse query parameters
            severities = self._parse_list_param(uri.query_params.get("severities"))
            types = self._parse_list_param(uri.query_params.get("types"))
            statuses = self._parse_list_param(uri.query_params.get("statuses"))
            created_after = uri.query_params.get("created_after")
            created_before = uri.query_params.get("created_before")
            
            # Build API parameters for summary
            params = {
                "ps": 1,  # We only want the facets and totals
                "facets": "projects,severities,types,statuses,assignees"
            }
            
            if severities:
                params["severities"] = ",".join(severities)
            if types:
                params["types"] = ",".join(types)
            if statuses:
                params["statuses"] = ",".join(statuses)
            if created_after:
                params["createdAfter"] = created_after
            if created_before:
                params["createdBefore"] = created_before
            
            # Make API call
            response = await self.client.get("/issues/search", params=params)
            
            facets = response.get("facets", [])
            total = response.get("total", 0)
            
            # Process facets for summary
            processed_facets = self._process_facets(facets)
            
            # Generate high-level summary
            summary = {
                "total_issues": total,
                "by_severity": self._extract_facet_values(processed_facets, "severities"),
                "by_type": self._extract_facet_values(processed_facets, "types"),
                "by_status": self._extract_facet_values(processed_facets, "statuses"),
                "by_project": self._extract_facet_values(processed_facets, "projects"),
                "by_assignee": self._extract_facet_values(processed_facets, "assignees"),
            }
            
            return {
                "uri": str(uri),
                "resource_type": "issues_summary",
                "summary": summary,
                "facets": processed_facets,
                "filters": {
                    "severities": severities,
                    "types": types,
                    "statuses": statuses,
                    "created_after": created_after,
                    "created_before": created_before,
                },
                "metadata": {
                    "generated_at": self._get_current_timestamp(),
                    "cache_ttl": 60,
                }
            }
        
        return await self._get_cached_or_fetch(uri, fetch_issues_summary, ttl=60)
    
    def _parse_list_param(self, param: Any) -> Optional[List[str]]:
        """Parse a parameter that can be a string or list."""
        if not param:
            return None
        
        if isinstance(param, str):
            return [item.strip() for item in param.split(",") if item.strip()]
        elif isinstance(param, list):
            return param
        
        return None
    
    def _enrich_issue(
        self, 
        issue: Dict[str, Any], 
        components_dict: Dict[str, Any],
        rules_dict: Dict[str, Any],
        users_dict: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Enrich issue with additional information."""
        enriched = issue.copy()
        
        # Add component information
        component_key = issue.get("component")
        if component_key and component_key in components_dict:
            enriched["component_info"] = components_dict[component_key]
        
        # Add rule information
        rule_key = issue.get("rule")
        if rule_key and rule_key in rules_dict:
            enriched["rule_info"] = rules_dict[rule_key]
        
        # Add assignee information
        assignee = issue.get("assignee")
        if assignee and assignee in users_dict:
            enriched["assignee_info"] = users_dict[assignee]
        
        # Add author information
        author = issue.get("author")
        if author and author in users_dict:
            enriched["author_info"] = users_dict[author]
        
        # Add computed fields
        enriched["age_days"] = self._calculate_issue_age(issue.get("creationDate"))
        enriched["is_new"] = self._is_new_issue(issue.get("creationDate"))
        
        return enriched
    
    def _generate_issues_summary(self, issues: List[Dict[str, Any]], facets: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate summary statistics for issues."""
        if not issues:
            return {
                "total_count": 0,
                "by_severity": {},
                "by_type": {},
                "by_status": {},
                "by_assignee": {},
                "new_issues_count": 0,
                "avg_age_days": 0,
            }
        
        summary = {
            "total_count": len(issues),
            "by_severity": {},
            "by_type": {},
            "by_status": {},
            "by_assignee": {},
            "new_issues_count": 0,
            "avg_age_days": 0,
        }
        
        total_age = 0
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
            
            # Count new issues and calculate age
            if issue.get("is_new", False):
                summary["new_issues_count"] += 1
            
            age_days = issue.get("age_days", 0)
            total_age += age_days
        
        summary["avg_age_days"] = total_age / len(issues) if issues else 0
        
        return summary
    
    def _process_facets(self, facets: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Process facets into a more usable format."""
        processed = {}
        
        for facet in facets:
            property_name = facet.get("property")
            values = facet.get("values", [])
            
            if property_name:
                processed[property_name] = [
                    {
                        "value": value.get("val"),
                        "count": value.get("count", 0)
                    }
                    for value in values
                ]
        
        return processed
    
    def _extract_facet_values(self, facets: Dict[str, Any], facet_name: str) -> Dict[str, int]:
        """Extract values from a specific facet."""
        facet_data = facets.get(facet_name, [])
        return {item["value"]: item["count"] for item in facet_data}
    
    def _calculate_issue_age(self, creation_date: Optional[str]) -> int:
        """Calculate issue age in days."""
        if not creation_date:
            return 0
        
        try:
            from datetime import datetime
            created = datetime.fromisoformat(creation_date.replace("Z", "+00:00"))
            now = datetime.utcnow().replace(tzinfo=created.tzinfo)
            return (now - created).days
        except Exception:
            return 0
    
    def _is_new_issue(self, creation_date: Optional[str], days_threshold: int = 7) -> bool:
        """Check if issue is considered new (created within threshold days)."""
        age_days = self._calculate_issue_age(creation_date)
        return age_days <= days_threshold
    
    def _get_current_timestamp(self) -> str:
        """Get current timestamp in ISO format."""
        from datetime import datetime
        return datetime.utcnow().isoformat() + "Z"
