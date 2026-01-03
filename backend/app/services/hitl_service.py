"""
Human-in-the-Loop (HITL) Service for SaralPolicy
Manages expert review and validation for low-confidence analyses.
Now uses database persistence instead of in-memory storage.

Data Structure Design Rationale:
================================

1. **Database Persistence (SQLite → PostgreSQL)**
   - Rationale: Data survives restarts, supports concurrent access, audit trail
   - Trade-off: Latency vs in-memory (~1-5ms per query, acceptable for HITL)
   - Migration path: SQLite for POC, PostgreSQL for production (same ORM)

2. **Session-per-Request Pattern**
   - Rationale: Thread safety, connection pooling, transaction isolation
   - Trade-off: Session creation overhead (~0.1ms, negligible)
   - Alternative considered: Global session (rejected for thread safety)

3. **Dictionary Returns (not ORM objects)**
   - Rationale: Serialization-ready, decoupled from ORM session lifecycle
   - Trade-off: Extra conversion step (to_dict())
   - Justification: API responses need JSON, not SQLAlchemy objects

4. **Threshold Configuration via Environment**
   - Rationale: Tunable without code changes, different per environment
   - Default: 0.85 confidence threshold (catches ~15% of analyses for review)
   - Tuning: Lower threshold = more reviews, higher quality; higher = fewer reviews

5. **Priority Calculation (confidence-based)**
   - HIGH: confidence < 0.5 (very unreliable, urgent)
   - MEDIUM: 0.5 <= confidence < 0.7 (questionable)
   - LOW: confidence >= 0.7 (minor issues)
   - Rationale: Triage experts' time toward highest-risk analyses

6. **Cleanup Strategy (30-day retention)**
   - Rationale: Balance audit needs vs storage growth
   - Configurable: days_old parameter in cleanup_old_reviews()
   - Growth estimate: ~100 reviews/day * 30 days * 10KB = 30MB (negligible)
"""

import uuid
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_, desc
import structlog

from app.models.hitl import (
    HITLReview, HITLFeedback,
    ReviewStatus, ReviewPriority, ReviewType, ValidationResult
)
from app.db.database import SessionLocal

logger = structlog.get_logger(__name__)


