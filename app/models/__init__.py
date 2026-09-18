"""
SQLAlchemy Models Package.

Re-exports Base and all ORM models so that Alembic and application modules
can import them conveniently from a single namespace.
"""

from app.core.database import Base
from app.models.user import User, UserRole
from app.models.disaster import Disaster, DisasterStatus
from app.models.volunteer import (
    VolunteerAssignment,
    VolunteerTask,
    AssignmentStatus,
    TaskStatus,
)
from app.models.donation import (
    Donation,
    DonationType,
    DonationStatus,
)
from app.models.inventory import (
    InventoryItem,
    InventoryStatus,
)
from app.models.beneficiary import (
    Beneficiary,
    VulnerabilityCategory,
    RegistrationStatus,
)
from app.models.distribution_center import (
    DistributionCenter,
    CenterStatus,
)
from app.models.distribution import ResourceDistribution

__all__ = [
    "Base",
    "User",
    "UserRole",
    "Disaster",
    "DisasterStatus",
    "VolunteerAssignment",
    "VolunteerTask",
    "AssignmentStatus",
    "TaskStatus",
    "Donation",
    "DonationType",
    "DonationStatus",
    "InventoryItem",
    "InventoryStatus",
    "Beneficiary",
    "VulnerabilityCategory",
    "RegistrationStatus",
    "DistributionCenter",
    "CenterStatus",
    "ResourceDistribution",
]
