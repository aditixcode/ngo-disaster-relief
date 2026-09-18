"""
Database Configuration & Session Management.

Sets up the SQLAlchemy Engine, SessionLocal factory, Declarative Base,
and the FastAPI `get_db` dependency for database session lifecycle management.
"""

from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from app.core.config import settings

# Determine connection arguments based on database type
# SQLite requires 'check_same_thread: False', whereas PostgreSQL does not
connect_args = {}
if settings.database_url.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

# 1. SQLAlchemy Engine:
# The core interface to the database. Manages connection pooling and dialect translation.
# 'pool_pre_ping=True' ensures stale or disconnected connections are automatically refreshed.
engine = create_engine(
    settings.database_url,
    connect_args=connect_args,
    pool_pre_ping=True,
)

# 2. SessionLocal Factory:
# Each instance of SessionLocal is an active database transaction/session.
# autocommit=False ensures transactions are explicitly committed.
# autoflush=False avoids premature flushes before explicit commit/flush calls.
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)

# 3. Declarative Base:
# All ORM models inherit from this Base class to be registered in SQLAlchemy metadata.
Base = declarative_base()


# 4. Database Session Dependency:
# A generator that provides a database session to each incoming HTTP request
# and guarantees that the session is closed when the request finishes.
def get_db() -> Generator[Session, None, None]:
    """
    FastAPI dependency that yields a database session for a single request
    and guarantees proper cleanup/closure afterwards.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