class HITLService:
    """
    Service for managing human-in-the-loop validation.
    Uses database persistence for production readiness.
    """
    
    def __init__(self, db: Optional[Session] = None):
        """
        Initialize HITL service.
        
        Args:
            db: Optional database session. If None, creates new session for each operation.
                For dependency injection in FastAPI, pass db from Depends(get_db).
        """
        self.db = db
        
        # HITL thresholds (configurable via environment)
        # Rationale: 0.85 threshold catches most low-confidence cases while avoiding
        # excessive review load. Tuned based on typical confidence distributions.
        import os
        self.confidence_threshold = float(os.environ.get("HITL_CONFIDENCE_THRESHOLD", "0.85"))
        self.max_pending_reviews = int(os.environ.get("MAX_PENDING_REVIEWS", "100"))
        
        logger.info(
            "HITL service initialized",
            confidence_threshold=self.confidence_threshold,
            max_pending_reviews=self.max_pending_reviews
        )
    
    def _get_db(self) -> Session:
        """Get database session (use provided or create new)."""
        if self.db:
            return self.db
        return SessionLocal()
    
    def _close_db(self, db: Session):
        """Close database session if we created it."""
        if not self.db:
            db.close()
    
    def check_analysis_quality(self, analysis: Dict[str, Any], text: str) -> Dict[str, Any]:
        """
        Check if analysis requires expert review based on confidence.
        
        Args:
            analysis: Analysis result dictionary
            text: Source text (for future use in quality checks)
            
        Returns:
            Dict with requires_review flag and reason
        """
        confidence = analysis.get("confidence", 0.95)
        
        if confidence < self.confidence_threshold:
            return {
                "requires_review": True,
                "reason": f"Low confidence score ({confidence:.2f} < {self.confidence_threshold})"
            }
        
        return {
            "requires_review": False,
            "reason": ""
        }
    
    def trigger_review(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """
        Trigger human review for low-confidence analysis.
        
        Args:
            analysis: Analysis result dictionary
            
        Returns:
            Dict with review_id and status
        """
        db = self._get_db()
        try:
            review_id = str(uuid.uuid4())
            confidence_score = analysis.get("confidence_score", analysis.get("confidence", 0.0))
            
            # Create review record
            review = HITLReview(
                review_id=review_id,
                review_type=ReviewType.ANALYSIS_REVIEW,
                status=ReviewStatus.PENDING,
                priority=self._calculate_priority(confidence_score),
                confidence_score=confidence_score,
                analysis_data=analysis,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            
            db.add(review)
            db.commit()
            
            logger.info(
                "HITL review triggered",
                review_id=review_id,
                confidence_score=confidence_score
            )
            
            return {
                "review_id": review_id,
                "status": "pending",
                "message": "Analysis flagged for expert review due to low confidence",
                "estimated_review_time": "2-4 hours"
            }
            
        except Exception as e:
            db.rollback()
            logger.error("Failed to trigger HITL review", error=str(e))
            return {
                "review_id": None,
                "status": "error",
                "message": f"Failed to trigger review: {str(e)}"
            }
        finally:
            self._close_db(db)
    
    def trigger_qa_review(self, question: str, answer: str, eval_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Trigger human review for Q&A responses.
        
        Args:
            question: User question
            answer: Generated answer
            eval_result: Evaluation results
            
        Returns:
            Dict with review_id and status
        """
        db = self._get_db()
        try:
            review_id = str(uuid.uuid4())
            confidence_score = eval_result.get("confidence_score", 0.0)
            
            # Create Q&A review record
            review = HITLReview(
                review_id=review_id,
                review_type=ReviewType.QA_REVIEW,
                status=ReviewStatus.PENDING,
                priority=self._calculate_priority(confidence_score),
                confidence_score=confidence_score,
                question=question,
                answer=answer,
                evaluation_data=eval_result,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            
            db.add(review)
            db.commit()
            
            logger.info(
                "HITL Q&A review triggered",
                review_id=review_id,
                confidence_score=confidence_score
            )
            
            return {
                "review_id": review_id,
                "status": "pending",
                "message": "Q&A response flagged for expert review"
            }
            
        except Exception as e:
            db.rollback()
            logger.error("Failed to trigger Q&A review", error=str(e))
            return {
                "review_id": None,
                "status": "error",
                "message": f"Failed to trigger Q&A review: {str(e)}"
            }
        finally:
            self._close_db(db)
    
    def submit_expert_feedback(
        self,
        review_id: str,
        feedback: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Submit expert feedback for a review.
        
        Args:
            review_id: Review identifier
            feedback: Feedback dictionary with expert_id, validation_result, notes, etc.
            
        Returns:
            Dict with status and message
        """
        db = self._get_db()
        try:
            # Get review
            review = db.query(HITLReview).filter(HITLReview.review_id == review_id).first()
            
            if not review:
                return {
                    "status": "error",
                    "message": "Review not found"
                }
            
            # Update review
            review.status = ReviewStatus.COMPLETED
            review.expert_id = feedback.get("expert_id", "anonymous")
            review.expert_notes = feedback.get("notes", feedback.get("expert_notes", ""))
            validation_result = feedback.get("validation_result", "approved")
            review.validation_result = ValidationResult(validation_result) if validation_result else None
            review.completed_at = datetime.utcnow()
            review.updated_at = datetime.utcnow()
            
            # Create feedback record
            feedback_record = HITLFeedback(
                feedback_id=str(uuid.uuid4()),
                review_id=review_id,
                expert_id=feedback.get("expert_id", "anonymous"),
                feedback_text=feedback.get("notes", feedback.get("feedback_text", "")),
                feedback_data=feedback,
                created_at=datetime.utcnow()
            )
            
            db.add(feedback_record)
            db.commit()
            
            logger.info(
                "Expert feedback submitted",
                review_id=review_id,
                validation_result=validation_result
            )
            
            return {
                "status": "success",
                "message": "Expert feedback submitted successfully",
                "review_id": review_id
            }
            
        except Exception as e:
            db.rollback()
            logger.error("Failed to submit expert feedback", error=str(e))
            return {
                "status": "error",
                "message": f"Failed to submit feedback: {str(e)}"
            }
        finally:
            self._close_db(db)
    
    def get_pending_reviews(self, expert_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get list of pending reviews for experts.
        
        Args:
            expert_id: Optional expert ID to filter reviews
            
        Returns:
            List of review summaries
        """
        db = self._get_db()
        try:
            query = db.query(HITLReview).filter(
                HITLReview.status == ReviewStatus.PENDING
            )
            
            if expert_id:
                query = query.filter(HITLReview.assigned_expert_id == expert_id)
            
            reviews = query.order_by(
                desc(HITLReview.priority),
                HITLReview.created_at
            ).all()
            
            return [review.to_dict() for review in reviews]
            
        except Exception as e:
            logger.error("Failed to get pending reviews", error=str(e))
            return []
        finally:
            self._close_db(db)
    
    def get_review_details(self, review_id: str) -> Dict[str, Any]:
        """
        Get detailed information about a specific review.
        
        Args:
            review_id: Review identifier
            
        Returns:
            Review details dictionary
        """
        db = self._get_db()
        try:
            review = db.query(HITLReview).filter(HITLReview.review_id == review_id).first()
            
            if not review:
                return {
                    "status": "error",
                    "message": "Review not found"
                }
            
            return review.to_dict()
            
        except Exception as e:
            logger.error("Failed to get review details", error=str(e))
            return {
                "status": "error",
                "message": f"Failed to get review details: {str(e)}"
            }
        finally:
            self._close_db(db)
    
    def get_hitl_metrics(self) -> Dict[str, Any]:
        """
        Get HITL system metrics.
        
        Returns:
            Dict with metrics
        """
        db = self._get_db()
        try:
            # Count pending reviews
            pending_count = db.query(HITLReview).filter(
                HITLReview.status == ReviewStatus.PENDING
            ).count()
            
            # Count completed reviews
            completed_count = db.query(HITLReview).filter(
                HITLReview.status == ReviewStatus.COMPLETED
            ).count()
            
            # Calculate average review time
            avg_review_time = self._calculate_average_review_time(db)
            
            # Calculate approval rate
            approval_rate = self._calculate_approval_rate(db)
            
            return {
                "total_pending_reviews": pending_count,
                "total_completed_reviews": completed_count,
                "average_review_time_hours": avg_review_time,
                "approval_rate": approval_rate,
                "system_health": "healthy" if pending_count < self.max_pending_reviews else "overloaded"
            }
            
        except Exception as e:
            logger.error("Failed to get HITL metrics", error=str(e))
            return {
                "error": str(e)
            }
        finally:
            self._close_db(db)
    
    def _calculate_priority(self, confidence_score: float) -> ReviewPriority:
        """
        Calculate review priority based on confidence score.
        
        Rationale:
        - High: confidence < 0.5 (very unreliable, needs urgent review)
        - Medium: 0.5 <= confidence < 0.7 (questionable, review soon)
        - Low: confidence >= 0.7 (minor issues, can wait)
        """
        if confidence_score < 0.5:
            return ReviewPriority.HIGH
        elif confidence_score < 0.7:
            return ReviewPriority.MEDIUM
        else:
            return ReviewPriority.LOW
    
    def _calculate_average_review_time(self, db: Session) -> float:
        """Calculate average review time in hours."""
        try:
            completed_reviews = db.query(HITLReview).filter(
                and_(
                    HITLReview.status == ReviewStatus.COMPLETED,
                    HITLReview.completed_at.isnot(None)
                )
            ).all()
            
            if not completed_reviews:
                return 0.0
            
            total_time = 0.0
            count = 0
            
            for review in completed_reviews:
                if review.completed_at and review.created_at:
                    duration = (review.completed_at - review.created_at).total_seconds() / 3600
                    total_time += duration
                    count += 1
            
            return total_time / count if count > 0 else 0.0
            
        except Exception as e:
            logger.error("Failed to calculate average review time", error=str(e))
            return 0.0
    
    def _calculate_approval_rate(self, db: Session) -> float:
        """Calculate approval rate for completed reviews."""
        try:
            completed_reviews = db.query(HITLReview).filter(
                HITLReview.status == ReviewStatus.COMPLETED
            ).all()
            
            if not completed_reviews:
                return 0.0
            
            approved_count = sum(
                1 for review in completed_reviews
                if review.validation_result == ValidationResult.APPROVED
            )
            
            return approved_count / len(completed_reviews) if completed_reviews else 0.0
            
        except Exception as e:
            logger.error("Failed to calculate approval rate", error=str(e))
            return 0.0
    
    def cleanup_old_reviews(self, days_old: int = 30) -> int:
        """
        Clean up old completed reviews to manage database size.
        
        Args:
            days_old: Number of days to retain reviews
            
        Returns:
            Number of reviews cleaned up
        """
        db = self._get_db()
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days_old)
            
            # Find old completed reviews
            old_reviews = db.query(HITLReview).filter(
                and_(
                    HITLReview.status == ReviewStatus.COMPLETED,
                    HITLReview.completed_at < cutoff_date
                )
            ).all()
            
            cleaned_count = len(old_reviews)
            
            # Delete old reviews (cascade will delete feedback)
            for review in old_reviews:
                db.delete(review)
            
            db.commit()
            
            logger.info("Cleaned up old reviews", count=cleaned_count, days_old=days_old)
            return cleaned_count
            
        except Exception as e:
            db.rollback()
            logger.error("Failed to cleanup old reviews", error=str(e))
            return 0
        finally:
            self._close_db(db)
