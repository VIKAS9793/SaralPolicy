"""
Tests for HITL persistence (CRITICAL-002).
Verifies that HITL reviews persist across restarts.
"""

import pytest
import os
import tempfile
from pathlib import Path
from datetime import datetime
from sqlalchemy.orm import Session

from app.models.hitl import (
    HITLReview, HITLFeedback,
    ReviewStatus, ReviewPriority, ReviewType, ValidationResult
)
from app.db.database import engine, SessionLocal, init_db
from app.services.hitl_service import HITLService


@pytest.fixture
def test_db():
    """Create a test database."""
    # Use in-memory SQLite for testing
    test_db_path = ":memory:"
    
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from app.models.hitl import Base
    
    test_engine = create_engine(f"sqlite:///{test_db_path}")
    Base.metadata.create_all(bind=test_engine)
    
    TestSessionLocal = sessionmaker(bind=test_engine)
    db = TestSessionLocal()
    
    yield db
    
    db.close()
    Base.metadata.drop_all(bind=test_engine)


def test_hitl_review_persistence(test_db: Session):
    """Test that HITL reviews persist in database."""
    service = HITLService(db=test_db)
    
    # Create a review
    analysis = {
        "summary": "Test analysis",
        "confidence": 0.6,  # Below threshold
        "confidence_score": 0.6
    }
    
    result = service.trigger_review(analysis)
    assert result["status"] == "pending"
    review_id = result["review_id"]
    
    # Verify review exists in database
    review = test_db.query(HITLReview).filter(HITLReview.review_id == review_id).first()
    assert review is not None
    assert review.status == ReviewStatus.PENDING
    assert review.confidence_score == 0.6
    assert review.review_type == ReviewType.ANALYSIS_REVIEW


def test_hitl_review_survives_restart(test_db: Session):
    """Test that reviews persist across service restarts (simulated)."""
    # Create review with first service instance
    service1 = HITLService(db=test_db)
    analysis = {"summary": "Test", "confidence_score": 0.5}
    result1 = service1.trigger_review(analysis)
    review_id = result1["review_id"]
    
    # Simulate restart: create new service instance
    service2 = HITLService(db=test_db)
    
    # Verify review still exists
    review = service2.get_review_details(review_id)
    assert review["status"] != "error"
    assert review["review_id"] == review_id
    assert review["confidence_score"] == 0.5


def test_hitl_feedback_persistence(test_db: Session):
    """Test that expert feedback persists in database."""
    service = HITLService(db=test_db)
    
    # Create review
    analysis = {"summary": "Test", "confidence_score": 0.5}
    result = service.trigger_review(analysis)
    review_id = result["review_id"]
    
    # Submit feedback
    feedback = {
        "expert_id": "expert_123",
        "validation_result": "approved",
        "notes": "Looks good"
    }
    
    result = service.submit_expert_feedback(review_id, feedback)
    assert result["status"] == "success"
    
    # Verify feedback exists in database
    feedback_records = test_db.query(HITLFeedback).filter(
        HITLFeedback.review_id == review_id
    ).all()
    
    assert len(feedback_records) > 0
    assert feedback_records[0].expert_id == "expert_123"
    assert feedback_records[0].feedback_text == "Looks good"


def test_get_pending_reviews(test_db: Session):
    """Test getting pending reviews from database."""
    service = HITLService(db=test_db)
    
    # Create multiple reviews
    for i in range(3):
        analysis = {"summary": f"Test {i}", "confidence_score": 0.5 + i * 0.1}
        service.trigger_review(analysis)
    
    # Get pending reviews
    pending = service.get_pending_reviews()
    assert len(pending) == 3
    
    # Verify they're sorted by priority
    priorities = [r["priority"] for r in pending]
    # Lower confidence = higher priority
    assert priorities[0] in ["high", "medium"]  # First should be higher priority


def test_cleanup_old_reviews(test_db: Session):
    """Test cleanup of old completed reviews."""
    service = HITLService(db=test_db)
    
    # Create and complete a review
    analysis = {"summary": "Test", "confidence_score": 0.5}
    result = service.trigger_review(analysis)
    review_id = result["review_id"]
    
    # Complete it
    feedback = {
        "expert_id": "expert_1",
        "validation_result": "approved",
        "notes": "Done"
    }
    service.submit_expert_feedback(review_id, feedback)
    
    # Manually set completion date to 31 days ago
    review = test_db.query(HITLReview).filter(HITLReview.review_id == review_id).first()
    from datetime import timedelta
    review.completed_at = datetime.utcnow() - timedelta(days=31)
    test_db.commit()
    
    # Cleanup old reviews
    cleaned = service.cleanup_old_reviews(days_old=30)
    assert cleaned == 1
    
    # Verify review is gone
    review = test_db.query(HITLReview).filter(HITLReview.review_id == review_id).first()
    assert review is None


def test_hitl_metrics_from_database(test_db: Session):
    """Test that metrics are calculated from database."""
    service = HITLService(db=test_db)
    
    # Create some reviews
    for i in range(2):
        analysis = {"summary": f"Test {i}", "confidence_score": 0.5}
        service.trigger_review(analysis)
    
    # Get metrics
    metrics = service.get_hitl_metrics()
    
    assert metrics["total_pending_reviews"] == 2
    assert metrics["total_completed_reviews"] == 0
    assert "average_review_time_hours" in metrics
    assert "approval_rate" in metrics

