"""
Relief Inventory Database Model.

Represents warehouse stock of physical relief goods associated with a disaster operation.
Enforces the lifecycle: RECEIVED -> STORED -> DISTRIBUTED.
"""

import enum
from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    DateTime,
    Enum as SQLEnum,
    ForeignKey,
    func,
)
from sqlalchemy.orm import relationship
from app.core.database import Base


class InventoryStatus(str, enum.Enum):
    """
    Operational lifecycle status of relief inventory:
    - RECEIVED: Goods delivered to warehouse/intake; awaiting inspection and storage.
    - STORED: Goods verified, cataloged, and warehoused; eligible for distribution.
    - DISTRIBUTED: Goods allocated and distributed to beneficiaries in the field.
    """
    RECEIVED = "RECEIVED"
    STORED = "STORED"
    DISTRIBUTED = "DISTRIBUTED"


class InventoryItem(Base):
    """
    SQLAlchemy model representing the 'inventory_items' table in PostgreSQL.
    """
    __tablename__ = "inventory_items"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    disaster_id = Column(
        Integer,
        ForeignKey("disasters.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    item_name = Column(String(150), nullable=False, index=True)
    quantity = Column(Float, nullable=False)
    original_quantity = Column(Float, nullable=True)
    unit = Column(String(50), nullable=False)
    status = Column(
        SQLEnum(InventoryStatus, name="inventory_status"),
        nullable=False,
        default=InventoryStatus.RECEIVED,
        index=True,
    )
    received_at = Column(DateTime(timezone=True), nullable=False)
    stored_at = Column(DateTime(timezone=True), nullable=True)
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
    disaster = relationship("Disaster", backref="inventory_items")

    def __repr__(self) -> str:
        return f"<InventoryItem(id={self.id}, item='{self.item_name}', qty={self.quantity} {self.unit}, status='{self.status}')>"
