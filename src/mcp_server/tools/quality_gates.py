"""Quality Gates management tools for SonarQube MCP."""

from typing import Any, Dict, List, Optional

import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from sonarqube_client import SonarQubeClient, InputValidator
from utils import CacheManager, get_logger

logger = get_logger(__name__)


class QualityGateTools:
    """Tools for SonarQube Quality Gates management."""

    def __init__(self, client: SonarQubeClient, cache_manager: Optional[CacheManager] = None):
        """Initialize Quality Gate tools."""
        self.client = client
        self.cache = cache_manager
        self.logger = logger

    async def list_quality_gates(self) -> Dict[str, Any]:
        """
        List all available Quality Gates.

        Returns:
            Dictionary containing Quality Gates list
        """
        try:
            # Try cache first
            if self.cache:
                cached_result = await self.cache.get("quality_gates", "list")
                if cached_result:
                    self.logger.debug("Returning cached Quality Gates list")
                    return cached_result

            # Make API call
            response = await self.client.get("/qualitygates/list")
            
            quality_gates = response.get("qualitygates", [])
            
            result = {
                "quality_gates": quality_gates,
                "total_count": len(quality_gates),
                "default_gate": next(
                    (qg for qg in quality_gates if qg.get("isDefault", False)),
                    None
                ),
            }
            
            # Cache result with longer TTL (Quality Gates don't change often)
            if self.cache:
                await self.cache.set("quality_gates", "list", result, ttl=1800)
            
            self.logger.info(f"Retrieved {len(quality_gates)} Quality Gates")
            return result
            
        except Exception as e:
            self.logger.error(f"Failed to list Quality Gates: {e}")
            raise RuntimeError(f"Failed to list Quality Gates: {str(e)}")

    async def get_quality_gate_conditions(self, quality_gate_name: str) -> Dict[str, Any]:
        """
        Get conditions for a specific Quality Gate.

        Args:
            quality_gate_name: Name of the Quality Gate

        Returns:
            Dictionary containing Quality Gate conditions and details
        """
        try:
            # Sanitize quality gate name
            quality_gate_name = quality_gate_name.strip()
            if not quality_gate_name:
                raise ValueError("Quality Gate name cannot be empty")
            
            # Try cache first
            if self.cache:
                cached_result = await self.cache.get(
                    "quality_gates", "conditions", name=quality_gate_name
                )
                if cached_result:
                    self.logger.debug(f"Returning cached conditions for Quality Gate {quality_gate_name}")
                    return cached_result

            # First, get the Quality Gate ID by name
            gates_response = await self.client.get("/qualitygates/list")
            quality_gates = gates_response.get("qualitygates", [])
            
            target_gate = None
            for gate in quality_gates:
                if gate.get("name") == quality_gate_name:
                    target_gate = gate
                    break
            
            if not target_gate:
                raise RuntimeError(f"Quality Gate not found: {quality_gate_name}")
            
            gate_id = target_gate.get("id")
            
            # Get conditions for the Quality Gate
            conditions_response = await self.client.get(
                "/qualitygates/show",
                params={"id": gate_id}
            )
            
            result = {
                "quality_gate": {
                    "id": gate_id,
                    "name": quality_gate_name,
                    "is_default": target_gate.get("isDefault", False),
                    "is_built_in": target_gate.get("isBuiltIn", False),
                },
                "conditions": conditions_response.get("conditions", []),
                "total_conditions": len(conditions_response.get("conditions", [])),
            }
            
            # Add condition analysis
            if result["conditions"]:
                result["condition_analysis"] = self._analyze_conditions(result["conditions"])
            
            # Cache result with longer TTL
            if self.cache:
                await self.cache.set(
                    "quality_gates", "conditions", result, ttl=1800, name=quality_gate_name
                )
            
            self.logger.info(f"Retrieved {len(result['conditions'])} conditions for Quality Gate {quality_gate_name}")
            return result
            
        except Exception as e:
            self.logger.error(f"Failed to get Quality Gate conditions for {quality_gate_name}: {e}")
            raise RuntimeError(f"Failed to get Quality Gate conditions: {str(e)}")

    async def get_project_quality_gate_status(self, project_key: str) -> Dict[str, Any]:
        """
        Get Quality Gate status for a specific project with detailed analysis.

        Args:
            project_key: Unique project key

        Returns:
            Dictionary containing detailed Quality Gate status
        """
        try:
            # Validate project key
            project_key = InputValidator.validate_project_key(project_key)
            
            # Try cache first
            if self.cache:
                cached_result = await self.cache.get(
                    "quality_gates", "project_status", project_key=project_key
                )
                if cached_result:
                    self.logger.debug(f"Returning cached Quality Gate status for {project_key}")
                    return cached_result

            # Make API call
            response = await self.client.get(
                "/qualitygates/project_status",
                params={"projectKey": project_key}
            )
            
            project_status = response.get("projectStatus", {})
            
            result = {
                "project_key": project_key,
                "status": project_status.get("status", "NONE"),
                "conditions": project_status.get("conditions", []),
                "ignored_conditions": project_status.get("ignoredConditions", False),
                "period": project_status.get("period"),
            }
            
            # Analyze conditions
            if result["conditions"]:
                result["condition_analysis"] = self._analyze_project_conditions(result["conditions"])
            
            # Add recommendations for failed conditions
            if result["status"] in ["ERROR", "WARN"]:
                result["recommendations"] = self._generate_quality_gate_recommendations(
                    result["conditions"]
                )
            
            # Cache result
            if self.cache:
                await self.cache.set(
                    "quality_gates", "project_status", result, project_key=project_key
                )
            
            self.logger.info(f"Retrieved Quality Gate status for project {project_key}: {result['status']}")
            return result
            
        except Exception as e:
            self.logger.error(f"Failed to get Quality Gate status for project {project_key}: {e}")
            raise RuntimeError(f"Failed to get Quality Gate status: {str(e)}")

    def _analyze_conditions(self, conditions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze Quality Gate conditions."""
        analysis = {
            "total_conditions": len(conditions),
            "by_metric": {},
            "by_operator": {},
            "coverage_conditions": [],
            "security_conditions": [],
            "maintainability_conditions": [],
        }
        
        for condition in conditions:
            metric = condition.get("metric", "unknown")
            operator = condition.get("op", "unknown")
            
            # Count by metric
            analysis["by_metric"][metric] = analysis["by_metric"].get(metric, 0) + 1
            
            # Count by operator
            analysis["by_operator"][operator] = analysis["by_operator"].get(operator, 0) + 1
            
            # Categorize conditions
            if "coverage" in metric.lower():
                analysis["coverage_conditions"].append(condition)
            elif any(sec in metric.lower() for sec in ["security", "vulnerability", "hotspot"]):
                analysis["security_conditions"].append(condition)
            elif any(maint in metric.lower() for maint in ["smell", "debt", "maintainability"]):
                analysis["maintainability_conditions"].append(condition)
        
        return analysis

    def _analyze_project_conditions(self, conditions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze project-specific Quality Gate conditions."""
        analysis = {
            "total_conditions": len(conditions),
            "passed_conditions": 0,
            "failed_conditions": 0,
            "warning_conditions": 0,
            "failed_condition_details": [],
        }
        
        for condition in conditions:
            status = condition.get("status", "UNKNOWN")
            
            if status == "OK":
                analysis["passed_conditions"] += 1
            elif status == "ERROR":
                analysis["failed_conditions"] += 1
                analysis["failed_condition_details"].append({
                    "metric": condition.get("metricKey"),
                    "operator": condition.get("comparator"),
                    "threshold": condition.get("errorThreshold"),
                    "actual_value": condition.get("actualValue"),
                    "status": status,
                })
            elif status == "WARN":
                analysis["warning_conditions"] += 1
        
        # Calculate pass rate
        if analysis["total_conditions"] > 0:
            analysis["pass_rate_percent"] = (
                analysis["passed_conditions"] / analysis["total_conditions"] * 100
            )
        else:
            analysis["pass_rate_percent"] = 100.0
        
        return analysis

    def _generate_quality_gate_recommendations(
        self, conditions: List[Dict[str, Any]]
    ) -> List[str]:
        """Generate recommendations for failed Quality Gate conditions."""
        recommendations = []
        
        for condition in conditions:
            if condition.get("status") not in ["ERROR", "WARN"]:
                continue
            
            metric = condition.get("metricKey", "")
            operator = condition.get("comparator", "")
            threshold = condition.get("errorThreshold", "")
            actual = condition.get("actualValue", "")
            
            if metric == "coverage":
                recommendations.append(
                    f"Increase test coverage from {actual}% to at least {threshold}%"
                )
            elif metric == "new_coverage":
                recommendations.append(
                    f"Ensure new code has at least {threshold}% test coverage (currently {actual}%)"
                )
            elif metric in ["bugs", "new_bugs"]:
                recommendations.append(
                    f"Fix existing bugs (currently {actual}, threshold: {threshold})"
                )
            elif metric in ["vulnerabilities", "new_vulnerabilities"]:
                recommendations.append(
                    f"Address security vulnerabilities (currently {actual}, threshold: {threshold})"
                )
            elif metric in ["code_smells", "new_code_smells"]:
                recommendations.append(
                    f"Resolve code smells (currently {actual}, threshold: {threshold})"
                )
            elif metric == "duplicated_lines_density":
                recommendations.append(
                    f"Reduce code duplication from {actual}% to under {threshold}%"
                )
            else:
                recommendations.append(
                    f"Improve {metric}: current value {actual}, required {operator} {threshold}"
                )
        
        return recommendations
