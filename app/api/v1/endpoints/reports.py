"""
Report & Summary Endpoints.

Provides read-only operational analytics, inventory levels, relief dispatches,
volunteer mobilization, and beneficiary demographic reports for disaster relief operations.
Restricted to ADMIN and NGO_STAFF roles.
"""

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_roles
from app.models.user import User, UserRole
from app.schemas.report import (
    DisasterSummaryResponse,
    InventoryReportResponse,
    DistributionReportResponse,
    VolunteerReportResponse,
    BeneficiaryReportResponse,
)
from app.services.report_service import (
    get_disaster_summary_report,
    get_inventory_report,
    get_distribution_report,
    get_volunteer_report,
    get_beneficiary_report,
)

router = APIRouter()


@router.get(
    "/disasters/{disaster_id}/summary",
    response_model=DisasterSummaryResponse,
    status_code=status.HTTP_200_OK,
    summary="Get disaster operational summary report",
    description=(
        "Retrieves a cross-module operational summary for a disaster relief event. "
        "Includes aggregate counts for beneficiaries, volunteers, tasks, donations, "
        "warehouse inventory, distribution centers, and resource dispatches. "
        "Restricted to ADMIN and NGO_STAFF roles."
    ),
    responses={
        401: {"description": "Unauthenticated access"},
        403: {"description": "Forbidden for VOLUNTEER or DONOR roles"},
        404: {"description": "Disaster not found"},
    },
)
def read_disaster_summary(
    disaster_id: int,
    current_user: User = Depends(require_roles([UserRole.ADMIN, UserRole.NGO_STAFF])),
    db: Session = Depends(get_db),
) -> DisasterSummaryResponse:
    """
    Returns high-level operational statistics for the specified disaster.
    """
    return get_disaster_summary_report(db=db, disaster_id=disaster_id)


@router.get(
    "/disasters/{disaster_id}/inventory",
    response_model=InventoryReportResponse,
    status_code=status.HTTP_200_OK,
    summary="Get disaster warehouse inventory report",
    description=(
        "Retrieves warehouse inventory stock metrics for a disaster relief operation. "
        "Breaks down total batches by status (RECEIVED, STORED, DISTRIBUTED) and "
        "provides per-item original intake vs currently available STORED balance. "
        "Restricted to ADMIN and NGO_STAFF roles."
    ),
    responses={
        401: {"description": "Unauthenticated access"},
        403: {"description": "Forbidden for VOLUNTEER or DONOR roles"},
        404: {"description": "Disaster not found"},
    },
)
def read_inventory_report(
    disaster_id: int,
    current_user: User = Depends(require_roles([UserRole.ADMIN, UserRole.NGO_STAFF])),
    db: Session = Depends(get_db),
) -> InventoryReportResponse:
    """
    Returns inventory batches and available stock for the specified disaster.
    """
    return get_inventory_report(db=db, disaster_id=disaster_id)


@router.get(
    "/disasters/{disaster_id}/distributions",
    response_model=DistributionReportResponse,
    status_code=status.HTTP_200_OK,
    summary="Get disaster resource distributions report",
    description=(
        "Retrieves aid distribution analytics for a disaster relief operation. "
        "Includes total disbursed volume, distributions grouped by relief item and unit, "
        "and dispatch counts per distribution center. "
        "Restricted to ADMIN and NGO_STAFF roles."
    ),
    responses={
        401: {"description": "Unauthenticated access"},
        403: {"description": "Forbidden for VOLUNTEER or DONOR roles"},
        404: {"description": "Disaster not found"},
    },
)
def read_distribution_report(
    disaster_id: int,
    current_user: User = Depends(require_roles([UserRole.ADMIN, UserRole.NGO_STAFF])),
    db: Session = Depends(get_db),
) -> DistributionReportResponse:
    """
    Returns distribution transactions and volume metrics for the specified disaster.
    """
    return get_distribution_report(db=db, disaster_id=disaster_id)


@router.get(
    "/disasters/{disaster_id}/volunteers",
    response_model=VolunteerReportResponse,
    status_code=status.HTTP_200_OK,
    summary="Get disaster volunteer mobilization report",
    description=(
        "Retrieves volunteer mobilization metrics for a disaster relief operation. "
        "Includes active/completed volunteer assignments, task status breakdowns, "
        "and overall task completion percentage. "
        "Restricted to ADMIN and NGO_STAFF roles."
    ),
    responses={
        401: {"description": "Unauthenticated access"},
        403: {"description": "Forbidden for VOLUNTEER or DONOR roles"},
        404: {"description": "Disaster not found"},
    },
)
def read_volunteer_report(
    disaster_id: int,
    current_user: User = Depends(require_roles([UserRole.ADMIN, UserRole.NGO_STAFF])),
    db: Session = Depends(get_db),
) -> VolunteerReportResponse:
    """
    Returns volunteer assignment and task completion metrics for the specified disaster.
    """
    return get_volunteer_report(db=db, disaster_id=disaster_id)


@router.get(
    "/disasters/{disaster_id}/beneficiaries",
    response_model=BeneficiaryReportResponse,
    status_code=status.HTTP_200_OK,
    summary="Get disaster beneficiary demographic report",
    description=(
        "Retrieves aggregate beneficiary demographic and vulnerability statistics. "
        "Includes verification status counts and distributions across vulnerability groups. "
        "Guarantees privacy by withholding all personally identifiable information (PII). "
        "Restricted to ADMIN and NGO_STAFF roles."
    ),
    responses={
        401: {"description": "Unauthenticated access"},
        403: {"description": "Forbidden for VOLUNTEER or DONOR roles"},
        404: {"description": "Disaster not found"},
    },
)
def read_beneficiary_report(
    disaster_id: int,
    current_user: User = Depends(require_roles([UserRole.ADMIN, UserRole.NGO_STAFF])),
    db: Session = Depends(get_db),
) -> BeneficiaryReportResponse:
    """
    Returns aggregate beneficiary metrics without personal information for the specified disaster.
    """
    return get_beneficiary_report(db=db, disaster_id=disaster_id)
