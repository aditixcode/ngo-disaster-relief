"""
Beneficiary Database Model.

Represents an individual or household eligible for disaster relief resources.
Tracks demographic context, vulnerability categorization, and registration verification lifecycle.
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


class VulnerabilityCategory(str, enum.Enum):
    """
    Categorization of affected individuals/households to prioritize relief.
    """
    GENERAL = "GENERAL"
    CHILDREN = "CHILDREN"
    ELDERLY = "ELDERLY"
    DISABLED = "DISABLED"
    PREGNANT = "PREGNANT"
    LOW_INCOME = "LOW_INCOME"


class RegistrationStatus(str, enum.Enum):
    """
    Verification lifecycle of a beneficiary registration.
    PENDING: Intake complete; awaiting field verification.
    VERIFIED: Vetted by staff; eligible for resource distribution.
    INACTIVE: Deactivated or archived record; ineligible for distribution.
    """
    PENDING = "PENDING"
    VERIFIED = "VERIFIED"
    INACTIVE = "INACTIVE"


class Beneficiary(Base):
    """
    SQLAlchemy model representing the 'beneficiaries' table in PostgreSQL.
    """
    __tablename__ = "beneficiaries"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    disaster_id = Column(
        Integer,
        ForeignKey("disasters.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name = Column(String(150), nullable=False, index=True)
    contact_number = Column(String(50), nullable=False)
    address = Column(Text, nullable=False)
    household_size = Column(Integer, nullable=False)
    vulnerability_category = Column(
        SQLEnum(VulnerabilityCategory, name="vulnerability_category"),
        nullable=False,
        default=VulnerabilityCategory.GENERAL,
    )
    registration_status = Column(
        SQLEnum(RegistrationStatus, name="registration_status"),
        nullable=False,
        default=RegistrationStatus.PENDING,
        index=True,
    )
    registered_by_id = Column(
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
    disaster = relationship("Disaster", backref="beneficiaries")
    registered_by = relationship("User", foreign_keys=[registered_by_id])

    # Composite unique constraint to prevent duplicate registrations within the same disaster event
    __table_args__ = (
        UniqueConstraint(
            "disaster_id",
            "name",
            "contact_number",
            name="uq_beneficiary_disaster_name_contact",
        ),
    )

    @property
    def is_eligible(self) -> bool:
        """Helper property evaluating whether the beneficiary is verified and eligible for relief."""
        return self.registration_status == RegistrationStatus.VERIFIED

    def __repr__(self) -> str:
        return (
            f"<Beneficiary(id={self.id}, name='{self.name}', "
            f"disaster_id={self.disaster_id}, status='{self.registration_status}')>"
        )
