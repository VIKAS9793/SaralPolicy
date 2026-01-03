
import time
import structlog
from typing import Dict, Any, List, Optional
from enum import Enum
from dataclasses import dataclass

# Import Services
from app.services.ollama_llm_service import OllamaLLMService
from app.services.rag_service import RAGService
from app.services.hitl_service import HITLService
from app.services.guardrails_service import GuardrailsService
from app.services.evaluation import EvaluationManager
from app.services.translation_service import TranslationService
from app.services.tts_service import TTSService

logger = structlog.get_logger(__name__)


class ServiceMode(str, Enum):
    """
    Operating modes for graceful degradation.
    
    Design Rationale:
    -----------------
    Graceful degradation allows the system to continue providing value
    even when some components are unavailable. This follows the principle
    that partial functionality is better than complete failure.
    
    Modes:
    - FULL: All services operational (LLM + RAG + IRDAI KB)
    - DEGRADED_NO_RAG: LLM works but RAG unavailable (no citations)
    - DEGRADED_NO_IRDAI: LLM + RAG work but IRDAI KB unavailable
    - MINIMAL: Only basic text processing (no LLM)
    - OFFLINE: System unavailable
    """
    FULL = "full"
    DEGRADED_NO_RAG = "degraded_no_rag"
    DEGRADED_NO_IRDAI = "degraded_no_irdai"
    MINIMAL = "minimal"
    OFFLINE = "offline"


@dataclass
class DegradedModeInfo:
    """Information about current degraded mode for user notification."""
    mode: ServiceMode
    available_features: List[str]
    unavailable_features: List[str]
    user_message: str


