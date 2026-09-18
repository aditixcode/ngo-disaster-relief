"""
Inventory Service Layer.

Encapsulates business logic for calculating available relief stock and maintaining
separation between data access and HTTP presentation layers.
"""

from sqlalchemy.orm import Session
from sqlalchemy import func
from app.models.inventory import InventoryItem, InventoryStatus


def get_available_quantity(
    db: Session,
    disaster_id: int,
    item_name: str,
    unit: str,
) -> float:
    """
    Calculates the distributable stock for a given relief resource.

    Critical Business Rules:
    1. Only inventory with status == STORED contributes to available stock.
    2. Items with status == RECEIVED are awaiting inspection and CANNOT be distributed.
    3. Items with status == DISTRIBUTED have already been dispatched.
    4. Aggregation matches disaster_id, item_name (case-insensitive), and unit.
    """
    total = (
        db.query(func.coalesce(func.sum(InventoryItem.quantity), 0.0))
        .filter(
            InventoryItem.disaster_id == disaster_id,
            func.lower(InventoryItem.item_name) == item_name.strip().lower(),
            func.lower(InventoryItem.unit) == unit.strip().lower(),
            InventoryItem.status == InventoryStatus.STORED,
        )
        .scalar()
    )
    return float(total) if total is not None else 0.0
