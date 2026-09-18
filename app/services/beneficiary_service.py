"""
Beneficiary Service Layer.

Encapsulates business rules for beneficiary eligibility verification and duplicate detection.
"""

from typing import Optional
from sqlalchemy.orm import Session
from app.models.beneficiary import Beneficiary, RegistrationStatus


def is_beneficiary_eligible(beneficiary: Beneficiary) -> bool:
    """
    Evaluates whether a beneficiary is eligible to receive disaster-relief resources.

    Core Business Rule:
    A beneficiary MUST be in VERIFIED status.
    - PENDING: Registration recorded but awaiting field inspection/vetting (INELIGIBLE).
    - INACTIVE: Deactivated, relocated, or expired case (INELIGIBLE).
    - VERIFIED: Formally verified and eligible for distribution (ELIGIBLE).
    """
    if not beneficiary:
        return False
    return beneficiary.registration_status == RegistrationStatus.VERIFIED


def check_duplicate_beneficiary(
    db: Session,
    disaster_id: int,
    name: str,
    contact_number: str,
    exclude_id: Optional[int] = None,
) -> bool:
    """
    Checks if an existing beneficiary with the same name and contact number
    is already registered under the specified disaster event.

    Prevents accidental double registration of the same person or household.
    Returns True if a duplicate exists, False otherwise.
    """
    clean_name = name.strip()
    clean_contact = contact_number.strip()

    query = db.query(Beneficiary).filter(
        Beneficiary.disaster_id == disaster_id,
        Beneficiary.name.ilike(clean_name),
        Beneficiary.contact_number == clean_contact,
    )

    if exclude_id is not None:
        query = query.filter(Beneficiary.id != exclude_id)

    return db.query(query.exists()).scalar()
