"""Metrics resources for MCP."""

from typing import Any, Dict, List, Optional

from ...sonarqube_client import InputValidator
from .base import BaseResource, ResourceURI


class MetricsResource(BaseResource):
    """Resource handler for metrics-related URIs."""
    
    # Common metric groups for dashboard-style presentation
    METRIC_GROUPS = {
        "overview": [
            "ncloc", "lines", "files", "functions", "classes",
            "complexity", "cognitive_complexity"
        ],
        "reliability": [
            "bugs", "new_bugs", "reliability_rating", "new_reliability_rating"
        ],
        "security": [
            "vulnerabilities", "new_vulnerabilities", "security_rating", 
            "new_security_rating", "security_hotspots", "new_security_hotspots"
        ],
        "maintainability": [
            "code_smells", "new_code_smells", "sqale_rating", "new_maintainability_rating",
            "technical_debt", "new_technical_debt"
        ],
        "coverage": [
            "coverage", "new_coverage", "line_coverage", "new_line_coverage",
            "branch_coverage", "new_branch_coverage", "tests", "test_execution_time"
        ],
        "duplication": [
            "duplicated_lines_density", "new_duplicated_lines_density",
            "duplicated_lines", "duplicated_blocks", "duplicated_files"
        ]
    }
    
    def supports_uri(self, uri: ResourceURI) -> bool:
        """Check if this resource supports the URI."""
        return uri.resource_type == "metrics"
    
    async def get_resource(self, uri: ResourceURI) -> Dict[str, Any]:
        """Get metrics resource data."""
        try:
            if not uri.resource_id:
                raise ValueError("Project key is required for metrics resource")
            
            return await self._get_project_metrics(uri)
        except Exception as e:
            self.logger.error(f"Failed to get metrics resource {uri}: {e}")
            raise RuntimeError(f"Failed to get metrics resource: {str(e)}")
    
    async def _get_project_metrics(self, uri: ResourceURI) -> Dict[str, Any]:
        """Get comprehensive metrics for a project."""
        project_key = uri.resource_id
        
        async def fetch_metrics():
            # Validate project key
            project_key_validated = InputValidator.validate_project_key(project_key)
            
            # Determine which metrics to fetch
            requested_metrics = self._parse_requested_metrics(uri.query_params)
            include_history = uri.query_params.get("include_history", "false").lower() == "true"
            
            # Get current metrics
            current_metrics = await self._get_current_metrics(project_key_validated, requested_metrics)
            
            # Get historical data if requested
            historical_data = None
            if include_history:
                historical_data = await self._get_historical_metrics(
                    project_key_validated, 
                    requested_metrics,
                    uri.query_params
                )
            
            # Get Quality Gate status
            quality_gate = await self._get_quality_gate_status(project_key_validated)
            
            # Organize metrics by groups for dashboard presentation
            grouped_metrics = self._group_metrics(current_metrics)
            
            return {
                "uri": str(uri),
                "resource_type": "project_metrics",
                "project_key": project_key,
                "metrics": {
                    "current": current_metrics,
                    "grouped": grouped_metrics,
                    "historical": historical_data,
                },
                "quality_gate": quality_gate,
                "metadata": {
                    "generated_at": self._get_current_timestamp(),
                    "cache_ttl": 300,
                    "requested_metrics": requested_metrics,
                    "includes_history": include_history,
                }
            }
        
        return await self._get_cached_or_fetch(uri, fetch_metrics, ttl=300)
    
    def _parse_requested_metrics(self, query_params: Dict[str, Any]) -> List[str]:
        """Parse requested metrics from query parameters."""
        metrics_param = query_params.get("metrics")
        
        if metrics_param:
            # Specific metrics requested
            if isinstance(metrics_param, str):
                return [m.strip() for m in metrics_param.split(",")]
            elif isinstance(metrics_param, list):
                return metrics_param
        
        # Check for metric groups
        groups_param = query_params.get("groups", "overview,reliability,security,maintainability")
        if isinstance(groups_param, str):
            requested_groups = [g.strip() for g in groups_param.split(",")]
        else:
            requested_groups = groups_param if isinstance(groups_param, list) else ["overview"]
        
        # Collect metrics from requested groups
        metrics = []
        for group in requested_groups:
            if group in self.METRIC_GROUPS:
                metrics.extend(self.METRIC_GROUPS[group])
        
        # Remove duplicates while preserving order
        return list(dict.fromkeys(metrics))
    
    async def _get_current_metrics(self, project_key: str, metrics: List[str]) -> Dict[str, Any]:
        """Get current metrics for the project."""
        try:
            response = await self.client.get(
                "/measures/component",
                params={
                    "component": project_key,
                    "metricKeys": ",".join(metrics)
                }
            )
            
            component = response.get("component", {})
            measures = component.get("measures", [])
            
            # Convert to dictionary with proper typing
            metrics_dict = {}
            for measure in measures:
                metric_key = measure.get("metric")
                value = measure.get("value")
                best_value = measure.get("bestValue", False)
                
                if metric_key and value is not None:
                    # Try to convert to appropriate type
                    try:
                        if "." in str(value):
                            typed_value = float(value)
                        else:
                            typed_value = int(value)
                    except (ValueError, TypeError):
                        typed_value = str(value)
                    
                    metrics_dict[metric_key] = {
                        "value": typed_value,
                        "best_value": best_value,
                        "formatted_value": self._format_metric_value(metric_key, typed_value)
                    }
            
            return metrics_dict
            
        except Exception as e:
            self.logger.error(f"Failed to get current metrics for {project_key}: {e}")
            return {}
    
    async def _get_historical_metrics(
        self, 
        project_key: str, 
        metrics: List[str],
        query_params: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Get historical metrics data."""
        try:
            # Parse time range parameters
            from_date = query_params.get("from_date")
            to_date = query_params.get("to_date")
            
            params = {
                "component": project_key,
                "metrics": ",".join(metrics[:10]),  # Limit to avoid too large requests
                "ps": 1000  # Get up to 1000 data points
            }
            
            if from_date:
                params["from"] = from_date
            if to_date:
                params["to"] = to_date
            
            response = await self.client.get("/measures/search_history", params=params)
            
            measures = response.get("measures", [])
            
            # Organize historical data by metric
            historical_data = {}
            for measure in measures:
                metric_key = measure.get("metric")
                history = measure.get("history", [])
                
                if metric_key and history:
                    historical_data[metric_key] = [
                        {
                            "date": point.get("date"),
                            "value": self._parse_metric_value(point.get("value"))
                        }
                        for point in history
                        if point.get("value") is not None
                    ]
            
            return historical_data
            
        except Exception as e:
            self.logger.warning(f"Failed to get historical metrics for {project_key}: {e}")
            return None
    
    async def _get_quality_gate_status(self, project_key: str) -> Dict[str, Any]:
        """Get Quality Gate status for the project."""
        try:
            response = await self.client.get(
                "/qualitygates/project_status",
                params={"projectKey": project_key}
            )
            
            project_status = response.get("projectStatus", {})
            
            # Simplify the response for resource consumption
            return {
                "status": project_status.get("status", "UNKNOWN"),
                "conditions": project_status.get("conditions", []),
                "ignored_conditions": project_status.get("ignoredConditions", False),
            }
            
        except Exception as e:
            self.logger.warning(f"Failed to get Quality Gate status for {project_key}: {e}")
            return {"status": "UNKNOWN", "conditions": [], "ignored_conditions": False}
    
    def _group_metrics(self, metrics: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
        """Group metrics by category for dashboard presentation."""
        grouped = {}
        
        for group_name, metric_keys in self.METRIC_GROUPS.items():
            group_metrics = {}
            for metric_key in metric_keys:
                if metric_key in metrics:
                    group_metrics[metric_key] = metrics[metric_key]
            
            if group_metrics:
                grouped[group_name] = group_metrics
        
        return grouped
    
    def _parse_metric_value(self, value: Any) -> Any:
        """Parse metric value to appropriate type."""
        if value is None:
            return None
        
        try:
            if isinstance(value, (int, float)):
                return value
            
            value_str = str(value)
            if "." in value_str:
                return float(value_str)
            else:
                return int(value_str)
        except (ValueError, TypeError):
            return str(value)
    
    def _format_metric_value(self, metric_key: str, value: Any) -> str:
        """Format metric value for display."""
        if value is None:
            return "N/A"
        
        # Percentage metrics
        if metric_key.endswith("_density") or metric_key.endswith("coverage") or metric_key.endswith("_rating"):
            if isinstance(value, (int, float)):
                return f"{value:.1f}%"
        
        # Time metrics
        if "time" in metric_key.lower():
            if isinstance(value, (int, float)):
                if value < 60:
                    return f"{value:.0f}s"
                elif value < 3600:
                    return f"{value/60:.1f}m"
                else:
                    return f"{value/3600:.1f}h"
        
        # Large numbers
        if isinstance(value, (int, float)) and value >= 1000:
            if value >= 1000000:
                return f"{value/1000000:.1f}M"
            elif value >= 1000:
                return f"{value/1000:.1f}K"
        
        return str(value)
    
    def _get_current_timestamp(self) -> str:
        """Get current timestamp in ISO format."""
        from datetime import datetime
        return datetime.utcnow().isoformat() + "Z"
