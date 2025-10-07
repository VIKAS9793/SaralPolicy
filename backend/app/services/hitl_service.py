"""
Human-in-the-Loop (HITL) Service for SaralPolicy
Manages expert review and validation for low-confidence analyses.
"""

import uuid
import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import structlog

logger = structlog.get_logger(__name__)


class HITLService:
    """Service for managing human-in-the-loop validation."""
    
    def __init__(self):
        self.pending_reviews = {}  # In-memory storage for POC
        self.completed_reviews = {}
        self.expert_feedback = {}
        
        # HITL thresholds
        self.confidence_threshold = 0.85
        self.max_pending_reviews = 100
        
        logger.info("HITL service initialized")
    
    def trigger_review(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Trigger human review for low-confidence analysis."""
        try:
            review_id = str(uuid.uuid4())
            confidence_score = analysis.get("confidence_score", 0.0)
            
            # Create review request
            review_request = {
                "review_id": review_id,
                "timestamp": datetime.utcnow().isoformat(),
                "confidence_score": confidence_score,
                "analysis": analysis,
                "status": "pending",
                "priority": self._calculate_priority(confidence_score),
                "expert_notes": "",
                "validation_result": None
            }
            
            # Store pending review
            self.pending_reviews[review_id] = review_request
            
            logger.info("HITL review triggered", 
                       review_id=review_id,
                       confidence_score=confidence_score)
            
            return {
                "review_id": review_id,
                "status": "pending",
                "message": "Analysis flagged for expert review due to low confidence",
                "estimated_review_time": "2-4 hours"
            }
            
        except Exception as e:
            logger.error("Failed to trigger HITL review", error=str(e))
            return {
                "review_id": None,
                "status": "error",
                "message": f"Failed to trigger review: {str(e)}"
            }
    
    def trigger_qa_review(self, question: str, answer: str, eval_result: Dict[str, Any]) -> Dict[str, Any]:
        """Trigger human review for Q&A responses."""
        try:
            review_id = str(uuid.uuid4())
            confidence_score = eval_result.get("confidence_score", 0.0)
            
            # Create Q&A review request
            review_request = {
                "review_id": review_id,
                "timestamp": datetime.utcnow().isoformat(),
                "type": "qa_review",
                "question": question,
                "answer": answer,
                "confidence_score": confidence_score,
                "evaluation": eval_result,
                "status": "pending",
                "priority": self._calculate_priority(confidence_score),
                "expert_notes": "",
                "validation_result": None
            }
            
            # Store pending review
            self.pending_reviews[review_id] = review_request
            
            logger.info("HITL Q&A review triggered", 
                       review_id=review_id,
                       confidence_score=confidence_score)
            
            return {
                "review_id": review_id,
                "status": "pending",
                "message": "Q&A response flagged for expert review"
            }
            
        except Exception as e:
            logger.error("Failed to trigger Q&A review", error=str(e))
            return {
                "review_id": None,
                "status": "error",
                "message": f"Failed to trigger Q&A review: {str(e)}"
            }
    
    def submit_expert_feedback(self, review_id: str, feedback: Dict[str, Any]) -> Dict[str, Any]:
        """Submit expert feedback for a review."""
        try:
            if review_id not in self.pending_reviews:
                return {
                    "status": "error",
                    "message": "Review not found"
                }
            
            review = self.pending_reviews[review_id]
            
            # Update review with expert feedback
            review.update({
                "status": "completed",
                "expert_feedback": feedback,
                "completion_timestamp": datetime.utcnow().isoformat(),
                "expert_id": feedback.get("expert_id", "anonymous"),
                "validation_result": feedback.get("validation_result", "approved")
            })
            
            # Move to completed reviews
            self.completed_reviews[review_id] = review
            del self.pending_reviews[review_id]
            
            # Store expert feedback
            self.expert_feedback[review_id] = feedback
            
            logger.info("Expert feedback submitted", 
                       review_id=review_id,
                       validation_result=feedback.get("validation_result"))
            
            return {
                "status": "success",
                "message": "Expert feedback submitted successfully",
                "review_id": review_id
            }
            
        except Exception as e:
            logger.error("Failed to submit expert feedback", error=str(e))
            return {
                "status": "error",
                "message": f"Failed to submit feedback: {str(e)}"
            }
    
    def get_pending_reviews(self, expert_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get list of pending reviews for experts."""
        try:
            pending_list = []
            
            for review_id, review in self.pending_reviews.items():
                # Filter by expert if specified
                if expert_id and review.get("assigned_expert") != expert_id:
                    continue
                
                # Create summary for expert dashboard
                review_summary = {
                    "review_id": review_id,
                    "timestamp": review["timestamp"],
                    "confidence_score": review["confidence_score"],
                    "priority": review["priority"],
                    "type": review.get("type", "analysis_review"),
                    "status": review["status"]
                }
                
                pending_list.append(review_summary)
            
            # Sort by priority and timestamp
            pending_list.sort(key=lambda x: (x["priority"], x["timestamp"]))
            
            return pending_list
            
        except Exception as e:
            logger.error("Failed to get pending reviews", error=str(e))
            return []
    
    def get_review_details(self, review_id: str) -> Dict[str, Any]:
        """Get detailed information about a specific review."""
        try:
            # Check pending reviews first
            if review_id in self.pending_reviews:
                return self.pending_reviews[review_id]
            
            # Check completed reviews
            if review_id in self.completed_reviews:
                return self.completed_reviews[review_id]
            
            return {
                "status": "error",
                "message": "Review not found"
            }
            
        except Exception as e:
            logger.error("Failed to get review details", error=str(e))
            return {
                "status": "error",
                "message": f"Failed to get review details: {str(e)}"
            }
    
    def get_hitl_metrics(self) -> Dict[str, Any]:
        """Get HITL system metrics."""
        try:
            total_pending = len(self.pending_reviews)
            total_completed = len(self.completed_reviews)
            
            # Calculate average review time
            avg_review_time = self._calculate_average_review_time()
            
            # Calculate approval rate
            approval_rate = self._calculate_approval_rate()
            
            return {
                "total_pending_reviews": total_pending,
                "total_completed_reviews": total_completed,
                "average_review_time_hours": avg_review_time,
                "approval_rate": approval_rate,
                "system_health": "healthy" if total_pending < self.max_pending_reviews else "overloaded"
            }
            
        except Exception as e:
            logger.error("Failed to get HITL metrics", error=str(e))
            return {
                "error": str(e)
            }
    
    def _calculate_priority(self, confidence_score: float) -> str:
        """Calculate review priority based on confidence score."""
        if confidence_score < 0.5:
            return "high"
        elif confidence_score < 0.7:
            return "medium"
        else:
            return "low"
    
    def _calculate_average_review_time(self) -> float:
        """Calculate average review time in hours."""
        try:
            if not self.completed_reviews:
                return 0.0
            
            total_time = 0.0
            count = 0
            
            for review in self.completed_reviews.values():
                if "completion_timestamp" in review and "timestamp" in review:
                    start_time = datetime.fromisoformat(review["timestamp"])
                    end_time = datetime.fromisoformat(review["completion_timestamp"])
                    duration = (end_time - start_time).total_seconds() / 3600  # Convert to hours
                    total_time += duration
                    count += 1
            
            return total_time / count if count > 0 else 0.0
            
        except Exception as e:
            logger.error("Failed to calculate average review time", error=str(e))
            return 0.0
    
    def _calculate_approval_rate(self) -> float:
        """Calculate approval rate for completed reviews."""
        try:
            if not self.completed_reviews:
                return 0.0
            
            approved_count = 0
            total_count = len(self.completed_reviews)
            
            for review in self.completed_reviews.values():
                if review.get("validation_result") == "approved":
                    approved_count += 1
            
            return approved_count / total_count if total_count > 0 else 0.0
            
        except Exception as e:
            logger.error("Failed to calculate approval rate", error=str(e))
            return 0.0
    
    def cleanup_old_reviews(self, days_old: int = 30) -> int:
        """Clean up old completed reviews to manage memory."""
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days_old)
            cleaned_count = 0
            
            review_ids_to_remove = []
            for review_id, review in self.completed_reviews.items():
                if "completion_timestamp" in review:
                    completion_time = datetime.fromisoformat(review["completion_timestamp"])
                    if completion_time < cutoff_date:
                        review_ids_to_remove.append(review_id)
            
            for review_id in review_ids_to_remove:
                del self.completed_reviews[review_id]
                if review_id in self.expert_feedback:
                    del self.expert_feedback[review_id]
                cleaned_count += 1
            
            logger.info("Cleaned up old reviews", count=cleaned_count)
            return cleaned_count
            
        except Exception as e:
            logger.error("Failed to cleanup old reviews", error=str(e))
            return 0