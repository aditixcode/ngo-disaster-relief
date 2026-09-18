"""
Donation Database Model.

Represents donations contributed to disaster relief operations, supporting:
1. MONEY: Monetary contributions with monetary amounts.
2. MATERIAL: Physical relief items with quantities, units, and item descriptions.
"""

import enum
from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    Text,
    DateTime,
    Enum as SQLEnum,
    ForeignKey,
    func,
)
from sqlalchemy.orm import relationship
from app.core.database import Base


class DonationType(str, enum.Enum):
    """Categorization of donation: monetary or physical goods."""
    MONEY = "MONEY"
    MATERIAL = "MATERIAL"


class DonationStatus(str, enum.Enum):
    """Lifecycle status of a donation."""
    PLEDGED = "PLEDGED"
    RECEIVED = "RECEIVED"
    CANCELLED = "CANCELLED"


class Donation(Base):
    """
    SQLAlchemy model representing the 'donations' table in PostgreSQL.
    """
    __tablename__ = "donations"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    donor_id = Column(
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
    donation_type = Column(
        SQLEnum(DonationType, name="donation_type"),
        nullable=False,
        index=True,
    )

    # Monetary fields
    amount = Column(Float, nullable=True)

    # Material goods fields
    item_name = Column(String(150), nullable=True)
    quantity = Column(Float, nullable=True)
    unit = Column(String(50), nullable=True)

    # Lifecycle & audit fields
    status = Column(
        SQLEnum(DonationStatus, name="donation_status"),
        nullable=False,
        default=DonationStatus.PLEDGED,
        index=True,
    )
    notes = Column(Text, nullable=True)
    received_at = Column(DateTime(timezone=True), nullable=True)
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
    donor = relationship("User", foreign_keys=[donor_id], backref="donations")
    disaster = relationship("Disaster", backref="donations")

    def __repr__(self) -> str:
        return f"<Donation(id={self.id}, donor_id={self.donor_id}, type='{self.donation_type}', status='{self.status}')>"
