"""
Resource Distribution Endpoints.

Handles recording and auditing of relief resource distributions to verified beneficiaries.
Enforces role-based permissions (ADMIN, NGO_STAFF), cross-entity disaster integrity,
beneficiary eligibility vetting, distribution center operational status, and atomic inventory deduction.
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_roles
from app.models.user import User, UserRole
from app.models.distribution import ResourceDistribution
from app.schemas.distribution import (
    ResourceDistributionCreate,
    ResourceDistributionResponse,
)
from app.services.distribution_service import (
    execute_resource_distribution,
    get_distributions,
    get_distribution_by_id,
)

router = APIRouter()


@router.post(
    "",
    response_model=ResourceDistributionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Record a resource distribution",
    description=(
        "Executes an atomic relief resource distribution transaction. "
        "Deducts inventory stock, updates batch status to DISTRIBUTED when depleted, "
        "and creates an immutable historical audit record. "
        "Restricted to ADMIN and NGO_STAFF roles."
    ),
)
def create_distribution(
    distribution_in: ResourceDistributionCreate,
    current_user: User = Depends(require_roles([UserRole.ADMIN, UserRole.NGO_STAFF])),
    db: Session = Depends(get_db),
) -> ResourceDistribution:
    """
    Records a resource distribution:
    1. Validates disaster existence.
    2. Validates beneficiary existence, matching disaster, and VERIFIED status.
    3. Validates distribution center existence, matching disaster, and ACTIVE status.
    4. Validates target inventory batch existence, matching disaster, STORED status, and matching unit.
    5. Validates total available STORED stock across matching batches.
    6. Atomically deducts inventory (depleting primary batch first, then sibling batches if needed).
    7. Records the authenticated staff/admin as distributed_by_id.
    8. Creates and commits the immutable ResourceDistribution audit log.
    """
    return execute_resource_distribution(
        db=db,
        disaster_id=distribution_in.disaster_id,
        inventory_item_id=distribution_in.inventory_item_id,
        beneficiary_id=distribution_in.beneficiary_id,
        distribution_center_id=distribution_in.distribution_center_id,
        quantity=distribution_in.quantity,
        unit=distribution_in.unit,
        distributed_by_id=current_user.id,
        item_name=distribution_in.item_name,
        notes=distribution_in.notes,
        distributed_at=distribution_in.distributed_at,
    )


@router.get(
    "",
    response_model=List[ResourceDistributionResponse],
    summary="List resource distributions",
    description=(
        "Retrieves historical resource distribution audit records with optional filtering. "
        "Restricted to ADMIN and NGO_STAFF roles."
    ),
)
def list_distributions(
    disaster_id: Optional[int] = Query(None, description="Filter by disaster ID"),
    beneficiary_id: Optional[int] = Query(None, description="Filter by beneficiary ID"),
    distribution_center_id: Optional[int] = Query(None, description="Filter by distribution center ID"),
    inventory_item_id: Optional[int] = Query(None, description="Filter by inventory item ID"),
    skip: int = Query(0, ge=0, description="Records to skip for pagination"),
    limit: int = Query(100, ge=1, le=500, description="Max records to return"),
    current_user: User = Depends(require_roles([UserRole.ADMIN, UserRole.NGO_STAFF])),
    db: Session = Depends(get_db),
) -> List[ResourceDistribution]:
    """
    Lists distribution records with optional filters.
    """
    return get_distributions(
        db=db,
        disaster_id=disaster_id,
        beneficiary_id=beneficiary_id,
        distribution_center_id=distribution_center_id,
        inventory_item_id=inventory_item_id,
        skip=skip,
        limit=limit,
    )


@router.get(
    "/{distribution_id}",
    response_model=ResourceDistributionResponse,
    summary="Get resource distribution by ID",
    description=(
        "Retrieves a single immutable resource distribution audit record by primary key ID. "
        "Restricted to ADMIN and NGO_STAFF roles."
    ),
)
def get_distribution(
    distribution_id: int,
    current_user: User = Depends(require_roles([UserRole.ADMIN, UserRole.NGO_STAFF])),
    db: Session = Depends(get_db),
) -> ResourceDistribution:
    """
    Retrieves distribution record or raises 404.
    """
    distribution = get_distribution_by_id(db=db, distribution_id=distribution_id)
    if not distribution:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Resource distribution record with ID {distribution_id} not found.",
        )
    return distribution
