"""Security assessment prompt for vulnerability evaluation."""

from typing import Any, Dict, List

from ...sonarqube_client import InputValidator
from .base import BasePrompt


class SecurityAssessmentPrompt(BasePrompt):
    """Prompt for comprehensive security assessment."""
    
    def get_name(self) -> str:
        return "security_assessment"
    
    def get_description(self) -> str:
        return "Perform comprehensive security assessment of a SonarQube project including vulnerabilities, hotspots, and risk analysis"
    
    def get_arguments(self) -> List[Dict[str, Any]]:
        return [
            {
                "name": "project_key",
                "description": "The SonarQube project key to assess",
                "required": True,
                "type": "string"
            },
            {
                "name": "include_resolved",
                "description": "Include resolved security issues in the assessment",
                "required": False,
                "type": "boolean",
                "default": False
            },
            {
                "name": "risk_threshold",
                "description": "Risk threshold for prioritization (LOW, MEDIUM, HIGH)",
                "required": False,
                "type": "string",
                "default": "MEDIUM"
            },
            {
                "name": "include_recommendations",
                "description": "Include detailed remediation recommendations",
                "required": False,
                "type": "boolean",
                "default": True
            }
        ]
    
    async def execute(self, arguments: Dict[str, Any]) -> str:
        """Execute the security assessment prompt."""
        project_key = arguments.get("project_key")
        include_resolved = arguments.get("include_resolved", False)
        risk_threshold = arguments.get("risk_threshold", "MEDIUM")
        include_recommendations = arguments.get("include_recommendations", True)
        
        if not project_key:
            raise ValueError("project_key is required")
        
        async def generate_assessment():
            # Validate project key
            project_key_validated = InputValidator.validate_project_key(project_key)
            
            # Get project information
            project_info = await self._get_project_info(project_key_validated)
            
            # Get security metrics
            security_metrics = await self._get_security_metrics(project_key_validated)
            
            # Get vulnerabilities
            vulnerabilities = await self._get_vulnerabilities(project_key_validated, include_resolved)
            
            # Get security hotspots
            hotspots = await self._get_security_hotspots(project_key_validated, include_resolved)
            
            # Perform risk analysis
            risk_analysis = self._perform_risk_analysis(vulnerabilities, hotspots, security_metrics)
            
            # Generate assessment report
            assessment = self._generate_security_assessment(
                project_info, security_metrics, vulnerabilities, hotspots, 
                risk_analysis, risk_threshold, include_recommendations
            )
            
            return assessment
        
        return await self._get_cached_or_execute(
            self.get_name(),
            generate_assessment,
            ttl=300,
            project_key=project_key,
            include_resolved=include_resolved,
            risk_threshold=risk_threshold,
            include_recommendations=include_recommendations
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
    
    async def _get_security_metrics(self, project_key: str) -> Dict[str, Any]:
        """Get security-related metrics."""
        security_metrics = [
            "vulnerabilities", "new_vulnerabilities", "security_rating", "new_security_rating",
            "security_hotspots", "new_security_hotspots", "security_review_rating",
            "ncloc", "lines"  # For context
        ]
        
        try:
            response = await self.client.get(
                "/measures/component",
                params={
                    "component": project_key,
                    "metricKeys": ",".join(security_metrics)
                }
            )
            
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
            self.logger.error(f"Failed to get security metrics for {project_key}: {e}")
            return {}
    
    async def _get_vulnerabilities(self, project_key: str, include_resolved: bool) -> List[Dict[str, Any]]:
        """Get vulnerabilities for the project."""
        try:
            params = {
                "projectKeys": project_key,
                "types": "VULNERABILITY",
                "ps": 500,  # Get up to 500 vulnerabilities
                "additionalFields": "comments"
            }
            
            if not include_resolved:
                params["statuses"] = "OPEN,CONFIRMED,REOPENED"
            
            response = await self.client.get("/issues/search", params=params)
            
            issues = response.get("issues", [])
            components = response.get("components", [])
            rules = response.get("rules", [])
            
            # Create lookup dictionaries
            components_dict = {comp["key"]: comp for comp in components}
            rules_dict = {rule["key"]: rule for rule in rules}
            
            # Enrich vulnerabilities
            enriched_vulns = []
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
                
                # Calculate risk score
                enriched["risk_score"] = self._calculate_vulnerability_risk_score(enriched)
                
                enriched_vulns.append(enriched)
            
            # Sort by risk score (highest first)
            enriched_vulns.sort(key=lambda x: x.get("risk_score", 0), reverse=True)
            
            return enriched_vulns
            
        except Exception as e:
            self.logger.error(f"Failed to get vulnerabilities for {project_key}: {e}")
            return []
    
    async def _get_security_hotspots(self, project_key: str, include_resolved: bool) -> List[Dict[str, Any]]:
        """Get security hotspots for the project."""
        try:
            params = {
                "projectKey": project_key,
                "ps": 500  # Get up to 500 hotspots
            }
            
            if not include_resolved:
                params["statuses"] = "TO_REVIEW,IN_REVIEW"
            
            response = await self.client.get("/hotspots/search", params=params)
            
            hotspots = response.get("hotspots", [])
            components = response.get("components", [])
            rules = response.get("rules", [])
            
            # Create lookup dictionaries
            components_dict = {comp["key"]: comp for comp in components}
            rules_dict = {rule["key"]: rule for rule in rules}
            
            # Enrich hotspots
            enriched_hotspots = []
            for hotspot in hotspots:
                enriched = hotspot.copy()
                
                # Add component info
                component_key = hotspot.get("component")
                if component_key and component_key in components_dict:
                    enriched["component_info"] = components_dict[component_key]
                
                # Add rule info
                rule_key = hotspot.get("rule")
                if rule_key and rule_key in rules_dict:
                    enriched["rule_info"] = rules_dict[rule_key]
                
                # Calculate risk score
                enriched["risk_score"] = self._calculate_hotspot_risk_score(enriched)
                
                enriched_hotspots.append(enriched)
            
            # Sort by risk score (highest first)
            enriched_hotspots.sort(key=lambda x: x.get("risk_score", 0), reverse=True)
            
            return enriched_hotspots
            
        except Exception as e:
            self.logger.error(f"Failed to get security hotspots for {project_key}: {e}")
            return []
    
    def _calculate_vulnerability_risk_score(self, vulnerability: Dict[str, Any]) -> int:
        """Calculate risk score for a vulnerability (0-100)."""
        score = 0
        
        # Severity scoring
        severity = vulnerability.get("severity", "")
        severity_scores = {"BLOCKER": 40, "CRITICAL": 30, "MAJOR": 20, "MINOR": 10, "INFO": 5}
        score += severity_scores.get(severity, 0)
        
        # Status scoring (open issues are higher risk)
        status = vulnerability.get("status", "")
        if status in ["OPEN", "CONFIRMED", "REOPENED"]:
            score += 20
        elif status == "RESOLVED":
            score -= 10
        
        # Age scoring (older issues might be more embedded)
        creation_date = vulnerability.get("creationDate")
        if creation_date:
            age_days = self._calculate_issue_age(creation_date)
            if age_days > 90:
                score += 10
            elif age_days > 30:
                score += 5
        
        # Component scoring (main source files are higher risk)
        component_info = vulnerability.get("component_info", {})
        component_path = component_info.get("path", "")
        if any(pattern in component_path.lower() for pattern in ["src/main", "lib", "core"]):
            score += 10
        elif any(pattern in component_path.lower() for pattern in ["test", "spec"]):
            score -= 5
        
        return min(score, 100)  # Cap at 100
    
    def _calculate_hotspot_risk_score(self, hotspot: Dict[str, Any]) -> int:
        """Calculate risk score for a security hotspot (0-100)."""
        score = 0
        
        # Vulnerability probability scoring
        prob = hotspot.get("vulnerabilityProbability", "")
        prob_scores = {"HIGH": 40, "MEDIUM": 25, "LOW": 10}
        score += prob_scores.get(prob, 0)
        
        # Security category scoring
        category = hotspot.get("securityCategory", "")
        high_risk_categories = ["sql-injection", "command-injection", "path-traversal", "ldap-injection"]
        medium_risk_categories = ["xss", "csrf", "weak-cryptography", "auth"]
        
        if category.lower() in high_risk_categories:
            score += 30
        elif any(cat in category.lower() for cat in medium_risk_categories):
            score += 20
        else:
            score += 10
        
        # Status scoring
        status = hotspot.get("status", "")
        if status == "TO_REVIEW":
            score += 15
        elif status == "IN_REVIEW":
            score += 10
        elif status == "REVIEWED":
            resolution = hotspot.get("resolution", "")
            if resolution == "SAFE":
                score -= 20
            elif resolution == "FIXED":
                score -= 30
        
        # Age scoring
        creation_date = hotspot.get("creationDate")
        if creation_date:
            age_days = self._calculate_issue_age(creation_date)
            if age_days > 90:
                score += 10
            elif age_days > 30:
                score += 5
        
        return min(score, 100)  # Cap at 100
    
    def _calculate_issue_age(self, creation_date: str) -> int:
        """Calculate issue age in days."""
        try:
            from datetime import datetime
            created = datetime.fromisoformat(creation_date.replace("Z", "+00:00"))
            now = datetime.utcnow().replace(tzinfo=created.tzinfo)
            return (now - created).days
        except Exception:
            return 0
    
    def _perform_risk_analysis(
        self, 
        vulnerabilities: List[Dict[str, Any]], 
        hotspots: List[Dict[str, Any]], 
        metrics: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Perform comprehensive risk analysis."""
        analysis = {
            "overall_risk_level": "LOW",
            "risk_factors": [],
            "vulnerability_analysis": {},
            "hotspot_analysis": {},
            "trend_analysis": {},
            "priority_items": []
        }
        
        # Analyze vulnerabilities
        if vulnerabilities:
            vuln_by_severity = {}
            vuln_by_status = {}
            high_risk_vulns = []
            
            for vuln in vulnerabilities:
                severity = vuln.get("severity", "UNKNOWN")
                status = vuln.get("status", "UNKNOWN")
                risk_score = vuln.get("risk_score", 0)
                
                vuln_by_severity[severity] = vuln_by_severity.get(severity, 0) + 1
                vuln_by_status[status] = vuln_by_status.get(status, 0) + 1
                
                if risk_score >= 70:
                    high_risk_vulns.append(vuln)
            
            analysis["vulnerability_analysis"] = {
                "total": len(vulnerabilities),
                "by_severity": vuln_by_severity,
                "by_status": vuln_by_status,
                "high_risk_count": len(high_risk_vulns),
                "avg_risk_score": sum(v.get("risk_score", 0) for v in vulnerabilities) / len(vulnerabilities)
            }
            
            # Add high-risk vulnerabilities to priority items
            for vuln in high_risk_vulns[:5]:  # Top 5
                analysis["priority_items"].append({
                    "type": "vulnerability",
                    "key": vuln.get("key"),
                    "message": vuln.get("message"),
                    "severity": vuln.get("severity"),
                    "risk_score": vuln.get("risk_score"),
                    "component": vuln.get("component_info", {}).get("name", vuln.get("component"))
                })
        
        # Analyze hotspots
        if hotspots:
            hotspot_by_prob = {}
            hotspot_by_category = {}
            high_risk_hotspots = []
            
            for hotspot in hotspots:
                prob = hotspot.get("vulnerabilityProbability", "UNKNOWN")
                category = hotspot.get("securityCategory", "UNKNOWN")
                risk_score = hotspot.get("risk_score", 0)
                
                hotspot_by_prob[prob] = hotspot_by_prob.get(prob, 0) + 1
                hotspot_by_category[category] = hotspot_by_category.get(category, 0) + 1
                
                if risk_score >= 70:
                    high_risk_hotspots.append(hotspot)
            
            analysis["hotspot_analysis"] = {
                "total": len(hotspots),
                "by_probability": hotspot_by_prob,
                "by_category": hotspot_by_category,
                "high_risk_count": len(high_risk_hotspots),
                "avg_risk_score": sum(h.get("risk_score", 0) for h in hotspots) / len(hotspots)
            }
            
            # Add high-risk hotspots to priority items
            for hotspot in high_risk_hotspots[:5]:  # Top 5
                analysis["priority_items"].append({
                    "type": "hotspot",
                    "key": hotspot.get("key"),
                    "message": hotspot.get("message", "Security hotspot"),
                    "probability": hotspot.get("vulnerabilityProbability"),
                    "category": hotspot.get("securityCategory"),
                    "risk_score": hotspot.get("risk_score"),
                    "component": hotspot.get("component_info", {}).get("name", hotspot.get("component"))
                })
        
        # Determine overall risk level
        total_vulns = len(vulnerabilities)
        total_hotspots = len(hotspots)
        high_risk_items = len([item for item in analysis["priority_items"] if item.get("risk_score", 0) >= 70])
        
        if total_vulns > 10 or high_risk_items > 5:
            analysis["overall_risk_level"] = "HIGH"
            analysis["risk_factors"].append("Multiple high-severity vulnerabilities")
        elif total_vulns > 5 or total_hotspots > 20 or high_risk_items > 2:
            analysis["overall_risk_level"] = "MEDIUM"
            analysis["risk_factors"].append("Moderate number of security issues")
        elif total_vulns > 0 or total_hotspots > 10:
            analysis["overall_risk_level"] = "MEDIUM"
            analysis["risk_factors"].append("Some security issues present")
        else:
            analysis["overall_risk_level"] = "LOW"
        
        # Add other risk factors
        security_rating = metrics.get("security_rating")
        if security_rating and security_rating > 3:
            analysis["risk_factors"].append("Poor security rating")
        
        new_vulns = metrics.get("new_vulnerabilities", 0)
        if new_vulns > 0:
            analysis["risk_factors"].append(f"{new_vulns} new vulnerabilities in recent code")
        
        return analysis
    
    def _generate_security_assessment(
        self,
        project_info: Dict[str, Any],
        metrics: Dict[str, Any],
        vulnerabilities: List[Dict[str, Any]],
        hotspots: List[Dict[str, Any]],
        risk_analysis: Dict[str, Any],
        risk_threshold: str,
        include_recommendations: bool
    ) -> str:
        """Generate comprehensive security assessment report."""
        project_name = project_info.get("name", project_info.get("key", "Unknown"))
        project_key = project_info.get("key", "Unknown")
        
        assessment = f"""# Security Assessment Report: {project_name}

## Executive Summary
- **Project**: {project_name} ({project_key})
- **Assessment Date**: {self._get_current_timestamp()}
- **Overall Risk Level**: {risk_analysis.get('overall_risk_level', 'UNKNOWN')}
- **Total Vulnerabilities**: {len(vulnerabilities)}
- **Total Security Hotspots**: {len(hotspots)}

"""
        
        # Risk level indicator
        risk_level = risk_analysis.get("overall_risk_level", "UNKNOWN")
        if risk_level == "HIGH":
            assessment += "🔴 **HIGH RISK**: Immediate security attention required.\n\n"
        elif risk_level == "MEDIUM":
            assessment += "🟡 **MEDIUM RISK**: Security issues should be addressed soon.\n\n"
        elif risk_level == "LOW":
            assessment += "🟢 **LOW RISK**: Good security posture with minor issues.\n\n"
        else:
            assessment += "❓ **UNKNOWN RISK**: Unable to determine risk level.\n\n"
        
        # Security Metrics Overview
        assessment += "## Security Metrics\n"
        
        total_vulns = metrics.get("vulnerabilities", 0)
        new_vulns = metrics.get("new_vulnerabilities", 0)
        security_rating = metrics.get("security_rating", "N/A")
        total_hotspots = metrics.get("security_hotspots", 0)
        new_hotspots = metrics.get("new_security_hotspots", 0)
        
        assessment += f"- **Vulnerabilities**: {total_vulns} total"
        if new_vulns > 0:
            assessment += f" ({new_vulns} new)"
        assessment += "\n"
        
        assessment += f"- **Security Hotspots**: {total_hotspots} total"
        if new_hotspots > 0:
            assessment += f" ({new_hotspots} new)"
        assessment += "\n"
        
        assessment += f"- **Security Rating**: {security_rating}\n"
        
        # Code size context
        ncloc = metrics.get("ncloc", 0)
        if ncloc > 0:
            vuln_density = (total_vulns / ncloc) * 1000
            assessment += f"- **Vulnerability Density**: {vuln_density:.2f} per 1K lines of code\n"
        
        assessment += "\n"
        
        # Vulnerability Analysis
        if vulnerabilities:
            vuln_analysis = risk_analysis.get("vulnerability_analysis", {})
            assessment += "## Vulnerability Analysis\n"
            
            by_severity = vuln_analysis.get("by_severity", {})
            if by_severity:
                assessment += "### By Severity\n"
                for severity in ["BLOCKER", "CRITICAL", "MAJOR", "MINOR", "INFO"]:
                    count = by_severity.get(severity, 0)
                    if count > 0:
                        emoji = {"BLOCKER": "🚫", "CRITICAL": "🔴", "MAJOR": "🟠", "MINOR": "🟡", "INFO": "ℹ️"}.get(severity, "•")
                        assessment += f"- {emoji} **{severity}**: {count}\n"
                assessment += "\n"
            
            by_status = vuln_analysis.get("by_status", {})
            if by_status:
                assessment += "### By Status\n"
                for status, count in by_status.items():
                    emoji = {"OPEN": "🔓", "CONFIRMED": "⚠️", "RESOLVED": "✅", "CLOSED": "🔒"}.get(status, "•")
                    assessment += f"- {emoji} **{status}**: {count}\n"
                assessment += "\n"
            
            high_risk_count = vuln_analysis.get("high_risk_count", 0)
            if high_risk_count > 0:
                assessment += f"⚠️ **{high_risk_count} high-risk vulnerabilities** require immediate attention.\n\n"
        
        # Security Hotspots Analysis
        if hotspots:
            hotspot_analysis = risk_analysis.get("hotspot_analysis", {})
            assessment += "## Security Hotspots Analysis\n"
            
            by_probability = hotspot_analysis.get("by_probability", {})
            if by_probability:
                assessment += "### By Vulnerability Probability\n"
                for prob in ["HIGH", "MEDIUM", "LOW"]:
                    count = by_probability.get(prob, 0)
                    if count > 0:
                        emoji = {"HIGH": "🔴", "MEDIUM": "🟡", "LOW": "🟢"}.get(prob, "•")
                        assessment += f"- {emoji} **{prob}**: {count}\n"
                assessment += "\n"
            
            by_category = hotspot_analysis.get("by_category", {})
            if by_category:
                assessment += "### Top Security Categories\n"
                sorted_categories = sorted(by_category.items(), key=lambda x: x[1], reverse=True)
                for category, count in sorted_categories[:5]:
                    assessment += f"- **{category}**: {count}\n"
                assessment += "\n"
        
        # Priority Items
        priority_items = risk_analysis.get("priority_items", [])
        if priority_items:
            assessment += "## High-Priority Security Issues\n"
            assessment += "*Top security issues requiring immediate attention:*\n\n"
            
            for i, item in enumerate(priority_items[:10], 1):  # Top 10
                item_type = item.get("type", "unknown")
                risk_score = item.get("risk_score", 0)
                component = item.get("component", "Unknown")
                message = item.get("message", "No description")
                
                # Truncate long messages
                if len(message) > 100:
                    message = message[:97] + "..."
                
                assessment += f"### {i}. {item_type.title()} (Risk Score: {risk_score})\n"
                assessment += f"- **Component**: {component}\n"
                assessment += f"- **Issue**: {message}\n"
                
                if item_type == "vulnerability":
                    severity = item.get("severity", "UNKNOWN")
                    assessment += f"- **Severity**: {severity}\n"
                elif item_type == "hotspot":
                    probability = item.get("probability", "UNKNOWN")
                    category = item.get("category", "UNKNOWN")
                    assessment += f"- **Probability**: {probability}\n"
                    assessment += f"- **Category**: {category}\n"
                
                assessment += "\n"
        
        # Risk Factors
        risk_factors = risk_analysis.get("risk_factors", [])
        if risk_factors:
            assessment += "## Risk Factors\n"
            for factor in risk_factors:
                assessment += f"- ⚠️ {factor}\n"
            assessment += "\n"
        
        # Recommendations
        if include_recommendations:
            assessment += "## Security Recommendations\n"
            
            # Immediate actions
            if risk_level == "HIGH":
                assessment += "### Immediate Actions (High Priority)\n"
                if total_vulns > 0:
                    assessment += "1. **Address Critical Vulnerabilities**: Focus on BLOCKER and CRITICAL severity vulnerabilities first\n"
                if len([item for item in priority_items if item.get("type") == "hotspot"]) > 0:
                    assessment += "2. **Review High-Risk Hotspots**: Examine security hotspots with HIGH vulnerability probability\n"
                assessment += "3. **Security Code Review**: Conduct thorough security review of affected components\n"
                assessment += "4. **Penetration Testing**: Consider external security testing\n\n"
            
            # General recommendations
            assessment += "### General Recommendations\n"
            
            if total_vulns > 0:
                assessment += "- **Vulnerability Management**: Establish a process for regular vulnerability scanning and remediation\n"
            
            if total_hotspots > 10:
                assessment += "- **Security Hotspot Review**: Regularly review and resolve security hotspots\n"
            
            if new_vulns > 0 or new_hotspots > 0:
                assessment += "- **Secure Development**: Implement security practices in the development lifecycle\n"
            
            assessment += "- **Security Training**: Provide security awareness training for development team\n"
            assessment += "- **Automated Security Testing**: Integrate security testing into CI/CD pipeline\n"
            assessment += "- **Regular Assessments**: Schedule periodic security assessments\n"
            
            # Tool-specific recommendations
            assessment += "\n### SonarQube Integration\n"
            assessment += "- Configure Quality Gates to include security conditions\n"
            assessment += "- Set up alerts for new security issues\n"
            assessment += "- Use SonarQube security rules appropriate for your technology stack\n"
            assessment += "- Regularly update SonarQube rules and plugins\n"
        
        assessment += f"\n---\n*Security assessment generated on {self._get_current_timestamp()}*\n"
        assessment += f"*Risk threshold: {risk_threshold}*"
        
        return assessment
