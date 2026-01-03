"""
Ollama LLM Service for SaralPolicy
Uses local Ollama for complete privacy and IRDAI compliance (model configurable)

Per Engineering Constitution Section 4.5:
- Design prompts intentionally
- Define evaluation strategies
- Use PromptRegistry for version control
"""

import re
import requests
from typing import Dict, Any, List, Optional
import structlog
from datetime import datetime

from app.prompts.registry import PromptRegistry, PromptCategory, get_prompt_registry

logger = structlog.get_logger(__name__)


class OllamaLLMService:
    """
    Production-grade LLM service using local Ollama:
    - Complete local processing via Ollama
    - No cloud dependencies
    - Insurance-specific knowledge base
    - IRDAI compliance built-in
    - Advanced analysis and entity extraction
    """
    
    # IRDAI-compliant insurance knowledge base
    INSURANCE_KNOWLEDGE_BASE = {
        "health_insurance": {
            "category": "Health Insurance",
            "irdai_guidelines": "https://www.irdai.gov.in/admincms/cms/frmGeneral_NoYearList.aspx?DF=PB&mid=3.2",
            "key_regulations": [
                "IRDAI (Health Insurance) Regulations, 2016",
                "Mandatory coverage for pre-existing diseases after 2-4 years waiting period",
                "Cashless facility at network hospitals mandatory",
                "30-day initial waiting period for illnesses (excluding accidents)",
                "Grace period of 15-30 days for premium payment"
            ],
            "standard_terms": {
                "sum_insured": {
                    "definition": "Maximum amount insurer pays for all claims in policy year",
                    "layman": "The total coverage limit per year. If limit is ₹5 lakh, that's max you can claim annually",
                    "example": "₹5 lakh sum insured = All hospital bills combined shouldn't exceed ₹5 lakh in one year",
                    "hindi": "एक वर्ष में बीमा कंपनी द्वारा भुगतान की जाने वाली अधिकतम राशि",
                    "importance": "CRITICAL"
                },
                "premium": {
                    "definition": "Amount paid to insurer to keep policy active",
                    "layman": "Your monthly/yearly subscription fee for insurance coverage",
                    "example": "₹7,500/year premium means you pay this amount annually to maintain coverage",
                    "hindi": "बीमा सक्रिय रखने के लिए भुगतान की गई राशि",
                    "importance": "CRITICAL"
                },
                "deductible": {
                    "definition": "Amount you pay before insurance starts paying",
                    "layman": "Your share that you must pay first from your pocket",
                    "example": "₹10,000 deductible on ₹50,000 bill: You pay ₹10k, insurance pays ₹40k",
                    "hindi": "बीमा भुगतान शुरू होने से पहले आपका हिस्सा",
                    "importance": "HIGH"
                },
                "co_payment": {
                    "definition": "Percentage of bill shared between you and insurer",
                    "layman": "You pay X%, insurance pays (100-X)% of total bill",
                    "example": "20% co-pay on ₹1 lakh bill: You pay ₹20k, insurance pays ₹80k",
                    "hindi": "बिल का प्रतिशत जो आप और बीमा कंपनी साझा करते हैं",
                    "importance": "HIGH"
                },
                "waiting_period": {
                    "definition": "Time before certain conditions are covered",
                    "layman": "Cooling period - you can't claim for specific illnesses immediately after buying",
                    "example": "30-day wait for illness means you can claim illness-related expenses only after 30 days (accidents covered from day 1)",
                    "hindi": "विशिष्ट स्थितियों के लिए प्रतीक्षा अवधि",
                    "importance": "HIGH"
                },
                "pre_existing_disease": {
                    "definition": "Health conditions existing before policy purchase",
                    "layman": "Illnesses you already have when buying insurance",
                    "example": "Have diabetes before insurance? Claims for diabetes covered only after 2-4 year waiting period",
                    "hindi": "पॉलिसी खरीदने से पहले मौजूद बीमारियाँ",
                    "importance": "CRITICAL"
                },
                "cashless_treatment": {
                    "definition": "Treatment without upfront payment at network hospitals",
                    "layman": "Show insurance card, get treated, no cash needed (at network hospitals)",
                    "example": "Hospitalized at network hospital: Show card, get treatment, insurance pays hospital directly",
                    "hindi": "नेटवर्क अस्पतालों में बिना अग्रिम भुगतान के उपचार",
                    "importance": "HIGH"
                },
                "reimbursement": {
                    "definition": "You pay first, insurance refunds later",
                    "layman": "Pay hospital bills yourself, submit to insurance, get money back",
                    "example": "Pay ₹50k at hospital, submit bills to insurance, receive ₹50k in bank within 30 days",
                    "hindi": "पहले भुगतान करें, बाद में बीमा से वापसी",
                    "importance": "MEDIUM"
                },
                "room_rent_limit": {
                    "definition": "Maximum daily room rent covered",
                    "layman": "Cap on how expensive a hospital room you can book",
                    "example": "₹2k/day limit: Book ₹3k room, you pay ₹1k extra daily",
                    "hindi": "दैनिक कमरे के किराए की अधिकतम सीमा",
                    "importance": "MEDIUM"
                },
                "sub_limit": {
                    "definition": "Caps on specific treatments within sum insured",
                    "layman": "Separate limits for specific procedures",
                    "example": "₹50k cataract limit even if sum insured is ₹5 lakh",
                    "hindi": "विशिष्ट उपचारों पर अलग सीमाएं",
                    "importance": "MEDIUM"
                }
            }
        }
    }
    
    def __init__(self, 
                 model_name: str = "gemma2:2b",
                 ollama_host: str = "http://localhost:11434",
                 prompt_registry: Optional[PromptRegistry] = None):
        """
        Initialize Ollama LLM service
        
        Args:
            model_name: Ollama model name (configurable via OLLAMA_MODEL env)
            ollama_host: Ollama API endpoint
            prompt_registry: Optional PromptRegistry instance (uses singleton if not provided)
        """
        self.model_name = model_name
        self.ollama_host = ollama_host
        self.api_url = f"{ollama_host}/api/generate"
        self.chat_url = f"{ollama_host}/api/chat"
        
        # Initialize prompt registry for versioned prompts
        self._prompt_registry = prompt_registry or get_prompt_registry()
        
        # Verify Ollama connection
        self._verify_connection()
        logger.info(f"✅ Ollama LLM Service initialized with {model_name}")
    
    def _verify_connection(self):
        """Verify Ollama is running and model is available"""
        try:
            response = requests.get(f"{self.ollama_host}/api/tags", timeout=5)
            if response.status_code == 200:
                models = response.json().get('models', [])
                model_names = [m['name'] for m in models]
                
                if self.model_name not in model_names:
                    logger.warning(f"⚠️ Model {self.model_name} not found. Available models: {model_names}")
                    logger.info(f"📥 Please run: ollama pull {self.model_name}")
                else:
                    logger.info(f"✅ Ollama connected. Model {self.model_name} available")
            else:
                raise ConnectionError("Ollama API returned non-200 status")
        except Exception as e:
            logger.error(f"❌ Cannot connect to Ollama: {e}")
            logger.info("💡 Ensure Ollama is running: ollama serve")
            raise ConnectionError(f"Ollama not available: {e}")
    
    def _generate(self, prompt: str, system: str = None, max_tokens: int = 2000) -> str:
        """Generate response from Ollama"""
        try:
            payload = {
                "model": self.model_name,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.3,
                    "num_predict": max_tokens
                }
            }
            
            if system:
                payload["system"] = system
            
            response = requests.post(self.api_url, json=payload, timeout=120)
            
            if response.status_code == 200:
                result = response.json()
                return result.get('response', '').strip()
            else:
                logger.error(f"Ollama API error: {response.status_code}")
                return ""
                
        except Exception as e:
            logger.error(f"Failed to generate response: {e}")
            return ""
    
    def generate_intelligent_summary(self, text: str, prompt_version: Optional[str] = None) -> Dict[str, Any]:
        """
        Generate comprehensive insurance policy summary using JSON schema.
        
        Args:
            text: Insurance document text to analyze
            prompt_version: Optional specific prompt version to use (for A/B testing)
            
        Returns:
            Dict with summary, policy_type, and metadata
        """
        try:
            # Get versioned prompt from registry
            prompt_obj = self._prompt_registry.get_prompt(PromptCategory.SUMMARY, version=prompt_version)
            if not prompt_obj:
                logger.error("Summary prompt not found in registry")
                return {"simple_summary": "Prompt configuration error.", "error": "Prompt not found"}
            
            system_prompt = prompt_obj.system_prompt
            prompt = self._prompt_registry.format_prompt(
                PromptCategory.SUMMARY,
                version=prompt_version,
                text=text[:3500]
            )
            
            if not prompt:
                logger.error("Failed to format summary prompt")
                return {"simple_summary": "Prompt formatting error.", "error": "Format failed"}
            
            # Log prompt version for audit trail
            logger.info(
                "Generating summary",
                prompt_version=prompt_obj.version,
                text_length=len(text)
            )

            response = self._generate(prompt, system=system_prompt, max_tokens=800)
            
            # Parse JSON response
            import json
            import re
            try:
                parsed = json.loads(response)
            except json.JSONDecodeError:
                # Fallback: extract JSON from response
                json_match = re.search(r'\{.*\}', response, re.DOTALL)
                if json_match:
                    parsed = json.loads(json_match.group(0))
                else:
                    raise ValueError("No valid JSON in response")
            
            # Build specific summary from extracted data
            summary_parts = []
            
            # Add specific amounts if found
            if parsed.get("sum_insured_amount") and parsed["sum_insured_amount"] != "Not mentioned":
                summary_parts.append(f"Sum Insured: {parsed['sum_insured_amount']}")
            
            if parsed.get("premium_amount") and parsed["premium_amount"] != "Not mentioned":
                summary_parts.append(f"Premium: {parsed['premium_amount']}")
            
            # Add policy number if found
            policy_num = parsed.get("policy_number", "")
            if policy_num and policy_num != "Not mentioned":
                summary_parts.append(f"Policy #{policy_num}")
            
            # Add coverage summary
            coverage_items = parsed.get("coverage_items", [])
            if coverage_items:
                summary_parts.append(f"Covers: {', '.join(coverage_items[:3])}")
            
            # Build final summary
            specific_summary = parsed.get("summary", "")
            if summary_parts:
                specific_summary = " | ".join(summary_parts) + ". " + specific_summary
            
            # Detect policy type as fallback
            policy_type = parsed.get("policy_type", self._detect_policy_type(text))
            
            # Get IRDAI context
            kb_info = self.INSURANCE_KNOWLEDGE_BASE.get(policy_type, {})
            
            return {
                "simple_summary": specific_summary or "Unable to extract specific policy details.",
                "policy_type": policy_type,
                "irdai_guidelines": kb_info.get("irdai_guidelines", ""),
                "key_regulations": kb_info.get("key_regulations", []),
                "confidence": parsed.get("confidence", 0.85),
                "model": self.model_name,
                "prompt_version": prompt_obj.version,  # Track which prompt version was used
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Summary generation failed: {e}")
            return {
                "simple_summary": "Unable to analyze document. Please ensure it contains insurance policy information.",
                "error": str(e),
                "policy_type": "general"
            }
    
    def extract_terms_with_explanations(self, text: str, prompt_version: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Extract insurance terms WITH their actual values from the document.
        
        Args:
            text: Insurance document text
            prompt_version: Optional specific prompt version (for A/B testing)
            
        Returns:
            List of term dictionaries with term, definition, example
        """
        try:
            # Get versioned prompt from registry
            prompt_obj = self._prompt_registry.get_prompt(PromptCategory.TERMS_EXTRACTION, version=prompt_version)
            if not prompt_obj:
                logger.error("Terms extraction prompt not found")
                return []
            
            system_prompt = prompt_obj.system_prompt
            prompt = self._prompt_registry.format_prompt(
                PromptCategory.TERMS_EXTRACTION,
                version=prompt_version,
                text=text[:2500]
            )
            
            if not prompt:
                logger.error("Failed to format terms prompt")
                return []
            
            logger.info(
                "Extracting terms",
                prompt_version=prompt_obj.version,
                text_length=len(text)
            )
            
            response = self._generate(prompt, system=system_prompt, max_tokens=800)
            
            # Parse JSON
            import json
            import re
            try:
                terms = json.loads(response)
            except json.JSONDecodeError:
                match = re.search(r'\[.*\]', response, re.DOTALL)
                if match:
                    terms = json.loads(match.group(0))
                else:
                    logger.warning("No valid JSON in terms response")
                    return []
            
            # Normalize structure for frontend
            normalized = []
            for item in terms[:8]:
                if isinstance(item, dict):
                    term_name = str(item.get("term", "")).strip()
                    term_value = str(item.get("value", item.get("definition", ""))).strip()
                    context = str(item.get("context", "")).strip()
                    
                    if term_name and term_value:
                        normalized.append({
                            "term": term_name,
                            "definition": f"{term_value}" + (f" - {context}" if context else ""),
                            "example": ""
                        })
            
            return normalized
            
        except Exception as e:
            logger.error(f"Term extraction failed: {e}")
            return []
    
    def identify_exclusions(self, text: str, prompt_version: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Identify policy exclusions using JSON schema.
        
        Args:
            text: Insurance document text
            prompt_version: Optional specific prompt version (for A/B testing)
            
        Returns:
            List of exclusion dictionaries
        """
        try:
            # Get versioned prompt from registry
            prompt_obj = self._prompt_registry.get_prompt(PromptCategory.EXCLUSIONS, version=prompt_version)
            if not prompt_obj:
                logger.error("Exclusions prompt not found")
                return []
            
            system_prompt = prompt_obj.system_prompt
            prompt = self._prompt_registry.format_prompt(
                PromptCategory.EXCLUSIONS,
                version=prompt_version,
                text=text[:2000]
            )
            
            if not prompt:
                logger.error("Failed to format exclusions prompt")
                return []
            
            logger.info(
                "Identifying exclusions",
                prompt_version=prompt_obj.version,
                text_length=len(text)
            )
            
            response = self._generate(prompt, system=system_prompt, max_tokens=600)
            
            # Parse JSON
            import json
            import re
            try:
                exclusions = json.loads(response)
            except json.JSONDecodeError:
                match = re.search(r'\[.*\]', response, re.DOTALL)
                if match:
                    exclusions = json.loads(match.group(0))
                else:
                    return []
            
            # Normalize
            normalized = []
            for item in exclusions[:6]:
                if isinstance(item, dict):
                    normalized.append({
                        "exclusion": str(item.get("exclusion", "")).strip(),
                        "explanation": str(item.get("explanation", "")).strip(),
                        "impact": ""
                    })
            
            return [e for e in normalized if e["exclusion"]]
            
        except Exception as e:
            logger.error(f"Exclusion extraction failed: {e}")
            return []
    
    def extract_coverage_details(self, text: str) -> Dict[str, Any]:
        """Extract coverage amounts and limits"""
        coverage = {}
        
        # Extract common coverage patterns
        patterns = {
            "sum_insured": r'sum\s+insured[:\s]+₹?\s*([\d,]+)',
            "coverage_amount": r'coverage[:\s]+₹?\s*([\d,]+)',
            "premium": r'premium[:\s]+₹?\s*([\d,]+)',
            "room_rent": r'room\s+rent[:\s]+₹?\s*([\d,]+)',
            "maternity": r'maternity[:\s]+₹?\s*([\d,]+)',
            "deductible": r'deductible[:\s]+₹?\s*([\d,]+)'
        }
        
        text_lower = text.lower()
        for key, pattern in patterns.items():
            match = re.search(pattern, text_lower, re.IGNORECASE)
            if match:
                coverage[key] = f"₹{match.group(1)}"
        
        return coverage
    
    def answer_question(self, context: str, question: str, prompt_version: Optional[str] = None) -> str:
        """
        Answer user questions about policy using provided context.
        
        Args:
            context: Policy document context
            question: User's question
            prompt_version: Optional specific prompt version (for A/B testing)
            
        Returns:
            Answer string
        """
        try:
            # Get versioned prompt from registry
            prompt_obj = self._prompt_registry.get_prompt(PromptCategory.QA, version=prompt_version)
            if not prompt_obj:
                logger.error("QA prompt not found")
                return "Configuration error. Please try again."
            
            system_prompt = prompt_obj.system_prompt
            prompt = self._prompt_registry.format_prompt(
                PromptCategory.QA,
                version=prompt_version,
                context=context[:3000],
                question=question
            )
            
            if not prompt:
                logger.error("Failed to format QA prompt")
                return "Error processing your question."
            
            logger.info(
                "Answering question",
                prompt_version=prompt_obj.version,
                question_length=len(question)
            )
            
            response = self._generate(prompt, system=system_prompt, max_tokens=500)
            return response.strip()
            
        except Exception as e:
            logger.error(f"Question answering failed: {e}")
            return "I encountered an error processing your question. Please try rephrasing it."
    

    
    def _detect_policy_type(self, text: str) -> str:
        """Detect type of insurance policy"""
        text_lower = text.lower()
        
        if any(term in text_lower for term in ['health', 'medical', 'hospitalization', 'disease']):
            return 'health_insurance'
        elif any(term in text_lower for term in ['life', 'death', 'mortality', 'beneficiary']):
            return 'life_insurance'
        elif any(term in text_lower for term in ['vehicle', 'motor', 'car', 'bike', 'accident']):
            return 'motor_insurance'
        else:
            return 'general_insurance'
    
    def _parse_terms_from_response(self, response: str) -> List[Dict[str, Any]]:
        """Parse terms from LLM response"""
        terms = []
        
        # Split by lines and look for term patterns
        lines = response.split('\n')
        for line in lines:
            if '|' in line or ':' in line:
                parts = re.split(r'[:|]', line)
                if len(parts) >= 2:
                    term_name = parts[0].replace('Term', '').strip()
                    explanation = parts[1].replace('Explanation', '').strip() if len(parts) > 1 else ""
                    example = parts[2].replace('Example', '').strip() if len(parts) > 2 else ""
                    
                    if term_name and len(term_name) < 50:
                        terms.append({
                            "term": term_name,
                            "simple_explanation": explanation,
                            "example": example,
                            "importance": "MEDIUM",
                            "found_in_document": True
                        })
        
        return terms
    
    def _parse_exclusions_from_response(self, response: str) -> List[Dict[str, Any]]:
        """Parse exclusions from LLM response"""
        exclusions = []
        
        lines = response.split('\n')
        for line in lines:
            if '|' in line or 'exclusion' in line.lower():
                parts = re.split(r'[:|]', line)
                if len(parts) >= 2:
                    exclusion = parts[0].replace('Exclusion', '').strip()
                    impact = parts[1].replace('Impact', '').strip() if len(parts) > 1 else ""
                    example = parts[2].replace('Example', '').strip() if len(parts) > 2 else ""
                    
                    if exclusion and len(exclusion) < 100:
                        exclusions.append({
                            "exclusion": exclusion,
                            "explanation": impact,
                            "example": example
                        })
        
        # If parsing fails, create from plain text
        if not exclusions and response:
            exclusion_items = [line.strip() for line in lines if line.strip() and len(line.strip()) > 10]
            exclusions = [{"exclusion": item, "explanation": "", "example": ""} for item in exclusion_items[:10]]
        
        return exclusions

    def analyze_policy(self, text: str) -> Dict[str, Any]:
        """
        Orchestrate complete policy analysis:
        1. Summary
        2. Terms
        3. Exclusions
        4. Coverage
        """
        try:
            # 1. Generate Summary & Type
            summary_data = self.generate_intelligent_summary(text)
            
            # 2. Extract Terms
            terms = self.extract_terms_with_explanations(text)
            
            # 3. Identify Exclusions
            exclusions = self.identify_exclusions(text)
            
            # 4. Extract Coverage
            coverage = self.extract_coverage_details(text)
            
            # Combine all data
            return {
                "summary": summary_data.get("simple_summary", ""),
                "type": summary_data.get("policy_type", "general"),
                "irdai_guidelines": summary_data.get("irdai_guidelines", ""),
                "key_terms": terms,
                "exclusions": exclusions,
                "coverage_details": coverage,
                "status": "success"
            }
            
        except Exception as e:
            logger.error(f"Full policy analysis failed: {e}")
            return {
                "summary": "Analysis failed due to an internal error.",
                "status": "error",
                "error": str(e)
            }
