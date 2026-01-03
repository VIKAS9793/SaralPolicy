"""
RAG Evaluation Service for SaralPolicy
Uses RAGAS (Retrieval Augmented Generation Assessment) for evaluation.

RAGAS is an open-source framework (Apache 2.0) for evaluating RAG pipelines.
GitHub: https://github.com/explodinggradients/ragas (7k+ stars)

Per Engineering Constitution Section 4.5:
- Ground techniques in research papers or official docs
- Define evaluation and rollback strategies

This service provides:
1. Context Relevancy - How relevant is the retrieved context to the question
2. Answer Relevancy - How relevant is the answer to the question
3. Faithfulness - Is the answer grounded in the context (hallucination detection)
4. Context Precision - Are the relevant items ranked higher

Note: RAGAS can work with local LLMs via LangChain's Ollama integration.
"""

import os
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
import structlog

logger = structlog.get_logger(__name__)

# Check if RAGAS is available
RAGAS_AVAILABLE = False
try:
    from ragas import evaluate
    from ragas.metrics import (
        faithfulness,
        answer_relevancy,
        context_precision,
        context_recall,
    )
    from datasets import Dataset
    RAGAS_AVAILABLE = True
    logger.info("RAGAS evaluation framework available")
except ImportError:
    logger.warning(
        "RAGAS not installed. Install with: pip install ragas datasets",
        fallback="Using heuristic-based evaluation"
    )


@dataclass
class RAGEvaluationResult:
    """Result of RAG evaluation."""
    faithfulness_score: float
    answer_relevancy_score: float
    context_precision_score: float
    context_recall_score: float
    overall_score: float
    is_hallucination_risk: bool
    evaluation_method: str  # "ragas" or "heuristic"
    details: Dict[str, Any]


