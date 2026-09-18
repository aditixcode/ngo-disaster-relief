"""
Report & Summary Pydantic Schemas.

Defines response structures for disaster relief aggregate analytics,
including cross-module disaster operational summaries, warehouse inventory stock reports,
aid distribution logs, volunteer deployment statistics, and beneficiary demographic aggregates.
"""

from typing import List, Optional
from pydantic import BaseModel, ConfigDict


# ==============================================================================
# 1. DISASTER SUMMARY SCHEMAS
# ==============================================================================

class BeneficiariesSummary(BaseModel):
    """Aggregate beneficiary counts by verification lifecycle status."""
    total: int = 0
    pending: int = 0
    verified: int = 0
    inactive: int = 0

    model_config = ConfigDict(from_attributes=True)


class VolunteersSummary(BaseModel):
    """Aggregate volunteer deployment and task statuses."""
    total_assigned: int = 0
    active_assignments: int = 0
    completed_assignments: int = 0
    tasks_total: int = 0
    tasks_pending: int = 0
    tasks_in_progress: int = 0
    tasks_completed: int = 0
    tasks_cancelled: int = 0

    model_config = ConfigDict(from_attributes=True)


class DonationsSummary(BaseModel):
    """Aggregate donation counts and financial contributions."""
    total_donations: int = 0
    pledged: int = 0
    received: int = 0
    cancelled: int = 0
    total_monetary_amount: float = 0.0

    model_config = ConfigDict(from_attributes=True)


class InventorySummary(BaseModel):
    """Aggregate warehouse inventory batch counts by status."""
    total_batches: int = 0
    received_batches: int = 0
    stored_batches: int = 0
    distributed_batches: int = 0

    model_config = ConfigDict(from_attributes=True)


class DistributionCentersSummary(BaseModel):
    """Aggregate distribution facility counts by operational status."""
    total: int = 0
    active: int = 0
    full: int = 0
    inactive: int = 0

    model_config = ConfigDict(from_attributes=True)


class ResourceDistributionsSummary(BaseModel):
    """Aggregate distribution transactions and disbursed volume."""
    total_transactions: int = 0
    total_quantity_distributed: float = 0.0

    model_config = ConfigDict(from_attributes=True)


class DisasterSummaryResponse(BaseModel):
    """
    Comprehensive operational summary report for an entire disaster relief operation.
    """
    disaster_id: int
    disaster_name: str
    location: str
    status: str
    beneficiaries: BeneficiariesSummary
    volunteers: VolunteersSummary
    donations: DonationsSummary
    inventory: InventorySummary
    distribution_centers: DistributionCentersSummary
    resource_distributions: ResourceDistributionsSummary

    model_config = ConfigDict(from_attributes=True)


# ==============================================================================
# 2. INVENTORY REPORT SCHEMAS
# ==============================================================================

class InventoryStatusCounts(BaseModel):
    """Warehouse batch counts broken down by lifecycle status."""
    received: int = 0
    stored: int = 0
    distributed: int = 0

    model_config = ConfigDict(from_attributes=True)


class InventoryItemReportItem(BaseModel):
    """Intake volume vs. current available balance for a specific relief resource."""
    item_name: str
    unit: str
    original_quantity: float = 0.0
    remaining_quantity: float = 0.0

    model_config = ConfigDict(from_attributes=True)


class InventoryReportResponse(BaseModel):
    """
    Warehouse inventory report detailing total batches, status breakdowns,
    and available stock grouped by item and measurement unit.
    """
    disaster_id: int
    total_batches: int = 0
    status_counts: InventoryStatusCounts
    items: List[InventoryItemReportItem] = []

    model_config = ConfigDict(from_attributes=True)


# ==============================================================================
# 3. DISTRIBUTION REPORT SCHEMAS
# ==============================================================================

class DistributionItemReport(BaseModel):
    """Total volume and count of distributions for a specific relief resource."""
    item_name: str
    unit: str
    total_quantity_distributed: float = 0.0
    distribution_count: int = 0

    model_config = ConfigDict(from_attributes=True)


class DistributionCenterActivityReport(BaseModel):
    """Distribution dispatch counts per active distribution hub."""
    distribution_center_id: int
    distribution_count: int = 0
    center_name: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class DistributionReportResponse(BaseModel):
    """
    Relief distribution report detailing overall transactions, disbursed quantity,
    and breakdowns by item type and distribution center.
    """
    disaster_id: int
    total_transactions: int = 0
    total_quantity_distributed: float = 0.0
    items: List[DistributionItemReport] = []
    centers: List[DistributionCenterActivityReport] = []

    model_config = ConfigDict(from_attributes=True)


# ==============================================================================
# 4. VOLUNTEER REPORT SCHEMAS
# ==============================================================================

class VolunteerTasksBreakdown(BaseModel):
    """Volunteer task counts broken down by task lifecycle status."""
    total: int = 0
    pending: int = 0
    in_progress: int = 0
    completed: int = 0
    cancelled: int = 0

    model_config = ConfigDict(from_attributes=True)


class VolunteerReportResponse(BaseModel):
    """
    Volunteer mobilization report detailing volunteer assignments,
    operational task statuses, and safe completion percentage calculation.
    """
    disaster_id: int
    total_assigned_volunteers: int = 0
    active_assignments: int = 0
    completed_assignments: int = 0
    tasks: VolunteerTasksBreakdown
    task_completion_percentage: float = 0.0

    model_config = ConfigDict(from_attributes=True)


# ==============================================================================
# 5. BENEFICIARY REPORT SCHEMAS
# ==============================================================================

class BeneficiaryStatusCounts(BaseModel):
    """Beneficiary counts broken down by verification status."""
    pending: int = 0
    verified: int = 0
    inactive: int = 0

    model_config = ConfigDict(from_attributes=True)


class BeneficiaryVulnerabilityCounts(BaseModel):
    """Beneficiary counts broken down by vulnerability categorization."""
    general: int = 0
    children: int = 0
    elderly: int = 0
    disabled: int = 0
    pregnant: int = 0
    low_income: int = 0

    model_config = ConfigDict(from_attributes=True)


class BeneficiaryReportResponse(BaseModel):
    """
    Aggregate demographic report on affected population.
    Guarantees zero PII exposure (no names, phone numbers, or addresses).
    """
    disaster_id: int
    total: int = 0
    status_counts: BeneficiaryStatusCounts
    vulnerability_categories: BeneficiaryVulnerabilityCounts

    model_config = ConfigDict(from_attributes=True)
