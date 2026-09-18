"""
Donation Management Endpoints.

Provides full REST operations for managing monetary and material relief contributions:
- POST /api/v1/donations (DONOR, ADMIN, NGO_STAFF)
- GET /api/v1/donations (Scoped for DONOR, full view for ADMIN/STAFF)
- GET /api/v1/donations/{donation_id} (IDOR protected)
- PUT /api/v1/donations/{donation_id} (Update details while PLEDGED)
- PATCH /api/v1/donations/{donation_id}/status (Staff/Admin state machine transitions)
- DELETE /api/v1/donations/{donation_id} (ADMIN only)
"""

from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query, Response
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_current_user, require_roles
from app.models.user import User, UserRole
from app.models.disaster import Disaster
from app.models.donation import Donation, DonationType, DonationStatus
from app.schemas.donation import (
    DonationCreate,
    DonationUpdate,
    DonationStatusUpdate,
    DonationResponse,
)

router = APIRouter()


@router.post(
    "",
    response_model=DonationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create or pledge a donation",
    description=(
        "Records a monetary or material donation. Donors can create donations for themselves. "
        "Admins and NGO Staff can record donations on behalf of any donor."
    ),
)
def create_donation(
    donation_in: DonationCreate,
    current_user: User = Depends(
        require_roles([UserRole.ADMIN, UserRole.NGO_STAFF, UserRole.DONOR])
    ),
    db: Session = Depends(get_db),
) -> Donation:
    """
    Creates a new donation record.
    - If caller is a DONOR: enforces donor_id == current_user.id.
    - If caller is ADMIN/STAFF: uses provided donor_id (or defaults to current_user.id).
    - Validates target disaster and donor exist in the database.
    """
    # 1. Determine effective donor ID
    if current_user.role == UserRole.DONOR:
        if donation_in.donor_id and donation_in.donor_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Donors cannot create donations on behalf of another user",
            )
        effective_donor_id = current_user.id
    else:
        effective_donor_id = donation_in.donor_id or current_user.id

    # 2. Validate target donor exists
    donor = db.query(User).filter(User.id == effective_donor_id).first()
    if not donor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Donor user with ID {effective_donor_id} not found",
        )

    # 3. Validate target disaster exists
    disaster = db.query(Disaster).filter(Disaster.id == donation_in.disaster_id).first()
    if not disaster:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Disaster with ID {donation_in.disaster_id} not found",
        )

    # 4. Create donation
    new_donation = Donation(
        donor_id=effective_donor_id,
        disaster_id=donation_in.disaster_id,
        donation_type=donation_in.donation_type,
        amount=donation_in.amount if donation_in.donation_type == DonationType.MONEY else None,
        item_name=donation_in.item_name if donation_in.donation_type == DonationType.MATERIAL else None,
        quantity=donation_in.quantity if donation_in.donation_type == DonationType.MATERIAL else None,
        unit=donation_in.unit if donation_in.donation_type == DonationType.MATERIAL else None,
        status=DonationStatus.PLEDGED,
        notes=donation_in.notes,
    )
    db.add(new_donation)
    db.commit()
    db.refresh(new_donation)
    return new_donation


@router.get(
    "",
    response_model=List[DonationResponse],
    summary="List donations",
    description=(
        "Lists donations. Admins and NGO Staff can see all donations. "
        "Donors can only see their own donations. Supports filtering by disaster, type, and status."
    ),
)
def list_donations(
    disaster_id: Optional[int] = Query(None, description="Filter by disaster ID"),
    donation_type: Optional[DonationType] = Query(None, description="Filter by MONEY or MATERIAL"),
    donation_status: Optional[DonationStatus] = Query(None, alias="status", description="Filter by status"),
    current_user: User = Depends(
        require_roles([UserRole.ADMIN, UserRole.NGO_STAFF, UserRole.DONOR])
    ),
    db: Session = Depends(get_db),
) -> List[Donation]:
    query = db.query(Donation)

    # Scoping: Donors can only inspect their own records
    if current_user.role == UserRole.DONOR:
        query = query.filter(Donation.donor_id == current_user.id)

    # Apply filters
    if disaster_id:
        query = query.filter(Donation.disaster_id == disaster_id)
    if donation_type:
        query = query.filter(Donation.donation_type == donation_type)
    if donation_status:
        query = query.filter(Donation.status == donation_status)

    return query.order_by(Donation.created_at.desc()).all()