class RAGEvaluationService:
    """
    Service for evaluating RAG pipeline outputs using RAGAS.
    
    RAGAS Metrics:
    - Faithfulness: Measures if the answer is grounded in the context
    - Answer Relevancy: Measures if the answer addresses the question
    - Context Precision: Measures if relevant context is ranked higher
    - Context Recall: Measures if all relevant info is retrieved
    
    Fallback: If RAGAS is not installed, uses heuristic-based evaluation.
    """
    
    def __init__(self, ollama_model: str = "gemma2:2b"):
        """
        Initialize RAG evaluation service.
        
        Args:
            ollama_model: Ollama model to use for evaluation (same as main LLM)
        """
        self.ollama_model = ollama_model
        self.ragas_available = RAGAS_AVAILABLE
        
        # Thresholds for quality assessment
        # Rationale: Based on RAGAS documentation and empirical testing
        # Faithfulness < 0.7 indicates potential hallucination
        self.faithfulness_threshold = 0.7
        self.relevancy_threshold = 0.6
        self.precision_threshold = 0.5
        
        if self.ragas_available:
            self._setup_ragas()
        
        logger.info(
            "RAG evaluation service initialized",
            ragas_available=self.ragas_available,
            model=ollama_model
        )
    
    def _setup_ragas(self):
        """Setup RAGAS with Ollama LLM."""
        try:
            # Use langchain-ollama package (updated, non-deprecated)
            from langchain_ollama import OllamaLLM, OllamaEmbeddings
            
            self.llm = OllamaLLM(model=self.ollama_model)
            self.embeddings = OllamaEmbeddings(model="nomic-embed-text")
            
            logger.info("RAGAS configured with Ollama backend (langchain-ollama)")
        except ImportError:
            try:
                # Fallback to langchain_community (deprecated but functional)
                from langchain_community.llms import Ollama
                from langchain_community.embeddings import OllamaEmbeddings
                
                self.llm = Ollama(model=self.ollama_model)
                self.embeddings = OllamaEmbeddings(model="nomic-embed-text")
                
                logger.warning(
                    "Using deprecated langchain_community.llms.Ollama",
                    recommendation="pip install langchain-ollama"
                )
            except ImportError:
                logger.warning(
                    "LangChain Ollama not available for RAGAS",
                    fallback="RAGAS will use default LLM (may require API key)"
                )
                self.llm = None
                self.embeddings = None
    
    def evaluate_rag_response(
        self,
        question: str,
        answer: str,
        contexts: List[str],
        ground_truth: Optional[str] = None
    ) -> RAGEvaluationResult:
        """
        Evaluate a RAG response using RAGAS metrics.
        
        Args:
            question: User's question
            answer: Generated answer
            contexts: Retrieved context chunks
            ground_truth: Optional ground truth answer for comparison
            
        Returns:
            RAGEvaluationResult with scores and hallucination risk assessment
        """
        if self.ragas_available and self.llm:
            return self._evaluate_with_ragas(question, answer, contexts, ground_truth)
        else:
            return self._evaluate_with_heuristics(question, answer, contexts)
    
    def _evaluate_with_ragas(
        self,
        question: str,
        answer: str,
        contexts: List[str],
        ground_truth: Optional[str] = None
    ) -> RAGEvaluationResult:
        """Evaluate using RAGAS framework."""
        try:
            # Prepare dataset for RAGAS
            data = {
                "question": [question],
                "answer": [answer],
                "contexts": [contexts],
            }
            
            if ground_truth:
                data["ground_truth"] = [ground_truth]
            
            dataset = Dataset.from_dict(data)
            
            # Select metrics based on available data
            metrics = [faithfulness, answer_relevancy, context_precision]
            if ground_truth:
                metrics.append(context_recall)
            
            # Run evaluation
            result = evaluate(
                dataset,
                metrics=metrics,
                llm=self.llm,
                embeddings=self.embeddings
            )
            
            # Extract scores
            faithfulness_score = result.get("faithfulness", 0.0)
            relevancy_score = result.get("answer_relevancy", 0.0)
            precision_score = result.get("context_precision", 0.0)
            recall_score = result.get("context_recall", 0.0) if ground_truth else 0.0
            
            # Calculate overall score
            overall_score = (
                faithfulness_score * 0.4 +
                relevancy_score * 0.3 +
                precision_score * 0.2 +
                recall_score * 0.1
            )
            
            # Determine hallucination risk
            is_hallucination_risk = faithfulness_score < self.faithfulness_threshold
            
            logger.info(
                "RAGAS evaluation completed",
                faithfulness=faithfulness_score,
                relevancy=relevancy_score,
                precision=precision_score,
                is_hallucination_risk=is_hallucination_risk
            )
            
            return RAGEvaluationResult(
                faithfulness_score=faithfulness_score,
                answer_relevancy_score=relevancy_score,
                context_precision_score=precision_score,
                context_recall_score=recall_score,
                overall_score=overall_score,
                is_hallucination_risk=is_hallucination_risk,
                evaluation_method="ragas",
                details={
                    "raw_scores": dict(result),
                    "thresholds": {
                        "faithfulness": self.faithfulness_threshold,
                        "relevancy": self.relevancy_threshold,
                        "precision": self.precision_threshold
                    }
                }
            )
            
        except Exception as e:
            logger.error("RAGAS evaluation failed, falling back to heuristics", error=str(e))
            return self._evaluate_with_heuristics(question, answer, contexts)
    
    def _evaluate_with_heuristics(
        self,
        question: str,
        answer: str,
        contexts: List[str]
    ) -> RAGEvaluationResult:
        """
        Fallback heuristic-based evaluation when RAGAS is not available.
        
        ⚠️ WARNING: This is a simple heuristic, not a validated metric.
        """
        try:
            # Combine contexts
            context_text = " ".join(contexts)
            
            # Faithfulness: Word overlap between answer and context
            faithfulness_score = self._calculate_word_overlap(answer, context_text)
            
            # Answer relevancy: Word overlap between answer and question
            relevancy_score = self._calculate_word_overlap(answer, question)
            
            # Context precision: How much of context is used in answer
            precision_score = self._calculate_context_usage(answer, contexts)
            
            # Overall score
            overall_score = (
                faithfulness_score * 0.4 +
                relevancy_score * 0.3 +
                precision_score * 0.3
            )
            
            # Hallucination risk
            is_hallucination_risk = faithfulness_score < self.faithfulness_threshold
            
            logger.info(
                "Heuristic evaluation completed",
                faithfulness=faithfulness_score,
                relevancy=relevancy_score,
                precision=precision_score,
                is_hallucination_risk=is_hallucination_risk
            )
            
            return RAGEvaluationResult(
                faithfulness_score=faithfulness_score,
                answer_relevancy_score=relevancy_score,
                context_precision_score=precision_score,
                context_recall_score=0.0,  # Cannot calculate without ground truth
                overall_score=overall_score,
                is_hallucination_risk=is_hallucination_risk,
                evaluation_method="heuristic",
                details={
                    "warning": "Using heuristic evaluation - install RAGAS for better accuracy",
                    "install_command": "pip install ragas datasets langchain-community"
                }
            )
            
        except Exception as e:
            logger.error("Heuristic evaluation failed", error=str(e))
            return RAGEvaluationResult(
                faithfulness_score=0.0,
                answer_relevancy_score=0.0,
                context_precision_score=0.0,
                context_recall_score=0.0,
                overall_score=0.0,
                is_hallucination_risk=True,
                evaluation_method="error",
                details={"error": str(e)}
            )
    
    def _calculate_word_overlap(self, text1: str, text2: str) -> float:
        """Calculate word overlap ratio between two texts."""
        if not text1 or not text2:
            return 0.0
        
        # Tokenize and normalize
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())
        
        # Remove stop words
        stop_words = {'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been',
                     'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will',
                     'would', 'could', 'should', 'may', 'might', 'must', 'shall',
                     'can', 'to', 'of', 'in', 'for', 'on', 'with', 'at', 'by',
                     'from', 'as', 'into', 'through', 'and', 'but', 'or', 'if'}
        
        words1 = words1 - stop_words
        words2 = words2 - stop_words
        
        if not words1:
            return 0.0
        
        overlap = len(words1.intersection(words2))
        return min(overlap / len(words1), 1.0)
    
    def _calculate_context_usage(self, answer: str, contexts: List[str]) -> float:
        """Calculate how much of the context is used in the answer."""
        if not answer or not contexts:
            return 0.0
        
        answer_words = set(answer.lower().split())
        
        # Check each context chunk
        used_contexts = 0
        for context in contexts:
            context_words = set(context.lower().split())
            overlap = len(answer_words.intersection(context_words))
            if overlap > 3:  # At least 3 words overlap
                used_contexts += 1
        
        return used_contexts / len(contexts) if contexts else 0.0
    
    def batch_evaluate(
        self,
        evaluations: List[Dict[str, Any]]
    ) -> List[RAGEvaluationResult]:
        """
        Batch evaluate multiple RAG responses.
        
        Args:
            evaluations: List of dicts with question, answer, contexts
            
        Returns:
            List of RAGEvaluationResult
        """
        results = []
        for eval_data in evaluations:
            result = self.evaluate_rag_response(
                question=eval_data.get("question", ""),
                answer=eval_data.get("answer", ""),
                contexts=eval_data.get("contexts", []),
                ground_truth=eval_data.get("ground_truth")
            )
            results.append(result)
        
        return results
    
    def get_evaluation_summary(self, results: List[RAGEvaluationResult]) -> Dict[str, Any]:
        """
        Get summary statistics for batch evaluation results.
        
        Args:
            results: List of RAGEvaluationResult
            
        Returns:
            Summary statistics
        """
        if not results:
            return {"error": "No results to summarize"}
        
        faithfulness_scores = [r.faithfulness_score for r in results]
        relevancy_scores = [r.answer_relevancy_score for r in results]
        overall_scores = [r.overall_score for r in results]
        hallucination_count = sum(1 for r in results if r.is_hallucination_risk)
        
        return {
            "total_evaluations": len(results),
            "average_faithfulness": sum(faithfulness_scores) / len(faithfulness_scores),
            "average_relevancy": sum(relevancy_scores) / len(relevancy_scores),
            "average_overall": sum(overall_scores) / len(overall_scores),
            "hallucination_risk_count": hallucination_count,
            "hallucination_risk_rate": hallucination_count / len(results),
            "evaluation_method": results[0].evaluation_method if results else "unknown"
        }


# Singleton instance
_rag_eval_service: Optional[RAGEvaluationService] = None


def get_rag_evaluation_service() -> RAGEvaluationService:
    """Get or create the RAG evaluation service singleton."""
    global _rag_eval_service
    if _rag_eval_service is None:
        model = os.environ.get("OLLAMA_MODEL", "gemma2:2b")
        _rag_eval_service = RAGEvaluationService(ollama_model=model)
    return _rag_eval_service
