"""
Prompt Registry - Centralized prompt management with versioning.

Design Rationale:
=================
1. **Version Control**: Each prompt has a version number for tracking changes
2. **Regression Testing**: Compare outputs across prompt versions
3. **Audit Trail**: Log which prompt version produced which output
4. **A/B Testing Ready**: Structure supports multiple active versions

Per Engineering Constitution:
- Section 4.5: Design prompts intentionally, define evaluation strategies
- Section 1.2: Optimize for readability and maintainability
"""

from dataclasses import dataclass, field
from typing import Dict, Optional, List
from datetime import datetime
from enum import Enum
import structlog

logger = structlog.get_logger(__name__)


class PromptCategory(str, Enum):
    """Categories of prompts used in the system."""
    SUMMARY = "summary"
    TERMS_EXTRACTION = "terms_extraction"
    EXCLUSIONS = "exclusions"
    QA = "question_answering"
    SYSTEM = "system"


@dataclass
class PromptVersion:
    """
    A versioned prompt with metadata.
    
    Attributes:
        version: Semantic version string (e.g., "1.0.0")
        prompt_text: The actual prompt template
        system_prompt: Optional system prompt
        created_at: Timestamp of creation
        description: Human-readable description of changes
        is_active: Whether this version is currently in use
    """
    version: str
    prompt_text: str
    system_prompt: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    description: str = ""
    is_active: bool = True
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization."""
        return {
            "version": self.version,
            "prompt_text": self.prompt_text,
            "system_prompt": self.system_prompt,
            "created_at": self.created_at,
            "description": self.description,
            "is_active": self.is_active
        }


class PromptRegistry:
    """
    Centralized registry for all prompts used in the system.
    
    Features:
    - Version tracking for each prompt
    - Active version management
    - Prompt retrieval by category and version
    - Audit logging
    
    Usage:
        registry = PromptRegistry()
        prompt = registry.get_prompt(PromptCategory.SUMMARY)
        # Use prompt.prompt_text and prompt.system_prompt
    """
    
    def __init__(self):
        self._prompts: Dict[PromptCategory, List[PromptVersion]] = {}
        self._initialize_default_prompts()
        logger.info("Prompt registry initialized", prompt_count=len(self._prompts))
    
    def _initialize_default_prompts(self):
        """Initialize with default production prompts."""
        
        # Summary Generation Prompt v1.0.0
        self.register_prompt(
            category=PromptCategory.SUMMARY,
            version="1.0.0",
            prompt_text="""Extract SPECIFIC information from this EXACT insurance policy document:

{text}

Respond with ONLY valid JSON containing actual details from THIS SPECIFIC document:
{{
  "policy_type": "<health/life/motor/general>",
  "policy_number": "<actual policy number from document or 'Not mentioned'>",
  "sum_insured_amount": "<exact rupee amount from document or 'Not mentioned'>",
  "premium_amount": "<exact rupee amount from document or 'Not mentioned'>",
  "coverage_items": ["<item 1 from document>", "<item 2 from document>"],
  "waiting_period": "<exact period from document or 'Not mentioned'>",
  "exclusions_preview": ["<exclusion 1 from document>", "<exclusion 2 from document>"],
  "summary": "<2-3 sentences describing THIS SPECIFIC policy's coverage and key terms>"
}}

CRITICAL RULES:
1. Extract ONLY information explicitly present in the document
2. Use EXACT amounts, numbers, and terms from document
3. If something is not mentioned, write "Not mentioned"
4. Do NOT add generic insurance knowledge
5. Use PLAIN TEXT only - absolutely NO markdown symbols like *, **, #, -, or bullet points
6. Write in simple, clear English sentences""",
            system_prompt="""You are an insurance document analyzer. Extract SPECIFIC details from the provided document.
Do NOT generate generic descriptions. Extract ONLY what is explicitly stated in the document.
Respond ONLY with valid JSON. Use plain text - no markdown formatting symbols.""",
            description="Initial production prompt for policy summary extraction"
        )
        
        # Terms Extraction Prompt v1.0.0
        self.register_prompt(
            category=PromptCategory.TERMS_EXTRACTION,
            version="1.0.0",
            prompt_text="""From this SPECIFIC insurance policy document, extract key terms and their ACTUAL VALUES as stated:

{text}

Respond with ONLY a JSON array containing terms and their ACTUAL VALUES from THIS document:
[
  {{"term": "Sum Insured", "value": "Rs 5,00,000", "context": "Maximum claim amount per year"}},
  {{"term": "Premium", "value": "Rs 12,500 annually", "context": "Payment due yearly"}},
  {{"term": "Waiting Period", "value": "30 days for illness, 24 months for pre-existing", "context": "Time before claims allowed"}}
]

CRITICAL RULES:
1. Extract ACTUAL VALUES from document (amounts, periods, percentages)
2. If a term is mentioned but no value given, use "As per policy schedule"
3. Maximum 8 most important terms
4. Use PLAIN TEXT only - absolutely NO markdown symbols like *, **, #, -, or bullet points
5. Write definitions in simple, clear English""",
            system_prompt="""You are an insurance document analyzer. Extract SPECIFIC terms and their ACTUAL VALUES from the document.
