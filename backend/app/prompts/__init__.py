"""
Prompt Registry for SaralPolicy

Centralized prompt management with versioning for:
- Regression testing
- A/B testing capability
- Audit trail

Per Engineering Constitution Section 4.5: AI/ML/Prompt Engineering
- Design prompts intentionally
- Define evaluation strategies
"""

from .registry import PromptRegistry, PromptVersion, get_prompt_registry

__all__ = ["PromptRegistry", "PromptVersion", "get_prompt_registry"]
