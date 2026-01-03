"""
Guardrails Service for SaralPolicy
Input validation and safety checks for insurance document analysis.
"""

import re
from typing import Dict, Any
import structlog

logger = structlog.get_logger(__name__)


class GuardrailsService:
    """Service for input validation and safety guardrails."""
    
    def __init__(self):
        # Text length limits for insurance document processing
        # Rationale: 50KB is sufficient for most insurance policy text extracts
        # while preventing memory exhaustion from extremely large inputs.
        # Typical insurance policy PDFs extract to 10-30KB of text.
        self.max_text_length = 50000  # 50KB max
        
        # Minimum text length to ensure meaningful analysis
        # Rationale: Insurance documents need sufficient context for accurate analysis.
        # 100 chars is roughly 15-20 words, minimum for a coherent policy excerpt.
        self.min_text_length = 100    # 100 chars min
        
        # Patterns to detect potentially sensitive information that should not be processed
        # These patterns catch common credential/secret formats to prevent accidental exposure
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
            # Remove potential PII patterns - Extended for Indian IDs
            pii_patterns = [
                # Credit cards (16 digits with optional separators)
                r'\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b',
                # US SSN
                r'\b\d{3}-\d{2}-\d{4}\b',
                # Email addresses
                r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
                # US Phone
                r'\b\d{3}-\d{3}-\d{4}\b',
                # Indian Aadhar (12 digits with optional spaces)
                r'\b\d{4}[\s]?\d{4}[\s]?\d{4}\b',
                # Indian PAN (AAAAA0000A format)
                r'\b[A-Z]{5}\d{4}[A-Z]\b',
                # Indian phone numbers (+91 or 0 prefix)
                r'\b(?:\+91[-\s]?|0)?[6-9]\d{9}\b',
                # Indian passport (A1234567 format)
                r'\b[A-Z]\d{7}\b',
                # Bank account numbers (9-18 digits)
                r'\b\d{9,18}\b',
                # IFSC codes
                r'\b[A-Z]{4}0[A-Z0-9]{6}\b',
            ]
            
            sanitized = output
            for pattern in pii_patterns:
                sanitized = re.sub(pattern, '[REDACTED]', sanitized)
            
            return sanitized
            
        except Exception as e:
            logger.error("Output sanitization failed", error=str(e))
            return output
    
    def check_hallucination_risk(self, text: str, response: str) -> Dict[str, Any]:
        """
        Check if response might be hallucinated.
        
        Detection Strategy (Per Engineering Constitution Section 4.5):
        1. Word overlap ratio - basic grounding check
        2. Number verification - check if numbers in response exist in source
        3. Key term presence - insurance-specific terms should come from source
        
        Known Limitations (documented per Section 2.4):
        - Cannot detect semantic contradictions (e.g., "covered" vs "not covered")
        - Cannot detect factual errors with same words (e.g., wrong amounts)
        - Synonyms reduce overlap score even when meaning is preserved
        - Paraphrased content may show lower overlap
        
        Args:
            text: Source document text
            response: Generated response to check
            
        Returns:
            Dict with high_risk (bool), reason (str), overlap_ratio (float),
            and additional detection signals
        """
        try:
            # Handle edge cases
            if not response or not response.strip():
                return {
                    "high_risk": False,
                    "reason": "Empty response",
                    "overlap_ratio": 0,
                    "checks_performed": ["empty_check"]
                }
            
            if not text or not text.strip():
                return {
                    "high_risk": True,
                    "reason": "No source text to verify against",
                    "overlap_ratio": 0,
                    "checks_performed": ["source_check"]
                }
            
            checks_performed = []
            risk_signals = []
            
            # 1. Word overlap check
            text_words = set(text.lower().split())
            response_words = set(response.lower().split())
            
            # Filter out common stop words for more meaningful overlap
            stop_words = {'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been',
                         'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will',
                         'would', 'could', 'should', 'may', 'might', 'must', 'shall',
                         'can', 'to', 'of', 'in', 'for', 'on', 'with', 'at', 'by',
                         'from', 'as', 'into', 'through', 'during', 'before', 'after',
                         'above', 'below', 'between', 'under', 'again', 'further',
                         'then', 'once', 'here', 'there', 'when', 'where', 'why',
                         'how', 'all', 'each', 'few', 'more', 'most', 'other', 'some',
                         'such', 'no', 'nor', 'not', 'only', 'own', 'same', 'so',
                         'than', 'too', 'very', 'just', 'and', 'but', 'if', 'or',
                         'because', 'until', 'while', 'this', 'that', 'these', 'those'}
            
            text_content_words = text_words - stop_words
            response_content_words = response_words - stop_words
            
            overlap = len(text_content_words.intersection(response_content_words))
            total_response_words = len(response_content_words)
            
            overlap_ratio = overlap / total_response_words if total_response_words > 0 else 0
            checks_performed.append("word_overlap")
            
            if overlap_ratio < 0.3:
                risk_signals.append("low_word_overlap")
            
            # 2. Number verification - check if numbers in response exist in source
            source_numbers = set(re.findall(r'\d+(?:,\d+)*(?:\.\d+)?', text))
            response_numbers = set(re.findall(r'\d+(?:,\d+)*(?:\.\d+)?', response))
            
            # Filter out very small numbers (1, 2, etc.) that are common
            significant_response_numbers = {n for n in response_numbers 
                                           if len(n.replace(',', '').replace('.', '')) >= 3}
            
            if significant_response_numbers:
                unverified_numbers = significant_response_numbers - source_numbers
                number_verification_ratio = 1 - (len(unverified_numbers) / len(significant_response_numbers))
                checks_performed.append("number_verification")
                
                if unverified_numbers:
                    risk_signals.append(f"unverified_numbers: {list(unverified_numbers)[:3]}")
            else:
                number_verification_ratio = 1.0
            
            # 3. Insurance term grounding - key terms should come from source
            insurance_terms = [
                'sum insured', 'premium', 'deductible', 'co-payment', 'copay',
                'waiting period', 'exclusion', 'coverage', 'claim', 'cashless',
                'network hospital', 'pre-existing', 'sub-limit', 'room rent'
            ]
            
            response_lower = response.lower()
            text_lower = text.lower()
            
            terms_in_response = [term for term in insurance_terms if term in response_lower]
            terms_in_source = [term for term in insurance_terms if term in text_lower]
            
            if terms_in_response:
                ungrounded_terms = [t for t in terms_in_response if t not in terms_in_source]
                if ungrounded_terms:
                    risk_signals.append(f"ungrounded_terms: {ungrounded_terms[:3]}")
                checks_performed.append("term_grounding")
            
            # Determine overall risk
            # High risk if: low overlap AND (unverified numbers OR ungrounded terms)
            high_risk = overlap_ratio < 0.3 and len(risk_signals) > 1
            
            # Also high risk if very low overlap regardless of other signals
            if overlap_ratio < 0.15:
                high_risk = True
                risk_signals.append("very_low_overlap")
            
            reason = "Response appears grounded in source text"
            if high_risk:
                reason = f"Potential hallucination detected: {', '.join(risk_signals)}"
            elif risk_signals:
                reason = f"Some concerns: {', '.join(risk_signals)}"
            
            return {
                "high_risk": high_risk,
                "reason": reason,
                "overlap_ratio": round(overlap_ratio, 3),
                "checks_performed": checks_performed,
                "risk_signals": risk_signals,
                "number_verification_ratio": round(number_verification_ratio, 3) if 'number_verification' in checks_performed else None
            }
            
        except Exception as e:
            logger.error("Hallucination check failed", error=str(e))
            return {
                "high_risk": False,
                "reason": f"Unable to perform hallucination check: {str(e)}",
                "overlap_ratio": 0,
                "checks_performed": [],
                "error": str(e)
            }
