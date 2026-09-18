"""
Resource Distribution Database Model.

Represents an immutable disbursement of physical relief inventory to a verified beneficiary
at a specific distribution center for an active disaster relief event.
Serves as an immutable historical audit record.
"""

from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    Text,
    DateTime,
    ForeignKey,
    func,
)
from sqlalchemy.orm import relationship
from app.core.database import Base


class ResourceDistribution(Base):
    """
    SQLAlchemy model representing the 'resource_distributions' table in PostgreSQL.
    """
    __tablename__ = "resource_distributions"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    disaster_id = Column(
        Integer,
        ForeignKey("disasters.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    inventory_item_id = Column(
        Integer,
        ForeignKey("inventory_items.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    beneficiary_id = Column(
        Integer,
        ForeignKey("beneficiaries.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    distribution_center_id = Column(
        Integer,
        ForeignKey("distribution_centers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    quantity = Column(Float, nullable=False)
    unit = Column(String(50), nullable=False)
    item_name = Column(String(150), nullable=False, index=True)
    distributed_by_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    distributed_at = Column(DateTime(timezone=True), nullable=False)
    notes = Column(Text, nullable=True)
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # ORM Relationships
    disaster = relationship("Disaster", backref="distributions")
    inventory_item = relationship("InventoryItem", backref="distributions")
    beneficiary = relationship("Beneficiary", backref="distributions")
    distribution_center = relationship("DistributionCenter", backref="distributions")
    distributed_by = relationship("User", foreign_keys=[distributed_by_id])

    def __repr__(self) -> str:
        return (
            f"<ResourceDistribution(id={self.id}, item='{self.item_name}', "
            f"qty={self.quantity} {self.unit}, beneficiary_id={self.beneficiary_id}, "
            f"center_id={self.distribution_center_id})>"
        )
