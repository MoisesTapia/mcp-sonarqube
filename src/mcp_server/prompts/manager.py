"""Prompt manager for MCP prompts."""

from typing import Any, Dict, List, Optional

from ...utils import get_logger
from .base import BasePrompt
from .quality_analysis import AnalyzeProjectQualityPrompt
from .security_assessment import SecurityAssessmentPrompt
from .code_review import CodeReviewSummaryPrompt

logger = get_logger(__name__)


class PromptManager:
    """Manages MCP prompts and execution."""
    
    def __init__(self, sonarqube_client, cache_manager=None):
        """Initialize prompt manager."""
        self.client = sonarqube_client
        self.cache = cache_manager
        self.logger = logger
        
        # Initialize prompt handlers
        self.prompts: Dict[str, BasePrompt] = {
            "analyze_project_quality": AnalyzeProjectQualityPrompt(sonarqube_client, cache_manager),
            "security_assessment": SecurityAssessmentPrompt(sonarqube_client, cache_manager),
            "code_review_summary": CodeReviewSummaryPrompt(sonarqube_client, cache_manager),
        }
    
    async def execute_prompt(self, name: str, arguments: Dict[str, Any]) -> str:
        """Execute a prompt with given arguments."""
        try:
            if name not in self.prompts:
                raise ValueError(f"Unknown prompt: {name}")
            
            prompt = self.prompts[name]
            self.logger.info(f"Executing prompt: {name}")
            
            return await prompt.execute(arguments)
            
        except Exception as e:
            self.logger.error(f"Failed to execute prompt {name}: {e}")
            raise RuntimeError(f"Failed to execute prompt: {str(e)}")
    
    def get_prompt(self, name: str) -> Optional[BasePrompt]:
        """Get a prompt by name."""
        return self.prompts.get(name)
    
    def list_prompts(self) -> List[Dict[str, Any]]:
        """List all available prompts with their metadata."""
        prompts_info = []
        
        for name, prompt in self.prompts.items():
            prompts_info.append({
                "name": name,
                "description": prompt.get_description(),
                "arguments": prompt.get_arguments(),
            })
        
        return prompts_info
    
    def get_prompt_schema(self, name: str) -> Optional[Dict[str, Any]]:
        """Get the schema for a specific prompt."""
        if name not in self.prompts:
            return None
        
        prompt = self.prompts[name]
        return {
            "name": name,
            "description": prompt.get_description(),
            "arguments": prompt.get_arguments(),
        }
