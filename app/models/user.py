"""
User Database Model.

Represents all users in the NGO disaster relief system, including
Admins, NGO Staff, Volunteers, and Donors.
"""

import enum
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, DateTime, Enum as SQLEnum, func
from app.core.database import Base


class UserRole(str, enum.Enum):
    """
    User roles supported by the system for role-based access control (RBAC).
    """
    ADMIN = "ADMIN"
    NGO_STAFF = "NGO_STAFF"
    VOLUNTEER = "VOLUNTEER"
    DONOR = "DONOR"


class User(Base):
    """
    SQLAlchemy model representing the 'users' table in PostgreSQL.
    """
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    role = Column(
        SQLEnum(UserRole, name="user_role"),
        nullable=False,
        default=UserRole.VOLUNTEER,
    )
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    def __repr__(self) -> str:
        return f"<User(id={self.id}, name='{self.name}', email='{self.email}', role='{self.role}')>"
