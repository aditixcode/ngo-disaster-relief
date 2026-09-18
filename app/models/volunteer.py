"""
Volunteer Database Models.

Represents:
1. VolunteerAssignment: Deployment record connecting a Volunteer to a Disaster event.
2. VolunteerTask: Operational tasks assigned to a Volunteer under a Disaster.
"""

import enum
from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    DateTime,
    Enum as SQLEnum,
    ForeignKey,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import relationship
from app.core.database import Base


class AssignmentStatus(str, enum.Enum):
    """Status of a volunteer's deployment to a disaster."""
    ACTIVE = "ACTIVE"
    COMPLETED = "COMPLETED"


class TaskStatus(str, enum.Enum):
    """Operational lifecycle status of an assigned volunteer task."""
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class VolunteerAssignment(Base):
    """
    Records a volunteer's deployment to a disaster operation.
    Enforces a unique constraint to avoid duplicate deployments of the same volunteer.
    """
    __tablename__ = "volunteer_assignments"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    volunteer_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    disaster_id = Column(
        Integer,
        ForeignKey("disasters.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    assigned_by_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    status = Column(
        SQLEnum(AssignmentStatus, name="assignment_status"),
        nullable=False,
        default=AssignmentStatus.ACTIVE,
    )
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # Prevent duplicate assignment to the same disaster
    __table_args__ = (
        UniqueConstraint("volunteer_id", "disaster_id", name="uq_volunteer_disaster"),
    )

    # ORM Relationships
    volunteer = relationship("User", foreign_keys=[volunteer_id], backref="disaster_assignments")
    disaster = relationship("Disaster", backref="volunteer_assignments")
    assigned_by = relationship("User", foreign_keys=[assigned_by_id])

    def __repr__(self) -> str:
        return f"<VolunteerAssignment(id={self.id}, volunteer_id={self.volunteer_id}, disaster_id={self.disaster_id}, status='{self.status}')>"


class VolunteerTask(Base):
    """
    Specific relief duty assigned to a volunteer under a disaster operation.
    """
    __tablename__ = "volunteer_tasks"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    title = Column(String(150), nullable=False, index=True)
    description = Column(Text, nullable=True)
    disaster_id = Column(
        Integer,
        ForeignKey("disasters.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    volunteer_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    assigned_by_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    status = Column(
        SQLEnum(TaskStatus, name="task_status"),
        nullable=False,
        default=TaskStatus.PENDING,
        index=True,
    )
    due_date = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # ORM Relationships
    volunteer = relationship("User", foreign_keys=[volunteer_id], backref="tasks")
    disaster = relationship("Disaster", backref="tasks")
    assigned_by = relationship("User", foreign_keys=[assigned_by_id])

    def __repr__(self) -> str:
        return f"<VolunteerTask(id={self.id}, title='{self.title}', status='{self.status}', volunteer_id={self.volunteer_id})>"
