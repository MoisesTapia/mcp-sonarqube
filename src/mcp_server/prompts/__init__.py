"""MCP prompts for SonarQube integration."""

from .base import BasePrompt
from .manager import PromptManager
from .quality_analysis import AnalyzeProjectQualityPrompt
from .security_assessment import SecurityAssessmentPrompt
from .code_review import CodeReviewSummaryPrompt

__all__ = [
    "BasePrompt",
    "PromptManager",
    "AnalyzeProjectQualityPrompt",
    "SecurityAssessmentPrompt",
    "CodeReviewSummaryPrompt",
]