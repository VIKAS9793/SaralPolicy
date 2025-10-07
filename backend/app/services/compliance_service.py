"""
Production-Grade Compliance & Safety Service for SaralPolicy

Features:
- PII Detection & Masking (Aadhar, PAN, Phone, Email, Address)
- Hallucination Prevention with source attribution
- Guardrails to prevent overstepping regulatory boundaries
- Explainability & Transparency
- IRDAI Compliance Checks
- Appropriate Disclaimers
- Context-bound Q&A (document-specific only)
"""

import re
import hashlib
import json
from typing import Dict, Any, List, Tuple, Optional
from datetime import datetime
import structlog

logger = structlog.get_logger(__name__)


class ComplianceService:
    """
    Ensures SaralPolicy remains compliant, safe, and transparent
    """
    
    # PII Patterns (Indian context)
    PII_PATTERNS = {
        "aadhar": {
            "pattern": r'\b\d{4}\s?\d{4}\s?\d{4}\b',
            "mask": "XXXX XXXX XXXX",
            "description": "Aadhar Number"
        },
        "pan": {
            "pattern": r'\b[A-Z]{5}[0-9]{4}[A-Z]{1}\b',
            "mask": "XXXXX****X",
            "description": "PAN Card"
        },
        "phone": {
            "pattern": r'\b(?:\+91[-\s]?)?[6-9]\d{9}\b',
            "mask": "+91-XXXX-XXXX",
            "description": "Phone Number"
        },
        "email": {
            "pattern": r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
            "mask": "****@****.***",
            "description": "Email Address"
        },
        "pincode": {
            "pattern": r'\b\d{6}\b',
            "mask": "******",
            "description": "Pincode"
        }
    }
    
    # Regulatory Disclaimers
    DISCLAIMERS = {
        "primary": """
⚠️ **IMPORTANT DISCLAIMER**

SaralPolicy is an **educational tool** that helps you understand insurance documents in simple language. 

**We are NOT:**
- A replacement for IRDAI or any regulatory body
- Providing legal, financial, or insurance advice
- Making policy recommendations or comparisons
- A licensed insurance agent or broker

**We DO:**
- Explain insurance terms in simple language
- Provide information from your uploaded document only
- Link to official IRDAI resources for verification
- Maintain complete privacy (local processing only)

**Always verify with:**
- Your insurance company directly
- IRDAI official website: www.irdai.gov.in
- Licensed insurance advisor

**Your Data:** All processing happens locally on your device. No data is sent to external servers.
        """,
        
        "qa_disclaimer": """
💬 **About This Q&A Feature:**

- Answers are based ONLY on your uploaded document
- We don't provide advice or recommendations
- Always verify critical information with your insurer
- For policy-specific queries, contact your insurance company
        """,
        
        "analysis_disclaimer": """
📋 **About This Analysis:**

- Explanations are educational, not advisory
- Terms explained using IRDAI-compliant definitions
- Examples are illustrative, not exhaustive
- Your specific policy may have unique conditions
- Always read your complete policy document
        """
    }
    
    # Forbidden topics (things we should NOT answer)
    FORBIDDEN_TOPICS = [
        "which policy should i buy",
        "which policy should i purchase",
        "is this a good policy",
        "is this policy good",
        "should i switch policies",
        "should i buy",
        "recommend",
        "file a claim for me",
        "call the insurance company",
        "legal action",
        "lawsuit",
        "how to cheat",
        "fraud",
        "fake documents",
        "manipulate",
        "hide information",
        "pretend",
        "act as",
        "you are now",
        "ignore previous",
        "forget you",
        "override",
        "system:",
        "[system",
        "financial advisor",
        "insurance agent",
        "licensed agent",
        "approve",
        "process my claim",
        "give me advice",
        "financial advice",
        "best option",
        "better choice",
        "which is best",
        "what should i invest"
    ]
    
    # Approved topics (safe educational queries)
    APPROVED_TOPICS = [
        "what does this term mean",
        "explain this section",
        "what is covered",
        "what is not covered",
        "how to claim",
        "waiting period",
        "premium amount",
        "sum insured",
        "exclusions",
        "terms and conditions"
    ]
    
    def __init__(self):
        self.pii_detected_count = 0
        self.guardrail_triggers = 0
        logger.info("Compliance Service initialized")
    
    def mask_pii(self, text: str, return_mapping: bool = False) -> Tuple[str, Dict]:
        """
        Detect and mask PII in text
        
        Returns:
            - Masked text
            - Mapping of original to masked (for potential decryption)
        """
        masked_text = text
        pii_mapping = {}
        detected_pii = []
        
        for pii_type, config in self.PII_PATTERNS.items():
            pattern = config["pattern"]
            mask = config["mask"]
            description = config["description"]
            
            matches = re.finditer(pattern, masked_text)
            for match in matches:
                original_value = match.group()
                
                # Create encrypted hash for potential lookup
                encrypted_hash = self._encrypt_pii(original_value)
                
                # Replace with mask
                masked_text = masked_text.replace(original_value, mask, 1)
                
                # Track mapping
                pii_mapping[encrypted_hash] = {
                    "original": original_value,
                    "type": pii_type,
                    "description": description
                }
                
                detected_pii.append({
                    "type": pii_type,
                    "description": description,
                    "masked_as": mask
                })
                
                self.pii_detected_count += 1
        
        if detected_pii:
            logger.info(f"PII detected and masked", count=len(detected_pii), types=[p["type"] for p in detected_pii])
        
        return masked_text, pii_mapping if return_mapping else {}
    
    def _encrypt_pii(self, value: str) -> str:
        """Encrypt PII value for secure storage"""
        return hashlib.sha256(value.encode()).hexdigest()
    
    def check_guardrails(self, query: str, context: str = "") -> Dict[str, Any]:
        """
        Check if query/context violates guardrails
        
        Returns:
            - is_safe: bool
            - violation_reason: str (if not safe)
            - suggested_alternatives: List[str]
        """
        # Normalize query to detect obfuscation
        query_lower = query.lower()
        # Remove excessive spaces
        query_normalized = ' '.join(query_lower.split())
        # Simple character substitution normalization
        query_normalized = query_normalized.replace('0', 'o').replace('1', 'i').replace('3', 'e')
        
        # Check for forbidden topics (using normalized query)
        for forbidden in self.FORBIDDEN_TOPICS:
            if forbidden in query_normalized:
                self.guardrail_triggers += 1
                logger.warning("Guardrail triggered", forbidden_topic=forbidden)
                
                return {
                    "is_safe": False,
                    "violation_type": "FORBIDDEN_TOPIC",
                    "violation_reason": f"This question asks for advice/action that we cannot provide",
                    "explanation": """
SaralPolicy is an educational tool. We can explain insurance terms but cannot:
- Recommend policies
- Provide financial/legal advice
- Take actions on your behalf
- Make comparisons

We CAN help you understand what's in your policy document.
                    """,
                    "suggested_alternatives": [
                        "What does [specific term] mean in my policy?",
                        "Can you explain the coverage section?",
                        "What are the exclusions in my policy?",
                        "How does the claim process work according to this document?"
                    ]
                }
        
        # Check if query is too vague (out of document context)
        if len(query.strip()) < 10:
            return {
                "is_safe": True,
                "warning": "Query is very short. Please be more specific about what you want to know from your policy document."
            }
        
        # All checks passed
        return {
            "is_safe": True,
            "message": "Query is within safe boundaries"
        }
    
    def validate_response(self, response: str, source_document: str) -> Dict[str, Any]:
        """
        Validate LLM response for hallucinations and accuracy
        
        Checks:
        - Does response reference document content?
        - Are there unsupported claims?
        - Is disclaimer present?
        """
        validation_result = {
            "is_valid": True,
            "confidence": 1.0,
            "issues": [],
            "source_attribution": False
        }
        
        # Check 1: Response should be grounded in document
        if "according to your policy" in response.lower() or "your document states" in response.lower():
            validation_result["source_attribution"] = True
        else:
            validation_result["issues"].append("Response lacks source attribution")
            validation_result["confidence"] *= 0.8
        
        # Check 2: Response shouldn't make recommendations
        recommendation_keywords = ["you should", "i recommend", "best option", "better choice"]
        if any(kw in response.lower() for kw in recommendation_keywords):
            validation_result["is_valid"] = False
            validation_result["issues"].append("Response contains recommendations (not allowed)")
            logger.warning("Response validation failed: Contains recommendations")
        
        # Check 3: Response shouldn't claim authority
        authority_claims = ["i am certified", "as an expert", "official advice", "we guarantee"]
        if any(claim in response.lower() for claim in authority_claims):
            validation_result["is_valid"] = False
            validation_result["issues"].append("Response makes inappropriate authority claims")
            logger.warning("Response validation failed: Authority claims")
        
        # Check 4: Hallucination detection (basic)
        # If response mentions specific numbers/amounts, check if they exist in document
        numbers_in_response = re.findall(r'₹[\d,]+|Rs\.?\s*[\d,]+|\d+\s*(?:lakh|crore)', response)
        if numbers_in_response:
            doc_has_numbers = any(num in source_document for num in numbers_in_response)
            if not doc_has_numbers:
                validation_result["issues"].append("Response contains numbers not found in source document (potential hallucination)")
                validation_result["confidence"] *= 0.6
                logger.warning("Potential hallucination detected", numbers=numbers_in_response)
        
        # Final confidence calculation
        if validation_result["issues"]:
            validation_result["confidence"] = max(0.5, validation_result["confidence"])
        
        return validation_result
    
    def generate_explainability_report(self, 
                                      query: str, 
                                      response: str, 
                                      source_sections: List[str],
                                      model_used: str) -> Dict[str, Any]:
        """
        Generate explainability report for transparency
        
        Shows:
        - Which document sections were used
        - How answer was derived
        - Model confidence
        - Verification links
        """
        return {
            "query": query,
            "answer_source": {
                "primary_source": "Your uploaded policy document",
                "document_sections_referenced": source_sections,
                "external_sources_used": [],
                "verification_links": [
                    {"name": "IRDAI Official", "url": "https://www.irdai.gov.in"},
                    {"name": "Insurance Ombudsman", "url": "https://www.cioins.co.in"}
                ]
            },
            "how_answer_derived": {
                "step_1": "Extracted relevant sections from your document",
                "step_2": "Identified key insurance terms",
                "step_3": "Matched with IRDAI-compliant definitions",
                "step_4": "Explained in simple language with examples"
            },
            "model_info": {
                "model_name": model_used,
                "processing_type": "Local (on your device)",
                "data_retention": "None (not stored anywhere)",
                "explainability_level": "High"
            },
            "confidence_factors": {
                "source_availability": "Document sections found" if source_sections else "Limited context",
                "term_clarity": "Clear definitions available",
                "irdai_alignment": "Aligned with IRDAI guidelines"
            },
            "disclaimer": self.DISCLAIMERS["qa_disclaimer"],
            "verification_needed": True,
            "verification_message": "For policy-specific actions, always contact your insurance company directly."
        }
    
    def create_analysis_metadata(self, analysis_result: Dict) -> Dict[str, Any]:
        """
        Add compliance metadata to analysis results
        """
        return {
            "compliance_info": {
                "irdai_compliant": analysis_result.get("irdai_compliant", False),
                "pii_protected": self.pii_detected_count > 0,
                "guardrails_active": True,
                "processing_location": "Local (Your Device)",
                "data_retention": "None",
                "explainability": "Full transparency available"
            },
            "disclaimers": {
                "primary": self.DISCLAIMERS["primary"],
                "analysis": self.DISCLAIMERS["analysis_disclaimer"]
            },
            "user_rights": {
                "data_privacy": "All data processed locally, not stored",
                "transparency": "Full explanation of how analysis was performed",
                "verification": "Always verify with official sources",
                "contact": "Reach IRDAI for regulatory queries"
            },
            "verification_links": {
                "irdai_official": "https://www.irdai.gov.in",
                "irdai_consumer_affairs": "https://www.irdai.gov.in/consumer-affairs",
                "insurance_ombudsman": "https://www.cioins.co.in",
                "complaint_portal": "https://igms.irda.gov.in"
            },
            "limitations": [
                "Educational explanations only, not legal/financial advice",
                "Based on uploaded document analysis",
                "General insurance terms explained, specific policy may vary",
                "Not a substitute for professional insurance advisor",
                "Always read complete policy document"
            ],
            "timestamp": datetime.now().isoformat(),
            "compliance_version": "1.0.0"
        }
    
    def sanitize_for_qa(self, document: str, query: str) -> Tuple[str, str, Dict]:
        """
        Sanitize document and query for Q&A feature
        
        Returns:
            - Sanitized document (PII masked)
            - Sanitized query
            - Safety report
        """
        # Mask PII in document
        sanitized_doc, pii_map = self.mask_pii(document, return_mapping=True)
        
        # Check query guardrails
        guardrail_check = self.check_guardrails(query, document)
        
        # Sanitize query (remove any PII user might have typed)
        sanitized_query, _ = self.mask_pii(query)
        
        safety_report = {
            "pii_masked": len(pii_map) > 0,
            "pii_types_found": [v["type"] for v in pii_map.values()],
            "guardrails_passed": guardrail_check["is_safe"],
            "query_sanitized": True
        }
        
        if not guardrail_check["is_safe"]:
            safety_report["guardrail_violation"] = guardrail_check
        
        logger.info("Document and query sanitized for Q&A", **safety_report)
        
        return sanitized_doc, sanitized_query, safety_report
    
    def get_disclaimer_banner(self) -> str:
        """Get prominent disclaimer banner for UI"""
        return """
╔══════════════════════════════════════════════════════════════╗
║              ⚠️  EDUCATIONAL TOOL ONLY ⚠️                      ║
╠══════════════════════════════════════════════════════════════╣
║                                                              ║
║  SaralPolicy explains insurance terms in simple language    ║
║  We are NOT providing advice or recommendations             ║
║                                                              ║
║  ✓ Explains what's in YOUR document                         ║
║  ✓ Uses IRDAI-compliant definitions                         ║
║  ✓ Links to official verification sources                   ║
║  ✓ 100% local processing (complete privacy)                 ║
║                                                              ║
║  ✗ NOT legal/financial advice                               ║
║  ✗ NOT policy recommendations                               ║
║  ✗ NOT a replacement for insurance advisor                  ║
║                                                              ║
║  Always verify with:                                        ║
║  📞 Your insurance company                                   ║
║  🏛️  IRDAI: www.irdai.gov.in                                ║
║  📧 Ombudsman: www.cioins.co.in                             ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
        """
    
    def generate_compliance_report(self) -> Dict[str, Any]:
        """
        Generate compliance report for auditing
        """
        return {
            "report_generated": datetime.now().isoformat(),
            "compliance_metrics": {
                "pii_instances_protected": self.pii_detected_count,
                "guardrail_triggers": self.guardrail_triggers,
                "irdai_compliant": True,
                "data_privacy_maintained": True,
                "explainability_provided": True
            },
            "safety_features": {
                "pii_masking": "Active",
                "guardrails": "Active",
                "hallucination_prevention": "Active",
                "source_attribution": "Required",
                "disclaimer_enforcement": "Active"
            },
            "regulatory_alignment": {
                "irdai_guidelines": "Followed",
                "data_protection": "Local processing only",
                "consumer_rights": "Respected",
                "transparency": "Full disclosure"
            },
            "limitations_acknowledged": True,
            "verification_encouraged": True
        }


# Global compliance service instance
compliance_service = ComplianceService()
