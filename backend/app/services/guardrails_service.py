"""
Guardrails Service for SaralPolicy
Input validation and safety checks for insurance document analysis.
"""

import re
import logging
from typing import Dict, Any, List
import structlog

logger = structlog.get_logger(__name__)


class GuardrailsService:
    """Service for input validation and safety guardrails."""
    
    def __init__(self):
        self.max_text_length = 50000  # 50KB max
        self.min_text_length = 100    # 100 chars min
        self.blocked_patterns = [
            r'password\s*[:=]\s*\w+',
            r'api[_-]?key\s*[:=]\s*\w+',
            r'secret\s*[:=]\s*\w+',
            r'token\s*[:=]\s*\w+',
        ]
    
    def validate_input(self, text: str) -> Dict[str, Any]:
        """Validate input text for safety and appropriateness."""
        try:
            # Check text length
            if len(text) < self.min_text_length:
                return {
                    "is_valid": False,
                    "reason": f"Text too short (minimum {self.min_text_length} characters required)"
                }
            
            if len(text) > self.max_text_length:
                return {
                    "is_valid": False,
                    "reason": f"Text too long (maximum {self.max_text_length} characters allowed)"
                }
            
            # Check for sensitive information
            for pattern in self.blocked_patterns:
                if re.search(pattern, text, re.IGNORECASE):
                    return {
                        "is_valid": False,
                        "reason": "Text contains potentially sensitive information"
                    }
            
            # Check for insurance-related content
            insurance_keywords = [
                'policy', 'insurance', 'coverage', 'premium', 'claim',
                'beneficiary', 'deductible', 'exclusion', 'policyholder'
            ]
            
            text_lower = text.lower()
            keyword_count = sum(1 for keyword in insurance_keywords if keyword in text_lower)
            
            if keyword_count < 2:
                return {
                    "is_valid": False,
                    "reason": "Text does not appear to be an insurance document"
                }
            
            return {
                "is_valid": True,
                "reason": "Input validation passed"
            }
            
        except Exception as e:
            logger.error("Input validation failed", error=str(e))
            return {
                "is_valid": False,
                "reason": f"Validation error: {str(e)}"
            }
    
    def validate_question(self, question: str) -> Dict[str, Any]:
        """Validate user questions for safety and appropriateness."""
        try:
            # Check question length
            if len(question) < 5:
                return {
                    "is_valid": False,
                    "reason": "Question too short"
                }
            
            if len(question) > 500:
                return {
                    "is_valid": False,
                    "reason": "Question too long (maximum 500 characters)"
                }
            
            # Check for inappropriate content
            inappropriate_patterns = [
                r'how\s+to\s+hack',
                r'bypass\s+security',
                r'steal\s+data',
                r'fraud',
                r'scam'
            ]
            
            for pattern in inappropriate_patterns:
                if re.search(pattern, question, re.IGNORECASE):
                    return {
                        "is_valid": False,
                        "reason": "Question contains inappropriate content"
                    }
            
            return {
                "is_valid": True,
                "reason": "Question validation passed"
            }
            
        except Exception as e:
            logger.error("Question validation failed", error=str(e))
            return {
                "is_valid": False,
                "reason": f"Validation error: {str(e)}"
            }
    
    def sanitize_output(self, output: str) -> str:
        """Sanitize output to remove any sensitive information."""
        try:
            # Remove potential PII patterns
            pii_patterns = [
                r'\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b',  # Credit card
                r'\b\d{3}-\d{2}-\d{4}\b',  # SSN
                r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',  # Email
                r'\b\d{3}-\d{3}-\d{4}\b',  # Phone
            ]
            
            sanitized = output
            for pattern in pii_patterns:
                sanitized = re.sub(pattern, '[REDACTED]', sanitized)
            
            return sanitized
            
        except Exception as e:
            logger.error("Output sanitization failed", error=str(e))
            return output
    
    def check_hallucination_risk(self, text: str, response: str) -> Dict[str, Any]:
        """Check if response might be hallucinated."""
        try:
            # Simple heuristic: check if response contains information not in source
            text_words = set(text.lower().split())
            response_words = set(response.lower().split())
            
            # Calculate overlap
            overlap = len(text_words.intersection(response_words))
            total_response_words = len(response_words)
            
            if total_response_words > 0:
                overlap_ratio = overlap / total_response_words
                
                if overlap_ratio < 0.3:  # Less than 30% overlap
                    return {
                        "high_risk": True,
                        "reason": "Low overlap with source text",
                        "overlap_ratio": overlap_ratio
                    }
            
            return {
                "high_risk": False,
                "reason": "Response appears grounded in source text",
                "overlap_ratio": overlap_ratio if total_response_words > 0 else 0
            }
            
        except Exception as e:
            logger.error("Hallucination check failed", error=str(e))
            return {
                "high_risk": False,
                "reason": "Unable to perform hallucination check"
            }
