"""
Prompt Regression Tests for SaralPolicy

Per Engineering Constitution Section 4.5:
- Design prompts intentionally
- Define evaluation strategies
- Reject brittle prompt hacks

These tests ensure:
1. Prompt versions are tracked
2. Prompt changes don't cause regressions
3. Output format consistency is maintained
"""

import pytest
from unittest.mock import patch, MagicMock
import json
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.prompts.registry import (
    PromptRegistry,
    PromptVersion,
    PromptCategory,
    get_prompt_registry
)


class TestPromptRegistry:
    """Test prompt registry functionality."""
    
    def test_registry_initialization(self):
        """Test registry initializes with default prompts."""
        registry = PromptRegistry()
        
        # Core categories used in production should have prompts
        # SYSTEM category is reserved for future use (YAGNI - not implemented yet)
        production_categories = [
            PromptCategory.SUMMARY,
            PromptCategory.TERMS_EXTRACTION,
            PromptCategory.EXCLUSIONS,
            PromptCategory.QA
        ]
        
        for category in production_categories:
            prompt = registry.get_prompt(category)
            assert prompt is not None, f"Missing prompt for {category.value}"
            assert prompt.version == "1.0.0"
            assert prompt.is_active is True
    
    def test_get_prompt_by_category(self):
        """Test retrieving prompts by category."""
        registry = PromptRegistry()
        
        summary_prompt = registry.get_prompt(PromptCategory.SUMMARY)
        assert summary_prompt is not None
        assert "insurance" in summary_prompt.prompt_text.lower()
        assert summary_prompt.system_prompt is not None
    
    def test_get_prompt_by_version(self):
        """Test retrieving specific prompt version."""
        registry = PromptRegistry()
        
        prompt = registry.get_prompt(PromptCategory.SUMMARY, version="1.0.0")
        assert prompt is not None
        assert prompt.version == "1.0.0"
        
        # Non-existent version returns None
        prompt = registry.get_prompt(PromptCategory.SUMMARY, version="99.0.0")
        assert prompt is None
    
    def test_register_new_prompt_version(self):
        """Test registering a new prompt version."""
        registry = PromptRegistry()
        
        # Register new version
        new_prompt = registry.register_prompt(
            category=PromptCategory.SUMMARY,
            version="1.1.0",
            prompt_text="New test prompt {text}",
            system_prompt="New system prompt",
            description="Test version",
            is_active=True
        )
        
        assert new_prompt.version == "1.1.0"
        assert new_prompt.is_active is True
        
        # New version should be active
        active = registry.get_prompt(PromptCategory.SUMMARY)
        assert active.version == "1.1.0"
        
        # Old version should still be retrievable
        old = registry.get_prompt(PromptCategory.SUMMARY, version="1.0.0")
        assert old is not None
        assert old.is_active is False
    
    def test_get_all_versions(self):
        """Test retrieving all versions of a prompt."""
        registry = PromptRegistry()
        
        # Add another version
        registry.register_prompt(
            category=PromptCategory.QA,
            version="1.1.0",
            prompt_text="Updated QA prompt",
            is_active=False
        )
        
        versions = registry.get_all_versions(PromptCategory.QA)
        assert len(versions) >= 2
        version_numbers = [v.version for v in versions]
        assert "1.0.0" in version_numbers
        assert "1.1.0" in version_numbers
    
    def test_get_active_prompts(self):
        """Test retrieving all active prompts."""
        registry = PromptRegistry()
        
        active = registry.get_active_prompts()
        
        # Should have 4 active prompts (SYSTEM is reserved, not implemented)
        assert len(active) >= 4
        
        # Core production categories must be present
        required_categories = ["summary", "terms_extraction", "exclusions", "question_answering"]
        for cat in required_categories:
            assert cat in active, f"Missing active prompt for {cat}"
    
    def test_format_prompt(self):
        """Test prompt formatting with variables."""
        registry = PromptRegistry()
        
        # Format summary prompt
        formatted = registry.format_prompt(
            PromptCategory.SUMMARY,
            text="Sample insurance document text"
        )
        
        assert formatted is not None
        assert "Sample insurance document text" in formatted
        assert "{text}" not in formatted
    
    def test_format_prompt_missing_variable(self):
        """Test formatting with missing variable returns None."""
        registry = PromptRegistry()
        
        # Missing required variable
        formatted = registry.format_prompt(PromptCategory.SUMMARY)
        assert formatted is None
    
    def test_format_qa_prompt(self):
        """Test QA prompt formatting with context and question."""
        registry = PromptRegistry()
        
        formatted = registry.format_prompt(
            PromptCategory.QA,
            context="Policy covers hospitalization",
            question="What is covered?"
        )
        
        assert formatted is not None
        assert "Policy covers hospitalization" in formatted
        assert "What is covered?" in formatted


