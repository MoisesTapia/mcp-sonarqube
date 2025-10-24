"""Service layer for SonarQube API interactions."""

import asyncio
from typing import Dict, Any, List, Optional, Tuple
import streamlit as st

from sonarqube_client.client import SonarQubeClient
from sonarqube_client.exceptions import SonarQubeException
from streamlit_app.config.settings import ConfigManager
from streamlit_app.utils.session import SessionManager
from streamlit_app.utils.performance import performance_timer, get_performance_monitor, PerformanceOptimizer


class SonarQubeService:
    """Service for interacting with SonarQube API."""
    
    def __init__(self, config_manager: ConfigManager):
        """Initialize service with configuration manager."""
        self.config_manager = config_manager
    
    async def _get_client(self) -> Optional[SonarQubeClient]:
        """Get SonarQube client instance."""
        if not self.config_manager.is_configured():
            return None
        
        try:
            params = self.config_manager.get_connection_params()
            return SonarQubeClient(**params)
        except Exception as e:
            st.error(f"Failed to create SonarQube client: {e}")
            return None
    
    def _run_async(self, coro):
        """Run async coroutine in sync context."""
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        return loop.run_until_complete(coro)
    
    async def _get_projects_async(self) -> List[Dict[str, Any]]:
        """Get all projects asynchronously."""
        client = await self._get_client()
        if not client:
            return []
        
        try:
            response = await client.get("/projects/search", params={"ps": 500})
            return response.get("components", [])
        except SonarQubeException as e:
            st.error(f"Failed to fetch projects: {e}")
            return []
        finally:
            await client.close()
    
    @performance_timer("get_projects")
    def get_projects(self, use_cache: bool = True) -> List[Dict[str, Any]]:
        """Get all projects."""
        if use_cache:
            cached_projects = SessionManager.get_cached_data("cached_projects", ttl_minutes=5)
            if cached_projects is not None:
                return cached_projects
        
        projects = self._run_async(self._get_projects_async())
        
        if use_cache:
            SessionManager.cache_data("cached_projects", projects, ttl_minutes=5)
        
        return projects
    
    async def _get_project_measures_async(self, project_key: str, metrics: List[str]) -> Dict[str, Any]:
        """Get project measures asynchronously."""
        client = await self._get_client()
        if not client:
            return {}
        
        try:
            metrics_param = ",".join(metrics)
            response = await client.get(
                "/measures/component",
                params={
                    "component": project_key,
                    "metricKeys": metrics_param
                }
            )
            
            component = response.get("component", {})
            measures = component.get("measures", [])
            
            # Convert to dict for easier access
            measures_dict = {}
            for measure in measures:
                measures_dict[measure["metric"]] = measure.get("value", "0")
            
            return measures_dict
        except SonarQubeException as e:
            st.error(f"Failed to fetch measures for {project_key}: {e}")
            return {}
        finally:
            await client.close()
    
    @performance_timer("get_project_measures")
    def get_project_measures(self, project_key: str, metrics: List[str]) -> Dict[str, Any]:
        """Get project measures."""
        return self._run_async(self._get_project_measures_async(project_key, metrics))
    
    async def _get_quality_gate_status_async(self, project_key: str) -> Dict[str, Any]:
        """Get quality gate status asynchronously."""
        client = await self._get_client()
        if not client:
            return {}
        
        try:
            response = await client.get(
                "/qualitygates/project_status",
                params={"projectKey": project_key}
            )
            return response.get("projectStatus", {})
        except SonarQubeException as e:
            st.error(f"Failed to fetch quality gate status for {project_key}: {e}")
            return {}
        finally:
            await client.close()
    
    def get_quality_gate_status(self, project_key: str) -> Dict[str, Any]:
        """Get quality gate status for a project."""
        return self._run_async(self._get_quality_gate_status_async(project_key))
    
    async def _get_all_quality_gates_async(self) -> List[Dict[str, Any]]:
        """Get all quality gates asynchronously."""
        client = await self._get_client()
        if not client:
            return []
        
        try:
            response = await client.get("/qualitygates/list")
            return response.get("qualitygates", [])
        except SonarQubeException as e:
            st.error(f"Failed to fetch quality gates: {e}")
            return []
        finally:
            await client.close()
    
    def get_all_quality_gates(self, use_cache: bool = True) -> List[Dict[str, Any]]:
        """Get all quality gates."""
        if use_cache:
            cached_gates = SessionManager.get_cached_data("cached_quality_gates", ttl_minutes=10)
            if cached_gates is not None:
                return cached_gates
        
        gates = self._run_async(self._get_all_quality_gates_async())
        
        if use_cache:
            SessionManager.cache_data("cached_quality_gates", gates, ttl_minutes=10)
        
        return gates
    
    def get_projects_with_quality_gates(self, project_keys: List[str]) -> List[Dict[str, Any]]:
        """Get projects with their quality gate status."""
        projects_with_gates = []
        
        for project_key in project_keys:
            quality_gate = self.get_quality_gate_status(project_key)
            projects_with_gates.append({
                "project_key": project_key,
                "quality_gate": quality_gate
            })
        
        return projects_with_gates
    
    async def _search_issues_async(self, project_key: str = None, filters: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """Search issues asynchronously."""
        client = await self._get_client()
        if not client:
            return []
        
        try:
            params = {"ps": 500}  # Page size
            
            if project_key:
                params["componentKeys"] = project_key
            
            if filters:
                if filters.get("severities"):
                    params["severities"] = ",".join(filters["severities"])
                if filters.get("types"):
                    params["types"] = ",".join(filters["types"])
                if filters.get("statuses"):
                    params["statuses"] = ",".join(filters["statuses"])
                if filters.get("assignees"):
                    params["assignees"] = ",".join(filters["assignees"])
                if filters.get("rules"):
                    params["rules"] = ",".join(filters["rules"])
            
            response = await client.get("/issues/search", params=params)
            return response.get("issues", [])
        except SonarQubeException as e:
            st.error(f"Failed to search issues: {e}")
            return []
        finally:
            await client.close()
    
    @performance_timer("search_issues")
    def search_issues(self, project_key: str = None, filters: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """Search issues."""
        return self._run_async(self._search_issues_async(project_key, filters))
    
    async def _get_security_hotspots_async(self, project_key: str = None, filters: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """Get security hotspots asynchronously."""
        client = await self._get_client()
        if not client:
            return []
        
        try:
            params = {"ps": 500}
            
            if project_key:
                params["projectKey"] = project_key
            
            if filters:
                if filters.get("statuses"):
                    params["status"] = ",".join(filters["statuses"])
                if filters.get("resolutions"):
                    params["resolution"] = ",".join(filters["resolutions"])
            
            response = await client.get("/hotspots/search", params=params)
            return response.get("hotspots", [])
        except SonarQubeException as e:
            st.error(f"Failed to fetch security hotspots: {e}")
            return []
        finally:
            await client.close()
    
    def get_security_hotspots(self, project_key: str = None, filters: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """Get security hotspots."""
        return self._run_async(self._get_security_hotspots_async(project_key, filters))
    
    async def _get_security_metrics_async(self, project_key: str) -> Dict[str, Any]:
        """Get security metrics for a project asynchronously."""
        client = await self._get_client()
        if not client:
            return {}
        
        try:
            security_metrics = [
                "vulnerabilities", "security_hotspots", "security_rating",
                "security_review_rating", "security_hotspots_reviewed"
            ]
            
            response = await client.get(
                "/measures/component",
                params={
                    "component": project_key,
                    "metricKeys": ",".join(security_metrics)
                }
            )
            
            component = response.get("component", {})
            measures = component.get("measures", [])
            
            # Convert to dict for easier access
            metrics_dict = {}
            for measure in measures:
                metrics_dict[measure["metric"]] = measure.get("value", "0")
            
            return metrics_dict
        except SonarQubeException as e:
            st.error(f"Failed to fetch security metrics for {project_key}: {e}")
            return {}
        finally:
            await client.close()
    
    def get_security_metrics(self, project_key: str) -> Dict[str, Any]:
        """Get security metrics for a project."""
        return self._run_async(self._get_security_metrics_async(project_key))
    
    def get_dashboard_summary(self) -> Dict[str, Any]:
        """Get dashboard summary data."""
        projects = self.get_projects()
        
        if not projects:
            return {
                "total_projects": 0,
                "projects_with_issues": 0,
                "quality_gates_passed": 0,
                "quality_gates_failed": 0,
                "projects": []
            }
        
        # Get quality gate status for all projects
        project_summaries = []
        quality_gates_passed = 0
        quality_gates_failed = 0
        projects_with_issues = 0
        
        for project in projects[:20]:  # Limit to first 20 projects for performance
            project_key = project["key"]
            
            # Get basic metrics
            metrics = ["bugs", "vulnerabilities", "code_smells", "coverage", "duplicated_lines_density"]
            measures = self.get_project_measures(project_key, metrics)
            
            # Get quality gate status
            quality_gate = self.get_quality_gate_status(project_key)
            gate_status = quality_gate.get("status", "NONE")
            
            if gate_status == "OK":
                quality_gates_passed += 1
            elif gate_status in ["ERROR", "WARN"]:
                quality_gates_failed += 1
            
            # Check if project has issues
            bugs = int(measures.get("bugs", "0"))
            vulnerabilities = int(measures.get("vulnerabilities", "0"))
            code_smells = int(measures.get("code_smells", "0"))
            
            if bugs > 0 or vulnerabilities > 0 or code_smells > 0:
                projects_with_issues += 1
            
            project_summaries.append({
                "key": project_key,
                "name": project.get("name", project_key),
                "last_analysis": project.get("lastAnalysisDate"),
                "quality_gate_status": gate_status,
                "bugs": bugs,
                "vulnerabilities": vulnerabilities,
                "code_smells": code_smells,
                "coverage": measures.get("coverage", "0"),
                "duplicated_lines": measures.get("duplicated_lines_density", "0")
            })
        
        return {
            "total_projects": len(projects),
            "projects_with_issues": projects_with_issues,
            "quality_gates_passed": quality_gates_passed,
            "quality_gates_failed": quality_gates_failed,
            "projects": project_summaries
        }
