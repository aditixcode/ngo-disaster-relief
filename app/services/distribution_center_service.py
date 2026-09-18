"""
Distribution Center Service Layer.

Encapsulates business rules for distribution center operational eligibility
and duplicate center naming detection.
"""

from typing import Optional
from sqlalchemy.orm import Session
from app.models.distribution_center import DistributionCenter, CenterStatus


def is_center_eligible_for_distribution(center: Optional[DistributionCenter]) -> bool:
    """
    Evaluates whether a distribution center is currently operational and permitted
    to dispatch relief resources to beneficiaries.

    Core Business Rules:
    - ACTIVE: Facility is open and within operating capacity (ELIGIBLE).
    - FULL: Declared recipient throughput reached; new dispatches blocked (INELIGIBLE).
    - INACTIVE: Facility is temporarily or permanently closed (INELIGIBLE).
    """
    if not center:
        return False
    return center.status == CenterStatus.ACTIVE


def check_duplicate_center_name(
    db: Session,
    disaster_id: int,
    name: str,
    exclude_id: Optional[int] = None,
) -> bool:
    """
    Checks if another distribution center under the same disaster event
    already uses the proposed name (case-insensitive).

    Returns True if a duplicate exists, False otherwise.
    """
    clean_name = name.strip()
    query = db.query(DistributionCenter).filter(
        DistributionCenter.disaster_id == disaster_id,
        DistributionCenter.name.ilike(clean_name),
    )

    if exclude_id is not None:
        query = query.filter(DistributionCenter.id != exclude_id)

    return db.query(query.exists()).scalar()