class TestPromptVersionDataclass:
    """Test PromptVersion dataclass."""
    
    def test_prompt_version_creation(self):
        """Test creating a PromptVersion."""
        prompt = PromptVersion(
            version="1.0.0",
            prompt_text="Test prompt",
            system_prompt="System prompt",
            description="Test description"
        )
        
        assert prompt.version == "1.0.0"
        assert prompt.prompt_text == "Test prompt"
        assert prompt.system_prompt == "System prompt"
        assert prompt.is_active is True
        assert prompt.created_at is not None
    
    def test_prompt_version_to_dict(self):
        """Test serialization to dictionary."""
        prompt = PromptVersion(
            version="1.0.0",
            prompt_text="Test prompt",
            description="Test"
        )
        
        data = prompt.to_dict()
        
        assert data["version"] == "1.0.0"
        assert data["prompt_text"] == "Test prompt"
        assert "created_at" in data
        assert data["is_active"] is True


class TestPromptRegressionDetection:
    """Tests for detecting prompt regressions."""
    
    def test_summary_prompt_contains_required_elements(self):
        """Verify summary prompt has required instructions."""
        registry = PromptRegistry()
        prompt = registry.get_prompt(PromptCategory.SUMMARY)
        
        # Required elements for insurance document analysis
        required_elements = [
            "policy_type",
            "sum_insured",
            "premium",
            "coverage",
            "exclusion",
            "JSON"
        ]
        
        prompt_lower = prompt.prompt_text.lower()
        for element in required_elements:
            assert element.lower() in prompt_lower, f"Missing required element: {element}"
    
    def test_terms_prompt_contains_required_elements(self):
        """Verify terms extraction prompt has required instructions."""
        registry = PromptRegistry()
        prompt = registry.get_prompt(PromptCategory.TERMS_EXTRACTION)
        
        required_elements = [
            "term",
            "value",
            "JSON"
        ]
        
        prompt_lower = prompt.prompt_text.lower()
        for element in required_elements:
            assert element.lower() in prompt_lower, f"Missing required element: {element}"
    
    def test_exclusions_prompt_contains_required_elements(self):
        """Verify exclusions prompt has required instructions."""
        registry = PromptRegistry()
        prompt = registry.get_prompt(PromptCategory.EXCLUSIONS)
        
        required_elements = [
            "exclusion",
            "explanation",
            "JSON"
        ]
        
        prompt_lower = prompt.prompt_text.lower()
        for element in required_elements:
            assert element.lower() in prompt_lower, f"Missing required element: {element}"
    
    def test_qa_prompt_contains_required_elements(self):
        """Verify QA prompt has required instructions."""
        registry = PromptRegistry()
        prompt = registry.get_prompt(PromptCategory.QA)
        
        required_elements = [
            "context",
            "question",
            "answer"
        ]
        
        prompt_lower = prompt.prompt_text.lower()
        for element in required_elements:
            assert element.lower() in prompt_lower, f"Missing required element: {element}"
    
    def test_prompts_request_json_output(self):
        """Verify prompts that need structured output request JSON."""
        registry = PromptRegistry()
        
        json_required_categories = [
            PromptCategory.SUMMARY,
            PromptCategory.TERMS_EXTRACTION,
            PromptCategory.EXCLUSIONS
        ]
        
        for category in json_required_categories:
            prompt = registry.get_prompt(category)
            assert "json" in prompt.prompt_text.lower(), \
                f"{category.value} prompt should request JSON output"
    
    def test_prompts_have_system_prompts(self):
        """Verify all prompts have system prompts defined."""
        registry = PromptRegistry()
        
        for category in PromptCategory:
            prompt = registry.get_prompt(category)
            # SYSTEM category may not have system_prompt
            if category != PromptCategory.SYSTEM:
                assert prompt.system_prompt is not None, \
                    f"{category.value} should have a system prompt"
    
    def test_prompts_prevent_hallucination(self):
        """Verify prompts include anti-hallucination instructions."""
        registry = PromptRegistry()
        
        # Summary and terms prompts should have anti-hallucination guidance
        for category in [PromptCategory.SUMMARY, PromptCategory.TERMS_EXTRACTION]:
            prompt = registry.get_prompt(category)
            prompt_lower = prompt.prompt_text.lower()
            
            # Should mention extracting from document, not generating
            has_grounding = any(phrase in prompt_lower for phrase in [
                "from this",
                "from the document",
                "explicitly",
                "actual",
                "not mentioned"
            ])
            
            assert has_grounding, \
                f"{category.value} prompt should include grounding instructions"


