"""
Disaster/Event Management Endpoints.

Provides full REST CRUD operations:
- POST /api/v1/disasters (ADMIN, NGO_STAFF)
- GET /api/v1/disasters (Authenticated, optional status filter)
- GET /api/v1/disasters/{disaster_id} (Authenticated)
- PUT /api/v1/disasters/{disaster_id} (ADMIN, NGO_STAFF)
- DELETE /api/v1/disasters/{disaster_id} (ADMIN only)
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query, Response
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_current_user, require_roles
from app.models.user import User, UserRole
from app.models.disaster import Disaster, DisasterStatus
from app.schemas.disaster import DisasterCreate, DisasterUpdate, DisasterResponse

router = APIRouter()


@router.post(
    "",
    response_model=DisasterResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new disaster/event",
    description="Registers a new disaster operation. Restricted to ADMIN and NGO_STAFF roles.",
)
def create_disaster(
    disaster_in: DisasterCreate,
    current_user: User = Depends(require_roles([UserRole.ADMIN, UserRole.NGO_STAFF])),
    db: Session = Depends(get_db),
) -> Disaster:
    """
    Creates a new disaster record with the authenticated user as the creator.
    """
    new_disaster = Disaster(
        name=disaster_in.name,
        description=disaster_in.description,
        location=disaster_in.location,
        status=disaster_in.status,
        start_date=disaster_in.start_date,
        end_date=disaster_in.end_date,
        created_by_id=current_user.id,
    )
    db.add(new_disaster)
    db.commit()
    db.refresh(new_disaster)
    return new_disaster


@router.get(
    "",
    response_model=List[DisasterResponse],
    summary="List all disasters",
    description="Returns a list of all disasters. Supports optional filtering by operational status.",
)
def list_disasters(
    status_filter: Optional[DisasterStatus] = Query(None, alias="status", description="Filter by status"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> List[Disaster]:
    """
    Retrieves all disasters, optionally filtered by status (ACTIVE, CONTAINED, RESOLVED).
    Requires any authenticated user.
    """
    query = db.query(Disaster)
    if status_filter:
        query = query.filter(Disaster.status == status_filter)
    return query.order_by(Disaster.created_at.desc()).all()


@router.get(
    "/{disaster_id}",
    response_model=DisasterResponse,
    summary="Get disaster details by ID",
    description="Retrieves a single disaster record by its ID. Requires authentication.",
)
def get_disaster(
    disaster_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Disaster:
    """
    Fetches a disaster record by ID. Returns 404 if not found.
    """
    disaster = db.query(Disaster).filter(Disaster.id == disaster_id).first()
    if not disaster:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Disaster with ID {disaster_id} not found",
        )
    return disaster


@router.put(
    "/{disaster_id}",
    response_model=DisasterResponse,
    summary="Update an existing disaster",
    description="Updates fields of an existing disaster. Restricted to ADMIN and NGO_STAFF roles.",
)
def update_disaster(
    disaster_id: int,
    disaster_in: DisasterUpdate,
    current_user: User = Depends(require_roles([UserRole.ADMIN, UserRole.NGO_STAFF])),
    db: Session = Depends(get_db),
) -> Disaster:
    """
    Updates a disaster record. Validates dates and returns 404 if not found.
    """
    disaster = db.query(Disaster).filter(Disaster.id == disaster_id).first()
    if not disaster:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Disaster with ID {disaster_id} not found",
        )

    # Determine effective start and end dates to guarantee date consistency
    update_data = disaster_in.model_dump(exclude_unset=True)

    effective_start = update_data.get("start_date", disaster.start_date)
    effective_end = update_data.get("end_date", disaster.end_date)

    if effective_end and effective_end < effective_start:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="end_date cannot be earlier than start_date",
        )

    for field, value in update_data.items():
        setattr(disaster, field, value)

    db.commit()
    db.refresh(disaster)
    return disaster


@router.delete(
    "/{disaster_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a disaster",
    description="Permanently deletes a disaster record. Restricted exclusively to ADMIN role.",
)
def delete_disaster(
    disaster_id: int,
    current_user: User = Depends(require_roles([UserRole.ADMIN])),
    db: Session = Depends(get_db),
):
    """
    Deletes a disaster record. Only ADMIN users are authorized. Returns 204 No Content.
    """
    disaster = db.query(Disaster).filter(Disaster.id == disaster_id).first()
    if not disaster:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Disaster with ID {disaster_id} not found",
        )

    db.delete(disaster)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
