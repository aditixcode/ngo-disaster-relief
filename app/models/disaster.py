"""
Disaster Database Model.

Represents natural or human-made disasters/relief events managed by the NGO.
Includes foreign key tracking to record which user created the disaster record.
"""

import enum
from sqlalchemy import Column, Integer, String, Text, DateTime, Enum as SQLEnum, ForeignKey, func
from sqlalchemy.orm import relationship
from app.core.database import Base


class DisasterStatus(str, enum.Enum):
    """
    Lifecycle status of a disaster/relief event.
    """
    ACTIVE = "ACTIVE"
    CONTAINED = "CONTAINED"
    RESOLVED = "RESOLVED"


class Disaster(Base):
    """
    SQLAlchemy model representing the 'disasters' table in PostgreSQL.
    """
    __tablename__ = "disasters"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(150), nullable=False, index=True)
    description = Column(Text, nullable=True)
    location = Column(String(255), nullable=False)
    status = Column(
        SQLEnum(DisasterStatus, name="disaster_status"),
        nullable=False,
        default=DisasterStatus.ACTIVE,
    )
    start_date = Column(DateTime(timezone=True), nullable=False)
    end_date = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # Creator audit relationship
    created_by_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    creator = relationship("User", backref="created_disasters")

    def __repr__(self) -> str:
        return f"<Disaster(id={self.id}, name='{self.name}', status='{self.status}', location='{self.location}')>"
