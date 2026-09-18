"""
Relief Inventory Endpoints.

Implements the warehouse inventory lifecycle:
RECEIVED -> STORED -> DISTRIBUTED

Provides:
- POST /api/v1/inventory (Intake new stock as RECEIVED)
- GET /api/v1/inventory (List stock with optional filters)
- GET /api/v1/inventory/available (Calculate distributable stock - STORED only)
- GET /api/v1/inventory/{inventory_id} (Fetch single item)
- PATCH /api/v1/inventory/{inventory_id}/store (Transition RECEIVED -> STORED)
- PATCH /api/v1/inventory/{inventory_id}/status (State machine transition guard)
"""

from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_current_user, require_roles
from app.models.user import User, UserRole
from app.models.disaster import Disaster
from app.models.inventory import InventoryItem, InventoryStatus
from app.schemas.inventory import (
    InventoryCreate,
    InventoryStatusUpdate,
    InventoryResponse,
    InventoryAvailabilityResponse,
)
from app.services.inventory_service import get_available_quantity

router = APIRouter()


@router.post(
    "",
    response_model=InventoryResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Record warehouse intake of relief supplies",
    description=(
        "Registers incoming physical relief items. Initial status is set to RECEIVED. "
        "Restricted to ADMIN and NGO_STAFF roles."
    ),
)
def create_inventory_item(
    inventory_in: InventoryCreate,
    current_user: User = Depends(require_roles([UserRole.ADMIN, UserRole.NGO_STAFF])),
    db: Session = Depends(get_db),
) -> InventoryItem:
    """
    Intakes new relief supplies.
    Validates disaster exists and quantity > 0.
    Initial status is set to RECEIVED, recording received_at automatically.
    """
    # 1. Validate disaster
    disaster = db.query(Disaster).filter(Disaster.id == inventory_in.disaster_id).first()
    if not disaster:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Disaster with ID {inventory_in.disaster_id} not found",
        )

    # 2. Create inventory record
    new_item = InventoryItem(
        disaster_id=inventory_in.disaster_id,
        item_name=inventory_in.item_name.strip(),
        quantity=inventory_in.quantity,
        original_quantity=inventory_in.quantity,
        unit=inventory_in.unit.strip(),
        status=InventoryStatus.RECEIVED,
        received_at=datetime.now(timezone.utc),
    )
    db.add(new_item)
    db.commit()
    db.refresh(new_item)
    return new_item


