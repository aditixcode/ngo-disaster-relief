"""
Report & Summary Service Layer.

Encapsulates efficient SQL aggregation queries across disasters, beneficiaries,
volunteers, donations, inventory, distribution centers, and resource disbursements.
Every query is strictly read-only and uses SQL aggregates (COUNT, SUM, GROUP BY, CASE)
to avoid loading unnecessary rows into Python memory.
"""

from typing import List
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func, case

from app.models.disaster import Disaster
from app.models.beneficiary import Beneficiary, RegistrationStatus, VulnerabilityCategory
from app.models.volunteer import (
    VolunteerAssignment,
    AssignmentStatus,
    VolunteerTask,
    TaskStatus,
)
from app.models.donation import Donation, DonationType, DonationStatus
from app.models.inventory import InventoryItem, InventoryStatus
from app.models.distribution_center import DistributionCenter, CenterStatus
from app.models.distribution import ResourceDistribution

from app.schemas.report import (
    DisasterSummaryResponse,
    BeneficiariesSummary,
    VolunteersSummary,
    DonationsSummary,
    InventorySummary,
    DistributionCentersSummary,
    ResourceDistributionsSummary,
    InventoryReportResponse,
    InventoryStatusCounts,
    InventoryItemReportItem,
    DistributionReportResponse,
    DistributionItemReport,
    DistributionCenterActivityReport,
    VolunteerReportResponse,
    VolunteerTasksBreakdown,
    BeneficiaryReportResponse,
    BeneficiaryStatusCounts,
    BeneficiaryVulnerabilityCounts,
)


def _get_disaster_or_404(db: Session, disaster_id: int) -> Disaster:
    """
    Validates that a disaster event exists or raises HTTP 404 Not Found.
    Guarantees reports are not generated for nonexistent disaster IDs.
    """
    disaster = db.query(Disaster).filter(Disaster.id == disaster_id).first()
    if not disaster:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Disaster with ID {disaster_id} not found",
        )
    return disaster


