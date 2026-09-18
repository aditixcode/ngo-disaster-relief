"""
Distribution Center Endpoints.

Handles registration, configuration updates, and operational status management
for physical disaster-relief distribution hubs.
Enforces role-based permissions (ADMIN, NGO_STAFF; deletion ADMIN-only),
capacity validation, duplicate center name protection, and operational state transitions.
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_roles
from app.models.user import User, UserRole
from app.models.disaster import Disaster
from app.models.distribution_center import DistributionCenter, CenterStatus
from app.schemas.distribution_center import (
    DistributionCenterCreate,
    DistributionCenterUpdate,
    DistributionCenterStatusUpdate,
    DistributionCenterResponse,
)
from app.services.distribution_center_service import check_duplicate_center_name

router = APIRouter()


@router.post(
    "",
    response_model=DistributionCenterResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new distribution center",
    description=(
        "Registers a physical relief dispatch facility associated with a disaster operation. "
        "Initial status is set to ACTIVE automatically. "
        "Restricted to ADMIN and NGO_STAFF roles."
    ),
)
def create_distribution_center(
    center_in: DistributionCenterCreate,
    current_user: User = Depends(require_roles([UserRole.ADMIN, UserRole.NGO_STAFF])),
    db: Session = Depends(get_db),
) -> DistributionCenter:
    """
    Registers a new distribution center:
    1. Validates that the disaster exists.
    2. Enforces unique center name per disaster.
    3. Records created_by_id as the authenticated staff/admin.
    4. Automatically initializes status to ACTIVE.
    """
    # 1. Validate disaster
    disaster = db.query(Disaster).filter(Disaster.id == center_in.disaster_id).first()
    if not disaster:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Disaster with ID {center_in.disaster_id} not found",
        )

    # 2. Check duplicate center name under the same disaster
    if check_duplicate_center_name(
        db=db,
        disaster_id=center_in.disaster_id,
        name=center_in.name,
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Distribution center '{center_in.name.strip()}' already exists for Disaster ID {center_in.disaster_id}",
        )

    # 3. Create center
    new_center = DistributionCenter(
        disaster_id=center_in.disaster_id,
        name=center_in.name.strip(),
        address=center_in.address.strip(),
        contact_number=center_in.contact_number.strip(),
        capacity=center_in.capacity,
        status=CenterStatus.ACTIVE,
        operating_hours=center_in.operating_hours.strip() if center_in.operating_hours else None,
        created_by_id=current_user.id,
    )
    db.add(new_center)
    db.commit()
    db.refresh(new_center)
    return new_center


@router.get(
    "",
    response_model=List[DistributionCenterResponse],
    summary="List distribution centers",
    description=(
        "Lists relief distribution centers with optional filtering by disaster or operational status. "
        "Restricted to ADMIN and NGO_STAFF roles."
    ),
)
def list_distribution_centers(
    disaster_id: Optional[int] = Query(None, description="Filter by disaster ID"),
    center_status: Optional[CenterStatus] = Query(None, alias="status", description="Filter by status (ACTIVE, INACTIVE, FULL)"),
    current_user: User = Depends(require_roles([UserRole.ADMIN, UserRole.NGO_STAFF])),
    db: Session = Depends(get_db),
) -> List[DistributionCenter]:
    """
    Retrieves distribution centers list with optional filtering.
    """
    query = db.query(DistributionCenter)
    if disaster_id is not None:
        query = query.filter(DistributionCenter.disaster_id == disaster_id)
    if center_status is not None:
        query = query.filter(DistributionCenter.status == center_status)

    return query.order_by(DistributionCenter.created_at.desc()).all()


@router.get(
    "/{center_id}",
    response_model=DistributionCenterResponse,
    summary="Get distribution center by ID",
    description="Retrieves a specific distribution center profile. Restricted to ADMIN and NGO_STAFF.",
)
def get_distribution_center(
    center_id: int,
    current_user: User = Depends(require_roles([UserRole.ADMIN, UserRole.NGO_STAFF])),
    db: Session = Depends(get_db),
) -> DistributionCenter:
    center = db.query(DistributionCenter).filter(DistributionCenter.id == center_id).first()
    if not center:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Distribution center with ID {center_id} not found",
        )
    return center


@router.put(
    "/{center_id}",
    response_model=DistributionCenterResponse,
    summary="Update distribution center information",
    description="Modifies distribution center details or declared capacity. Restricted to ADMIN and NGO_STAFF.",
)
def update_distribution_center(
    center_id: int,
    center_in: DistributionCenterUpdate,
    current_user: User = Depends(require_roles([UserRole.ADMIN, UserRole.NGO_STAFF])),
    db: Session = Depends(get_db),
) -> DistributionCenter:
    """
    Updates distribution center details with duplicate name prevention.
    """
    center = db.query(DistributionCenter).filter(DistributionCenter.id == center_id).first()
    if not center:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Distribution center with ID {center_id} not found",
        )

    # Check duplicate name if name is changing
    if center_in.name is not None:
        target_name = center_in.name.strip()
        if target_name.lower() != center.name.lower():
            if check_duplicate_center_name(
                db=db,
                disaster_id=center.disaster_id,
                name=target_name,
                exclude_id=center.id,
            ):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Distribution center '{target_name}' already exists for Disaster ID {center.disaster_id}",
                )
        center.name = target_name

    if center_in.address is not None:
        center.address = center_in.address.strip()
    if center_in.contact_number is not None:
        center.contact_number = center_in.contact_number.strip()
    if center_in.capacity is not None:
        center.capacity = center_in.capacity
    if center_in.operating_hours is not None:
        center.operating_hours = center_in.operating_hours.strip()

    db.commit()
    db.refresh(center)
    return center


@router.patch(
    "/{center_id}/status",
    response_model=DistributionCenterResponse,
    summary="Update distribution center operational status",
    description=(
        "Updates status to ACTIVE, FULL, or INACTIVE. "
        "Enforces operational transition logic (e.g. INACTIVE center cannot transition directly to FULL). "
        "Restricted to ADMIN and NGO_STAFF."
    ),
)
def update_center_status(
    center_id: int,
    status_in: DistributionCenterStatusUpdate,
    current_user: User = Depends(require_roles([UserRole.ADMIN, UserRole.NGO_STAFF])),
    db: Session = Depends(get_db),
) -> DistributionCenter:
    """
    State machine validation:
    - ACTIVE -> FULL: Valid (facility capacity reached).
    - ACTIVE -> INACTIVE: Valid (facility temporarily closed/offline).
    - FULL -> ACTIVE: Valid (space freed / throughput expanded).
    - FULL -> INACTIVE: Valid (closed while full).
    - INACTIVE -> ACTIVE: Valid (reopened facility).
    - INACTIVE -> FULL: Invalid (facility must be reopened as ACTIVE before being considered full).
    - Same-status: No-op.
    """
    center = db.query(DistributionCenter).filter(DistributionCenter.id == center_id).first()
    if not center:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Distribution center with ID {center_id} not found",
        )

    current_status = center.status
    target_status = status_in.status

    if current_status == target_status:
        return center  # No-op

    if current_status == CenterStatus.INACTIVE and target_status == CenterStatus.FULL:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot mark an INACTIVE center as FULL directly. Reopen it as ACTIVE first.",
        )

    center.status = target_status
    db.commit()
    db.refresh(center)
    return center


@router.delete(
    "/{center_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a distribution center",
    description="Permanently removes a distribution center record. Restricted strictly to ADMIN role.",
)
def delete_distribution_center(
    center_id: int,
    current_user: User = Depends(require_roles([UserRole.ADMIN])),
    db: Session = Depends(get_db),
) -> None:
    """
    Deletes a distribution center. Restricted exclusively to ADMIN.
    """
    center = db.query(DistributionCenter).filter(DistributionCenter.id == center_id).first()
    if not center:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Distribution center with ID {center_id} not found",
        )

    db.delete(center)
    db.commit()
    return None
