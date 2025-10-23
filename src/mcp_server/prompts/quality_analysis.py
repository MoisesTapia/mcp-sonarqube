"""Quality analysis prompt for comprehensive project analysis."""

from typing import Any, Dict, List

from ...sonarqube_client import InputValidator
from .base import BasePrompt


class AnalyzeProjectQualityPrompt(BasePrompt):
    """Prompt for comprehensive project quality analysis."""
    
    def get_name(self) -> str:
        return "analyze_project_quality"
    
    def get_description(self) -> str:
        return "Perform comprehensive quality analysis of a SonarQube project including metrics, issues, and recommendations"
    
    def get_arguments(self) -> List[Dict[str, Any]]:
        return [
            {
                "name": "project_key",
                "description": "The SonarQube project key to analyze",
                "required": True,
                "type": "string"
            },
            {
                "name": "include_history",
                "description": "Include historical trend analysis",
                "required": False,
                "type": "boolean",
                "default": False
            },
            {
                "name": "focus_areas",
                "description": "Specific areas to focus on (reliability, security, maintainability, coverage, duplication)",
                "required": False,
                "type": "array",
                "items": {"type": "string"},
                "default": ["reliability", "security", "maintainability", "coverage"]
            }
        ]
    
    async def execute(self, arguments: Dict[str, Any]) -> str:
        """Execute the quality analysis prompt."""
        project_key = arguments.get("project_key")
        include_history = arguments.get("include_history", False)
        focus_areas = arguments.get("focus_areas", ["reliability", "security", "maintainability", "coverage"])
        
        if not project_key:
            raise ValueError("project_key is required")
        
        async def generate_analysis():
            # Validate project key
            project_key_validated = InputValidator.validate_project_key(project_key)
            
            # Get project information
            project_info = await self._get_project_info(project_key_validated)
            
            # Get comprehensive metrics
            metrics = await self._get_project_metrics(project_key_validated, focus_areas)
            
            # Get Quality Gate status
            quality_gate = await self._get_quality_gate_status(project_key_validated)
            
            # Get issues summary
            issues_summary = await self._get_issues_summary(project_key_validated)
            
            # Get historical data if requested
            historical_analysis = None
            if include_history:
                historical_analysis = await self._get_historical_analysis(project_key_validated, focus_areas)
            
            # Generate comprehensive analysis
            analysis = self._generate_comprehensive_analysis(
                project_info, metrics, quality_gate, issues_summary, historical_analysis, focus_areas
            )
            
            return analysis
        
        return await self._get_cached_or_execute(
            self.get_name(),
            generate_analysis,
            ttl=300,
            project_key=project_key,
            include_history=include_history,
            focus_areas=",".join(sorted(focus_areas))
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
    
    async def _get_project_metrics(self, project_key: str, focus_areas: List[str]) -> Dict[str, Any]:
        """Get comprehensive project metrics."""
        # Define metrics by focus area
        metrics_by_area = {
            "reliability": ["bugs", "new_bugs", "reliability_rating", "new_reliability_rating"],
            "security": ["vulnerabilities", "new_vulnerabilities", "security_rating", "new_security_rating", "security_hotspots"],
            "maintainability": ["code_smells", "new_code_smells", "sqale_rating", "new_maintainability_rating", "technical_debt"],
            "coverage": ["coverage", "new_coverage", "line_coverage", "branch_coverage", "tests"],
            "duplication": ["duplicated_lines_density", "new_duplicated_lines_density", "duplicated_lines"],
            "overview": ["ncloc", "lines", "files", "functions", "classes", "complexity"]
        }
        
        # Collect metrics for requested focus areas
        all_metrics = set()
        for area in focus_areas + ["overview"]:  # Always include overview
            if area in metrics_by_area:
                all_metrics.update(metrics_by_area[area])
        
        try:
            response = await self.client.get(
                "/measures/component",
                params={
                    "component": project_key,
                    "metricKeys": ",".join(all_metrics)
                }
            )
            
            component = response.get("component", {})
            measures = component.get("measures", [])
            
            # Organize metrics by area
            organized_metrics = {}
            for area in focus_areas + ["overview"]:
                if area in metrics_by_area:
                    area_metrics = {}
                    for metric_key in metrics_by_area[area]:
                        for measure in measures:
                            if measure.get("metric") == metric_key:
                                value = measure.get("value")
                                if value is not None:
                                    try:
                                        if "." in str(value):
                                            typed_value = float(value)
                                        else:
                                            typed_value = int(value)
                                    except (ValueError, TypeError):
                                        typed_value = str(value)
                                    
                                    area_metrics[metric_key] = {
                                        "value": typed_value,
                                        "formatted": self._format_metric_value(metric_key, typed_value)
                                    }
                                break
                    
                    if area_metrics:
                        organized_metrics[area] = area_metrics
            
            return organized_metrics
            
        except Exception as e:
            self.logger.error(f"Failed to get metrics for {project_key}: {e}")
            return {}
    
    async def _get_quality_gate_status(self, project_key: str) -> Dict[str, Any]:
        """Get Quality Gate status."""
        try:
            response = await self.client.get(
                "/qualitygates/project_status",
                params={"projectKey": project_key}
            )
            
            return response.get("projectStatus", {})
        except Exception as e:
            self.logger.error(f"Failed to get Quality Gate status for {project_key}: {e}")
            return {"status": "UNKNOWN"}
    
    async def _get_issues_summary(self, project_key: str) -> Dict[str, Any]:
        """Get issues summary."""
        try:
            response = await self.client.get(
                "/issues/search",
                params={
                    "projectKeys": project_key,
                    "ps": 1,  # We only want the facets
                    "facets": "severities,types,statuses"
                }
            )
            
            total = response.get("total", 0)
            facets = response.get("facets", [])
            
            # Process facets
            summary = {"total": total}
            for facet in facets:
                property_name = facet.get("property")
                values = facet.get("values", [])
                
                if property_name:
                    summary[f"by_{property_name}"] = {
                        value.get("val"): value.get("count", 0)
                        for value in values
                    }
            
            return summary
        except Exception as e:
            self.logger.error(f"Failed to get issues summary for {project_key}: {e}")
            return {"total": 0}
    
    async def _get_historical_analysis(self, project_key: str, focus_areas: List[str]) -> Dict[str, Any]:
        """Get historical trend analysis."""
        try:
            # Get key metrics for trend analysis
            key_metrics = ["bugs", "vulnerabilities", "code_smells", "coverage", "duplicated_lines_density"]
            
            response = await self.client.get(
                "/measures/search_history",
                params={
                    "component": project_key,
                    "metrics": ",".join(key_metrics),
                    "ps": 100  # Last 100 data points
                }
            )
            
            measures = response.get("measures", [])
            
            # Analyze trends
            trends = {}
            for measure in measures:
                metric_key = measure.get("metric")
                history = measure.get("history", [])
                
                if len(history) >= 2:
                    # Calculate trend (simple: compare first and last values)
                    first_value = self._parse_numeric_value(history[0].get("value"))
                    last_value = self._parse_numeric_value(history[-1].get("value"))
                    
                    if first_value is not None and last_value is not None:
                        if first_value == 0:
                            trend = "stable" if last_value == 0 else "increasing"
                        else:
                            change_percent = ((last_value - first_value) / first_value) * 100
                            if abs(change_percent) < 5:
                                trend = "stable"
                            elif change_percent > 0:
                                trend = "increasing" if metric_key not in ["coverage"] else "improving"
                            else:
                                trend = "decreasing" if metric_key not in ["coverage"] else "declining"
                        
                        trends[metric_key] = {
                            "trend": trend,
                            "change_percent": change_percent if first_value != 0 else 0,
                            "first_value": first_value,
                            "last_value": last_value,
                            "data_points": len(history)
                        }
            
            return trends
        except Exception as e:
            self.logger.error(f"Failed to get historical analysis for {project_key}: {e}")
            return {}
    
    def _parse_numeric_value(self, value: Any) -> float:
        """Parse a value to numeric."""
        if value is None:
            return None
        
        try:
            return float(value)
        except (ValueError, TypeError):
            return None
    
    def _generate_comprehensive_analysis(
        self,
        project_info: Dict[str, Any],
        metrics: Dict[str, Any],
        quality_gate: Dict[str, Any],
        issues_summary: Dict[str, Any],
        historical_analysis: Dict[str, Any],
        focus_areas: List[str]
    ) -> str:
        """Generate comprehensive analysis report."""
        project_name = project_info.get("name", project_info.get("key", "Unknown"))
        project_key = project_info.get("key", "Unknown")
        
        analysis = f"""# Comprehensive Quality Analysis: {project_name}

## Project Overview
- **Project Key**: {project_key}
- **Project Name**: {project_name}
- **Analysis Date**: {self._get_current_timestamp()}
- **Quality Gate Status**: {quality_gate.get('status', 'UNKNOWN')}

"""
        
        # Quality Gate Analysis
        qg_status = quality_gate.get("status", "UNKNOWN")
        if qg_status == "OK":
            analysis += "✅ **Quality Gate**: PASSED - All quality conditions are met.\n\n"
        elif qg_status == "ERROR":
            analysis += "❌ **Quality Gate**: FAILED - Some quality conditions are not met.\n\n"
            conditions = quality_gate.get("conditions", [])
            failed_conditions = [c for c in conditions if c.get("status") == "ERROR"]
            if failed_conditions:
                analysis += "**Failed Conditions**:\n"
                for condition in failed_conditions:
                    metric = condition.get("metricKey", "Unknown")
                    actual = condition.get("actualValue", "N/A")
                    threshold = condition.get("errorThreshold", "N/A")
                    analysis += f"- {metric}: {actual} (threshold: {threshold})\n"
                analysis += "\n"
        else:
            analysis += f"⚠️ **Quality Gate**: {qg_status}\n\n"
        
        # Issues Summary
        total_issues = issues_summary.get("total", 0)
        analysis += f"## Issues Summary\n"
        analysis += f"- **Total Issues**: {total_issues}\n"
        
        by_severity = issues_summary.get("by_severities", {})
        if by_severity:
            analysis += "- **By Severity**:\n"
            for severity in ["BLOCKER", "CRITICAL", "MAJOR", "MINOR", "INFO"]:
                count = by_severity.get(severity, 0)
                if count > 0:
                    emoji = {"BLOCKER": "🚫", "CRITICAL": "🔴", "MAJOR": "🟠", "MINOR": "🟡", "INFO": "ℹ️"}.get(severity, "•")
                    analysis += f"  - {emoji} {severity}: {count}\n"
        
        by_type = issues_summary.get("by_types", {})
        if by_type:
            analysis += "- **By Type**:\n"
            for issue_type in ["BUG", "VULNERABILITY", "CODE_SMELL", "SECURITY_HOTSPOT"]:
                count = by_type.get(issue_type, 0)
                if count > 0:
                    emoji = {"BUG": "🐛", "VULNERABILITY": "🔓", "CODE_SMELL": "💨", "SECURITY_HOTSPOT": "🔥"}.get(issue_type, "•")
                    analysis += f"  - {emoji} {issue_type}: {count}\n"
        
        analysis += "\n"
        
        # Metrics Analysis by Focus Area
        for area in focus_areas:
            if area in metrics:
                area_metrics = metrics[area]
                area_title = area.replace("_", " ").title()
                analysis += f"## {area_title} Analysis\n"
                
                if area == "reliability":
                    bugs = area_metrics.get("bugs", {}).get("value", 0)
                    new_bugs = area_metrics.get("new_bugs", {}).get("value", 0)
                    rating = area_metrics.get("reliability_rating", {}).get("value", "N/A")
                    
                    analysis += f"- **Bugs**: {bugs} total"
                    if new_bugs > 0:
                        analysis += f" ({new_bugs} new)"
                    analysis += "\n"
                    analysis += f"- **Reliability Rating**: {rating}\n"
                    
                    if bugs == 0:
                        analysis += "✅ No reliability issues found.\n"
                    elif bugs <= 5:
                        analysis += "⚠️ Few reliability issues - consider addressing them.\n"
                    else:
                        analysis += "❌ Multiple reliability issues require attention.\n"
                
                elif area == "security":
                    vulns = area_metrics.get("vulnerabilities", {}).get("value", 0)
                    new_vulns = area_metrics.get("new_vulnerabilities", {}).get("value", 0)
                    hotspots = area_metrics.get("security_hotspots", {}).get("value", 0)
                    rating = area_metrics.get("security_rating", {}).get("value", "N/A")
                    
                    analysis += f"- **Vulnerabilities**: {vulns} total"
                    if new_vulns > 0:
                        analysis += f" ({new_vulns} new)"
                    analysis += "\n"
                    analysis += f"- **Security Hotspots**: {hotspots}\n"
                    analysis += f"- **Security Rating**: {rating}\n"
                    
                    if vulns == 0 and hotspots == 0:
                        analysis += "✅ No security issues found.\n"
                    elif vulns > 0:
                        analysis += "❌ Security vulnerabilities require immediate attention.\n"
                    elif hotspots > 0:
                        analysis += "⚠️ Security hotspots should be reviewed.\n"
                
                elif area == "maintainability":
                    smells = area_metrics.get("code_smells", {}).get("value", 0)
                    new_smells = area_metrics.get("new_code_smells", {}).get("value", 0)
                    debt = area_metrics.get("technical_debt", {}).get("formatted", "N/A")
                    rating = area_metrics.get("sqale_rating", {}).get("value", "N/A")
                    
                    analysis += f"- **Code Smells**: {smells} total"
                    if new_smells > 0:
                        analysis += f" ({new_smells} new)"
                    analysis += "\n"
                    analysis += f"- **Technical Debt**: {debt}\n"
                    analysis += f"- **Maintainability Rating**: {rating}\n"
                    
                    if smells <= 10:
                        analysis += "✅ Good maintainability - few code smells.\n"
                    elif smells <= 50:
                        analysis += "⚠️ Moderate maintainability issues.\n"
                    else:
                        analysis += "❌ High technical debt - many code smells to address.\n"
                
                elif area == "coverage":
                    coverage = area_metrics.get("coverage", {}).get("value")
                    new_coverage = area_metrics.get("new_coverage", {}).get("value")
                    line_coverage = area_metrics.get("line_coverage", {}).get("value")
                    branch_coverage = area_metrics.get("branch_coverage", {}).get("value")
                    tests = area_metrics.get("tests", {}).get("value", 0)
                    
                    if coverage is not None:
                        analysis += f"- **Overall Coverage**: {coverage:.1f}%\n"
                    if new_coverage is not None:
                        analysis += f"- **New Code Coverage**: {new_coverage:.1f}%\n"
                    if line_coverage is not None:
                        analysis += f"- **Line Coverage**: {line_coverage:.1f}%\n"
                    if branch_coverage is not None:
                        analysis += f"- **Branch Coverage**: {branch_coverage:.1f}%\n"
                    analysis += f"- **Total Tests**: {tests}\n"
                    
                    if coverage and coverage >= 80:
                        analysis += "✅ Excellent test coverage.\n"
                    elif coverage and coverage >= 60:
                        analysis += "⚠️ Good test coverage, could be improved.\n"
                    elif coverage and coverage >= 40:
                        analysis += "⚠️ Moderate test coverage - consider adding more tests.\n"
                    else:
                        analysis += "❌ Low test coverage - significant testing needed.\n"
                
                elif area == "duplication":
                    density = area_metrics.get("duplicated_lines_density", {}).get("value")
                    lines = area_metrics.get("duplicated_lines", {}).get("value", 0)
                    
                    if density is not None:
                        analysis += f"- **Duplication Density**: {density:.1f}%\n"
                    analysis += f"- **Duplicated Lines**: {lines}\n"
                    
                    if density and density <= 3:
                        analysis += "✅ Low code duplication.\n"
                    elif density and density <= 10:
                        analysis += "⚠️ Moderate code duplication.\n"
                    else:
                        analysis += "❌ High code duplication - refactoring recommended.\n"
                
                analysis += "\n"
        
        # Historical Trends
        if historical_analysis:
            analysis += "## Historical Trends\n"
            for metric, trend_data in historical_analysis.items():
                trend = trend_data.get("trend", "unknown")
                change = trend_data.get("change_percent", 0)
                
                trend_emoji = {
                    "improving": "📈",
                    "declining": "📉", 
                    "increasing": "📈" if metric in ["coverage"] else "📉",
                    "decreasing": "📉" if metric in ["coverage"] else "📈",
                    "stable": "➡️"
                }.get(trend, "❓")
                
                analysis += f"- **{metric}**: {trend_emoji} {trend}"
                if abs(change) > 0:
                    analysis += f" ({change:+.1f}%)"
                analysis += "\n"
            analysis += "\n"
        
        # Recommendations
        analysis += "## Recommendations\n"
        
        # Quality Gate recommendations
        if qg_status == "ERROR":
            analysis += "### Quality Gate Issues\n"
            conditions = quality_gate.get("conditions", [])
            failed_conditions = [c for c in conditions if c.get("status") == "ERROR"]
            for condition in failed_conditions:
                metric = condition.get("metricKey", "")
                if metric == "coverage":
                    analysis += "- Increase test coverage by adding unit tests for uncovered code\n"
                elif "bugs" in metric:
                    analysis += "- Fix existing bugs to improve reliability\n"
                elif "vulnerabilities" in metric:
                    analysis += "- Address security vulnerabilities immediately\n"
                elif "code_smells" in metric:
                    analysis += "- Refactor code to reduce technical debt\n"
        
        # General recommendations based on metrics
        if "reliability" in focus_areas and "reliability" in metrics:
            bugs = metrics["reliability"].get("bugs", {}).get("value", 0)
            if bugs > 10:
                analysis += "- **Reliability**: Focus on bug fixing to improve code reliability\n"
        
        if "security" in focus_areas and "security" in metrics:
            vulns = metrics["security"].get("vulnerabilities", {}).get("value", 0)
            hotspots = metrics["security"].get("security_hotspots", {}).get("value", 0)
            if vulns > 0:
                analysis += "- **Security**: Address security vulnerabilities as high priority\n"
            elif hotspots > 5:
                analysis += "- **Security**: Review security hotspots to prevent future vulnerabilities\n"
        
        if "coverage" in focus_areas and "coverage" in metrics:
            coverage = metrics["coverage"].get("coverage", {}).get("value")
            if coverage and coverage < 60:
                analysis += "- **Testing**: Increase test coverage to improve code quality assurance\n"
        
        if "duplication" in focus_areas and "duplication" in metrics:
            density = metrics["duplication"].get("duplicated_lines_density", {}).get("value")
            if density and density > 10:
                analysis += "- **Duplication**: Refactor duplicated code to improve maintainability\n"
        
        analysis += f"\n---\n*Analysis generated on {self._get_current_timestamp()}*"
        
        return analysis