def get_disaster_summary_report(db: Session, disaster_id: int) -> DisasterSummaryResponse:
    """
    Generates a unified operational summary for a disaster relief operation.
    Aggregates metrics across beneficiaries, volunteers, donations, inventory, centers, and distributions.
    """
    disaster = _get_disaster_or_404(db, disaster_id)

    # 1. Beneficiaries summary
    b_counts = (
        db.query(
            func.count(Beneficiary.id).label("total"),
            func.coalesce(func.sum(case((Beneficiary.registration_status == RegistrationStatus.PENDING, 1), else_=0)), 0).label("pending"),
            func.coalesce(func.sum(case((Beneficiary.registration_status == RegistrationStatus.VERIFIED, 1), else_=0)), 0).label("verified"),
            func.coalesce(func.sum(case((Beneficiary.registration_status == RegistrationStatus.INACTIVE, 1), else_=0)), 0).label("inactive"),
        )
        .filter(Beneficiary.disaster_id == disaster_id)
        .one()
    )

    # 2. Volunteers & Tasks summary
    va_counts = (
        db.query(
            func.count(VolunteerAssignment.id).label("total"),
            func.coalesce(func.sum(case((VolunteerAssignment.status == AssignmentStatus.ACTIVE, 1), else_=0)), 0).label("active"),
            func.coalesce(func.sum(case((VolunteerAssignment.status == AssignmentStatus.COMPLETED, 1), else_=0)), 0).label("completed"),
        )
        .filter(VolunteerAssignment.disaster_id == disaster_id)
        .one()
    )

    vt_counts = (
        db.query(
            func.count(VolunteerTask.id).label("total"),
            func.coalesce(func.sum(case((VolunteerTask.status == TaskStatus.PENDING, 1), else_=0)), 0).label("pending"),
            func.coalesce(func.sum(case((VolunteerTask.status == TaskStatus.IN_PROGRESS, 1), else_=0)), 0).label("in_progress"),
            func.coalesce(func.sum(case((VolunteerTask.status == TaskStatus.COMPLETED, 1), else_=0)), 0).label("completed"),
            func.coalesce(func.sum(case((VolunteerTask.status == TaskStatus.CANCELLED, 1), else_=0)), 0).label("cancelled"),
        )
        .filter(VolunteerTask.disaster_id == disaster_id)
        .one()
    )

    # 3. Donations summary
    don_counts = (
        db.query(
            func.count(Donation.id).label("total"),
            func.coalesce(func.sum(case((Donation.status == DonationStatus.PLEDGED, 1), else_=0)), 0).label("pledged"),
            func.coalesce(func.sum(case((Donation.status == DonationStatus.RECEIVED, 1), else_=0)), 0).label("received"),
            func.coalesce(func.sum(case((Donation.status == DonationStatus.CANCELLED, 1), else_=0)), 0).label("cancelled"),
            func.coalesce(
                func.sum(
                    case(
                        (
                            (Donation.donation_type == DonationType.MONEY) & (Donation.status != DonationStatus.CANCELLED),
                            Donation.amount,
                        ),
                        else_=0.0,
                    )
                ),
                0.0,
            ).label("monetary_sum"),
        )
        .filter(Donation.disaster_id == disaster_id)
        .one()
    )

    # 4. Inventory summary
    inv_counts = (
        db.query(
            func.count(InventoryItem.id).label("total"),
            func.coalesce(func.sum(case((InventoryItem.status == InventoryStatus.RECEIVED, 1), else_=0)), 0).label("received"),
            func.coalesce(func.sum(case((InventoryItem.status == InventoryStatus.STORED, 1), else_=0)), 0).label("stored"),
            func.coalesce(func.sum(case((InventoryItem.status == InventoryStatus.DISTRIBUTED, 1), else_=0)), 0).label("distributed"),
        )
        .filter(InventoryItem.disaster_id == disaster_id)
        .one()
    )

    # 5. Distribution centers summary
    dc_counts = (
        db.query(
            func.count(DistributionCenter.id).label("total"),
            func.coalesce(func.sum(case((DistributionCenter.status == CenterStatus.ACTIVE, 1), else_=0)), 0).label("active"),
            func.coalesce(func.sum(case((DistributionCenter.status == CenterStatus.FULL, 1), else_=0)), 0).label("full"),
            func.coalesce(func.sum(case((DistributionCenter.status == CenterStatus.INACTIVE, 1), else_=0)), 0).label("inactive"),
        )
        .filter(DistributionCenter.disaster_id == disaster_id)
        .one()
    )

    # 6. Resource distributions summary
    rd_counts = (
        db.query(
            func.count(ResourceDistribution.id).label("total_tx"),
            func.coalesce(func.sum(ResourceDistribution.quantity), 0.0).label("total_qty"),
        )
        .filter(ResourceDistribution.disaster_id == disaster_id)
        .one()
    )

    return DisasterSummaryResponse(
        disaster_id=disaster.id,
        disaster_name=disaster.name,
        location=disaster.location,
        status=disaster.status.value,
        beneficiaries=BeneficiariesSummary(
            total=b_counts.total or 0,
            pending=b_counts.pending or 0,
            verified=b_counts.verified or 0,
            inactive=b_counts.inactive or 0,
        ),
        volunteers=VolunteersSummary(
            total_assigned=va_counts.total or 0,
            active_assignments=va_counts.active or 0,
            completed_assignments=va_counts.completed or 0,
            tasks_total=vt_counts.total or 0,
            tasks_pending=vt_counts.pending or 0,
            tasks_in_progress=vt_counts.in_progress or 0,
            tasks_completed=vt_counts.completed or 0,
            tasks_cancelled=vt_counts.cancelled or 0,
        ),
        donations=DonationsSummary(
            total_donations=don_counts.total or 0,
            pledged=don_counts.pledged or 0,
            received=don_counts.received or 0,
            cancelled=don_counts.cancelled or 0,
            total_monetary_amount=float(don_counts.monetary_sum or 0.0),
        ),
        inventory=InventorySummary(
            total_batches=inv_counts.total or 0,
            received_batches=inv_counts.received or 0,
            stored_batches=inv_counts.stored or 0,
            distributed_batches=inv_counts.distributed or 0,
        ),
        distribution_centers=DistributionCentersSummary(
            total=dc_counts.total or 0,
            active=dc_counts.active or 0,
            full=dc_counts.full or 0,
            inactive=dc_counts.inactive or 0,
        ),
        resource_distributions=ResourceDistributionsSummary(
            total_transactions=rd_counts.total_tx or 0,
            total_quantity_distributed=float(rd_counts.total_qty or 0.0),
        ),
    )