Do NOT provide generic definitions. Extract what the document actually says.
Respond ONLY with valid JSON array. Use plain text - no markdown formatting.""",
            description="Initial production prompt for terms extraction"
        )
        
        # Exclusions Extraction Prompt v1.0.0
        self.register_prompt(
            category=PromptCategory.EXCLUSIONS,
            version="1.0.0",
            prompt_text="""Identify exclusions from this insurance policy:

{text}

Respond with ONLY a JSON array:
[
  {{"exclusion": "Cosmetic surgery", "explanation": "Not covered unless medically necessary"}},
  {{"exclusion": "Pre-existing conditions", "explanation": "Not covered for first 2 years"}}
]

CRITICAL RULES:
1. Use PLAIN TEXT only - absolutely NO markdown symbols like *, **, #, -, or bullet points
2. Write explanations in simple, clear English sentences
3. Maximum 6 exclusions
4. Extract only what is explicitly stated in the document""",
            system_prompt="""You are an insurance policy analyst. Respond ONLY with valid JSON array.
Use plain text only - no markdown symbols, asterisks, or bullet points.""",
            description="Initial production prompt for exclusions extraction"
        )
        
        # Question Answering Prompt v1.0.0
        self.register_prompt(
            category=PromptCategory.QA,
            version="1.0.0",
            prompt_text="""Policy Context:
{context}

Customer Question: {question}

Provide a clear, accurate answer based on the policy context above. If the answer is not in the context, say so clearly.""",
            system_prompt="""You are an insurance policy advisor. Answer questions accurately based ONLY on the provided policy context.
If information is not in the context, clearly state this.
Use simple, clear language.""",
            description="Initial production prompt for Q&A"
        )
    
    def register_prompt(
        self,
        category: PromptCategory,
        version: str,
        prompt_text: str,
        system_prompt: Optional[str] = None,
        description: str = "",
        is_active: bool = True
    ) -> PromptVersion:
        """
        Register a new prompt version.
        
        Args:
            category: The prompt category
            version: Semantic version string
            prompt_text: The prompt template
            system_prompt: Optional system prompt
            description: Description of this version
            is_active: Whether this is the active version
            
        Returns:
            The created PromptVersion
        """
        prompt = PromptVersion(
            version=version,
            prompt_text=prompt_text,
            system_prompt=system_prompt,
            description=description,
            is_active=is_active
        )
        
        if category not in self._prompts:
            self._prompts[category] = []
        
        # If this is active, deactivate others
        if is_active:
            for existing in self._prompts[category]:
                existing.is_active = False
        
        self._prompts[category].append(prompt)
        
        logger.info(
            "Prompt registered",
            category=category.value,
            version=version,
            is_active=is_active
        )
        
        return prompt
    
    def get_prompt(
        self,
        category: PromptCategory,
        version: Optional[str] = None
    ) -> Optional[PromptVersion]:
        """
        Get a prompt by category and optionally version.
        
        Args:
            category: The prompt category
            version: Specific version to retrieve (None = active version)
            
        Returns:
            PromptVersion or None if not found
        """
        if category not in self._prompts:
            logger.warning("Prompt category not found", category=category.value)
            return None
        
        prompts = self._prompts[category]
        
        if version:
            # Find specific version
            for prompt in prompts:
                if prompt.version == version:
                    return prompt
            logger.warning(
                "Prompt version not found",
                category=category.value,
                version=version
            )
            return None
        
        # Find active version
        for prompt in prompts:
            if prompt.is_active:
                return prompt
        
        # Fallback to latest
        return prompts[-1] if prompts else None
    
    def get_all_versions(self, category: PromptCategory) -> List[PromptVersion]:
        """Get all versions of a prompt category."""
        return self._prompts.get(category, [])
    
    def get_active_prompts(self) -> Dict[str, PromptVersion]:
        """Get all active prompts."""
        return {
            cat.value: self.get_prompt(cat)
            for cat in PromptCategory
            if self.get_prompt(cat)
        }
    
    def format_prompt(
        self,
        category: PromptCategory,
        version: Optional[str] = None,
        **kwargs
    ) -> Optional[str]:
        """
        Get and format a prompt with provided variables.
        
        Args:
            category: The prompt category
            version: Specific version (None = active)
            **kwargs: Variables to substitute in the prompt
            
        Returns:
            Formatted prompt string or None
        """
        prompt = self.get_prompt(category, version)
        if not prompt:
            return None
        
        try:
            return prompt.prompt_text.format(**kwargs)
        except KeyError as e:
            logger.error(
                "Missing prompt variable",
                category=category.value,
                missing_key=str(e)
            )
            return None


# Singleton instance
_registry: Optional[PromptRegistry] = None


def get_prompt_registry() -> PromptRegistry:
    """Get or create the prompt registry singleton."""
    global _registry
    if _registry is None:
        _registry = PromptRegistry()
    return _registry
