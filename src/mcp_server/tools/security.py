"""Security analysis tools for SonarQube MCP."""

from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta, timezone

from ...sonarqube_client import SonarQubeClient, InputValidator
from ...utils import CacheManager, get_logger

logger = get_logger(__name__)


class SecurityTools:
    """Tools for SonarQube security analysis and vulnerability management."""

    # Valid security hotspot statuses
    VALID_HOTSPOT_STATUSES = ["TO_REVIEW", "IN_REVIEW", "REVIEWED"]
    
    # Valid security hotspot resolutions
    VALID_HOTSPOT_RESOLUTIONS = ["FIXED", "SAFE", "ACKNOWLEDGED"]
    
    # Valid vulnerability probabilities
    VALID_PROBABILITIES = ["HIGH", "MEDIUM", "LOW"]
    
    # Security categories mapping
    SECURITY_CATEGORIES = {
        "sql-injection": "SQL Injection",
        "command-injection": "Command Injection",
        "path-traversal-injection": "Path Traversal",
        "ldap-injection": "LDAP Injection",
        "xpath-injection": "XPath Injection",
        "rce": "Remote Code Execution",
        "dos": "Denial of Service",
        "ssrf": "Server-Side Request Forgery",
        "csrf": "Cross-Site Request Forgery",
        "xss": "Cross-Site Scripting",
        "log-injection": "Log Injection",
        "http-response-splitting": "HTTP Response Splitting",
        "open-redirect": "Open Redirect",
        "xxe": "XML External Entity",
        "object-injection": "Object Injection",
        "weak-cryptography": "Weak Cryptography",
        "auth": "Authentication",
        "insecure-conf": "Insecure Configuration",
        "file-manipulation": "File Manipulation",
        "others": "Others"
    }

    def __init__(self, client: SonarQubeClient, cache_manager: Optional[CacheManager] = None):
        """Initialize security tools."""
        self.client = client
        self.cache = cache_manager
        self.logger = logger

    async def search_hotspots(
        self,
        project_key: str,
        statuses: Optional[List[str]] = None,
        resolutions: Optional[List[str]] = None,
        hotspot_keys: Optional[List[str]] = None,
        branch: Optional[str] = None,
        pull_request: Optional[str] = None,
        since_leak_period: bool = False,
        only_mine: bool = False,
        page: int = 1,
        page_size: int = 100,
    ) -> Dict[str, Any]:
        """
        Search for security hotspots in a project.

        Args:
            project_key: Unique project key
            statuses: List of hotspot statuses (TO_REVIEW, IN_REVIEW, REVIEWED)
            resolutions: List of resolutions (FIXED, SAFE, ACKNOWLEDGED)
            hotspot_keys: List of specific hotspot keys to retrieve
            branch: Branch name to analyze
            pull_request: Pull request key to analyze
            since_leak_period: Only return hotspots from leak period
            only_mine: Only return hotspots assigned to current user
            page: Page number (1-based)
            page_size: Number of hotspots per page (max 500)

        Returns:
            Dictionary containing hotspots list and metadata
        """
        try:
            # Validate project key
            project_key = InputValidator.validate_project_key(project_key)
            
            # Validate pagination parameters
            page, page_size = InputValidator.validate_pagination_params(page, page_size)
            
            # Validate statuses
            if statuses:
                for status in statuses:
                    if status not in self.VALID_HOTSPOT_STATUSES:
                        raise ValueError(f"Invalid hotspot status: {status}")
            
            # Validate resolutions
            if resolutions:
                for resolution in resolutions:
                    if resolution not in self.VALID_HOTSPOT_RESOLUTIONS:
                        raise ValueError(f"Invalid hotspot resolution: {resolution}")
            
            # Build cache key
            cache_key_params = {
                "project_key": project_key,
                "statuses": ",".join(sorted(statuses or [])),
                "resolutions": ",".join(sorted(resolutions or [])),
                "hotspot_keys": ",".join(sorted(hotspot_keys or [])),
                "branch": branch,
                "pull_request": pull_request,
                "since_leak_period": since_leak_period,
                "only_mine": only_mine,
                "page": page,
                "page_size": page_size,
            }
            
            # Try cache first
            if self.cache:
                cached_result = await self.cache.get("security", "hotspots", **cache_key_params)
                if cached_result:
                    self.logger.debug(f"Returning cached hotspots for project {project_key}")
                    return cached_result

            # Build API parameters
            params = {
                "projectKey": project_key,
                "p": page,
                "ps": page_size,
            }
            
            if statuses:
                params["status"] = ",".join(statuses)
            if resolutions:
                params["resolution"] = ",".join(resolutions)
            if hotspot_keys:
                params["hotspots"] = ",".join(hotspot_keys)
            if branch:
                params["branch"] = branch
            if pull_request:
                params["pullRequest"] = pull_request
            if since_leak_period:
                params["sinceLeakPeriod"] = "true"
            if only_mine:
                params["onlyMine"] = "true"

            # Make API call
            response = await self.client.get("/hotspots/search", params=params)
            
            # Format response
            result = {
                "hotspots": response.get("hotspots", []),
                "components": response.get("components", []),
                "rules": response.get("rules", []),
                "paging": response.get("paging", {}),
                "total": response.get("paging", {}).get("total", 0),
            }
            
            # Add security analysis
            if result["hotspots"]:
                result["security_analysis"] = self._analyze_hotspots(result["hotspots"])
            
            # Cache result with shorter TTL (security data changes frequently)
            if self.cache:
                await self.cache.set("security", "hotspots", result, ttl=120, **cache_key_params)
            
            self.logger.info(f"Found {len(result['hotspots'])} security hotspots for project {project_key}")
            return result
            
        except Exception as e:
            self.logger.error(f"Failed to search security hotspots for project {project_key}: {e}")
            raise RuntimeError(f"Failed to search security hotspots: {str(e)}")

    async def get_hotspot_details(self, hotspot_key: str) -> Dict[str, Any]:
        """
        Get detailed information about a specific security hotspot.

        Args:
            hotspot_key: Unique hotspot key

        Returns:
            Dictionary containing detailed hotspot information
        """
        try:
            # Validate hotspot key (basic validation, hotspots have different format than issues)
            if not hotspot_key or not isinstance(hotspot_key, str):
                raise ValueError("Hotspot key must be a non-empty string")
            hotspot_key = hotspot_key.strip()
            
            # Try cache first
            if self.cache:
                cached_result = await self.cache.get("security", "hotspot_details", hotspot_key=hotspot_key)
                if cached_result:
                    self.logger.debug(f"Returning cached hotspot details for {hotspot_key}")
                    return cached_result

            # Make API call
            response = await self.client.get(
                "/hotspots/show",
                params={"hotspot": hotspot_key}
            )
            
            # Enrich with additional information
            hotspot = response
            
            # Add risk assessment
            hotspot["risk_assessment"] = self._assess_hotspot_risk(hotspot)
            
            # Add remediation recommendations
            hotspot["remediation_recommendations"] = self._generate_remediation_recommendations(hotspot)
            
            # Cache result
            if self.cache:
                await self.cache.set("security", "hotspot_details", hotspot, hotspot_key=hotspot_key)
            
            self.logger.info(f"Retrieved details for security hotspot {hotspot_key}")
            return hotspot
            
        except Exception as e:
            self.logger.error(f"Failed to get hotspot details for {hotspot_key}: {e}")
            raise RuntimeError(f"Failed to get hotspot details: {str(e)}")

    async def generate_security_assessment(
        self,
        project_key: str,
        include_resolved: bool = False,
        time_period_days: int = 30,
    ) -> Dict[str, Any]:
        """
        Generate a comprehensive security assessment report for a project.

        Args:
            project_key: Unique project key
            include_resolved: Include resolved hotspots in analysis
            time_period_days: Number of days to look back for trend analysis

        Returns:
            Dictionary containing comprehensive security assessment
        """
        try:
            # Validate project key
            project_key = InputValidator.validate_project_key(project_key)
            
            # Try cache first
            cache_key_params = {
                "project_key": project_key,
                "include_resolved": include_resolved,
                "time_period_days": time_period_days,
            }
            
            if self.cache:
                cached_result = await self.cache.get("security", "assessment", **cache_key_params)
                if cached_result:
                    self.logger.debug(f"Returning cached security assessment for project {project_key}")
                    return cached_result

            # Get current hotspots
            current_hotspots = await self.search_hotspots(
                project_key=project_key,
                statuses=["TO_REVIEW", "IN_REVIEW"] if not include_resolved else None,
                page_size=500
            )
            
            # Get project measures for security metrics
            security_metrics = await self._get_security_metrics(project_key)
            
            # Generate assessment
            assessment = {
                "project_key": project_key,
                "assessment_date": datetime.now(timezone.utc).isoformat(),
                "time_period_days": time_period_days,
                "summary": {
                    "total_hotspots": len(current_hotspots.get("hotspots", [])),
                    "high_risk_hotspots": 0,
                    "medium_risk_hotspots": 0,
                    "low_risk_hotspots": 0,
                    "unreviewed_hotspots": 0,
                },
                "security_metrics": security_metrics,
                "hotspot_analysis": current_hotspots.get("security_analysis", {}),
                "risk_score": 0.0,
                "recommendations": [],
                "trend_analysis": {},
            }
            
            # Analyze hotspots by risk level
            for hotspot in current_hotspots.get("hotspots", []):
                vulnerability_prob = hotspot.get("vulnerabilityProbability", "LOW")
                status = hotspot.get("status", "TO_REVIEW")
                
                if vulnerability_prob == "HIGH":
                    assessment["summary"]["high_risk_hotspots"] += 1
                elif vulnerability_prob == "MEDIUM":
                    assessment["summary"]["medium_risk_hotspots"] += 1
                else:
                    assessment["summary"]["low_risk_hotspots"] += 1
                
                if status == "TO_REVIEW":
                    assessment["summary"]["unreviewed_hotspots"] += 1
            
            # Calculate risk score (0-100)
            assessment["risk_score"] = self._calculate_project_risk_score(
                assessment["summary"], security_metrics
            )
            
            # Generate recommendations
            assessment["recommendations"] = self._generate_security_recommendations(
                assessment["summary"], security_metrics, current_hotspots.get("hotspots", [])
            )
            
            # Add trend analysis if we have historical data
            assessment["trend_analysis"] = await self._analyze_security_trends(
                project_key, time_period_days
            )
            
            # Cache result with longer TTL (assessments are expensive to generate)
            if self.cache:
                await self.cache.set("security", "assessment", assessment, ttl=600, **cache_key_params)
            
            self.logger.info(f"Generated security assessment for project {project_key} with risk score {assessment['risk_score']}")
            return assessment
            
        except Exception as e:
            self.logger.error(f"Failed to generate security assessment for project {project_key}: {e}")
            raise RuntimeError(f"Failed to generate security assessment: {str(e)}")

    async def update_hotspot_status(
        self,
        hotspot_key: str,
        status: str,
        resolution: Optional[str] = None,
        comment: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Update the status of a security hotspot.

        Args:
            hotspot_key: Unique hotspot key
            status: New status (TO_REVIEW, IN_REVIEW, REVIEWED)
            resolution: Resolution if status is REVIEWED (FIXED, SAFE, ACKNOWLEDGED)
            comment: Optional comment explaining the change

        Returns:
            Dictionary containing update confirmation
        """
        try:
            # Validate hotspot key (basic validation, hotspots have different format than issues)
            if not hotspot_key or not isinstance(hotspot_key, str):
                raise ValueError("Hotspot key must be a non-empty string")
            hotspot_key = hotspot_key.strip()
            
            # Validate status
            if status not in self.VALID_HOTSPOT_STATUSES:
                raise ValueError(f"Invalid hotspot status: {status}")
            
            # Validate resolution if provided
            if resolution and resolution not in self.VALID_HOTSPOT_RESOLUTIONS:
                raise ValueError(f"Invalid hotspot resolution: {resolution}")
            
            # Sanitize comment if provided
            if comment:
                comment = InputValidator.sanitize_search_query(comment)
            
            # Build request data
            data = {
                "hotspot": hotspot_key,
                "status": status,
            }
            
            if resolution:
                data["resolution"] = resolution
            if comment:
                data["comment"] = comment
            
            # Make API call
            await self.client.post("/hotspots/change_status", data=data)
            
            # Invalidate caches
            if self.cache:
                await self.cache.delete("security", "hotspot_details", hotspot_key=hotspot_key)
                await self.cache.invalidate_pattern("security", "hotspots")
                await self.cache.invalidate_pattern("security", "assessment")
            
            result = {
                "success": True,
                "hotspot_key": hotspot_key,
                "new_status": status,
                "resolution": resolution,
                "message": f"Hotspot {hotspot_key} status updated to {status}",
            }
            
            self.logger.info(f"Updated hotspot {hotspot_key} status to {status}")
            return result
            
        except Exception as e:
            self.logger.error(f"Failed to update hotspot status for {hotspot_key}: {e}")
            raise RuntimeError(f"Failed to update hotspot status: {str(e)}")

    def _analyze_hotspots(self, hotspots: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze security hotspots and generate statistics."""
        if not hotspots:
            return {}
        
        analysis = {
            "total_count": len(hotspots),
            "by_vulnerability_probability": {},
            "by_status": {},
            "by_security_category": {},
            "by_component": {},
            "unreviewed_count": 0,
            "high_risk_count": 0,
        }
        
        for hotspot in hotspots:
            # Count by vulnerability probability
            prob = hotspot.get("vulnerabilityProbability", "LOW")
            analysis["by_vulnerability_probability"][prob] = analysis["by_vulnerability_probability"].get(prob, 0) + 1
            
            # Count by status
            status = hotspot.get("status", "TO_REVIEW")
            analysis["by_status"][status] = analysis["by_status"].get(status, 0) + 1
            
            # Count by security category
            category = hotspot.get("securityCategory", "others")
            category_name = self.SECURITY_CATEGORIES.get(category, category)
            analysis["by_security_category"][category_name] = analysis["by_security_category"].get(category_name, 0) + 1
            
            # Count by component
            component = hotspot.get("component", "unknown")
            analysis["by_component"][component] = analysis["by_component"].get(component, 0) + 1
            
            # Count unreviewed and high risk
            if status == "TO_REVIEW":
                analysis["unreviewed_count"] += 1
            if prob == "HIGH":
                analysis["high_risk_count"] += 1
        
        return analysis

    def _assess_hotspot_risk(self, hotspot: Dict[str, Any]) -> Dict[str, Any]:
        """Assess the risk level of a security hotspot."""
        vulnerability_prob = hotspot.get("vulnerabilityProbability", "LOW")
        security_category = hotspot.get("securityCategory", "others")
        status = hotspot.get("status", "TO_REVIEW")
        
        # Base risk score based on vulnerability probability
        risk_scores = {"HIGH": 8, "MEDIUM": 5, "LOW": 2}
        base_score = risk_scores.get(vulnerability_prob, 2)
        
        # Adjust based on security category (some are more critical)
        critical_categories = ["sql-injection", "rce", "command-injection", "xxe"]
        if security_category in critical_categories:
            base_score += 2
        
        # Adjust based on status
        if status == "TO_REVIEW":
            base_score += 1  # Unreviewed is riskier
        
        # Cap at 10
        risk_score = min(base_score, 10)
        
        # Determine risk level
        if risk_score >= 8:
            risk_level = "CRITICAL"
        elif risk_score >= 6:
            risk_level = "HIGH"
        elif risk_score >= 4:
            risk_level = "MEDIUM"
        else:
            risk_level = "LOW"
        
        return {
            "risk_score": risk_score,
            "risk_level": risk_level,
            "vulnerability_probability": vulnerability_prob,
            "security_category": self.SECURITY_CATEGORIES.get(security_category, security_category),
            "status": status,
        }

    def _generate_remediation_recommendations(self, hotspot: Dict[str, Any]) -> List[str]:
        """Generate remediation recommendations for a security hotspot."""
        recommendations = []
        security_category = hotspot.get("securityCategory", "others")
        
        # Category-specific recommendations
        category_recommendations = {
            "sql-injection": [
                "Use parameterized queries or prepared statements",
                "Implement input validation and sanitization",
                "Use ORM frameworks with built-in SQL injection protection",
                "Apply principle of least privilege for database access"
            ],
            "xss": [
                "Implement proper output encoding/escaping",
                "Use Content Security Policy (CSP) headers",
                "Validate and sanitize all user inputs",
                "Use secure templating engines with auto-escaping"
            ],
            "command-injection": [
                "Avoid executing system commands with user input",
                "Use safe APIs instead of shell commands",
                "Implement strict input validation",
                "Use allowlists for permitted commands"
            ],
            "weak-cryptography": [
                "Use strong, up-to-date cryptographic algorithms",
                "Implement proper key management practices",
                "Use secure random number generators",
                "Regularly update cryptographic libraries"
            ],
            "auth": [
                "Implement multi-factor authentication",
                "Use secure session management",
                "Apply proper password policies",
                "Implement account lockout mechanisms"
            ],
        }
        
        recommendations.extend(category_recommendations.get(security_category, [
            "Review the code for security vulnerabilities",
            "Follow secure coding best practices",
            "Conduct security testing",
            "Consider security code review"
        ]))
        
        # Add general recommendations
        recommendations.extend([
            "Test the fix thoroughly before deployment",
            "Document the security issue and resolution",
            "Consider adding automated security tests"
        ])
        
        return recommendations

    async def _get_security_metrics(self, project_key: str) -> Dict[str, Any]:
        """Get security-related metrics for a project."""
        try:
            security_metric_keys = [
                "security_hotspots",
                "security_hotspots_reviewed",
                "security_review_rating",
                "vulnerabilities",
                "new_vulnerabilities",
                "security_rating",
                "new_security_rating"
            ]
            
            response = await self.client.get(
                "/measures/component",
                params={
                    "component": project_key,
                    "metricKeys": ",".join(security_metric_keys)
                }
            )
            
            measures = response.get("component", {}).get("measures", [])
            metrics = {}
            
            for measure in measures:
                metric_key = measure.get("metric")
                value = measure.get("value")
                if value is not None:
                    # Convert numeric values
                    try:
                        if "." in value:
                            metrics[metric_key] = float(value)
                        else:
                            metrics[metric_key] = int(value)
                    except ValueError:
                        metrics[metric_key] = value
            
            return metrics
            
        except Exception as e:
            self.logger.warning(f"Failed to get security metrics for project {project_key}: {e}")
            return {}

    def _calculate_project_risk_score(
        self,
        summary: Dict[str, Any],
        security_metrics: Dict[str, Any]
    ) -> float:
        """Calculate overall project risk score (0-100)."""
        risk_score = 0.0
        
        # Base score from hotspot counts
        total_hotspots = summary.get("total_hotspots", 0)
        high_risk = summary.get("high_risk_hotspots", 0)
        medium_risk = summary.get("medium_risk_hotspots", 0)
        unreviewed = summary.get("unreviewed_hotspots", 0)
        
        # Weight by severity
        risk_score += high_risk * 10
        risk_score += medium_risk * 5
        risk_score += unreviewed * 2
        
        # Factor in security rating if available
        security_rating = security_metrics.get("security_rating")
        if security_rating:
            # SonarQube security rating: 1=A (best), 5=E (worst)
            rating_penalty = (int(security_rating) - 1) * 10
            risk_score += rating_penalty
        
        # Factor in vulnerability count
        vulnerabilities = security_metrics.get("vulnerabilities", 0)
        risk_score += vulnerabilities * 3
        
        # Normalize to 0-100 scale (rough approximation)
        if total_hotspots > 0:
            risk_score = min(risk_score / max(total_hotspots, 1) * 10, 100.0)
        else:
            risk_score = 0.0
        
        return round(float(risk_score), 1)

    def _generate_security_recommendations(
        self,
        summary: Dict[str, Any],
        security_metrics: Dict[str, Any],
        hotspots: List[Dict[str, Any]]
    ) -> List[str]:
        """Generate security recommendations based on analysis."""
        recommendations = []
        
        # High-level recommendations based on counts
        if summary.get("high_risk_hotspots", 0) > 0:
            recommendations.append(
                f"Prioritize reviewing {summary['high_risk_hotspots']} high-risk security hotspots"
            )
        
        if summary.get("unreviewed_hotspots", 0) > 0:
            recommendations.append(
                f"Review {summary['unreviewed_hotspots']} unreviewed security hotspots"
            )
        
        # Recommendations based on security rating
        security_rating = security_metrics.get("security_rating")
        if security_rating and int(security_rating) > 2:
            recommendations.append(
                "Improve security rating by addressing critical vulnerabilities"
            )
        
        # Category-specific recommendations
        category_counts = {}
        for hotspot in hotspots:
            category = hotspot.get("securityCategory", "others")
            category_counts[category] = category_counts.get(category, 0) + 1
        
        # Recommend focus areas
        if category_counts:
            top_category = max(category_counts.items(), key=lambda x: x[1])
            category_name = self.SECURITY_CATEGORIES.get(top_category[0], top_category[0])
            recommendations.append(
                f"Focus on {category_name} issues ({top_category[1]} hotspots)"
            )
        
        # General recommendations
        if summary.get("total_hotspots", 0) > 10:
            recommendations.append("Consider implementing automated security testing")
        
        recommendations.append("Establish regular security code review processes")
        recommendations.append("Provide security training for development team")
        
        return recommendations

    async def _analyze_security_trends(
        self,
        project_key: str,
        time_period_days: int
    ) -> Dict[str, Any]:
        """Analyze security trends over time."""
        try:
            # This would require historical data analysis
            # For now, return a placeholder structure
            return {
                "period_days": time_period_days,
                "trend_direction": "stable",  # Could be "improving", "degrading", "stable"
                "hotspot_trend": "stable",
                "vulnerability_trend": "stable",
                "note": "Historical trend analysis requires time-series data collection"
            }
        except Exception as e:
            self.logger.warning(f"Failed to analyze security trends: {e}")
            return {}