def get_inventory_report(db: Session, disaster_id: int) -> InventoryReportResponse:
    """
    Generates warehouse inventory report for a disaster operation.
    Reports intake volume (original_quantity) vs current available stock (STORED quantity).
    """
    _get_disaster_or_404(db, disaster_id)

    # 1. Total batches and status counts
    inv_status = (
        db.query(
            func.count(InventoryItem.id).label("total"),
            func.coalesce(func.sum(case((InventoryItem.status == InventoryStatus.RECEIVED, 1), else_=0)), 0).label("received"),
            func.coalesce(func.sum(case((InventoryItem.status == InventoryStatus.STORED, 1), else_=0)), 0).label("stored"),
            func.coalesce(func.sum(case((InventoryItem.status == InventoryStatus.DISTRIBUTED, 1), else_=0)), 0).label("distributed"),
        )
        .filter(InventoryItem.disaster_id == disaster_id)
        .one()
    )

    # 2. Grouped items breakdown: original volume vs available stored stock
    item_rows = (
        db.query(
            InventoryItem.item_name,
            InventoryItem.unit,
            func.coalesce(
                func.sum(
                    func.coalesce(InventoryItem.original_quantity, InventoryItem.quantity)
                ),
                0.0,
            ).label("original_qty"),
            func.coalesce(
                func.sum(
                    case(
                        (InventoryItem.status == InventoryStatus.STORED, InventoryItem.quantity),
                        else_=0.0,
                    )
                ),
                0.0,
            ).label("remaining_qty"),
        )
        .filter(InventoryItem.disaster_id == disaster_id)
        .group_by(InventoryItem.item_name, InventoryItem.unit)
        .order_by(InventoryItem.item_name.asc())
        .all()
    )

    items: List[InventoryItemReportItem] = [
        InventoryItemReportItem(
            item_name=row.item_name,
            unit=row.unit,
            original_quantity=float(row.original_qty),
            remaining_quantity=float(row.remaining_qty),
        )
        for row in item_rows
    ]

    return InventoryReportResponse(
        disaster_id=disaster_id,
        total_batches=inv_status.total or 0,
        status_counts=InventoryStatusCounts(
            received=inv_status.received or 0,
            stored=inv_status.stored or 0,
            distributed=inv_status.distributed or 0,
        ),
        items=items,
    )


def get_distribution_report(db: Session, disaster_id: int) -> DistributionReportResponse:
    """
    Generates relief distribution report detailing total disbursed volume,
    disbursements grouped by item/unit, and activity counts per distribution center.
    """
    _get_disaster_or_404(db, disaster_id)

    # 1. Total transactions and total quantity
    totals = (
        db.query(
            func.count(ResourceDistribution.id).label("total_tx"),
            func.coalesce(func.sum(ResourceDistribution.quantity), 0.0).label("total_qty"),
        )
        .filter(ResourceDistribution.disaster_id == disaster_id)
        .one()
    )

    # 2. Disbursements grouped by item_name and unit
    item_rows = (
        db.query(
            ResourceDistribution.item_name,
            ResourceDistribution.unit,
            func.coalesce(func.sum(ResourceDistribution.quantity), 0.0).label("qty_sum"),
            func.count(ResourceDistribution.id).label("tx_count"),
        )
        .filter(ResourceDistribution.disaster_id == disaster_id)
        .group_by(ResourceDistribution.item_name, ResourceDistribution.unit)
        .order_by(ResourceDistribution.item_name.asc())
        .all()
    )

    items = [
        DistributionItemReport(
            item_name=row.item_name,
            unit=row.unit,
            total_quantity_distributed=float(row.qty_sum),
            distribution_count=row.tx_count,
        )
        for row in item_rows
    ]

    # 3. Disbursements grouped by distribution_center_id
    center_rows = (
        db.query(
            ResourceDistribution.distribution_center_id,
            func.count(ResourceDistribution.id).label("tx_count"),
            DistributionCenter.name.label("center_name"),
        )
        .join(DistributionCenter, ResourceDistribution.distribution_center_id == DistributionCenter.id, isouter=True)
        .filter(ResourceDistribution.disaster_id == disaster_id)
        .group_by(ResourceDistribution.distribution_center_id, DistributionCenter.name)
        .order_by(func.count(ResourceDistribution.id).desc())
        .all()
    )

    centers = [
        DistributionCenterActivityReport(
            distribution_center_id=row.distribution_center_id,
            distribution_count=row.tx_count,
            center_name=row.center_name,
        )
        for row in center_rows
    ]

    return DistributionReportResponse(
        disaster_id=disaster_id,
        total_transactions=totals.total_tx or 0,
        total_quantity_distributed=float(totals.total_qty or 0.0),
        items=items,
        centers=centers,
    )


