"""
Beneficiary Management Endpoints.

Handles registration, demographic updates, and verification status lifecycle for relief beneficiaries.
Enforces role-based permissions (ADMIN, NGO_STAFF), duplicate checking, and strict lifecycle transitions:
PENDING -> VERIFIED / INACTIVE
VERIFIED -> INACTIVE
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_roles
from app.models.user import User, UserRole
from app.models.disaster import Disaster
from app.models.beneficiary import Beneficiary, VulnerabilityCategory, RegistrationStatus
from app.schemas.beneficiary import (
    BeneficiaryCreate,
    BeneficiaryUpdate,
    BeneficiaryStatusUpdate,
    BeneficiaryResponse,
)
from app.services.beneficiary_service import check_duplicate_beneficiary

router = APIRouter()


@router.post(
    "",
    response_model=BeneficiaryResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new disaster relief beneficiary",
    description=(
        "Registers an individual or household eligible for emergency resources. "
        "Initial status is set to PENDING pending field verification. "
        "Restricted to ADMIN and NGO_STAFF roles."
    ),
)
def create_beneficiary(
    beneficiary_in: BeneficiaryCreate,
    current_user: User = Depends(require_roles([UserRole.ADMIN, UserRole.NGO_STAFF])),
    db: Session = Depends(get_db),
) -> Beneficiary:
    """
    Intakes a new beneficiary record.
    1. Validates that the disaster exists.
    2. Enforces duplicate protection on (disaster_id, name, contact_number).
    3. Records registered_by_id as the authenticated staff/admin.
    4. Automatically initializes registration_status to PENDING.
    """
    # 1. Validate disaster
    disaster = db.query(Disaster).filter(Disaster.id == beneficiary_in.disaster_id).first()
    if not disaster:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Disaster with ID {beneficiary_in.disaster_id} not found",
        )

    # 2. Check for duplicate registration within the same disaster
    if check_duplicate_beneficiary(
        db=db,
        disaster_id=beneficiary_in.disaster_id,
        name=beneficiary_in.name,
        contact_number=beneficiary_in.contact_number,
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Beneficiary '{beneficiary_in.name.strip()}' with contact '{beneficiary_in.contact_number.strip()}' "
                f"is already registered under Disaster ID {beneficiary_in.disaster_id}"
            ),
        )

    # 3. Create beneficiary
    new_beneficiary = Beneficiary(
        disaster_id=beneficiary_in.disaster_id,
        name=beneficiary_in.name.strip(),
        contact_number=beneficiary_in.contact_number.strip(),
        address=beneficiary_in.address.strip(),
        household_size=beneficiary_in.household_size,
        vulnerability_category=beneficiary_in.vulnerability_category,
        registration_status=RegistrationStatus.PENDING,
        registered_by_id=current_user.id,
    )
    db.add(new_beneficiary)
    db.commit()
    db.refresh(new_beneficiary)
    return new_beneficiary


@router.get(
    "",
    response_model=List[BeneficiaryResponse],
    summary="List registered beneficiaries",
    description=(
        "Lists beneficiaries with optional filtering by disaster, vulnerability category, or status. "
        "Restricted to ADMIN and NGO_STAFF roles to protect vulnerable beneficiary privacy."
    ),
)
def list_beneficiaries(
    disaster_id: Optional[int] = Query(None, description="Filter by disaster ID"),
    vulnerability_category: Optional[VulnerabilityCategory] = Query(None, description="Filter by vulnerability category"),
    registration_status: Optional[RegistrationStatus] = Query(None, alias="status", description="Filter by registration status"),
    current_user: User = Depends(require_roles([UserRole.ADMIN, UserRole.NGO_STAFF])),
    db: Session = Depends(get_db),
) -> List[Beneficiary]:
    """
    Retrieves beneficiary list with flexible filtering.
    """
    query = db.query(Beneficiary)
    if disaster_id is not None:
        query = query.filter(Beneficiary.disaster_id == disaster_id)
    if vulnerability_category is not None:
        query = query.filter(Beneficiary.vulnerability_category == vulnerability_category)
    if registration_status is not None:
        query = query.filter(Beneficiary.registration_status == registration_status)

    return query.order_by(Beneficiary.created_at.desc()).all()


@router.get(
    "/{beneficiary_id}",
    response_model=BeneficiaryResponse,
    summary="Get beneficiary details by ID",
    description="Retrieves a specific beneficiary profile. Restricted to ADMIN and NGO_STAFF.",
)
def get_beneficiary(
    beneficiary_id: int,
    current_user: User = Depends(require_roles([UserRole.ADMIN, UserRole.NGO_STAFF])),
    db: Session = Depends(get_db),
) -> Beneficiary:
    beneficiary = db.query(Beneficiary).filter(Beneficiary.id == beneficiary_id).first()
    if not beneficiary:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Beneficiary with ID {beneficiary_id} not found",
        )
    return beneficiary


@router.put(
    "/{beneficiary_id}",
    response_model=BeneficiaryResponse,
    summary="Update beneficiary details",
    description="Updates demographic or household information of a beneficiary. Restricted to ADMIN and NGO_STAFF.",
)
def update_beneficiary(
    beneficiary_id: int,
    beneficiary_in: BeneficiaryUpdate,
    current_user: User = Depends(require_roles([UserRole.ADMIN, UserRole.NGO_STAFF])),
    db: Session = Depends(get_db),
) -> Beneficiary:
    """
    Updates beneficiary details with duplicate collision prevention.
    """
    beneficiary = db.query(Beneficiary).filter(Beneficiary.id == beneficiary_id).first()
    if not beneficiary:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Beneficiary with ID {beneficiary_id} not found",
        )

    # If name or contact number is modified, check duplicate constraint
    target_name = beneficiary_in.name.strip() if beneficiary_in.name is not None else beneficiary.name
    target_contact = (
        beneficiary_in.contact_number.strip()
        if beneficiary_in.contact_number is not None
        else beneficiary.contact_number
    )

    if target_name != beneficiary.name or target_contact != beneficiary.contact_number:
        if check_duplicate_beneficiary(
            db=db,
            disaster_id=beneficiary.disaster_id,
            name=target_name,
            contact_number=target_contact,
            exclude_id=beneficiary.id,
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Another beneficiary with name '{target_name}' and contact '{target_contact}' already exists",
            )

    # Apply updates
    if beneficiary_in.name is not None:
        beneficiary.name = target_name
    if beneficiary_in.contact_number is not None:
        beneficiary.contact_number = target_contact
    if beneficiary_in.address is not None:
        beneficiary.address = beneficiary_in.address.strip()
    if beneficiary_in.household_size is not None:
        beneficiary.household_size = beneficiary_in.household_size
    if beneficiary_in.vulnerability_category is not None:
        beneficiary.vulnerability_category = beneficiary_in.vulnerability_category

    db.commit()
    db.refresh(beneficiary)
    return beneficiary


@router.patch(
    "/{beneficiary_id}/status",
    response_model=BeneficiaryResponse,
    summary="Update beneficiary verification status",
    description=(
        "Enforces the verification state machine: "
        "PENDING -> VERIFIED / INACTIVE, and VERIFIED -> INACTIVE. "
        "Rejects backward transitions (e.g. VERIFIED -> PENDING) or reactivation of INACTIVE cases."
    ),
)
def update_beneficiary_status(
    beneficiary_id: int,
    status_in: BeneficiaryStatusUpdate,
    current_user: User = Depends(require_roles([UserRole.ADMIN, UserRole.NGO_STAFF])),
    db: Session = Depends(get_db),
) -> Beneficiary:
    """
    State machine validation:
    - PENDING -> VERIFIED: Valid (field inspection passed).
    - PENDING -> INACTIVE: Valid (invalid or duplicate claim).
    - VERIFIED -> INACTIVE: Valid (relocated, resolved, or archived).
    - VERIFIED -> PENDING: Invalid (HTTP 400).
    - INACTIVE -> VERIFIED: Invalid (HTTP 400 - cannot reactivate closed file).
    - INACTIVE -> PENDING: Invalid (HTTP 400).
    """
    beneficiary = db.query(Beneficiary).filter(Beneficiary.id == beneficiary_id).first()
    if not beneficiary:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Beneficiary with ID {beneficiary_id} not found",
        )

    current_status = beneficiary.registration_status
    target_status = status_in.status

    if current_status == RegistrationStatus.PENDING:
        if target_status in (RegistrationStatus.VERIFIED, RegistrationStatus.INACTIVE):
            beneficiary.registration_status = target_status
        elif target_status == RegistrationStatus.PENDING:
            pass  # No-op
    elif current_status == RegistrationStatus.VERIFIED:
        if target_status == RegistrationStatus.INACTIVE:
            beneficiary.registration_status = target_status
        elif target_status == RegistrationStatus.PENDING:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot revert a VERIFIED beneficiary back to PENDING status",
            )
        elif target_status == RegistrationStatus.VERIFIED:
            pass  # No-op
    elif current_status == RegistrationStatus.INACTIVE:
        if target_status != RegistrationStatus.INACTIVE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot modify or reactivate an INACTIVE beneficiary record",
            )

    db.commit()
    db.refresh(beneficiary)
    return beneficiary


@router.delete(
    "/{beneficiary_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a beneficiary record",
    description="Permanently removes a beneficiary record. Restricted strictly to ADMIN role.",
)
def delete_beneficiary(
    beneficiary_id: int,
    current_user: User = Depends(require_roles([UserRole.ADMIN])),
    db: Session = Depends(get_db),
) -> None:
    """
    Deletes a beneficiary. Restricted exclusively to ADMIN.
    """
    beneficiary = db.query(Beneficiary).filter(Beneficiary.id == beneficiary_id).first()
    if not beneficiary:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Beneficiary with ID {beneficiary_id} not found",
        )

    db.delete(beneficiary)
    db.commit()
    return None