class TestPromptOutputConsistency:
    """Tests for output format consistency."""
    
    def test_summary_output_schema(self):
        """Verify summary prompt requests consistent output schema."""
        registry = PromptRegistry()
        prompt = registry.get_prompt(PromptCategory.SUMMARY)
        
        # Expected fields in output
        expected_fields = [
            "policy_type",
            "policy_number",
            "sum_insured",
            "premium",
            "coverage",
            "summary"
        ]
        
        prompt_lower = prompt.prompt_text.lower()
        for field in expected_fields:
            # Field should be mentioned (with variations like sum_insured_amount)
            field_variations = [field, field.replace("_", " "), field.replace("_", "")]
            has_field = any(var in prompt_lower for var in field_variations)
            assert has_field, f"Summary prompt should request {field}"
    
    def test_terms_output_schema(self):
        """Verify terms prompt requests consistent output schema."""
        registry = PromptRegistry()
        prompt = registry.get_prompt(PromptCategory.TERMS_EXTRACTION)
        
        expected_fields = ["term", "value"]
        
        prompt_lower = prompt.prompt_text.lower()
        for field in expected_fields:
            assert field in prompt_lower, f"Terms prompt should request {field}"
    
    def test_exclusions_output_schema(self):
        """Verify exclusions prompt requests consistent output schema."""
        registry = PromptRegistry()
        prompt = registry.get_prompt(PromptCategory.EXCLUSIONS)
        
        expected_fields = ["exclusion", "explanation"]
        
        prompt_lower = prompt.prompt_text.lower()
        for field in expected_fields:
            assert field in prompt_lower, f"Exclusions prompt should request {field}"


class TestPromptSingleton:
    """Test singleton pattern for prompt registry."""
    
    def test_get_prompt_registry_returns_same_instance(self):
        """Test singleton returns same instance."""
        # Reset singleton for test
        import app.prompts.registry as registry_module
        registry_module._registry = None
        
        registry1 = get_prompt_registry()
        registry2 = get_prompt_registry()
        
        assert registry1 is registry2


class TestPromptCategoryEnum:
    """Test PromptCategory enum."""
    
    def test_all_categories_defined(self):
        """Verify all expected categories exist."""
        expected = ["summary", "terms_extraction", "exclusions", "question_answering", "system"]
        
        actual = [c.value for c in PromptCategory]
        
        for exp in expected:
            assert exp in actual, f"Missing category: {exp}"
    
    def test_category_string_values(self):
        """Test category enum string values."""
        assert PromptCategory.SUMMARY.value == "summary"
        assert PromptCategory.QA.value == "question_answering"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
