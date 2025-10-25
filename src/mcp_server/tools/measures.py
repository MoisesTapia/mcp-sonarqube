"""Metrics and quality analysis tools for SonarQube MCP."""

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from sonarqube_client import SonarQubeClient, InputValidator
from utils import CacheManager, get_logger

logger = get_logger(__name__)


class MeasureTools:
    """Tools for SonarQube metrics and quality analysis."""

    # Standard SonarQube metrics
    CORE_METRICS = [
        "ncloc",  # Lines of code
        "coverage",  # Test coverage
        "bugs",  # Number of bugs
        "vulnerabilities",  # Number of vulnerabilities
        "code_smells",  # Number of code smells
        "sqale_index",  # Technical debt (minutes)
        "duplicated_lines_density",  # Duplication percentage
        "reliability_rating",  # Reliability rating (A-E)
        "security_rating",  # Security rating (A-E)
        "sqale_rating",  # Maintainability rating (A-E)
    ]

    QUALITY_METRICS = [
        "alert_status",  # Quality Gate status
        "quality_gate_details",  # Quality Gate details
        "new_coverage",  # New code coverage
        "new_bugs",  # New bugs
        "new_vulnerabilities",  # New vulnerabilities
        "new_code_smells",  # New code smells
    ]

    def __init__(self, client: SonarQubeClient, cache_manager: Optional[CacheManager] = None):
        """Initialize measure tools."""
        self.client = client
        self.cache = cache_manager
        self.logger = logger

    async def get_measures(
        self,
        project_key: str,
        metric_keys: Optional[List[str]] = None,
        additional_fields: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Get metrics for a specific project.

        Args:
            project_key: Unique project key
            metric_keys: List of metric keys to retrieve (defaults to core metrics)
            additional_fields: Additional fields to include (periods, metrics)

        Returns:
            Dictionary containing project metrics
        """
        try:
            # Validate project key
            project_key = InputValidator.validate_project_key(project_key)
            
            # Use core metrics if none specified
            if not metric_keys:
                metric_keys = self.CORE_METRICS
            else:
                metric_keys = InputValidator.validate_metric_keys(metric_keys)
            
            # Build cache key
            cache_key_params = {
                "project_key": project_key,
                "metrics": ",".join(sorted(metric_keys)),
                "fields": ",".join(sorted(additional_fields or [])),
            }
            
            # Try cache first
            if self.cache:
                cached_result = await self.cache.get("metrics", "measures", **cache_key_params)
                if cached_result:
                    self.logger.debug(f"Returning cached measures for {project_key}")
                    return cached_result

            # Build API parameters
            params = {
                "component": project_key,
                "metricKeys": ",".join(metric_keys),
            }
            
            if additional_fields:
                params["additionalFields"] = ",".join(additional_fields)

            # Make API call
            response = await self.client.get("/measures/component", params=params)
            
            # Format response
            component = response.get("component", {})
            measures = component.get("measures", [])
            
            # Convert measures to dictionary for easier access
            metrics_dict = {}
            for measure in measures:
                metric_key = measure["metric"]
                metrics_dict[metric_key] = {
                    "value": measure.get("value"),
                    "best_value": measure.get("bestValue", False),
                }
                
                # Include period data if available
                if "periods" in measure:
                    metrics_dict[metric_key]["periods"] = measure["periods"]

            result = {
                "project_key": project_key,
                "project_name": component.get("name", ""),
                "metrics": metrics_dict,
                "last_analysis": component.get("analysisDate"),
                "version": component.get("version"),
            }
            
            # Cache result
            if self.cache:
                await self.cache.set("metrics", "measures", result, **cache_key_params)
            
            self.logger.info(f"Retrieved {len(metrics_dict)} metrics for project {project_key}")
            return result
            
        except Exception as e:
            self.logger.error(f"Failed to get measures for project {project_key}: {e}")
            raise RuntimeError(f"Failed to get project measures: {str(e)}")

    async def get_quality_gate_status(self, project_key: str) -> Dict[str, Any]:
        """
        Get Quality Gate status for a specific project.

        Args:
            project_key: Unique project key

        Returns:
            Dictionary containing Quality Gate status and conditions
        """
        try:
            # Validate project key
            project_key = InputValidator.validate_project_key(project_key)
            
            # Try cache first
            if self.cache:
                cached_result = await self.cache.get("quality_gates", "status", project_key=project_key)
                if cached_result:
                    self.logger.debug(f"Returning cached Quality Gate status for {project_key}")
                    return cached_result

            # Make API call
            response = await self.client.get(
                "/qualitygates/project_status",
                params={"projectKey": project_key}
            )
            
            project_status = response.get("projectStatus", {})
            
            # Format response
            result = {
                "project_key": project_key,
                "status": project_status.get("status", "NONE"),
                "conditions": project_status.get("conditions", []),
                "ignored_conditions": project_status.get("ignoredConditions", False),
                "period": project_status.get("period"),
            }
            
            # Add summary information
            if result["conditions"]:
                failed_conditions = [
                    c for c in result["conditions"] 
                    if c.get("status") in ["ERROR", "WARN"]
                ]
                result["failed_conditions_count"] = len(failed_conditions)
                result["total_conditions_count"] = len(result["conditions"])
            else:
                result["failed_conditions_count"] = 0
                result["total_conditions_count"] = 0
            
            # Cache result
            if self.cache:
                await self.cache.set("quality_gates", "status", result, project_key=project_key)
            
            self.logger.info(f"Retrieved Quality Gate status for project {project_key}: {result['status']}")
            return result
            
        except Exception as e:
            self.logger.error(f"Failed to get Quality Gate status for project {project_key}: {e}")
            raise RuntimeError(f"Failed to get Quality Gate status: {str(e)}")

    async def get_project_history(
        self,
        project_key: str,
        metrics: Optional[List[str]] = None,
        from_date: Optional[str] = None,
        to_date: Optional[str] = None,
        page: int = 1,
        page_size: int = 1000,
    ) -> Dict[str, Any]:
        """
        Get historical metrics data for a project.

        Args:
            project_key: Unique project key
            metrics: List of metrics to retrieve history for
            from_date: Start date (YYYY-MM-DD format)
            to_date: End date (YYYY-MM-DD format)
            page: Page number (1-based)
            page_size: Number of records per page

        Returns:
            Dictionary containing historical metrics data
        """
        try:
            # Validate project key
            project_key = InputValidator.validate_project_key(project_key)
            
            # Use core metrics if none specified
            if not metrics:
                metrics = self.CORE_METRICS[:5]  # Limit to first 5 for performance
            else:
                metrics = InputValidator.validate_metric_keys(metrics)
            
            # Validate pagination
            page, page_size = InputValidator.validate_pagination_params(page, page_size)
            
            # Build cache key
            cache_key_params = {
                "project_key": project_key,
                "metrics": ",".join(sorted(metrics)),
                "from_date": from_date,
                "to_date": to_date,
                "page": page,
                "page_size": page_size,
            }
            
            # Try cache first
            if self.cache:
                cached_result = await self.cache.get("metrics", "history", **cache_key_params)
                if cached_result:
                    self.logger.debug(f"Returning cached history for {project_key}")
                    return cached_result

            # Build API parameters
            params = {
                "component": project_key,
                "metrics": ",".join(metrics),
                "p": page,
                "ps": page_size,
            }
            
            if from_date:
                params["from"] = from_date
            if to_date:
                params["to"] = to_date

            # Make API call
            response = await self.client.get("/measures/search_history", params=params)
            
            # Format response
            measures = response.get("measures", [])
            paging = response.get("paging", {})
            
            # Organize data by metric
            metrics_history = {}
            for measure in measures:
                metric_key = measure["metric"]
                history = measure.get("history", [])
                
                metrics_history[metric_key] = [
                    {
                        "date": entry["date"],
                        "value": entry.get("value"),
                    }
                    for entry in history
                ]
            
            result = {
                "project_key": project_key,
                "metrics_history": metrics_history,
                "paging": paging,
                "date_range": {
                    "from": from_date,
                    "to": to_date,
                },
            }
            
            # Cache result with longer TTL (historical data doesn't change often)
            if self.cache:
                await self.cache.set("metrics", "history", result, ttl=1800, **cache_key_params)
            
            total_points = sum(len(history) for history in metrics_history.values())
            self.logger.info(f"Retrieved {total_points} historical data points for project {project_key}")
            return result
            
        except Exception as e:
            self.logger.error(f"Failed to get project history for {project_key}: {e}")
            raise RuntimeError(f"Failed to get project history: {str(e)}")

    async def get_metrics_definitions(self) -> Dict[str, Any]:
        """
        Get definitions of all available metrics.

        Returns:
            Dictionary containing metric definitions
        """
        try:
            # Try cache first
            if self.cache:
                cached_result = await self.cache.get("metrics", "definitions")
                if cached_result:
                    self.logger.debug("Returning cached metrics definitions")
                    return cached_result

            # Make API call
            response = await self.client.get("/metrics/search", params={"ps": 500})
            
            metrics = response.get("metrics", [])
            
            # Format response
            result = {
                "metrics": {
                    metric["key"]: {
                        "name": metric.get("name", ""),
                        "description": metric.get("description", ""),
                        "type": metric.get("type", ""),
                        "domain": metric.get("domain", ""),
                        "direction": metric.get("direction", 0),
                        "qualitative": metric.get("qualitative", False),
                        "hidden": metric.get("hidden", False),
                    }
                    for metric in metrics
                },
                "total_metrics": len(metrics),
            }
            
            # Cache result with long TTL (definitions don't change often)
            if self.cache:
                await self.cache.set("metrics", "definitions", result, ttl=3600)
            
            self.logger.info(f"Retrieved {len(metrics)} metric definitions")
            return result
            
        except Exception as e:
            self.logger.error(f"Failed to get metrics definitions: {e}")
            raise RuntimeError(f"Failed to get metrics definitions: {str(e)}")

    async def analyze_project_quality(self, project_key: str) -> Dict[str, Any]:
        """
        Perform comprehensive quality analysis of a project.

        Args:
            project_key: Unique project key

        Returns:
            Dictionary containing comprehensive quality analysis
        """
        try:
            # Validate project key
            project_key = InputValidator.validate_project_key(project_key)
            
            # Get all relevant data
            measures = await self.get_measures(project_key, self.CORE_METRICS)
            quality_gate = await self.get_quality_gate_status(project_key)
            
            # Analyze metrics
            metrics = measures["metrics"]
            analysis = {
                "project_key": project_key,
                "project_name": measures["project_name"],
                "last_analysis": measures["last_analysis"],
                "overall_status": quality_gate["status"],
                "quality_summary": {},
                "recommendations": [],
                "risk_factors": [],
            }
            
            # Coverage analysis
            coverage = metrics.get("coverage", {}).get("value")
            if coverage:
                coverage_val = float(coverage)
                analysis["quality_summary"]["coverage"] = {
                    "value": coverage_val,
                    "status": "good" if coverage_val >= 80 else "warning" if coverage_val >= 60 else "poor",
                }
                
                if coverage_val < 80:
                    analysis["recommendations"].append(
                        f"Increase test coverage from {coverage_val}% to at least 80%"
                    )
                if coverage_val < 60:
                    analysis["risk_factors"].append("Low test coverage increases bug risk")

            # Bug analysis
            bugs = metrics.get("bugs", {}).get("value")
            if bugs:
                bugs_val = int(bugs)
                analysis["quality_summary"]["bugs"] = {
                    "value": bugs_val,
                    "status": "good" if bugs_val == 0 else "warning" if bugs_val <= 5 else "poor",
                }
                
                if bugs_val > 0:
                    analysis["recommendations"].append(f"Fix {bugs_val} existing bugs")
                if bugs_val > 10:
                    analysis["risk_factors"].append("High number of bugs affects reliability")

            # Vulnerability analysis
            vulnerabilities = metrics.get("vulnerabilities", {}).get("value")
            if vulnerabilities:
                vuln_val = int(vulnerabilities)
                analysis["quality_summary"]["vulnerabilities"] = {
                    "value": vuln_val,
                    "status": "good" if vuln_val == 0 else "poor",
                }
                
                if vuln_val > 0:
                    analysis["recommendations"].append(f"Fix {vuln_val} security vulnerabilities immediately")
                    analysis["risk_factors"].append("Security vulnerabilities pose immediate risk")

            # Technical debt analysis
            tech_debt = metrics.get("sqale_index", {}).get("value")
            if tech_debt:
                debt_minutes = int(tech_debt)
                debt_hours = debt_minutes / 60
                debt_days = debt_hours / 8  # 8-hour work day
                
                analysis["quality_summary"]["technical_debt"] = {
                    "minutes": debt_minutes,
                    "hours": round(debt_hours, 1),
                    "days": round(debt_days, 1),
                    "status": "good" if debt_days <= 5 else "warning" if debt_days <= 20 else "poor",
                }
                
                if debt_days > 10:
                    analysis["recommendations"].append(
                        f"Address technical debt ({debt_days:.1f} days of work)"
                    )

            # Duplication analysis
            duplication = metrics.get("duplicated_lines_density", {}).get("value")
            if duplication:
                dup_val = float(duplication)
                analysis["quality_summary"]["duplication"] = {
                    "value": dup_val,
                    "status": "good" if dup_val <= 3 else "warning" if dup_val <= 10 else "poor",
                }
                
                if dup_val > 5:
                    analysis["recommendations"].append(
                        f"Reduce code duplication from {dup_val}% to under 5%"
                    )

            # Overall risk assessment
            risk_count = len(analysis["risk_factors"])
            analysis["overall_risk"] = (
                "low" if risk_count == 0 else
                "medium" if risk_count <= 2 else
                "high"
            )
            
            self.logger.info(f"Completed quality analysis for project {project_key}")
            return analysis
            
        except Exception as e:
            self.logger.error(f"Failed to analyze project quality for {project_key}: {e}")
            raise RuntimeError(f"Failed to analyze project quality: {str(e)}")