class PolicyService:
    """
    Service for Policy Analysis Orchestration.
    Coordinates: LLM, RAG, Guardrails, HITL, Translation, TTS.
    
    Graceful Degradation:
    ---------------------
    This service implements graceful degradation to maintain partial
    functionality when dependencies are unavailable:
    
    1. LLM unavailable → Return cached/template responses
    2. RAG unavailable → Use direct text search, no citations
    3. IRDAI KB unavailable → Skip regulatory context
    
    The service tracks its operating mode and notifies users of
    reduced functionality.
    """

    def __init__(
        self,
        ollama_service: Optional[OllamaLLMService],
        rag_service: RAGService,
        guardrails_service: GuardrailsService,
        hitl_service: HITLService,
        eval_manager: EvaluationManager,
        translation_service: TranslationService,
        tts_service: TTSService
    ):
        self.ollama_service = ollama_service
        self.rag_service = rag_service
        self.guardrails_service = guardrails_service
        self.hitl_service = hitl_service
        self.eval_manager = eval_manager
        self.translation_service = translation_service
        self.tts_service = tts_service
        
        # Graceful degradation state
        self._current_mode: ServiceMode = ServiceMode.FULL
        self._last_mode_check: float = 0
        self._mode_check_interval: float = 30.0  # Re-check every 30 seconds
    
    def get_service_mode(self, force_check: bool = False) -> DegradedModeInfo:
        """
        Determine current service operating mode.
        
        Checks availability of all dependencies and returns the
        appropriate degraded mode with user-friendly messaging.
        
        Args:
            force_check: Force re-check even if within interval
            
        Returns:
            DegradedModeInfo with current mode and feature availability
        """
        current_time = time.time()
        
        # Use cached mode if within check interval
        if not force_check and (current_time - self._last_mode_check) < self._mode_check_interval:
            return self._get_mode_info(self._current_mode)
        
        self._last_mode_check = current_time
        
        # Check LLM availability
        llm_available = self.ollama_service is not None
        if llm_available:
            try:
                # Quick health check - just verify service exists
                llm_available = hasattr(self.ollama_service, 'analyze_policy')
            except Exception:
                llm_available = False
        
        # Check RAG availability
        rag_available = (
            self.rag_service is not None and 
            hasattr(self.rag_service, 'enabled') and 
            self.rag_service.enabled
        )
        
        # Check IRDAI KB availability (part of RAG)
        irdai_available = rag_available
        if rag_available:
            try:
                # Check if IRDAI collection has data
                stats = self.rag_service.get_stats()
                irdai_available = stats.get('irdai_indexed', False)
            except Exception:
                irdai_available = False
        
        # Determine mode based on availability
        if llm_available and rag_available and irdai_available:
            self._current_mode = ServiceMode.FULL
        elif llm_available and rag_available and not irdai_available:
            self._current_mode = ServiceMode.DEGRADED_NO_IRDAI
        elif llm_available and not rag_available:
            self._current_mode = ServiceMode.DEGRADED_NO_RAG
        elif not llm_available:
            self._current_mode = ServiceMode.MINIMAL
        else:
            self._current_mode = ServiceMode.OFFLINE
        
        logger.info(
            "Service mode determined",
            mode=self._current_mode.value,
            llm=llm_available,
            rag=rag_available,
            irdai=irdai_available
        )
        
        return self._get_mode_info(self._current_mode)
    
    def _get_mode_info(self, mode: ServiceMode) -> DegradedModeInfo:
        """Get detailed information about a service mode."""
        mode_configs = {
            ServiceMode.FULL: DegradedModeInfo(
                mode=ServiceMode.FULL,
                available_features=[
                    "AI-powered policy analysis",
                    "Document Q&A with citations",
                    "IRDAI regulatory context",
                    "Translation and TTS"
                ],
                unavailable_features=[],
                user_message="All features operational."
            ),
            ServiceMode.DEGRADED_NO_IRDAI: DegradedModeInfo(
                mode=ServiceMode.DEGRADED_NO_IRDAI,
                available_features=[
                    "AI-powered policy analysis",
                    "Document Q&A with citations",
                    "Translation and TTS"
                ],
                unavailable_features=[
                    "IRDAI regulatory context"
                ],
                user_message="Operating in degraded mode: IRDAI regulatory context unavailable. "
                            "Analysis will not include regulatory references."
            ),
            ServiceMode.DEGRADED_NO_RAG: DegradedModeInfo(
                mode=ServiceMode.DEGRADED_NO_RAG,
                available_features=[
                    "AI-powered policy analysis",
                    "Basic Q&A (no citations)",
                    "Translation and TTS"
                ],
                unavailable_features=[
                    "Document citations",
                    "IRDAI regulatory context"
                ],
                user_message="Operating in degraded mode: Citation system unavailable. "
                            "Answers will not include specific document references."
            ),
            ServiceMode.MINIMAL: DegradedModeInfo(
                mode=ServiceMode.MINIMAL,
                available_features=[
                    "Document upload and viewing",
                    "Basic text extraction"
                ],
                unavailable_features=[
                    "AI-powered analysis",
                    "Q&A functionality",
                    "IRDAI regulatory context"
                ],
                user_message="Operating in minimal mode: AI service unavailable. "
                            "Only basic document viewing is available. "
                            "Please try again later or contact support."
            ),
            ServiceMode.OFFLINE: DegradedModeInfo(
                mode=ServiceMode.OFFLINE,
                available_features=[],
                unavailable_features=["All features"],
                user_message="Service temporarily unavailable. Please try again later."
            )
        }
        return mode_configs.get(mode, mode_configs[ServiceMode.OFFLINE])

    def analyze_policy(self, text: str, pages: List[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Analyze insurance policy using Ollama LLM.
        Complete local processing with IRDAI compliance.
        
        Graceful Degradation:
        - If LLM unavailable: Returns minimal analysis with extracted text
        - If RAG unavailable: Skips document indexing, continues with LLM
        - If IRDAI KB unavailable: Skips regulatory context
        """
        # Track overall performance
        analysis_start = time.time()
        performance_metrics = {}
        
        # Check service mode and include in response
        mode_info = self.get_service_mode()
        
        try:
            logger.info(
                "🚀 Starting policy analysis",
                text_length=len(text),
                mode=mode_info.mode.value
            )
            
            # Apply guardrails first
            guardrails_result = self.guardrails_service.validate_input(text)
            if not guardrails_result["is_valid"]:
                return {
                    "error": f"Input validation failed: {guardrails_result['reason']}",
                    "status": "error",
                    "service_mode": mode_info.mode.value
                }
            
            # Handle MINIMAL mode (no LLM)
            if mode_info.mode == ServiceMode.MINIMAL:
                logger.warning("⚠️ Operating in MINIMAL mode - returning basic analysis")
                return self._get_minimal_analysis(text, mode_info)
            
            # Handle OFFLINE mode
            if mode_info.mode == ServiceMode.OFFLINE:
                return {
                    "error": mode_info.user_message,
                    "status": "error",
                    "service_mode": mode_info.mode.value
                }
            
            # Use Ollama LLM Service
            if self.ollama_service:
                try:
                    logger.info("⚙️ Using Ollama LLM service")
                    
                    # RAG Enhancement: Index document for session-based Q&A
                    # Skip if RAG unavailable (graceful degradation)
                    doc_id = f"policy_{hash(text[:100])}"  # Simple doc ID
                    if self.rag_service and self.rag_service.enabled:
                        rag_start = time.time()
                        logger.info("📚 Indexing document for RAG-enhanced Q&A")
                        
                        try:
                            self.rag_service.index_document(
                                text=pages if pages else text,
                                document_id=doc_id,
                                metadata={
                                    'title': 'User Policy Document',
                                    'policy_type': 'insurance',
                                    'section': 'General'
                                }
                            )
                            performance_metrics['rag_indexing_time'] = round(time.time() - rag_start, 2)
                        except Exception as e:
                            # RAG indexing failed - continue without it
                            logger.warning(
                                "RAG indexing failed - continuing without citations",
                                error=str(e)
                            )
                            performance_metrics['rag_indexing_error'] = str(e)[:100]
                    else:
                        logger.info("📚 RAG not available - skipping document indexing")
                    
                    start_llm = time.time()
                    analysis = self.ollama_service.analyze_policy(text)
                    performance_metrics['llm_latency'] = round(time.time() - start_llm, 2)
                    
                    if not analysis:
                         # Fallback if Ollama fails or returns empty
                         logger.warning("⚠️ Ollama returned empty analysis, using fallback structure")
                         return self._get_fallback_analysis_structure()

                    analysis['platform'] = 'local_ollama'
                    analysis['model'] = self.ollama_service.model_name
                except Exception as e:
                    logger.error(f"❌ Ollama analysis failed: {e}")
                    # Try minimal fallback instead of complete failure
                    if mode_info.mode in [ServiceMode.DEGRADED_NO_RAG, ServiceMode.DEGRADED_NO_IRDAI]:
                        return self._get_minimal_analysis(text, mode_info, error=str(e))
                    return self._get_fallback_analysis_structure_error(str(e))
            else:
                logger.error("❌ No LLM service available")
                return self._get_minimal_analysis(text, mode_info)
            
            # Post-process validation (HITL)
            hitl_result = self.hitl_service.check_analysis_quality(analysis, text)
            if hitl_result['requires_review']:
                analysis['review_flag'] = True
                analysis['review_reason'] = hitl_result['reason']
                logger.warning(f"⚠️ Analysis flagged for review: {hitl_result['reason']}")
            
            # Add performance metrics and mode info
            performance_metrics['total_time'] = round(time.time() - analysis_start, 2)
            analysis['metrics'] = performance_metrics
            analysis['status'] = "success"
            analysis['service_mode'] = mode_info.mode.value
            
            # Add degradation notice if not in full mode
            if mode_info.mode != ServiceMode.FULL:
                analysis['degradation_notice'] = mode_info.user_message
                analysis['unavailable_features'] = mode_info.unavailable_features
            
            return analysis
            
        except Exception as e:
            logger.error("Analysis failed", error=str(e))
            return {
                "error": str(e),
                "status": "error",
                "service_mode": mode_info.mode.value
            }
    
    def _get_minimal_analysis(
        self, 
        text: str, 
        mode_info: DegradedModeInfo,
        error: str = None
    ) -> Dict[str, Any]:
        """
        Return minimal analysis when LLM is unavailable.
        
        Extracts basic information from text without AI processing.
        """
        # Basic text statistics
        word_count = len(text.split())
        char_count = len(text)
        
        # Try to extract some basic patterns (policy number, dates, amounts)
        import re
        
        # Simple pattern matching for common policy elements
        policy_numbers = re.findall(r'[A-Z]{2,4}[/-]?\d{4,}[/-]?\d*', text[:2000])
        amounts = re.findall(r'Rs\.?\s*[\d,]+(?:\.\d{2})?', text[:5000])
        
        return {
            "summary": "AI analysis unavailable. Basic document information extracted.",
            "text_stats": {
                "word_count": word_count,
                "character_count": char_count
            },
            "extracted_patterns": {
                "possible_policy_numbers": policy_numbers[:5] if policy_numbers else [],
                "mentioned_amounts": amounts[:10] if amounts else []
            },
            "status": "partial",
            "service_mode": mode_info.mode.value,
            "degradation_notice": mode_info.user_message,
            "unavailable_features": mode_info.unavailable_features,
            "error": error
        }

    def answer_question(self, document_text: str, question: str) -> Dict[str, Any]:
        """
        Answer user questions about the policy using RAG + LLM.
        
        Graceful Degradation:
        - If LLM unavailable: Returns helpful error message
        - If RAG unavailable: Uses direct text search instead of vector search
        - If IRDAI KB unavailable: Skips regulatory context
        
        Returns: { "answer": str, "document_excerpts": [], "irdai_context": [], "confidence": float }
        """
        mode_info = self.get_service_mode()
        
        # Handle MINIMAL/OFFLINE modes
        if mode_info.mode in [ServiceMode.MINIMAL, ServiceMode.OFFLINE]:
            return {
                "answer": mode_info.user_message,
                "document_excerpts": [],
                "irdai_context": [],
                "confidence": 0.0,
                "service_mode": mode_info.mode.value,
                "degradation_notice": mode_info.user_message
            }
        
        if not self.ollama_service:
            return {
                "answer": "I apologize, but the AI service is currently unavailable. "
                         "Please try again later.",
                "document_excerpts": [],
                "irdai_context": [],
                "confidence": 0.0,
                "service_mode": ServiceMode.MINIMAL.value
            }
            
        try:
            # 1. RAG Retrieval (Document) - with fallback
            doc_context = []
            doc_excerpts = []
            rag_available = (
                self.rag_service and 
                hasattr(self.rag_service, 'enabled') and 
                self.rag_service.enabled
            )
            
            if rag_available:
                try:
                    results = self.rag_service.query_document(question, top_k=3)
                    if results:
                        for result in results:
                            doc_context.append(result['content'])
                            doc_excerpts.append({
                                "content": result['content'][:250] + "...",
                                "relevance": round(result['hybrid_score'], 3),
                                "page": result['metadata'].get('page_number', None)
                            })
                        logger.info(f"📚 Retrieved {len(results)} chunks from RAG")
                except Exception as e:
                    logger.warning(
                        "RAG document query failed - using fallback text search",
                        error=str(e)
                    )
                    # Fallback: Simple keyword search in document
                    doc_context, doc_excerpts = self._fallback_text_search(
                        document_text, question
                    )
            else:
                # RAG not available - use fallback text search
                logger.info("📚 RAG not available - using fallback text search")
                doc_context, doc_excerpts = self._fallback_text_search(
                    document_text, question
                )
            
            # 2. RAG Retrieval (IRDAI Knowledge Base - Optional)
            irdai_context_list = []
            irdai_text_list = []
            
            # Only try IRDAI KB if in FULL mode
            if mode_info.mode == ServiceMode.FULL and rag_available:
                try: 
                    kb_results = self.rag_service.query_knowledge_base(question, top_k=2)
                    for result in kb_results:
                        # Relevance threshold for IRDAI knowledge base results
                        # Rationale: 0.4 is a moderate threshold that filters out low-relevance
                        # results while still including partially relevant regulatory context.
                        # Lower than document search threshold (0.5) because regulatory context
                        # is valuable even with moderate relevance.
                        if result['hybrid_score'] >= 0.4:
                            irdai_item = {
                                "source": result['metadata'].get('source', 'IRDAI'),
                                "excerpt": result['content'][:200] + "...",
                                "relevance": round(result['hybrid_score'], 3)
                            }
                            irdai_context_list.append(irdai_item)
                            irdai_text_list.append(result['content'])
                except Exception as e:
                    # Log IRDAI KB query failure but continue - this is optional enhancement
                    logger.warning(
                        "IRDAI knowledge base query failed - continuing without regulatory context",
                        error=str(e),
                        question=question[:100]
                    )

            # 3. Construct Context
            full_context = ""
            if doc_context:
                full_context += "Your Policy Document:\n" + "\n\n".join(doc_context)
            else:
                full_context += "Policy Text:\n" + document_text[:2000]

            if irdai_text_list:
                full_context += "\n\nRelevant Regulations:\n" + "\n".join(irdai_text_list)

            # 4. Generate Answer
            answer = self.ollama_service.answer_question(
                context=full_context,
                question=question
            )
            
            # 5. Calculate Confidence Score
            # Initial heuristic: Average of top RAG relevance scores
            rag_scores = [d['relevance'] for d in doc_excerpts if 'relevance' in d]
            
            if rag_scores:
                avg_score = sum(rag_scores) / len(rag_scores)
                # Boost slighty as RAG scores > 0.4 are generally good
                confidence = min(max(avg_score * 1.5, 0.5), 0.98) 
            else:
                confidence = 0.5  # Base confidence without specific citations

            response = {
                "answer": answer,
                "document_excerpts": [
                    {
                        "text": d['content'], 
                        "page_num": d['page'], 
                        "confidence": d['relevance']
                    } for d in doc_excerpts
                ],
                "irdai_context": irdai_context_list,
                "confidence": round(confidence, 2),
                "service_mode": mode_info.mode.value
            }
            
            # Add degradation notice if not in full mode
            if mode_info.mode != ServiceMode.FULL:
                response['degradation_notice'] = mode_info.user_message
                response['unavailable_features'] = mode_info.unavailable_features
            
            return response

        except Exception as e:
            logger.error("Question answering failed", error=str(e))
            return {
                "answer": "I encountered an error while processing your question. "
                         "Please try rephrasing or try again later.",
                "document_excerpts": [],
                "irdai_context": [],
                "confidence": 0.0,
                "service_mode": mode_info.mode.value,
                "error": str(e)[:200]
            }
    
    def _fallback_text_search(
        self, 
        document_text: str, 
        question: str
    ) -> tuple[List[str], List[Dict[str, Any]]]:
        """
        Fallback text search when RAG is unavailable.
        
        Uses simple keyword matching to find relevant sections.
        """
        import re
        
        # Extract keywords from question (simple approach)
        stop_words = {'what', 'is', 'the', 'a', 'an', 'in', 'on', 'at', 'to', 'for', 
                     'of', 'and', 'or', 'my', 'your', 'this', 'that', 'how', 'when',
                     'where', 'why', 'can', 'does', 'do', 'are', 'was', 'were'}
        
        words = re.findall(r'\b\w+\b', question.lower())
        keywords = [w for w in words if w not in stop_words and len(w) > 2]
        
        if not keywords:
            return [], []
        
        # Split document into paragraphs
        paragraphs = re.split(r'\n\s*\n', document_text)
        
        # Score paragraphs by keyword matches
        scored_paragraphs = []
        for i, para in enumerate(paragraphs):
            if len(para.strip()) < 50:  # Skip very short paragraphs
                continue
            
            para_lower = para.lower()
            score = sum(1 for kw in keywords if kw in para_lower)
            
            if score > 0:
                scored_paragraphs.append({
                    'content': para[:500],
                    'score': score / len(keywords),
                    'index': i
                })
        
        # Sort by score and take top 3
        scored_paragraphs.sort(key=lambda x: x['score'], reverse=True)
        top_results = scored_paragraphs[:3]
        
        doc_context = [r['content'] for r in top_results]
        doc_excerpts = [
            {
                'content': r['content'][:250] + "...",
                'relevance': round(r['score'], 3),
                'page': None  # No page info in fallback mode
            }
            for r in top_results
        ]
        
        return doc_context, doc_excerpts

    def _get_fallback_analysis_structure(self) -> Dict[str, Any]:
        """Return a safe empty structure on failure."""
        return {
            "summary": "Analysis failed to generate.",
            "coverage_details": {},
            "exclusions": [],
            "status": "partial_error"
        }

    def _get_fallback_analysis_structure_error(self, error_msg: str) -> Dict[str, Any]:
        return {
            "error": error_msg,
            "status": "error"
        }