@router.get(
    "/{donation_id}",
    response_model=DonationResponse,
    summary="Get donation by ID",
    description="Retrieves details of a donation. Donors can only view their own donations.",
)
def get_donation(
    donation_id: int,
    current_user: User = Depends(
        require_roles([UserRole.ADMIN, UserRole.NGO_STAFF, UserRole.DONOR])
    ),
    db: Session = Depends(get_db),
) -> Donation:
    donation = db.query(Donation).filter(Donation.id == donation_id).first()
    if not donation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Donation with ID {donation_id} not found",
        )

    # Protect against Insecure Direct Object Reference (IDOR)
    if current_user.role == UserRole.DONOR and donation.donor_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to view this donation",
        )

    return donation


@router.put(
    "/{donation_id}",
    response_model=DonationResponse,
    summary="Update donation details",
    description=(
        "Updates details of a donation. Staff/Admin can edit any donation. "
        "Donors can only edit their own donation while it is still in PLEDGED status."
    ),
)
def update_donation(
    donation_id: int,
    donation_in: DonationUpdate,
    current_user: User = Depends(
        require_roles([UserRole.ADMIN, UserRole.NGO_STAFF, UserRole.DONOR])
    ),
    db: Session = Depends(get_db),
) -> Donation:
    donation = db.query(Donation).filter(Donation.id == donation_id).first()
    if not donation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Donation with ID {donation_id} not found",
        )

    # Authorization & Status lock check
    if current_user.role == UserRole.DONOR:
        if donation.donor_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to modify this donation",
            )
        if donation.status != DonationStatus.PLEDGED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Donors cannot modify a donation with status '{donation.status.value}'",
            )

    update_data = donation_in.model_dump(exclude_unset=True)
    for field, val in update_data.items():
        setattr(donation, field, val)

    db.commit()
    db.refresh(donation)
    return donation


@router.patch(
    "/{donation_id}/status",
    response_model=DonationResponse,
    summary="Update donation status (State Machine)",
    description=(
        "Transitions the donation status. Restricted to ADMIN and NGO_STAFF. "
        "Valid transitions: PLEDGED -> RECEIVED, PLEDGED -> CANCELLED. "
        "Terminal statuses (RECEIVED, CANCELLED) cannot be changed."
    ),
)
def update_donation_status(
    donation_id: int,
    status_in: DonationStatusUpdate,
    current_user: User = Depends(require_roles([UserRole.ADMIN, UserRole.NGO_STAFF])),
    db: Session = Depends(get_db),
) -> Donation:
    donation = db.query(Donation).filter(Donation.id == donation_id).first()
    if not donation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Donation with ID {donation_id} not found",
        )

    current_status = donation.status
    target_status = status_in.status

    # State machine transition rules
    if current_status == DonationStatus.PLEDGED:
        if target_status not in [DonationStatus.RECEIVED, DonationStatus.CANCELLED]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid transition from '{current_status.value}' to '{target_status.value}'",
            )
        if target_status == DonationStatus.RECEIVED:
            donation.received_at = datetime.now(timezone.utc)
    elif current_status in [DonationStatus.RECEIVED, DonationStatus.CANCELLED]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot transition status from terminal state '{current_status.value}'",
        )

    donation.status = target_status
    db.commit()
    db.refresh(donation)
    return donation


@router.delete(
    "/{donation_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a donation record",
    description="Permanently deletes a donation record. Restricted exclusively to ADMIN.",
)
def delete_donation(
    donation_id: int,
    current_user: User = Depends(require_roles([UserRole.ADMIN])),
    db: Session = Depends(get_db),
):
    donation = db.query(Donation).filter(Donation.id == donation_id).first()
    if not donation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Donation with ID {donation_id} not found",
        )

    db.delete(donation)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
