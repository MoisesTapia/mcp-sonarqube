"""Code review summary prompt for change analysis."""

from typing import Any, Dict, List

from ...sonarqube_client import InputValidator
from .base import BasePrompt


class CodeReviewSummaryPrompt(BasePrompt):
    """Prompt for code review summary and change analysis."""
    
    def get_name(self) -> str:
        return "code_review_summary"
    
    def get_description(self) -> str:
        return "Generate a comprehensive code review summary focusing on new issues, quality changes, and recommendations"
    
    def get_arguments(self) -> List[Dict[str, Any]]:
        return [
            {
                "name": "project_key",
                "description": "The SonarQube project key to analyze",
                "required": True,
                "type": "string"
            },
            {
                "name": "branch",
                "description": "Specific branch to analyze (optional)",
                "required": False,
                "type": "string"
            },
            {
                "name": "pull_request",
                "description": "Pull request key to analyze (optional)",
                "required": False,
                "type": "string"
            },
            {
                "name": "focus_on_new_code",
                "description": "Focus analysis on new/changed code only",
                "required": False,
                "type": "boolean",
                "default": True
            },
            {
                "name": "include_test_coverage",
                "description": "Include test coverage analysis in the review",
                "required": False,
                "type": "boolean",
                "default": True
            }
        ]
    
    async def execute(self, arguments: Dict[str, Any]) -> str:
        """Execute the code review summary prompt."""
        project_key = arguments.get("project_key")
        branch = arguments.get("branch")
        pull_request = arguments.get("pull_request")
        focus_on_new_code = arguments.get("focus_on_new_code", True)
        include_test_coverage = arguments.get("include_test_coverage", True)
        
        if not project_key:
            raise ValueError("project_key is required")
        
        async def generate_review():
            # Validate project key
            project_key_validated = InputValidator.validate_project_key(project_key)
            
            # Get project information
            project_info = await self._get_project_info(project_key_validated)
            
            # Get new code metrics
            new_code_metrics = await self._get_new_code_metrics(project_key_validated, branch, pull_request)
            
            # Get new issues
            new_issues = await self._get_new_issues(project_key_validated, branch, pull_request)
            
            # Get Quality Gate status
            quality_gate = await self._get_quality_gate_status(project_key_validated, branch, pull_request)
            
            # Get test coverage information
            coverage_info = None
            if include_test_coverage:
                coverage_info = await self._get_coverage_info(project_key_validated, branch, pull_request)
            
            # Generate code review summary
            review = self._generate_code_review_summary(
                project_info, new_code_metrics, new_issues, quality_gate, 
                coverage_info, focus_on_new_code, branch, pull_request
            )
            
            return review
        
        return await self._get_cached_or_execute(
            self.get_name(),
            generate_review,
            ttl=300,
            project_key=project_key,
            branch=branch or "main",
            pull_request=pull_request or "none",
            focus_on_new_code=focus_on_new_code,
            include_test_coverage=include_test_coverage
        )
    
    async def _get_project_info(self, project_key: str) -> Dict[str, Any]:
        """Get basic project information."""
        try:
            response = await self.client.get(
                "/projects/search",
                params={"projects": project_key}
            )
            
            projects = response.get("components", [])
            if not projects:
                raise RuntimeError(f"Project not found: {project_key}")
            
            return projects[0]
        except Exception as e:
            self.logger.error(f"Failed to get project info for {project_key}: {e}")
            return {"key": project_key, "name": project_key}
    
    async def _get_new_code_metrics(self, project_key: str, branch: str = None, pull_request: str = None) -> Dict[str, Any]:
        """Get metrics for new/changed code."""
        new_code_metrics = [
            "new_lines", "new_coverage", "new_line_coverage", "new_branch_coverage",
            "new_bugs", "new_vulnerabilities", "new_code_smells", "new_security_hotspots",
            "new_duplicated_lines_density", "new_maintainability_rating", 
            "new_reliability_rating", "new_security_rating"
        ]
        
        try:
            params = {
                "component": project_key,
                "metricKeys": ",".join(new_code_metrics)
            }
            
            if branch:
                params["branch"] = branch
            if pull_request:
                params["pullRequest"] = pull_request
            
            response = await self.client.get("/measures/component", params=params)
            
            component = response.get("component", {})
            measures = component.get("measures", [])
            
            # Convert to dictionary
            metrics = {}
            for measure in measures:
                metric_key = measure.get("metric")
                value = measure.get("value")
                
                if metric_key and value is not None:
                    try:
                        if "." in str(value):
                            typed_value = float(value)
                        else:
                            typed_value = int(value)
                    except (ValueError, TypeError):
                        typed_value = str(value)
                    
                    metrics[metric_key] = typed_value
            
            return metrics
            
        except Exception as e:
            self.logger.error(f"Failed to get new code metrics for {project_key}: {e}")
            return {}
    
    async def _get_new_issues(self, project_key: str, branch: str = None, pull_request: str = None) -> List[Dict[str, Any]]:
        """Get new issues in the code."""
        try:
            params = {
                "projectKeys": project_key,
                "sinceLeakPeriod": "true",  # Only new issues
                "ps": 500,  # Get up to 500 new issues
                "additionalFields": "comments",
                "facets": "severities,types,rules"
            }
            
            if branch:
                params["branch"] = branch
            if pull_request:
                params["pullRequest"] = pull_request
            
            response = await self.client.get("/issues/search", params=params)
            
            issues = response.get("issues", [])
            components = response.get("components", [])
            rules = response.get("rules", [])
            facets = response.get("facets", [])
            
            # Create lookup dictionaries
            components_dict = {comp["key"]: comp for comp in components}
            rules_dict = {rule["key"]: rule for rule in rules}
            
            # Enrich issues
            enriched_issues = []
            for issue in issues:
                enriched = issue.copy()
                
                # Add component info
                component_key = issue.get("component")
                if component_key and component_key in components_dict:
                    enriched["component_info"] = components_dict[component_key]
                
                # Add rule info
                rule_key = issue.get("rule")
                if rule_key and rule_key in rules_dict:
                    enriched["rule_info"] = rules_dict[rule_key]
                
                enriched_issues.append(enriched)
            
            return {
                "issues": enriched_issues,
                "total": len(enriched_issues),
                "facets": facets
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get new issues for {project_key}: {e}")
            return {"issues": [], "total": 0, "facets": []}
    
    async def _get_quality_gate_status(self, project_key: str, branch: str = None, pull_request: str = None) -> Dict[str, Any]:
        """Get Quality Gate status."""
        try:
            params = {"projectKey": project_key}
            
            if branch:
                params["branch"] = branch
            if pull_request:
                params["pullRequest"] = pull_request
            
            response = await self.client.get("/qualitygates/project_status", params=params)
            
            return response.get("projectStatus", {})
        except Exception as e:
            self.logger.error(f"Failed to get Quality Gate status for {project_key}: {e}")
            return {"status": "UNKNOWN"}
    
    async def _get_coverage_info(self, project_key: str, branch: str = None, pull_request: str = None) -> Dict[str, Any]:
        """Get detailed coverage information."""
        coverage_metrics = [
            "coverage", "new_coverage", "line_coverage", "new_line_coverage",
            "branch_coverage", "new_branch_coverage", "lines_to_cover", "new_lines_to_cover",
            "uncovered_lines", "new_uncovered_lines", "tests", "test_execution_time"
        ]
        
        try:
            params = {
                "component": project_key,
                "metricKeys": ",".join(coverage_metrics)
            }
            
            if branch:
                params["branch"] = branch
            if pull_request:
                params["pullRequest"] = pull_request
            
            response = await self.client.get("/measures/component", params=params)
            
            component = response.get("component", {})
            measures = component.get("measures", [])
            
            # Convert to dictionary
            coverage = {}
            for measure in measures:
                metric_key = measure.get("metric")
                value = measure.get("value")
                
                if metric_key and value is not None:
                    try:
                        if "." in str(value):
                            typed_value = float(value)
                        else:
                            typed_value = int(value)
                    except (ValueError, TypeError):
                        typed_value = str(value)
                    
                    coverage[metric_key] = typed_value
            
            return coverage
            
        except Exception as e:
            self.logger.error(f"Failed to get coverage info for {project_key}: {e}")
            return {}
    
    def _generate_code_review_summary(
        self,
        project_info: Dict[str, Any],
        new_code_metrics: Dict[str, Any],
        new_issues: Dict[str, Any],
        quality_gate: Dict[str, Any],
        coverage_info: Dict[str, Any],
        focus_on_new_code: bool,
        branch: str = None,
        pull_request: str = None
    ) -> str:
        """Generate comprehensive code review summary."""
        project_name = project_info.get("name", project_info.get("key", "Unknown"))
        project_key = project_info.get("key", "Unknown")
        
        # Determine context
        context = "main branch"
        if pull_request:
            context = f"Pull Request #{pull_request}"
        elif branch:
            context = f"branch '{branch}'"
        
        review = f"""# Code Review Summary: {project_name}

## Review Context
- **Project**: {project_name} ({project_key})
- **Context**: {context}
- **Review Date**: {self._get_current_timestamp()}
- **Focus**: {"New/Changed Code" if focus_on_new_code else "All Code"}

"""
        
        # Quality Gate Status
        qg_status = quality_gate.get("status", "UNKNOWN")
        if qg_status == "OK":
            review += "✅ **Quality Gate**: PASSED - All quality conditions are met.\n\n"
        elif qg_status == "ERROR":
            review += "❌ **Quality Gate**: FAILED - Quality conditions not met.\n\n"
            conditions = quality_gate.get("conditions", [])
            failed_conditions = [c for c in conditions if c.get("status") == "ERROR"]
            if failed_conditions:
                review += "**Failed Conditions**:\n"
                for condition in failed_conditions:
                    metric = condition.get("metricKey", "Unknown")
                    actual = condition.get("actualValue", "N/A")
                    threshold = condition.get("errorThreshold", "N/A")
                    review += f"- {metric}: {actual} (required: {threshold})\n"
                review += "\n"
        else:
            review += f"⚠️ **Quality Gate**: {qg_status}\n\n"
        
        # New Code Metrics Summary
        if new_code_metrics:
            review += "## New Code Analysis\n"
            
            new_lines = new_code_metrics.get("new_lines", 0)
            new_bugs = new_code_metrics.get("new_bugs", 0)
            new_vulnerabilities = new_code_metrics.get("new_vulnerabilities", 0)
            new_code_smells = new_code_metrics.get("new_code_smells", 0)
            new_hotspots = new_code_metrics.get("new_security_hotspots", 0)
            
            review += f"- **Lines of New Code**: {new_lines:,}\n"
            review += f"- **New Issues**: {new_bugs + new_vulnerabilities + new_code_smells} total\n"
            review += f"  - 🐛 Bugs: {new_bugs}\n"
            review += f"  - 🔓 Vulnerabilities: {new_vulnerabilities}\n"
            review += f"  - 💨 Code Smells: {new_code_smells}\n"
            if new_hotspots > 0:
                review += f"  - 🔥 Security Hotspots: {new_hotspots}\n"
            
            # Quality ratings for new code
            new_reliability = new_code_metrics.get("new_reliability_rating")
            new_security = new_code_metrics.get("new_security_rating")
            new_maintainability = new_code_metrics.get("new_maintainability_rating")
            
            if any([new_reliability, new_security, new_maintainability]):
                review += "\n**New Code Quality Ratings**:\n"
                if new_reliability:
                    review += f"- Reliability: {self._format_rating(new_reliability)}\n"
                if new_security:
                    review += f"- Security: {self._format_rating(new_security)}\n"
                if new_maintainability:
                    review += f"- Maintainability: {self._format_rating(new_maintainability)}\n"
            
            review += "\n"
        
        # Test Coverage Analysis
        if coverage_info:
            review += "## Test Coverage Analysis\n"
            
            overall_coverage = coverage_info.get("coverage")
            new_coverage = coverage_info.get("new_coverage")
            line_coverage = coverage_info.get("line_coverage")
            new_line_coverage = coverage_info.get("new_line_coverage")
            branch_coverage = coverage_info.get("branch_coverage")
            new_branch_coverage = coverage_info.get("new_branch_coverage")
            
            if overall_coverage is not None:
                review += f"- **Overall Coverage**: {overall_coverage:.1f}%\n"
            if new_coverage is not None:
                review += f"- **New Code Coverage**: {new_coverage:.1f}%\n"
            if line_coverage is not None:
                review += f"- **Line Coverage**: {line_coverage:.1f}%\n"
            if new_line_coverage is not None:
                review += f"- **New Line Coverage**: {new_line_coverage:.1f}%\n"
            if branch_coverage is not None:
                review += f"- **Branch Coverage**: {branch_coverage:.1f}%\n"
            if new_branch_coverage is not None:
                review += f"- **New Branch Coverage**: {new_branch_coverage:.1f}%\n"
            
            # Coverage assessment
            target_coverage = new_coverage if new_coverage is not None else overall_coverage
            if target_coverage is not None:
                if target_coverage >= 80:
                    review += "✅ Excellent test coverage.\n"
                elif target_coverage >= 60:
                    review += "⚠️ Good test coverage, could be improved.\n"
                elif target_coverage >= 40:
                    review += "⚠️ Moderate test coverage - consider adding more tests.\n"
                else:
                    review += "❌ Low test coverage - significant testing needed.\n"
            
            # Test count and execution time
            tests = coverage_info.get("tests", 0)
            test_time = coverage_info.get("test_execution_time")
            if tests > 0:
                review += f"- **Total Tests**: {tests:,}\n"
            if test_time is not None:
                review += f"- **Test Execution Time**: {self._format_metric_value('test_execution_time', test_time)}\n"
            
            review += "\n"
        
        # New Issues Analysis
        issues_data = new_issues.get("issues", [])
        total_new_issues = new_issues.get("total", 0)
        
        if total_new_issues > 0:
            review += f"## New Issues Analysis ({total_new_issues} total)\n"
            
            # Group issues by severity and type
            by_severity = {}
            by_type = {}
            by_rule = {}
            
            for issue in issues_data:
                severity = issue.get("severity", "UNKNOWN")
                issue_type = issue.get("type", "UNKNOWN")
                rule = issue.get("rule", "UNKNOWN")
                
                by_severity[severity] = by_severity.get(severity, 0) + 1
                by_type[issue_type] = by_type.get(issue_type, 0) + 1
                by_rule[rule] = by_rule.get(rule, 0) + 1
            
            # Severity breakdown
            if by_severity:
                review += "### By Severity\n"
                for severity in ["BLOCKER", "CRITICAL", "MAJOR", "MINOR", "INFO"]:
                    count = by_severity.get(severity, 0)
                    if count > 0:
                        emoji = {"BLOCKER": "🚫", "CRITICAL": "🔴", "MAJOR": "🟠", "MINOR": "🟡", "INFO": "ℹ️"}.get(severity, "•")
                        review += f"- {emoji} **{severity}**: {count}\n"
                review += "\n"
            
            # Type breakdown
            if by_type:
                review += "### By Type\n"
                for issue_type in ["BUG", "VULNERABILITY", "CODE_SMELL", "SECURITY_HOTSPOT"]:
                    count = by_type.get(issue_type, 0)
                    if count > 0:
                        emoji = {"BUG": "🐛", "VULNERABILITY": "🔓", "CODE_SMELL": "💨", "SECURITY_HOTSPOT": "🔥"}.get(issue_type, "•")
                        review += f"- {emoji} **{issue_type}**: {count}\n"
                review += "\n"
            
            # Top rules (most frequent issues)
            if by_rule:
                review += "### Most Frequent Issues\n"
                sorted_rules = sorted(by_rule.items(), key=lambda x: x[1], reverse=True)
                for rule, count in sorted_rules[:5]:  # Top 5
                    # Try to get rule name from issues
                    rule_name = rule
                    for issue in issues_data:
                        if issue.get("rule") == rule:
                            rule_info = issue.get("rule_info", {})
                            rule_name = rule_info.get("name", rule)
                            break
                    
                    review += f"- **{rule_name}**: {count} occurrences\n"
                review += "\n"
            
            # Critical issues that need immediate attention
            critical_issues = [
                issue for issue in issues_data 
                if issue.get("severity") in ["BLOCKER", "CRITICAL"] or issue.get("type") == "VULNERABILITY"
            ]
            
            if critical_issues:
                review += f"### Critical Issues Requiring Immediate Attention ({len(critical_issues)})\n"
                for i, issue in enumerate(critical_issues[:5], 1):  # Top 5 critical
                    component_info = issue.get("component_info", {})
                    component_name = component_info.get("name", issue.get("component", "Unknown"))
                    message = issue.get("message", "No description")
                    severity = issue.get("severity", "UNKNOWN")
                    issue_type = issue.get("type", "UNKNOWN")
                    
                    # Truncate long messages
                    if len(message) > 80:
                        message = message[:77] + "..."
                    
                    review += f"{i}. **{severity} {issue_type}** in `{component_name}`\n"
                    review += f"   {message}\n"
                
                review += "\n"
        else:
            review += "## New Issues Analysis\n"
            review += "✅ No new issues found in the analyzed code.\n\n"
        
        # Code Review Recommendations
        review += "## Code Review Recommendations\n"
        
        # Quality Gate recommendations
        if qg_status == "ERROR":
            review += "### Quality Gate Issues\n"
            review += "- Address failed Quality Gate conditions before merging\n"
            conditions = quality_gate.get("conditions", [])
            failed_conditions = [c for c in conditions if c.get("status") == "ERROR"]
            for condition in failed_conditions:
                metric = condition.get("metricKey", "")
                if "coverage" in metric:
                    review += "- Add tests to improve coverage\n"
                elif "bugs" in metric:
                    review += "- Fix bugs before merging\n"
                elif "vulnerabilities" in metric:
                    review += "- Address security vulnerabilities\n"
                elif "code_smells" in metric:
                    review += "- Refactor code to reduce technical debt\n"
            review += "\n"
        
        # Issue-based recommendations
        if total_new_issues > 0:
            review += "### Issue Resolution\n"
            
            new_bugs = new_code_metrics.get("new_bugs", 0)
            new_vulnerabilities = new_code_metrics.get("new_vulnerabilities", 0)
            new_code_smells = new_code_metrics.get("new_code_smells", 0)
            
            if new_vulnerabilities > 0:
                review += f"- **High Priority**: Address {new_vulnerabilities} security vulnerabilities\n"
            if new_bugs > 0:
                review += f"- **Medium Priority**: Fix {new_bugs} bugs\n"
            if new_code_smells > 10:
                review += f"- **Low Priority**: Consider refactoring {new_code_smells} code smells\n"
            elif new_code_smells > 0:
                review += f"- **Optional**: Address {new_code_smells} code smells if time permits\n"
            
            review += "\n"
        
        # Coverage recommendations
        if coverage_info:
            new_coverage = coverage_info.get("new_coverage")
            if new_coverage is not None and new_coverage < 80:
                review += "### Test Coverage\n"
                review += f"- Current new code coverage is {new_coverage:.1f}%\n"
                if new_coverage < 60:
                    review += "- **Strongly recommended**: Add comprehensive tests\n"
                else:
                    review += "- **Recommended**: Add additional tests to reach 80% coverage\n"
                review += "\n"
        
        # General recommendations
        review += "### General Recommendations\n"
        
        if total_new_issues == 0 and qg_status == "OK":
            review += "- ✅ Code meets quality standards - ready for merge\n"
        elif total_new_issues <= 5 and qg_status != "ERROR":
            review += "- ⚠️ Minor issues present - consider addressing before merge\n"
        else:
            review += "- ❌ Significant issues present - address before merge\n"
        
        review += "- Review code for adherence to team coding standards\n"
        review += "- Ensure proper documentation for new features\n"
        review += "- Verify that changes align with requirements\n"
        
        if pull_request:
            review += "- Consider breaking large changes into smaller, focused PRs\n"
        
        review += f"\n---\n*Code review summary generated on {self._get_current_timestamp()}*"
        
        return review
    
    def _format_rating(self, rating: Any) -> str:
        """Format quality rating for display."""
        if rating is None:
            return "N/A"
        
        rating_map = {
            1: "A (Excellent)",
            2: "B (Good)", 
            3: "C (Fair)",
            4: "D (Poor)",
            5: "E (Very Poor)"
        }
        
        try:
            rating_int = int(float(rating))
            return rating_map.get(rating_int, f"Rating {rating}")
        except (ValueError, TypeError):
            return str(rating)
