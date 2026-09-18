"""
Automated Tests for Database Connection and Initial Models (User & Disaster).
"""

from datetime import datetime, timezone
import pytest
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.models import User, UserRole, Disaster, DisasterStatus
from app.core.database import get_db


def test_database_session_lifecycle():
    """
    Test that the get_db generator yields a valid session and closes cleanly.
    """
    session_generator = get_db()
    session = next(session_generator)
    assert isinstance(session, Session)
    # Closing via generator completion
    try:
        next(session_generator)
    except StopIteration:
        pass


def test_create_user(db_session: Session):
    """
    Test creating, committing, and querying a User model with an assigned role.
    """
    new_user = User(
        name="Admin Person",
        email="admin@relief.org",
        password_hash="$2b$12$e8Y4vL2l...",
        role=UserRole.ADMIN,
    )
    db_session.add(new_user)
    db_session.commit()
    db_session.refresh(new_user)

    assert new_user.id is not None
    assert new_user.name == "Admin Person"
    assert new_user.email == "admin@relief.org"
    assert new_user.role == UserRole.ADMIN
    assert new_user.created_at is not None

    # Query from database to verify persistence
    queried_user = db_session.query(User).filter_by(email="admin@relief.org").first()
    assert queried_user is not None
    assert queried_user.id == new_user.id


def test_user_email_unique_constraint(db_session: Session):
    """
    Test that creating two users with the same email violates the unique constraint.
    """
    user1 = User(
        name="Volunteer One",
        email="volunteer@relief.org",
        password_hash="hash1",
        role=UserRole.VOLUNTEER,
    )
    db_session.add(user1)
    db_session.commit()

    user2 = User(
        name="Volunteer Two",
        email="volunteer@relief.org",
        password_hash="hash2",
        role=UserRole.VOLUNTEER,
    )
    db_session.add(user2)

    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_create_disaster(db_session: Session):
    """
    Test creating, committing, and querying a Disaster model.
    """
    start_time = datetime.now(timezone.utc)
    new_disaster = Disaster(
        name="Flood Relief Operation Alpha",
        description="Major flooding affecting coastal districts.",
        location="Eastern Coast, Sector 4",
        status=DisasterStatus.ACTIVE,
        start_date=start_time,
        end_date=None,
    )
    db_session.add(new_disaster)
    db_session.commit()
    db_session.refresh(new_disaster)

    assert new_disaster.id is not None
    assert new_disaster.name == "Flood Relief Operation Alpha"
    assert new_disaster.status == DisasterStatus.ACTIVE
    assert new_disaster.end_date is None

    # Update status to RESOLVED
    new_disaster.status = DisasterStatus.RESOLVED
    new_disaster.end_date = datetime.now(timezone.utc)
    db_session.commit()
    db_session.refresh(new_disaster)

    assert new_disaster.status == DisasterStatus.RESOLVED
    assert new_disaster.end_date is not None


def test_user_roles_supported(db_session: Session):
    """
    Verify all required user roles can be persisted:
    ADMIN, NGO_STAFF, VOLUNTEER, DONOR.
    """
    roles = [UserRole.ADMIN, UserRole.NGO_STAFF, UserRole.VOLUNTEER, UserRole.DONOR]
    for idx, role in enumerate(roles):
        user = User(
            name=f"User {role.value}",
            email=f"user_{idx}@relief.org",
            password_hash=f"hash_{idx}",
            role=role,
        )
        db_session.add(user)
    db_session.commit()

    count = db_session.query(User).count()
    assert count == len(roles)
