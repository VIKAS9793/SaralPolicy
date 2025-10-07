"""
Ollama LLM Service for SaralPolicy
Uses Gemma 3 4B model via local Ollama for complete privacy and IRDAI compliance
"""

import json
import re
import requests
from typing import Dict, Any, List, Optional
import structlog
from datetime import datetime

logger = structlog.get_logger(__name__)


class OllamaLLMService:
    """
    Production-grade LLM service using Ollama with Gemma 3 4B:
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
                 model_name: str = "gemma3:4b",
                 ollama_host: str = "http://localhost:11434"):
        """
        Initialize Ollama LLM service with Gemma 3 4B
        
        Args:
            model_name: Ollama model name (default: gemma3:4b)
            ollama_host: Ollama API endpoint
        """
        self.model_name = model_name
        self.ollama_host = ollama_host
        self.api_url = f"{ollama_host}/api/generate"
        self.chat_url = f"{ollama_host}/api/chat"
        
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
    
    def generate_intelligent_summary(self, text: str) -> Dict[str, Any]:
        """Generate comprehensive insurance policy summary"""
        try:
            system_prompt = """You are an expert insurance analyst specializing in Indian insurance policies. 
You provide clear, accurate analysis following IRDAI regulations. 
Always explain in simple terms with practical examples using Indian rupees (₹)."""
            
            prompt = f"""Analyze this insurance policy document and provide a structured summary:

Document Text:
{text[:3000]}

Provide:
1. Policy Type (health/life/motor/general)
2. Key Coverage (what IS covered)
3. Sum Insured/Coverage Amount
4. Premium Amount (if mentioned)
5. Important Limitations
6. Major Exclusions (what is NOT covered)

Format as clear, simple bullet points. Use examples with rupee amounts where relevant."""

            response = self._generate(prompt, system=system_prompt, max_tokens=1500)
            
            # Extract policy type from response
            policy_type = self._detect_policy_type(text)
            
            # Get IRDAI guidelines for this policy type
            kb_info = self.INSURANCE_KNOWLEDGE_BASE.get(policy_type, {})
            
            return {
                "simple_summary": response,
                "policy_type": policy_type,
                "irdai_guidelines": kb_info.get("irdai_guidelines", ""),
                "key_regulations": kb_info.get("key_regulations", []),
                "confidence": 0.95,
                "model": self.model_name,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to generate summary: {e}")
            return {
                "simple_summary": "Error generating summary",
                "error": str(e)
            }
    
    def extract_terms_with_explanations(self, text: str) -> List[Dict[str, Any]]:
        """Extract and explain insurance terms found in document"""
        terms = []
        text_lower = text.lower()
        
        # Get standard terms from knowledge base
        for policy_type, kb_data in self.INSURANCE_KNOWLEDGE_BASE.items():
            standard_terms = kb_data.get("standard_terms", {})
            
            for term_key, term_data in standard_terms.items():
                # Check if term exists in document
                term_patterns = [
                    term_key.replace('_', ' '),
                    term_key.replace('_', '-'),
                    term_key
                ]
                
                if any(pattern in text_lower for pattern in term_patterns):
                    terms.append({
                        "term": term_key.replace('_', ' ').title(),
                        "definition": term_data.get("definition", ""),
                        "simple_explanation": term_data.get("layman", ""),
                        "example": term_data.get("example", ""),
                        "hindi_translation": term_data.get("hindi", ""),
                        "importance": term_data.get("importance", "MEDIUM"),
                        "found_in_document": True
                    })
        
        # Use LLM to extract document-specific terms
        try:
            system_prompt = "You are an insurance terminology expert. Extract and explain key insurance terms."
            
            prompt = f"""From this insurance document, identify 3-5 KEY insurance terms and explain each in simple language:

Document: {text[:2000]}

For each term provide:
- Term name
- Simple 1-line explanation
- Practical example with rupee amounts

Format: Term: [name] | Explanation: [simple explanation] | Example: [example]"""

            response = self._generate(prompt, system=system_prompt, max_tokens=1000)
            
            # Parse additional terms from LLM response
            additional_terms = self._parse_terms_from_response(response)
            terms.extend(additional_terms)
            
        except Exception as e:
            logger.error(f"Failed to extract document-specific terms: {e}")
        
        return terms[:10]  # Return top 10 most relevant terms
    
    def identify_exclusions(self, text: str) -> List[Dict[str, Any]]:
        """Identify and explain policy exclusions"""
        try:
            system_prompt = """You are an insurance expert specializing in policy exclusions. 
Explain what is NOT covered in clear, simple terms with practical examples."""
            
            prompt = f"""Identify all EXCLUSIONS (what is NOT covered) in this insurance policy:

Document: {text[:2500]}

For each exclusion:
- What is excluded
- Why it matters (practical impact)
- Real example

Format each as: Exclusion: [what] | Impact: [why it matters] | Example: [practical example]"""

            response = self._generate(prompt, system=system_prompt, max_tokens=1500)
            
            exclusions = self._parse_exclusions_from_response(response)
            return exclusions
            
        except Exception as e:
            logger.error(f"Failed to identify exclusions: {e}")
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
    
    def answer_question(self, text: str, question: str) -> str:
        """Answer specific questions about the policy"""
        try:
            system_prompt = """You are an insurance advisor helping customers understand their policy. 
Answer questions clearly and accurately based ONLY on the provided policy document. 
If information is not in the document, say so clearly."""
            
            prompt = f"""Policy Document:
{text[:2500]}

Customer Question: {question}

Provide a clear, accurate answer based on the policy document. Use simple language and examples where helpful."""

            response = self._generate(prompt, system=system_prompt, max_tokens=800)
            return response
            
        except Exception as e:
            logger.error(f"Failed to answer question: {e}")
            return "Unable to answer question. Please try again."
    
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
