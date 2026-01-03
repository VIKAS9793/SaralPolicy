"""
Database configuration and session management for SaralPolicy.
Uses SQLite for POC, can be upgraded to PostgreSQL for production.
"""

import os
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool
import structlog

logger = structlog.get_logger(__name__)

# Database configuration
# For POC: SQLite (file-based, no server required)
# For production: PostgreSQL (recommended)
DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    f"sqlite:///{Path(__file__).parent.parent.parent / 'data' / 'saralpolicy.db'}"
)

# Create database directory if it doesn't exist
if DATABASE_URL.startswith("sqlite"):
    db_path = Path(DATABASE_URL.replace("sqlite:///", ""))
    db_path.parent.mkdir(parents=True, exist_ok=True)

# Engine configuration
# SQLite-specific: use StaticPool for single-threaded access, check_same_thread=False for FastAPI
if DATABASE_URL.startswith("sqlite"):
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=False  # Set to True for SQL query logging
    )
else:
    # PostgreSQL or other databases
    engine = create_engine(
        DATABASE_URL,
        pool_pre_ping=True,  # Verify connections before using
        pool_size=5,
        max_overflow=10
    )

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Session:
    """
    Dependency function for FastAPI to get database session.
    
    Usage:
        @app.get("/endpoint")
        def endpoint(db: Session = Depends(get_db)):
            # Use db session
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """
    Initialize database: create all tables.
    Should be called at application startup.
    """
    from app.models.hitl import Base
    
    try:
        # Create all tables
        Base.metadata.create_all(bind=engine)
        logger.info("Database initialized successfully", database_url=DATABASE_URL)
    except Exception as e:
        logger.error("Failed to initialize database", error=str(e))
        raise

