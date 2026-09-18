"""
Distribution Center Database Model.

Represents a physical distribution facility/hub deployed under a disaster relief operation.
Tracks capacity, operational availability, and management audit.
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


class CenterStatus(str, enum.Enum):
    """
    Operational status of a distribution center.
    ACTIVE: Operating normally and accepting beneficiaries for distribution.
    INACTIVE: Temporarily or permanently closed/offline; cannot accept distributions.
    FULL: Reached declared recipient handling capacity; cannot accept new distributions.
    """
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    FULL = "FULL"


class DistributionCenter(Base):
    """
    SQLAlchemy model representing the 'distribution_centers' table in PostgreSQL.
    """
    __tablename__ = "distribution_centers"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    disaster_id = Column(
        Integer,
        ForeignKey("disasters.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name = Column(String(150), nullable=False, index=True)
    address = Column(Text, nullable=False)
    contact_number = Column(String(50), nullable=False)
    capacity = Column(Integer, nullable=False)
    status = Column(
        SQLEnum(CenterStatus, name="center_status"),
        nullable=False,
        default=CenterStatus.ACTIVE,
        index=True,
    )
    operating_hours = Column(String(100), nullable=True)
    created_by_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
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

    # Relationships
    disaster = relationship("Disaster", backref="distribution_centers")
    creator = relationship("User", foreign_keys=[created_by_id])

    # Uniqueness constraint on center name per disaster event
    __table_args__ = (
        UniqueConstraint(
            "disaster_id",
            "name",
            name="uq_center_disaster_name",
        ),
    )

    @property
    def is_operational(self) -> bool:
        """Helper property evaluating whether the center is active and ready for distributions."""
        return self.status == CenterStatus.ACTIVE

    def __repr__(self) -> str:
        return (
            f"<DistributionCenter(id={self.id}, name='{self.name}', "
            f"disaster_id={self.disaster_id}, status='{self.status}', capacity={self.capacity})>"
        )