@router.get(
    "",
    response_model=List[InventoryResponse],
    summary="List inventory items",
    description="Returns inventory records with optional filtering by disaster, status, or item name.",
)
def list_inventory(
    disaster_id: Optional[int] = Query(None, description="Filter by disaster ID"),
    inventory_status: Optional[InventoryStatus] = Query(None, alias="status", description="Filter by status"),
    item_name: Optional[str] = Query(None, description="Filter by item name (case-insensitive substring)"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> List[InventoryItem]:
    """
    Lists inventory stock. Accessible to any authenticated user.
    """
    query = db.query(InventoryItem)
    if disaster_id:
        query = query.filter(InventoryItem.disaster_id == disaster_id)
    if inventory_status:
        query = query.filter(InventoryItem.status == inventory_status)
    if item_name:
        query = query.filter(InventoryItem.item_name.ilike(f"%{item_name.strip()}%"))

    return query.order_by(InventoryItem.created_at.desc()).all()


@router.get(
    "/available",
    response_model=InventoryAvailabilityResponse,
    summary="Get available/distributable quantity of an item",
    description=(
        "Calculates the total quantity of an item eligible for distribution. "
        "Strict rule: Only items with status == STORED are counted. "
        "Items in RECEIVED or DISTRIBUTED status are completely excluded."
    ),
)
def get_available_stock(
    disaster_id: int = Query(..., description="Target disaster ID"),
    item_name: str = Query(..., description="Item name to query"),
    unit: str = Query(..., description="Unit of measurement (e.g. kg, boxes)"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> InventoryAvailabilityResponse:
    """
    Uses the inventory_service to compute distributable stock.
    """
    avail_qty = get_available_quantity(
        db=db,
        disaster_id=disaster_id,
        item_name=item_name,
        unit=unit,
    )
    return InventoryAvailabilityResponse(
        disaster_id=disaster_id,
        item_name=item_name,
        unit=unit,
        available_quantity=avail_qty,
    )


@router.get(
    "/{inventory_id}",
    response_model=InventoryResponse,
    summary="Get inventory record by ID",
    description="Retrieves details of a specific inventory batch. Accessible to any authenticated user.",
)
def get_inventory_item(
    inventory_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> InventoryItem:
    item = db.query(InventoryItem).filter(InventoryItem.id == inventory_id).first()
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Inventory item with ID {inventory_id} not found",
        )
    return item


@router.patch(
    "/{inventory_id}/store",
    response_model=InventoryResponse,
    summary="Store inventory (RECEIVED -> STORED)",
    description=(
        "Confirms warehouse inspection and verification of received goods, moving status "
        "from RECEIVED to STORED. Stored items immediately become available for distribution. "
        "Restricted to ADMIN and NGO_STAFF."
    ),
)
def store_inventory_item(
    inventory_id: int,
    current_user: User = Depends(require_roles([UserRole.ADMIN, UserRole.NGO_STAFF])),
    db: Session = Depends(get_db),
) -> InventoryItem:
    """
    Transitions an item from RECEIVED to STORED, recording stored_at automatically.
    Rejects operation if already in STORED or DISTRIBUTED status.
    """
    item = db.query(InventoryItem).filter(InventoryItem.id == inventory_id).first()
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Inventory item with ID {inventory_id} not found",
        )

    if item.status != InventoryStatus.RECEIVED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot store inventory that is already in '{item.status.value}' status",
        )

    item.status = InventoryStatus.STORED
    item.stored_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(item)
    return item


@router.patch(
    "/{inventory_id}/status",
    response_model=InventoryResponse,
    summary="Update inventory lifecycle status",
    description=(
        "Enforces the strict lifecycle state machine: RECEIVED -> STORED. "
        "Rejects arbitrary or backward transitions (e.g. STORED -> RECEIVED). "
        "Restricted to ADMIN and NGO_STAFF."
    ),
)
def update_inventory_status(
    inventory_id: int,
    status_in: InventoryStatusUpdate,
    current_user: User = Depends(require_roles([UserRole.ADMIN, UserRole.NGO_STAFF])),
    db: Session = Depends(get_db),
) -> InventoryItem:
    """
    State machine transition rules:
    - RECEIVED -> STORED: Valid (sets stored_at = now()).
    - STORED -> RECEIVED: Invalid (HTTP 400).
    - DISTRIBUTED -> STORED / RECEIVED: Invalid (HTTP 400).
    """
    item = db.query(InventoryItem).filter(InventoryItem.id == inventory_id).first()
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Inventory item with ID {inventory_id} not found",
        )

    current_status = item.status
    target_status = status_in.status

    if current_status == InventoryStatus.RECEIVED:
        if target_status == InventoryStatus.STORED:
            item.status = InventoryStatus.STORED
            item.stored_at = datetime.now(timezone.utc)
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid transition from '{current_status.value}' to '{target_status.value}'. Must transition to STORED first.",
            )
    elif current_status == InventoryStatus.STORED:
        if target_status == InventoryStatus.RECEIVED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot revert STORED inventory back to RECEIVED status",
            )
        elif target_status == InventoryStatus.DISTRIBUTED:
            # Inform caller that distributions are managed in Stage 10
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Direct transition to DISTRIBUTED is reserved for the Resource Distribution module",
            )
        elif target_status == InventoryStatus.STORED:
            pass  # No-op
    elif current_status == InventoryStatus.DISTRIBUTED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot alter status of an already DISTRIBUTED inventory record",
        )

    db.commit()
    db.refresh(item)
    return item
