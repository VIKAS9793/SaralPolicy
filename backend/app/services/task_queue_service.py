"""
Task Queue Service for SaralPolicy
Uses Huey for background task processing with SQLite backend.

Huey is a lightweight task queue (MIT License).
GitHub: https://github.com/coleifer/huey (5k+ stars)

Per Engineering Constitution Section 4.3:
- Design for idempotency where applicable
- Handle failures explicitly

This service provides:
1. Background task processing for HITL reviews
2. Async notification delivery
3. Scheduled cleanup jobs

Note: Uses SQLite backend - no Redis/RabbitMQ required.
"""

import os
import uuid
from typing import Dict, Any, Optional, Callable, List
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
import structlog

logger = structlog.get_logger(__name__)

# Check if Huey is available
HUEY_AVAILABLE = False
try:
    from huey import SqliteHuey
    HUEY_AVAILABLE = True
    logger.info("Huey task queue available")
except ImportError:
    logger.warning(
        "Huey not installed. Install with: pip install huey",
        fallback="Using in-memory task queue"
    )


class TaskStatus(str, Enum):
    """Task execution status."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"


class TaskPriority(str, Enum):
    """Task priority levels."""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class Task:
    """A queued task."""
    task_id: str
    task_type: str
    payload: Dict[str, Any]
    status: TaskStatus = TaskStatus.PENDING
    priority: TaskPriority = TaskPriority.MEDIUM
    created_at: datetime = field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error: Optional[str] = None
    retries: int = 0
    max_retries: int = 3
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "task_id": self.task_id,
            "task_type": self.task_type,
            "payload": self.payload,
            "status": self.status.value,
            "priority": self.priority.value,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "error": self.error,
            "retries": self.retries,
            "max_retries": self.max_retries
        }


class TaskQueueService:
    """
    Service for background task processing.
    
    Features:
    - SQLite-backed task queue (no Redis required)
    - Priority-based task scheduling
    - Automatic retries with exponential backoff
    - Task status tracking
    
    Fallback: If Huey is not installed, uses in-memory queue.
    """
    
    def __init__(self, db_path: str = "data/tasks.db"):
        """
        Initialize task queue service.
        
        Args:
            db_path: Path to SQLite database for task storage
        """
        self.db_path = db_path
        self.huey_available = HUEY_AVAILABLE
        
        # In-memory task storage (fallback and for status tracking)
        self._tasks: Dict[str, Task] = {}
        self._handlers: Dict[str, Callable] = {}
        
        # Initialize Huey if available
        if self.huey_available:
            self._setup_huey()
        
        logger.info(
            "Task queue service initialized",
            huey_available=self.huey_available,
            db_path=db_path
        )
    
    def _setup_huey(self):
        """Setup Huey with SQLite backend."""
        try:
            # Ensure data directory exists
            os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
            
            # Create Huey instance with SQLite storage
            self.huey = SqliteHuey(
                name="saralpolicy",
                filename=self.db_path,
                immediate=False  # Use queue, not immediate execution
            )
            
            logger.info("Huey configured with SQLite backend", db_path=self.db_path)
            
        except Exception as e:
            logger.error("Failed to setup Huey", error=str(e))
            self.huey_available = False
    
    def register_handler(self, task_type: str, handler: Callable):
        """
        Register a handler for a task type.
        
        Args:
            task_type: Type of task to handle
            handler: Function to call when task is executed
        """
        self._handlers[task_type] = handler
        
        if self.huey_available:
            # Create Huey task wrapper
            @self.huey.task()
            def huey_handler(task_id: str, payload: Dict[str, Any]):
                return self._execute_task(task_id, task_type, payload)
            
            self._handlers[f"huey_{task_type}"] = huey_handler
        
        logger.info("Task handler registered", task_type=task_type)
    
    def enqueue(
        self,
        task_type: str,
        payload: Dict[str, Any],
        priority: TaskPriority = TaskPriority.MEDIUM,
        delay_seconds: int = 0
    ) -> str:
        """
        Enqueue a task for background processing.
        
        Args:
            task_type: Type of task
            payload: Task payload data
            priority: Task priority
            delay_seconds: Delay before execution
            
        Returns:
            Task ID
        """
        task_id = str(uuid.uuid4())
        
        task = Task(
            task_id=task_id,
            task_type=task_type,
            payload=payload,
            priority=priority,
            status=TaskStatus.PENDING
        )
        
        self._tasks[task_id] = task
        
        if self.huey_available and f"huey_{task_type}" in self._handlers:
            try:
                huey_handler = self._handlers[f"huey_{task_type}"]
                if delay_seconds > 0:
                    huey_handler.schedule(
                        args=(task_id, payload),
                        delay=delay_seconds
                    )
                else:
                    huey_handler(task_id, payload)
                
                logger.info(
                    "Task enqueued via Huey",
                    task_id=task_id,
                    task_type=task_type,
                    priority=priority.value
                )
            except Exception as e:
                logger.error("Failed to enqueue via Huey, using fallback", error=str(e))
                self._enqueue_fallback(task)
        else:
            self._enqueue_fallback(task)
        
        return task_id
    
    def _enqueue_fallback(self, task: Task):
        """Fallback: Execute task immediately (synchronous)."""
        logger.info(
            "Executing task synchronously (fallback)",
            task_id=task.task_id,
            task_type=task.task_type
        )
        
        try:
            self._execute_task(task.task_id, task.task_type, task.payload)
        except Exception as e:
            logger.error("Fallback task execution failed", error=str(e))
            task.status = TaskStatus.FAILED
            task.error = str(e)
    
    def _execute_task(self, task_id: str, task_type: str, payload: Dict[str, Any]) -> Any:
        """
        Execute a task.
        
        Args:
            task_id: Task identifier
            task_type: Type of task
            payload: Task payload
            
        Returns:
            Task result
        """
        task = self._tasks.get(task_id)
        if task:
            task.status = TaskStatus.RUNNING
            task.started_at = datetime.utcnow()
        
        handler = self._handlers.get(task_type)
        if not handler:
            error_msg = f"No handler registered for task type: {task_type}"
            logger.error(error_msg)
            if task:
                task.status = TaskStatus.FAILED
                task.error = error_msg
            raise ValueError(error_msg)
        
        try:
            result = handler(payload)
            
            if task:
                task.status = TaskStatus.COMPLETED
                task.completed_at = datetime.utcnow()
            
            logger.info(
                "Task completed",
                task_id=task_id,
                task_type=task_type
            )
            
            return result
            
        except Exception as e:
            logger.error(
                "Task execution failed",
                task_id=task_id,
                task_type=task_type,
                error=str(e)
            )
            
            if task:
                task.retries += 1
                if task.retries < task.max_retries:
                    task.status = TaskStatus.RETRYING
                    # Re-enqueue with exponential backoff
                    delay = 2 ** task.retries * 60  # 2, 4, 8 minutes
                    self.enqueue(task_type, payload, task.priority, delay_seconds=delay)
                else:
                    task.status = TaskStatus.FAILED
                    task.error = str(e)
            
            raise
    
    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        Get status of a task.
        
        Args:
            task_id: Task identifier
            
        Returns:
            Task status dict or None
        """
        task = self._tasks.get(task_id)
        return task.to_dict() if task else None
    
    def get_pending_tasks(self, task_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get list of pending tasks.
        
        Args:
            task_type: Optional filter by task type
            
        Returns:
            List of pending task dicts
        """
        pending = [
            task.to_dict() for task in self._tasks.values()
            if task.status == TaskStatus.PENDING
            and (task_type is None or task.task_type == task_type)
        ]
        
        # Sort by priority (high first) then by created_at
        priority_order = {TaskPriority.HIGH: 0, TaskPriority.MEDIUM: 1, TaskPriority.LOW: 2}
        pending.sort(key=lambda t: (priority_order.get(TaskPriority(t["priority"]), 1), t["created_at"]))
        
        return pending
    
    def get_queue_stats(self) -> Dict[str, Any]:
        """
        Get queue statistics.
        
        Returns:
            Queue statistics dict
        """
        status_counts = {}
        for task in self._tasks.values():
            status = task.status.value
            status_counts[status] = status_counts.get(status, 0) + 1
        
        return {
            "total_tasks": len(self._tasks),
            "status_counts": status_counts,
            "huey_enabled": self.huey_available,
            "registered_handlers": list(self._handlers.keys())
        }
    
    def cleanup_completed_tasks(self, older_than_hours: int = 24) -> int:
        """
        Clean up old completed tasks.
        
        Args:
            older_than_hours: Remove tasks older than this
            
        Returns:
            Number of tasks removed
        """
        cutoff = datetime.utcnow() - timedelta(hours=older_than_hours)
        
        to_remove = [
            task_id for task_id, task in self._tasks.items()
            if task.status in (TaskStatus.COMPLETED, TaskStatus.FAILED)
            and task.completed_at and task.completed_at < cutoff
        ]
        
        for task_id in to_remove:
            del self._tasks[task_id]
        
        logger.info("Cleaned up old tasks", count=len(to_remove))
        return len(to_remove)


# Pre-defined task types for HITL
class HITLTaskTypes:
    """Standard HITL task types."""
    REVIEW_NOTIFICATION = "hitl_review_notification"
    EXPERT_ASSIGNMENT = "hitl_expert_assignment"
    REVIEW_REMINDER = "hitl_review_reminder"
    FEEDBACK_PROCESSING = "hitl_feedback_processing"


# Singleton instance
_task_queue_service: Optional[TaskQueueService] = None


def get_task_queue_service() -> TaskQueueService:
    """Get or create the task queue service singleton."""
    global _task_queue_service
    if _task_queue_service is None:
        db_path = os.environ.get("TASK_QUEUE_DB", "data/tasks.db")
        _task_queue_service = TaskQueueService(db_path=db_path)
    return _task_queue_service


def setup_hitl_task_handlers(task_queue: TaskQueueService, hitl_service):
    """
    Setup standard HITL task handlers.
    
    Args:
        task_queue: TaskQueueService instance
        hitl_service: HITLService instance
    """
    
    def handle_review_notification(payload: Dict[str, Any]) -> Dict[str, Any]:
        """Handle review notification task."""
        review_id = payload.get("review_id")
        logger.info("Processing review notification", review_id=review_id)
        # In production, send email/push notification
        return {"status": "notified", "review_id": review_id}
    
    def handle_expert_assignment(payload: Dict[str, Any]) -> Dict[str, Any]:
        """Handle expert assignment task."""
        review_id = payload.get("review_id")
        logger.info("Processing expert assignment", review_id=review_id)
        # In production, implement expert selection logic
        return {"status": "assigned", "review_id": review_id}
    
    def handle_review_reminder(payload: Dict[str, Any]) -> Dict[str, Any]:
        """Handle review reminder task."""
        review_id = payload.get("review_id")
        logger.info("Processing review reminder", review_id=review_id)
        # In production, send reminder notification
        return {"status": "reminded", "review_id": review_id}
    
    def handle_feedback_processing(payload: Dict[str, Any]) -> Dict[str, Any]:
        """Handle feedback processing task."""
        review_id = payload.get("review_id")
        feedback = payload.get("feedback", {})
        logger.info("Processing feedback", review_id=review_id)
        # Process feedback for model improvement
        return {"status": "processed", "review_id": review_id}
    
    # Register handlers
    task_queue.register_handler(HITLTaskTypes.REVIEW_NOTIFICATION, handle_review_notification)
    task_queue.register_handler(HITLTaskTypes.EXPERT_ASSIGNMENT, handle_expert_assignment)
    task_queue.register_handler(HITLTaskTypes.REVIEW_REMINDER, handle_review_reminder)
    task_queue.register_handler(HITLTaskTypes.FEEDBACK_PROCESSING, handle_feedback_processing)
    
    logger.info("HITL task handlers registered")
