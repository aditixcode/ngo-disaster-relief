"""
Resource Distribution Service Layer.

Encapsulates business logic, validation, transactional integrity, and inventory deduction
for relief resource distributions to verified beneficiaries.
"""

from datetime import datetime, timezone
from typing import Optional, List
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.disaster import Disaster
from app.models.beneficiary import Beneficiary
from app.models.distribution_center import DistributionCenter
from app.models.inventory import InventoryItem, InventoryStatus
from app.models.distribution import ResourceDistribution
from app.services.beneficiary_service import is_beneficiary_eligible
from app.services.distribution_center_service import is_center_eligible_for_distribution


def execute_resource_distribution(
    db: Session,
    disaster_id: int,
    inventory_item_id: int,
    beneficiary_id: int,
    distribution_center_id: int,
    quantity: float,
    unit: str,
    distributed_by_id: Optional[int] = None,
    item_name: Optional[str] = None,
    notes: Optional[str] = None,
    distributed_at: Optional[datetime] = None,
) -> ResourceDistribution:
    """
    Executes an atomic relief resource distribution transaction.

    Business Rules Enforced:
    1. Quantity must be strictly greater than 0.
    2. Disaster event must exist.
    3. Beneficiary must exist and belong to the same disaster event.
    4. Beneficiary must be in VERIFIED status (is_beneficiary_eligible == True).
    5. Distribution center must exist and belong to the same disaster event.
    6. Distribution center must be in ACTIVE status (is_center_eligible_for_distribution == True).
    7. Primary inventory item batch must exist, belong to the disaster event, and be in STORED status.
    8. Unit must match the inventory batch unit.
    9. If item_name is provided, it must match the inventory batch item_name.
    10. Sufficient stock must exist across matching STORED batches for this disaster.
    11. Stock is atomically decremented:
        - Prioritizes the target batch first.
        - If target batch is depleted to 0.0, status transitions to DISTRIBUTED.
        - If additional stock is required, subsequent STORED sibling batches are consumed.
    12. An immutable ResourceDistribution audit record is created and committed.
    """
    if quantity <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Distributed quantity must be strictly greater than zero.",
        )

    # 1. Validate Disaster
    disaster = db.query(Disaster).filter(Disaster.id == disaster_id).first()
    if not disaster:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Disaster with ID {disaster_id} not found.",
        )

    # 2. Validate Beneficiary & Eligibility
    beneficiary = db.query(Beneficiary).filter(Beneficiary.id == beneficiary_id).first()
    if not beneficiary:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Beneficiary with ID {beneficiary_id} not found.",
        )
    if beneficiary.disaster_id != disaster_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Beneficiary #{beneficiary_id} is registered under disaster #{beneficiary.disaster_id}, "
                f"not disaster #{disaster_id}."
            ),
        )
    if not is_beneficiary_eligible(beneficiary):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Beneficiary '{beneficiary.name}' is currently in '{beneficiary.registration_status.value}' status. "
                f"Only VERIFIED beneficiaries are eligible to receive relief distributions."
            ),
        )

    # 3. Validate Distribution Center & Operational Eligibility
    center = db.query(DistributionCenter).filter(DistributionCenter.id == distribution_center_id).first()
    if not center:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Distribution center with ID {distribution_center_id} not found.",
        )
    if center.disaster_id != disaster_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Distribution center #{distribution_center_id} is assigned to disaster #{center.disaster_id}, "
                f"not disaster #{disaster_id}."
            ),
        )
    if not is_center_eligible_for_distribution(center):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Distribution center '{center.name}' is currently in '{center.status.value}' status. "
                f"Distributions can only be dispatched from ACTIVE distribution centers."
            ),
        )

    # 4. Validate Target Inventory Item
    target_item = (
        db.query(InventoryItem)
        .filter(InventoryItem.id == inventory_item_id)
        .with_for_update()
        .first()
    )
    if not target_item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Inventory item with ID {inventory_item_id} not found.",
        )
    if target_item.disaster_id != disaster_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Inventory item #{inventory_item_id} belongs to disaster #{target_item.disaster_id}, "
                f"not disaster #{disaster_id}."
            ),
        )
    if target_item.status != InventoryStatus.STORED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Inventory item #{inventory_item_id} ('{target_item.item_name}') has status '{target_item.status.value}'. "
                f"Only inventory items in STORED status can be distributed."
            ),
        )
    if target_item.unit.strip().lower() != unit.strip().lower():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Unit mismatch: requested distribution in '{unit}' but inventory item #{inventory_item_id} "
                f"is measured in '{target_item.unit}'."
            ),
        )
    if item_name and target_item.item_name.strip().lower() != item_name.strip().lower():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Item name mismatch: specified '{item_name}' but inventory item #{inventory_item_id} "
                f"is '{target_item.item_name}'."
            ),
        )

    # 5. Query candidate STORED batches for multi-batch allocation
    # Lock matching batches with FOR UPDATE to prevent race conditions during deduction
    candidate_batches: List[InventoryItem] = (
        db.query(InventoryItem)
        .filter(
            InventoryItem.disaster_id == disaster_id,
            func.lower(InventoryItem.item_name) == target_item.item_name.strip().lower(),
            func.lower(InventoryItem.unit) == target_item.unit.strip().lower(),
            InventoryItem.status == InventoryStatus.STORED,
        )
        .order_by(
            (InventoryItem.id != target_item.id),  # Primary target batch first
            InventoryItem.id.asc(),
        )
        .with_for_update()
        .all()
    )

    total_available = sum(b.quantity for b in candidate_batches)
    if quantity > round(total_available, 6):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Insufficient inventory for '{target_item.item_name}': requested {quantity} {target_item.unit}, "
                f"but only {total_available:.1f} {target_item.unit} available in STORED stock."
            ),
        )

    # 6. Execute atomic stock deduction across batches
    remaining_to_deduct = quantity
    for batch in candidate_batches:
        if remaining_to_deduct <= 0:
            break
        if batch.quantity <= 0:
            continue

        if batch.quantity <= remaining_to_deduct + 1e-7:
            # Fully deplete this batch
            deducted = batch.quantity
            batch.quantity = 0.0
            batch.status = InventoryStatus.DISTRIBUTED
            remaining_to_deduct -= deducted
        else:
            # Partially deduct from this batch
            batch.quantity = round(batch.quantity - remaining_to_deduct, 4)
            # Status remains STORED
            remaining_to_deduct = 0.0
            break

    # 7. Create immutable distribution record
    now = distributed_at or datetime.now(timezone.utc)
    distribution = ResourceDistribution(
        disaster_id=disaster_id,
        inventory_item_id=target_item.id,
        beneficiary_id=beneficiary_id,
        distribution_center_id=distribution_center_id,
        quantity=quantity,
        unit=target_item.unit,
        item_name=target_item.item_name,
        distributed_by_id=distributed_by_id,
        distributed_at=now,
        notes=notes.strip() if notes else None,
    )

    try:
        db.add(distribution)
        db.commit()
        db.refresh(distribution)
    except Exception:
        db.rollback()
        raise

    return distribution


def get_distributions(
    db: Session,
    disaster_id: Optional[int] = None,
    beneficiary_id: Optional[int] = None,
    distribution_center_id: Optional[int] = None,
    inventory_item_id: Optional[int] = None,
    skip: int = 0,
    limit: int = 100,
) -> List[ResourceDistribution]:
    """
    Retrieves filtered resource distribution records.
    """
    query = db.query(ResourceDistribution)

    if disaster_id is not None:
        query = query.filter(ResourceDistribution.disaster_id == disaster_id)
    if beneficiary_id is not None:
        query = query.filter(ResourceDistribution.beneficiary_id == beneficiary_id)
    if distribution_center_id is not None:
        query = query.filter(ResourceDistribution.distribution_center_id == distribution_center_id)
    if inventory_item_id is not None:
        query = query.filter(ResourceDistribution.inventory_item_id == inventory_item_id)

    return query.order_by(ResourceDistribution.created_at.desc()).offset(skip).limit(limit).all()


def get_distribution_by_id(
    db: Session,
    distribution_id: int,
) -> Optional[ResourceDistribution]:
    """
    Retrieves a single distribution record by its primary key ID.
    """
    return db.query(ResourceDistribution).filter(ResourceDistribution.id == distribution_id).first()
