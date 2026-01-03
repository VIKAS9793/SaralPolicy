"""
Database models for Human-in-the-Loop (HITL) reviews.

Data Structure Design Rationale:
================================

1. **SQLAlchemy ORM over Raw SQL**
   - Rationale: Type safety, migration support (Alembic), and ORM patterns
   - Trade-off: Slight performance overhead vs raw SQL, acceptable for HITL volumes
   - Alternative considered: Raw SQL with connection pooling (rejected for maintainability)

2. **UUID Primary Keys (String(36))**
   - Rationale: Globally unique, no coordination needed, safe for distributed systems
   - Trade-off: 36 bytes vs 4-8 bytes for auto-increment integers
   - Justification: HITL reviews are low-volume (<1000/day expected), storage cost negligible

3. **JSON Columns for Flexible Data (analysis_data, evaluation_data, feedback_data)**
   - Rationale: Schema flexibility for evolving analysis formats without migrations
   - Trade-off: No SQL-level querying of JSON fields (acceptable for this use case)
   - Alternative considered: Normalized tables (rejected for complexity vs benefit)
   - Growth limit: JSON fields capped by SQLite's 1GB blob limit (far exceeds needs)

4. **Enum Types for Status/Priority/Type**
   - Rationale: Type safety, self-documenting, prevents invalid values
   - Trade-off: Requires migration for new enum values
   - Justification: Status values are stable, changes are rare

5. **Separate HITLFeedback Table**
   - Rationale: One review can have multiple feedback entries (audit trail)
   - Trade-off: JOIN required for full review data
   - Justification: Audit requirements outweigh query complexity

6. **Index Strategy**
   - idx_hitl_reviews_status: Most queries filter by status (pending reviews)
   - idx_hitl_reviews_priority: Sorting by priority for expert queue
   - idx_hitl_reviews_created_at: Time-based queries and cleanup
   - idx_hitl_reviews_expert: Expert-specific review lists
   - Trade-off: Write overhead for index maintenance
   - Justification: Read-heavy workload (experts checking queue frequently)

Memory and Growth Considerations:
- Expected volume: <100 reviews/day for POC, <1000/day at scale
- Retention: 30-day cleanup for completed reviews (configurable)
- SQLite limit: 140TB max database size (far exceeds needs)
- Upgrade path: PostgreSQL for production (same SQLAlchemy models)
"""

from datetime import datetime
from typing import Optional
from sqlalchemy import Column, String, Float, DateTime, Text, JSON, Index, Enum as SQLEnum
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import relationship
import enum

Base = declarative_base()


class ReviewStatus(str, enum.Enum):
    """Review status enumeration."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    REJECTED = "rejected"
    CANCELLED = "cancelled"


class ReviewPriority(str, enum.Enum):
    """Review priority enumeration."""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class ReviewType(str, enum.Enum):
    """Review type enumeration."""
    ANALYSIS_REVIEW = "analysis_review"
    QA_REVIEW = "qa_review"


class ValidationResult(str, enum.Enum):
    """Validation result enumeration."""
    APPROVED = "approved"
    REJECTED = "rejected"
    NEEDS_REVISION = "needs_revision"


class HITLReview(Base):
    """
    Database model for HITL review requests.
    
    Stores review requests for low-confidence analyses and Q&A responses.
    """
    __tablename__ = "hitl_reviews"
    
    # Primary key
    review_id = Column(String(36), primary_key=True, nullable=False)
    
    # Review metadata
    review_type = Column(SQLEnum(ReviewType), nullable=False, default=ReviewType.ANALYSIS_REVIEW)
    status = Column(SQLEnum(ReviewStatus), nullable=False, default=ReviewStatus.PENDING)
    priority = Column(SQLEnum(ReviewPriority), nullable=False, default=ReviewPriority.MEDIUM)
    
    # Confidence and scoring
    confidence_score = Column(Float, nullable=False)
    
    # Review content (stored as JSON for flexibility)
    analysis_data = Column(JSON, nullable=True)  # For analysis reviews
    question = Column(Text, nullable=True)  # For Q&A reviews
    answer = Column(Text, nullable=True)  # For Q&A reviews
    evaluation_data = Column(JSON, nullable=True)  # Evaluation results
    
    # Expert assignment
    assigned_expert_id = Column(String(100), nullable=True)
    expert_id = Column(String(100), nullable=True)  # Expert who completed review
    
    # Expert feedback
    expert_notes = Column(Text, nullable=True)
    validation_result = Column(SQLEnum(ValidationResult), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    
    # Indexes for performance
    __table_args__ = (
        Index('idx_hitl_reviews_status', 'status'),
        Index('idx_hitl_reviews_priority', 'priority'),
        Index('idx_hitl_reviews_created_at', 'created_at'),
        Index('idx_hitl_reviews_expert', 'assigned_expert_id'),
    )
    
    def to_dict(self) -> dict:
        """Convert model to dictionary for API responses."""
        return {
            "review_id": self.review_id,
            "review_type": self.review_type.value if self.review_type else None,
            "status": self.status.value if self.status else None,
            "priority": self.priority.value if self.priority else None,
            "confidence_score": self.confidence_score,
            "analysis_data": self.analysis_data,
            "question": self.question,
            "answer": self.answer,
            "evaluation_data": self.evaluation_data,
            "assigned_expert_id": self.assigned_expert_id,
            "expert_id": self.expert_id,
            "expert_notes": self.expert_notes,
            "validation_result": self.validation_result.value if self.validation_result else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }


class HITLFeedback(Base):
    """
    Database model for expert feedback on reviews.
    
    Stores detailed feedback from experts for audit and improvement.
    """
    __tablename__ = "hitl_feedback"
    
    # Primary key
    feedback_id = Column(String(36), primary_key=True, nullable=False)
    review_id = Column(String(36), nullable=False)  # Foreign key to HITLReview
    
    # Feedback content
    expert_id = Column(String(100), nullable=False)
    feedback_text = Column(Text, nullable=False)
    feedback_data = Column(JSON, nullable=True)  # Structured feedback
    
    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    
    # Indexes
    __table_args__ = (
        Index('idx_hitl_feedback_review_id', 'review_id'),
        Index('idx_hitl_feedback_expert', 'expert_id'),
        Index('idx_hitl_feedback_created_at', 'created_at'),
    )
    
    def to_dict(self) -> dict:
        """Convert model to dictionary for API responses."""
        return {
            "feedback_id": self.feedback_id,
            "review_id": self.review_id,
            "expert_id": self.expert_id,
            "feedback_text": self.feedback_text,
            "feedback_data": self.feedback_data,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

