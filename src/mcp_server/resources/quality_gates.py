"""Quality Gates resources for MCP."""

from typing import Any, Dict, List, Optional

from ...sonarqube_client import InputValidator
from .base import BaseResource, ResourceURI


class QualityGatesResource(BaseResource):
    """Resource handler for Quality Gates-related URIs."""
    
    def supports_uri(self, uri: ResourceURI) -> bool:
        """Check if this resource supports the URI."""
        return uri.resource_type == "quality_gates" or uri.resource_type == "quality_gate"
    
    async def get_resource(self, uri: ResourceURI) -> Dict[str, Any]:
        """Get Quality Gates resource data."""
        try:
            if uri.resource_id:
                # Specific project Quality Gate: sonarqube://quality_gate/{project_key}
                return await self._get_project_quality_gate(uri)
            else:
                # All Quality Gates: sonarqube://quality_gates
                return await self._get_quality_gates_list(uri)
        except Exception as e:
            self.logger.error(f"Failed to get Quality Gates resource {uri}: {e}")
            raise RuntimeError(f"Failed to get Quality Gates resource: {str(e)}")
    
    async def _get_quality_gates_list(self, uri: ResourceURI) -> Dict[str, Any]:
        """Get list of all Quality Gates with their conditions."""
        async def fetch_quality_gates():
            # Get all Quality Gates
            response = await self.client.get("/qualitygates/list")
            quality_gates = response.get("qualitygates", [])
            
            # Enrich each Quality Gate with conditions if requested
            include_conditions = uri.query_params.get("include_conditions", "false").lower() == "true"
            
            enriched_gates = []
            for gate in quality_gates:
                enriched_gate = gate.copy()
                
                if include_conditions:
                    try:
                        gate_id = gate.get("id")
                        conditions_response = await self.client.get(
                            "/qualitygates/show",
                            params={"id": gate_id}
                        )
                        enriched_gate["conditions"] = conditions_response.get("conditions", [])
                        enriched_gate["condition_count"] = len(enriched_gate["conditions"])
                    except Exception as e:
                        self.logger.warning(f"Failed to get conditions for gate {gate.get('name')}: {e}")
                        enriched_gate["conditions"] = []
                        enriched_gate["condition_count"] = 0
                
                enriched_gates.append(enriched_gate)
            
            # Find default gate
            default_gate = next((gate for gate in enriched_gates if gate.get("isDefault")), None)
            
            return {
                "uri": str(uri),
                "resource_type": "quality_gates_list",
                "quality_gates": enriched_gates,
                "total_count": len(enriched_gates),
                "default_gate": default_gate,
                "metadata": {
                    "generated_at": self._get_current_timestamp(),
                    "cache_ttl": 600,  # Quality Gates don't change often
                    "includes_conditions": include_conditions,
                }
            }
        
        return await self._get_cached_or_fetch(uri, fetch_quality_gates, ttl=600)
    
    async def _get_project_quality_gate(self, uri: ResourceURI) -> Dict[str, Any]:
        """Get Quality Gate status for a specific project."""
        project_key = uri.resource_id
        
        async def fetch_project_quality_gate():
            # Validate project key
            project_key_validated = InputValidator.validate_project_key(project_key)
            
            # Get project Quality Gate status
            status_response = await self.client.get(
                "/qualitygates/project_status",
                params={"projectKey": project_key_validated}
            )
            
            project_status = status_response.get("projectStatus", {})
            
            # Get Quality Gate details if requested
            include_gate_details = uri.query_params.get("include_gate_details", "true").lower() == "true"
            gate_details = None
            
            if include_gate_details:
                gate_details = await self._get_project_gate_details(project_key_validated)
            
            # Analyze conditions
            conditions = project_status.get("conditions", [])
            condition_analysis = self._analyze_conditions(conditions)
            
            # Generate recommendations for failed conditions
            recommendations = []
            if project_status.get("status") in ["ERROR", "WARN"]:
                recommendations = self._generate_recommendations(conditions)
            
            return {
                "uri": str(uri),
                "resource_type": "project_quality_gate",
                "project_key": project_key,
                "status": {
                    "overall": project_status.get("status", "UNKNOWN"),
                    "conditions": conditions,
                    "ignored_conditions": project_status.get("ignoredConditions", False),
                    "period": project_status.get("period"),
                },
                "analysis": condition_analysis,
                "recommendations": recommendations,
                "quality_gate": gate_details,
                "metadata": {
                    "generated_at": self._get_current_timestamp(),
                    "cache_ttl": 300,
                    "includes_gate_details": include_gate_details,
                }
            }
        
        return await self._get_cached_or_fetch(uri, fetch_project_quality_gate, ttl=300)
    
    async def _get_project_gate_details(self, project_key: str) -> Optional[Dict[str, Any]]:
        """Get details about the Quality Gate assigned to the project."""
        try:
            # First, get the project's Quality Gate assignment
            # Note: This might require admin permissions in some SonarQube versions
            
            # Get all Quality Gates to find which one applies to this project
            gates_response = await self.client.get("/qualitygates/list")
            quality_gates = gates_response.get("qualitygates", [])
            
            # For now, we'll return the default gate details
            # In a full implementation, you'd need to check project-specific assignments
            default_gate = next((gate for gate in quality_gates if gate.get("isDefault")), None)
            
            if default_gate:
                gate_id = default_gate.get("id")
                conditions_response = await self.client.get(
                    "/qualitygates/show",
                    params={"id": gate_id}
                )
                
                return {
                    "id": gate_id,
                    "name": default_gate.get("name"),
                    "is_default": True,
                    "is_built_in": default_gate.get("isBuiltIn", False),
                    "conditions": conditions_response.get("conditions", []),
                }
            
            return None
            
        except Exception as e:
            self.logger.warning(f"Failed to get Quality Gate details for {project_key}: {e}")
            return None
    
    def _analyze_conditions(self, conditions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze Quality Gate conditions."""
        if not conditions:
            return {
                "total_conditions": 0,
                "passed_conditions": 0,
                "failed_conditions": 0,
                "warning_conditions": 0,
                "pass_rate_percent": 100.0,
                "failed_condition_details": [],
                "condition_categories": {},
            }
        
        analysis = {
            "total_conditions": len(conditions),
            "passed_conditions": 0,
            "failed_conditions": 0,
            "warning_conditions": 0,
            "failed_condition_details": [],
            "condition_categories": {
                "reliability": [],
                "security": [],
                "maintainability": [],
                "coverage": [],
                "duplication": [],
                "other": [],
            }
        }
        
        for condition in conditions:
            status = condition.get("status", "UNKNOWN")
            metric_key = condition.get("metricKey", "")
            
            # Count by status
            if status == "OK":
                analysis["passed_conditions"] += 1
            elif status == "ERROR":
                analysis["failed_conditions"] += 1
                analysis["failed_condition_details"].append({
                    "metric": metric_key,
                    "operator": condition.get("comparator"),
                    "threshold": condition.get("errorThreshold"),
                    "actual_value": condition.get("actualValue"),
                    "status": status,
                })
            elif status == "WARN":
                analysis["warning_conditions"] += 1
            
            # Categorize by metric type
            category = self._categorize_metric(metric_key)
            analysis["condition_categories"][category].append({
                "metric": metric_key,
                "status": status,
                "actual_value": condition.get("actualValue"),
                "threshold": condition.get("errorThreshold"),
            })
        
        # Calculate pass rate
        analysis["pass_rate_percent"] = (
            analysis["passed_conditions"] / analysis["total_conditions"] * 100
            if analysis["total_conditions"] > 0 else 100.0
        )
        
        return analysis
    
    def _categorize_metric(self, metric_key: str) -> str:
        """Categorize a metric by its type."""
        metric_lower = metric_key.lower()
        
        if any(keyword in metric_lower for keyword in ["bug", "reliability"]):
            return "reliability"
        elif any(keyword in metric_lower for keyword in ["vulnerability", "security", "hotspot"]):
            return "security"
        elif any(keyword in metric_lower for keyword in ["smell", "debt", "maintainability"]):
            return "maintainability"
        elif any(keyword in metric_lower for keyword in ["coverage", "test"]):
            return "coverage"
        elif any(keyword in metric_lower for keyword in ["duplicat", "duplication"]):
            return "duplication"
        else:
            return "other"
    
    def _generate_recommendations(self, conditions: List[Dict[str, Any]]) -> List[str]:
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
                    f"Increase test coverage from {actual}% to at least {threshold}% by adding unit tests"
                )
            elif metric == "new_coverage":
                recommendations.append(
                    f"Ensure new code has at least {threshold}% test coverage (currently {actual}%)"
                )
            elif metric in ["bugs", "new_bugs"]:
                recommendations.append(
                    f"Fix {actual} bug(s) to meet the threshold of {threshold}"
                )
            elif metric in ["vulnerabilities", "new_vulnerabilities"]:
                recommendations.append(
                    f"Address {actual} security vulnerabilities to meet the threshold of {threshold}"
                )
            elif metric in ["code_smells", "new_code_smells"]:
                recommendations.append(
                    f"Resolve {actual} code smells to meet the threshold of {threshold}"
                )
            elif metric == "duplicated_lines_density":
                recommendations.append(
                    f"Reduce code duplication from {actual}% to under {threshold}%"
                )
            elif metric in ["sqale_rating", "reliability_rating", "security_rating"]:
                recommendations.append(
                    f"Improve {metric.replace('_', ' ')} from {actual} to {threshold} or better"
                )
            else:
                recommendations.append(
                    f"Improve {metric}: current value {actual}, required {operator} {threshold}"
                )
        
        return recommendations
    
    def _get_current_timestamp(self) -> str:
        """Get current timestamp in ISO format."""
        from datetime import datetime
        return datetime.utcnow().isoformat() + "Z"