def get_volunteer_report(db: Session, disaster_id: int) -> VolunteerReportResponse:
    """
    Generates volunteer mobilization report with safe task completion percentage.
    """
    _get_disaster_or_404(db, disaster_id)

    # 1. Assignment counts
    va_counts = (
        db.query(
            func.count(VolunteerAssignment.id).label("total"),
            func.coalesce(func.sum(case((VolunteerAssignment.status == AssignmentStatus.ACTIVE, 1), else_=0)), 0).label("active"),
            func.coalesce(func.sum(case((VolunteerAssignment.status == AssignmentStatus.COMPLETED, 1), else_=0)), 0).label("completed"),
        )
        .filter(VolunteerAssignment.disaster_id == disaster_id)
        .one()
    )

    # 2. Task counts
    vt_counts = (
        db.query(
            func.count(VolunteerTask.id).label("total"),
            func.coalesce(func.sum(case((VolunteerTask.status == TaskStatus.PENDING, 1), else_=0)), 0).label("pending"),
            func.coalesce(func.sum(case((VolunteerTask.status == TaskStatus.IN_PROGRESS, 1), else_=0)), 0).label("in_progress"),
            func.coalesce(func.sum(case((VolunteerTask.status == TaskStatus.COMPLETED, 1), else_=0)), 0).label("completed"),
            func.coalesce(func.sum(case((VolunteerTask.status == TaskStatus.CANCELLED, 1), else_=0)), 0).label("cancelled"),
        )
        .filter(VolunteerTask.disaster_id == disaster_id)
        .one()
    )

    total_tasks = vt_counts.total or 0
    completed_tasks = vt_counts.completed or 0
    completion_percentage = (
        round((completed_tasks / total_tasks) * 100.0, 2)
        if total_tasks > 0
        else 0.0
    )

    return VolunteerReportResponse(
        disaster_id=disaster_id,
        total_assigned_volunteers=va_counts.total or 0,
        active_assignments=va_counts.active or 0,
        completed_assignments=va_counts.completed or 0,
        tasks=VolunteerTasksBreakdown(
            total=total_tasks,
            pending=vt_counts.pending or 0,
            in_progress=vt_counts.in_progress or 0,
            completed=completed_tasks,
            cancelled=vt_counts.cancelled or 0,
        ),
        task_completion_percentage=completion_percentage,
    )


def get_beneficiary_report(db: Session, disaster_id: int) -> BeneficiaryReportResponse:
    """
    Generates aggregate beneficiary demographics and vulnerability distributions.
    Protects personal information by exposing only aggregate numbers.
    """
    _get_disaster_or_404(db, disaster_id)

    # 1. Verification status counts
    status_counts = (
        db.query(
            func.count(Beneficiary.id).label("total"),
            func.coalesce(func.sum(case((Beneficiary.registration_status == RegistrationStatus.PENDING, 1), else_=0)), 0).label("pending"),
            func.coalesce(func.sum(case((Beneficiary.registration_status == RegistrationStatus.VERIFIED, 1), else_=0)), 0).label("verified"),
            func.coalesce(func.sum(case((Beneficiary.registration_status == RegistrationStatus.INACTIVE, 1), else_=0)), 0).label("inactive"),
        )
        .filter(Beneficiary.disaster_id == disaster_id)
        .one()
    )

    # 2. Vulnerability category counts
    vuln_counts = (
        db.query(
            func.coalesce(func.sum(case((Beneficiary.vulnerability_category == VulnerabilityCategory.GENERAL, 1), else_=0)), 0).label("general"),
            func.coalesce(func.sum(case((Beneficiary.vulnerability_category == VulnerabilityCategory.CHILDREN, 1), else_=0)), 0).label("children"),
            func.coalesce(func.sum(case((Beneficiary.vulnerability_category == VulnerabilityCategory.ELDERLY, 1), else_=0)), 0).label("elderly"),
            func.coalesce(func.sum(case((Beneficiary.vulnerability_category == VulnerabilityCategory.DISABLED, 1), else_=0)), 0).label("disabled"),
            func.coalesce(func.sum(case((Beneficiary.vulnerability_category == VulnerabilityCategory.PREGNANT, 1), else_=0)), 0).label("pregnant"),
            func.coalesce(func.sum(case((Beneficiary.vulnerability_category == VulnerabilityCategory.LOW_INCOME, 1), else_=0)), 0).label("low_income"),
        )
        .filter(Beneficiary.disaster_id == disaster_id)
        .one()
    )

    return BeneficiaryReportResponse(
        disaster_id=disaster_id,
        total=status_counts.total or 0,
        status_counts=BeneficiaryStatusCounts(
            pending=status_counts.pending or 0,
            verified=status_counts.verified or 0,
            inactive=status_counts.inactive or 0,
        ),
        vulnerability_categories=BeneficiaryVulnerabilityCounts(
            general=vuln_counts.general or 0,
            children=vuln_counts.children or 0,
            elderly=vuln_counts.elderly or 0,
            disabled=vuln_counts.disabled or 0,
            pregnant=vuln_counts.pregnant or 0,
            low_income=vuln_counts.low_income or 0,
        ),
    )
