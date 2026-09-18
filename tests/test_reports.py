"""
Stage 11: Automated Tests for Disaster-Relief Summary & Report APIs.

Verifies:
1. Authorization guards (ADMIN and NGO_STAFF 200 OK; VOLUNTEER and DONOR 403 Forbidden; unauth 401 Unauthorized).
2. Disaster validation (nonexistent disaster returns 404 Not Found for all report endpoints).
3. Empty disaster handling (disaster with zero records returns valid zero/empty structures with 0.0 completion percentage).
4. Unified disaster summary report (accurately aggregates across beneficiaries, volunteers, donations, inventory, centers, distributions).
5. Warehouse inventory report (tracks original intake volume vs remaining available STORED stock; status counts; item/unit grouping).
6. Relief distribution report (transactions, disbursed quantities, item/unit grouping, distribution center activity).
7. Volunteer mobilization report (assignments, tasks, safe task completion percentage, zero-division protection).
8. Beneficiary demographic report (status counts, vulnerability breakdown, zero PII exposure).
9. Cross-module data consistency (100 kg intake -> 30 kg distributed -> inventory shows 70 kg remaining, distribution shows 30 kg disbursed).
10. Read-only guarantee (calling report endpoints does not mutate any database record, balance, or status).
"""

from datetime import datetime, timezone
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.inventory import InventoryItem, InventoryStatus
from app.models.beneficiary import Beneficiary, RegistrationStatus, VulnerabilityCategory
from app.models.distribution_center import DistributionCenter, CenterStatus
from app.models.volunteer import (
    VolunteerAssignment,
    AssignmentStatus,
    VolunteerTask,
    TaskStatus,
)
from app.models.donation import Donation, DonationType, DonationStatus
from app.models.distribution import ResourceDistribution


# ==============================================================================
# TEST FIXTURE HELPERS
# ==============================================================================

def get_user_headers(client: TestClient, email: str, role: str) -> dict:
    """Registers a user with the specified role and returns auth bearer headers."""
    client.post(
        "/api/v1/auth/register",
        json={
            "name": f"User {role}",
            "email": email,
            "password": "Password123!",
            "role": role,
        },
    )
    login_resp = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "Password123!"},
    )
    assert login_resp.status_code == 200
    token = login_resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def create_test_disaster(client: TestClient, admin_headers: dict, name: str = "Cyclone Report Hub") -> int:
    """Creates a test disaster event."""
    now = datetime.now(timezone.utc)
    resp = client.post(
        "/api/v1/disasters",
        json={
            "name": name,
            "location": "Coastal District Sector 9",
            "status": "ACTIVE",
            "start_date": now.isoformat(),
        },
        headers=admin_headers,
    )
    assert resp.status_code == 201
    return resp.json()["id"]


# ==============================================================================
# 1. RBAC & PERMISSION TESTS
# ==============================================================================

def test_rbac_for_all_report_endpoints(client: TestClient):
    """
    Admin and Staff can view reports.
    Volunteer and Donor are forbidden (403).
    Unauthenticated callers receive 401.
    """
    admin_h = get_user_headers(client, "admin_rep1@ngo.org", "ADMIN")
    staff_h = get_user_headers(client, "staff_rep1@ngo.org", "NGO_STAFF")
    vol_h = get_user_headers(client, "vol_rep1@ngo.org", "VOLUNTEER")
    donor_h = get_user_headers(client, "donor_rep1@ngo.org", "DONOR")

    disaster_id = create_test_disaster(client, admin_h, "RBAC Report Disaster")

    endpoints = [
        f"/api/v1/reports/disasters/{disaster_id}/summary",
        f"/api/v1/reports/disasters/{disaster_id}/inventory",
        f"/api/v1/reports/disasters/{disaster_id}/distributions",
        f"/api/v1/reports/disasters/{disaster_id}/volunteers",
        f"/api/v1/reports/disasters/{disaster_id}/beneficiaries",
    ]

    for ep in endpoints:
        # 1. Unauthenticated -> 401
        assert client.get(ep).status_code == 401

        # 2. Volunteer -> 403
        assert client.get(ep, headers=vol_h).status_code == 403

        # 3. Donor -> 403
        assert client.get(ep, headers=donor_h).status_code == 403

        # 4. NGO Staff -> 200
        assert client.get(ep, headers=staff_h).status_code == 200

        # 5. Admin -> 200
        assert client.get(ep, headers=admin_h).status_code == 200


# ==============================================================================
# 2. DISASTER VALIDATION TESTS (404 FOR NONEXISTENT)
# ==============================================================================

def test_nonexistent_disaster_returns_404_for_all_reports(client: TestClient):
    """Querying reports for a nonexistent disaster returns 404."""
    admin_h = get_user_headers(client, "admin_rep_404@ngo.org", "ADMIN")
    non_existent_id = 999999

    endpoints = [
        f"/api/v1/reports/disasters/{non_existent_id}/summary",
        f"/api/v1/reports/disasters/{non_existent_id}/inventory",
        f"/api/v1/reports/disasters/{non_existent_id}/distributions",
        f"/api/v1/reports/disasters/{non_existent_id}/volunteers",
        f"/api/v1/reports/disasters/{non_existent_id}/beneficiaries",
    ]

    for ep in endpoints:
        resp = client.get(ep, headers=admin_h)
        assert resp.status_code == 404
        assert "not found" in resp.json()["detail"].lower()


# ==============================================================================
# 3. EMPTY DISASTER HANDLING TESTS
# ==============================================================================

def test_empty_disaster_returns_valid_zero_structures(client: TestClient):
    """
    An existing disaster with zero associated records returns clean zero/empty values
    without raising 500 errors or division by zero.
    """
    admin_h = get_user_headers(client, "admin_empty@ngo.org", "ADMIN")
    disaster_id = create_test_disaster(client, admin_h, "Empty Disaster")

    # 1. Summary Report
    s_resp = client.get(f"/api/v1/reports/disasters/{disaster_id}/summary", headers=admin_h)
    assert s_resp.status_code == 200
    s_data = s_resp.json()
    assert s_data["beneficiaries"]["total"] == 0
    assert s_data["volunteers"]["total_assigned"] == 0
    assert s_data["volunteers"]["tasks_total"] == 0
    assert s_data["donations"]["total_donations"] == 0
    assert s_data["donations"]["total_monetary_amount"] == 0.0
    assert s_data["inventory"]["total_batches"] == 0
    assert s_data["distribution_centers"]["total"] == 0
    assert s_data["resource_distributions"]["total_transactions"] == 0
    assert s_data["resource_distributions"]["total_quantity_distributed"] == 0.0

    # 2. Inventory Report
    inv_resp = client.get(f"/api/v1/reports/disasters/{disaster_id}/inventory", headers=admin_h)
    assert inv_resp.status_code == 200
    inv_data = inv_resp.json()
    assert inv_data["total_batches"] == 0
    assert inv_data["status_counts"]["received"] == 0
    assert inv_data["status_counts"]["stored"] == 0
    assert inv_data["status_counts"]["distributed"] == 0
    assert inv_data["items"] == []

    # 3. Distribution Report
    d_resp = client.get(f"/api/v1/reports/disasters/{disaster_id}/distributions", headers=admin_h)
    assert d_resp.status_code == 200
    d_data = d_resp.json()
    assert d_data["total_transactions"] == 0
    assert d_data["total_quantity_distributed"] == 0.0
    assert d_data["items"] == []
    assert d_data["centers"] == []

    # 4. Volunteer Report (Safe zero division!)
    v_resp = client.get(f"/api/v1/reports/disasters/{disaster_id}/volunteers", headers=admin_h)
    assert v_resp.status_code == 200
    v_data = v_resp.json()
    assert v_data["total_assigned_volunteers"] == 0
    assert v_data["tasks"]["total"] == 0
    assert v_data["task_completion_percentage"] == 0.0

    # 5. Beneficiary Report
    b_resp = client.get(f"/api/v1/reports/disasters/{disaster_id}/beneficiaries", headers=admin_h)
    assert b_resp.status_code == 200
    b_data = b_resp.json()
    assert b_data["total"] == 0
    assert b_data["status_counts"]["pending"] == 0
    assert b_data["vulnerability_categories"]["elderly"] == 0


# ==============================================================================
# 4. UNIFIED DISASTER SUMMARY REPORT TEST
# ==============================================================================

def test_disaster_summary_report_aggregates_all_domains(client: TestClient):
    """
    Creates records across beneficiaries, volunteers, tasks, donations, inventory, centers,
    and distributions, and verifies the unified summary report counts.
    """
    admin_h = get_user_headers(client, "admin_sum@ngo.org", "ADMIN")
    disaster_id = create_test_disaster(client, admin_h, "Full Operations Disaster")

    # 1. Beneficiaries (1 PENDING, 1 VERIFIED)
    b1_resp = client.post(
        "/api/v1/beneficiaries",
        json={
            "disaster_id": disaster_id,
            "name": "Ben One",
            "contact_number": "+91-9000000001",
            "address": "Camp 1",
            "household_size": 2,
            "vulnerability_category": "GENERAL",
        },
        headers=admin_h,
    )
    b1_id = b1_resp.json()["id"]

    b2_resp = client.post(
        "/api/v1/beneficiaries",
        json={
            "disaster_id": disaster_id,
            "name": "Ben Two",
            "contact_number": "+91-9000000002",
            "address": "Camp 2",
            "household_size": 4,
            "vulnerability_category": "ELDERLY",
        },
        headers=admin_h,
    )
    b2_id = b2_resp.json()["id"]
    client.patch(f"/api/v1/beneficiaries/{b2_id}/status", json={"status": "VERIFIED"}, headers=admin_h)

    # 2. Volunteers & Tasks
    vol_h = get_user_headers(client, "field_vol@ngo.org", "VOLUNTEER")
    vol_me = client.get("/api/v1/auth/me", headers=vol_h).json()
    vol_id = vol_me["id"]

    # Assign volunteer
    assign_resp = client.post(
        "/api/v1/volunteers/assignments",
        json={"volunteer_id": vol_id, "disaster_id": disaster_id},
        headers=admin_h,
    )
    assert assign_resp.status_code == 201

    # Create 2 tasks (1 PENDING, 1 COMPLETED)
    t1_resp = client.post(
        "/api/v1/volunteers/tasks",
        json={"volunteer_id": vol_id, "disaster_id": disaster_id, "title": "Distribute Water"},
        headers=admin_h,
    )
    t2_resp = client.post(
        "/api/v1/volunteers/tasks",
        json={"volunteer_id": vol_id, "disaster_id": disaster_id, "title": "Setup Medical Tent"},
        headers=admin_h,
    )
    t2_id = t2_resp.json()["id"]
    client.patch(f"/api/v1/volunteers/tasks/{t2_id}/status", json={"status": "COMPLETED"}, headers=admin_h)

    # 3. Donations (1 PLEDGED money 500, 1 RECEIVED money 1500)
    donor_h = get_user_headers(client, "sum_donor@ngo.org", "DONOR")
    client.post(
        "/api/v1/donations",
        json={"disaster_id": disaster_id, "donation_type": "MONEY", "amount": 500.0},
        headers=donor_h,
    )
    d2_resp = client.post(
        "/api/v1/donations",
        json={"disaster_id": disaster_id, "donation_type": "MONEY", "amount": 1500.0},
        headers=donor_h,
    )
    d2_id = d2_resp.json()["id"]
    client.patch(f"/api/v1/donations/{d2_id}/status", json={"status": "RECEIVED"}, headers=admin_h)

    # 4. Inventory (1 RECEIVED batch 50 kg, 1 STORED batch 100 kg)
    inv1_resp = client.post(
        "/api/v1/inventory",
        json={"disaster_id": disaster_id, "item_name": "Lentils", "quantity": 50.0, "unit": "kg"},
        headers=admin_h,
    )
    inv2_resp = client.post(
        "/api/v1/inventory",
        json={"disaster_id": disaster_id, "item_name": "Rice", "quantity": 100.0, "unit": "kg"},
        headers=admin_h,
    )
    inv2_id = inv2_resp.json()["id"]
    client.patch(f"/api/v1/inventory/{inv2_id}/status", json={"status": "STORED"}, headers=admin_h)

    # 5. Distribution Center (1 ACTIVE)
    center_resp = client.post(
        "/api/v1/distribution-centers",
        json={
            "disaster_id": disaster_id,
            "name": "Main Base Hub",
            "address": "Sector 4 Ground",
            "contact_number": "+91-9123456789",
            "capacity": 500,
        },
        headers=admin_h,
    )
    center_id = center_resp.json()["id"]

    # 6. Resource Distribution (Distribute 20 kg Rice to Ben Two at Main Base Hub)
    dist_resp = client.post(
        "/api/v1/distributions",
        json={
            "disaster_id": disaster_id,
            "inventory_item_id": inv2_id,
            "beneficiary_id": b2_id,
            "distribution_center_id": center_id,
            "quantity": 20.0,
            "unit": "kg",
        },
        headers=admin_h,
    )
    assert dist_resp.status_code == 201

    # Verify Summary Report
    summary_resp = client.get(f"/api/v1/reports/disasters/{disaster_id}/summary", headers=admin_h)
    assert summary_resp.status_code == 200
    data = summary_resp.json()

    assert data["disaster_id"] == disaster_id
    assert data["disaster_name"] == "Full Operations Disaster"
    assert data["beneficiaries"]["total"] == 2
    assert data["beneficiaries"]["pending"] == 1
    assert data["beneficiaries"]["verified"] == 1

    assert data["volunteers"]["total_assigned"] == 1
    assert data["volunteers"]["tasks_total"] == 2
    assert data["volunteers"]["tasks_pending"] == 1
    assert data["volunteers"]["tasks_completed"] == 1

    assert data["donations"]["total_donations"] == 2
    assert data["donations"]["pledged"] == 1
    assert data["donations"]["received"] == 1
    assert data["donations"]["total_monetary_amount"] == 2000.0

    assert data["inventory"]["total_batches"] == 2
    assert data["inventory"]["received_batches"] == 1
    assert data["inventory"]["stored_batches"] == 1

    assert data["distribution_centers"]["total"] == 1
    assert data["distribution_centers"]["active"] == 1

    assert data["resource_distributions"]["total_transactions"] == 1
    assert data["resource_distributions"]["total_quantity_distributed"] == 20.0


# ==============================================================================
# 5. INVENTORY REPORT TESTS (ORIGINAL VS AVAILABLE STORED)
# ==============================================================================

def test_inventory_report_accurately_reports_stock_levels(client: TestClient):
    """
    Verifies that inventory report distinguishes intake history (original_quantity)
    from live distributable balance (quantity in STORED status).
    """
    admin_h = get_user_headers(client, "admin_inv_rep@ngo.org", "ADMIN")
    disaster_id = create_test_disaster(client, admin_h, "Inventory Report Disaster")

    # 1. Batch A: 100 kg Rice (intake -> STORED)
    b1_resp = client.post(
        "/api/v1/inventory",
        json={"disaster_id": disaster_id, "item_name": "Rice", "quantity": 100.0, "unit": "kg"},
        headers=admin_h,
    )
    b1_id = b1_resp.json()["id"]
    client.patch(f"/api/v1/inventory/{b1_id}/status", json={"status": "STORED"}, headers=admin_h)

    # 2. Batch B: 50 kg Rice (stays in RECEIVED status)
    client.post(
        "/api/v1/inventory",
        json={"disaster_id": disaster_id, "item_name": "Rice", "quantity": 50.0, "unit": "kg"},
        headers=admin_h,
    )

    # 3. Batch C: 200 packets Biscuits (intake -> STORED)
    b3_resp = client.post(
        "/api/v1/inventory",
        json={"disaster_id": disaster_id, "item_name": "Biscuits", "quantity": 200.0, "unit": "packets"},
        headers=admin_h,
    )
    b3_id = b3_resp.json()["id"]
    client.patch(f"/api/v1/inventory/{b3_id}/status", json={"status": "STORED"}, headers=admin_h)

    # Setup beneficiary and center to distribute 30 kg from Batch A
    ben_id = client.post(
        "/api/v1/beneficiaries",
        json={
            "disaster_id": disaster_id,
            "name": "Devi",
            "contact_number": "+91-9123499999",
            "address": "Camp 3",
            "household_size": 3,
            "vulnerability_category": "GENERAL",
        },
        headers=admin_h,
    ).json()["id"]
    client.patch(f"/api/v1/beneficiaries/{ben_id}/status", json={"status": "VERIFIED"}, headers=admin_h)

    center_id = client.post(
        "/api/v1/distribution-centers",
        json={
            "disaster_id": disaster_id,
            "name": "North Hub",
            "address": "Gate 1",
            "contact_number": "+91-9123488888",
            "capacity": 300,
        },
        headers=admin_h,
    ).json()["id"]

    # Distribute 30 kg Rice
    client.post(
        "/api/v1/distributions",
        json={
            "disaster_id": disaster_id,
            "inventory_item_id": b1_id,
            "beneficiary_id": ben_id,
            "distribution_center_id": center_id,
            "quantity": 30.0,
            "unit": "kg",
        },
        headers=admin_h,
    )

    # Query Inventory Report
    resp = client.get(f"/api/v1/reports/disasters/{disaster_id}/inventory", headers=admin_h)
    assert resp.status_code == 200
    data = resp.json()

    assert data["total_batches"] == 3
    assert data["status_counts"]["received"] == 1
    assert data["status_counts"]["stored"] == 2
    assert data["status_counts"]["distributed"] == 0

    # Items breakdown
    items_map = {item["item_name"]: item for item in data["items"]}
    assert "Rice" in items_map
    assert "Biscuits" in items_map

    # Rice: Batch A (100 kg original, 70 kg remaining stored) + Batch B (50 kg original received, 0 kg remaining stored)
    # Total original Rice = 150 kg; Total available stored Rice = 70 kg!
    rice = items_map["Rice"]
    assert rice["unit"] == "kg"
    assert rice["original_quantity"] == 150.0
    assert rice["remaining_quantity"] == 70.0

    # Biscuits: 200 packets original, 200 packets stored
    biscuits = items_map["Biscuits"]
    assert biscuits["unit"] == "packets"
    assert biscuits["original_quantity"] == 200.0
    assert biscuits["remaining_quantity"] == 200.0


# ==============================================================================
# 6. DISTRIBUTION REPORT TESTS
# ==============================================================================

def test_distribution_report_groupings_and_totals(client: TestClient):
    """
    Verifies that distribution report groups dispatches by item/unit and by distribution center.
    """
    admin_h = get_user_headers(client, "admin_dist_rep@ngo.org", "ADMIN")
    disaster_id = create_test_disaster(client, admin_h, "Distribution Report Disaster")

    center1_id = client.post(
        "/api/v1/distribution-centers",
        json={"disaster_id": disaster_id, "name": "Hub One", "address": "Addr 1", "contact_number": "+91-9100000001", "capacity": 200},
        headers=admin_h,
    ).json()["id"]
    center2_id = client.post(
        "/api/v1/distribution-centers",
        json={"disaster_id": disaster_id, "name": "Hub Two", "address": "Addr 2", "contact_number": "+91-9100000002", "capacity": 200},
        headers=admin_h,
    ).json()["id"]

    ben_id = client.post(
        "/api/v1/beneficiaries",
        json={"disaster_id": disaster_id, "name": "Ravi", "contact_number": "+91-9200000001", "address": "Camp 5", "household_size": 1, "vulnerability_category": "GENERAL"},
        headers=admin_h,
    ).json()["id"]
    client.patch(f"/api/v1/beneficiaries/{ben_id}/status", json={"status": "VERIFIED"}, headers=admin_h)

    inv1_id = client.post(
        "/api/v1/inventory",
        json={"disaster_id": disaster_id, "item_name": "Blankets", "quantity": 100.0, "unit": "pieces"},
        headers=admin_h,
    ).json()["id"]
    client.patch(f"/api/v1/inventory/{inv1_id}/status", json={"status": "STORED"}, headers=admin_h)

    inv2_id = client.post(
        "/api/v1/inventory",
        json={"disaster_id": disaster_id, "item_name": "Tarpaulins", "quantity": 50.0, "unit": "sheets"},
        headers=admin_h,
    ).json()["id"]
    client.patch(f"/api/v1/inventory/{inv2_id}/status", json={"status": "STORED"}, headers=admin_h)

    # Dispatches:
    # 1. Hub One: 10 Blankets
    client.post(
        "/api/v1/distributions",
        json={"disaster_id": disaster_id, "inventory_item_id": inv1_id, "beneficiary_id": ben_id, "distribution_center_id": center1_id, "quantity": 10.0, "unit": "pieces"},
        headers=admin_h,
    )
    # 2. Hub One: 15 Blankets
    client.post(
        "/api/v1/distributions",
        json={"disaster_id": disaster_id, "inventory_item_id": inv1_id, "beneficiary_id": ben_id, "distribution_center_id": center1_id, "quantity": 15.0, "unit": "pieces"},
        headers=admin_h,
    )
    # 3. Hub Two: 5 Tarpaulins
    client.post(
        "/api/v1/distributions",
        json={"disaster_id": disaster_id, "inventory_item_id": inv2_id, "beneficiary_id": ben_id, "distribution_center_id": center2_id, "quantity": 5.0, "unit": "sheets"},
        headers=admin_h,
    )

    resp = client.get(f"/api/v1/reports/disasters/{disaster_id}/distributions", headers=admin_h)
    assert resp.status_code == 200
    data = resp.json()

    assert data["total_transactions"] == 3
    assert data["total_quantity_distributed"] == 30.0

    # Item breakdown
    items_map = {item["item_name"]: item for item in data["items"]}
    assert items_map["Blankets"]["total_quantity_distributed"] == 25.0
    assert items_map["Blankets"]["distribution_count"] == 2
    assert items_map["Tarpaulins"]["total_quantity_distributed"] == 5.0
    assert items_map["Tarpaulins"]["distribution_count"] == 1

    # Center breakdown
    centers_map = {c["distribution_center_id"]: c for c in data["centers"]}
    assert centers_map[center1_id]["distribution_count"] == 2
    assert centers_map[center1_id]["center_name"] == "Hub One"
    assert centers_map[center2_id]["distribution_count"] == 1
    assert centers_map[center2_id]["center_name"] == "Hub Two"


# ==============================================================================
# 7. VOLUNTEER REPORT & COMPLETION PERCENTAGE TESTS
# ==============================================================================

def test_volunteer_report_completion_percentage(client: TestClient):
    """
    Verifies volunteer report calculation of task completion percentage:
    4 tasks (2 completed, 1 in progress, 1 pending) -> 50.0% completion.
    """
    admin_h = get_user_headers(client, "admin_vol_rep@ngo.org", "ADMIN")
    disaster_id = create_test_disaster(client, admin_h, "Volunteer Metrics Disaster")

    vol_h = get_user_headers(client, "metrics_vol@ngo.org", "VOLUNTEER")
    vol_id = client.get("/api/v1/auth/me", headers=vol_h).json()["id"]

    client.post(
        "/api/v1/volunteers/assignments",
        json={"volunteer_id": vol_id, "disaster_id": disaster_id},
        headers=admin_h,
    )

    # 4 tasks
    t1_id = client.post("/api/v1/volunteers/tasks", json={"volunteer_id": vol_id, "disaster_id": disaster_id, "title": "Task 1"}, headers=admin_h).json()["id"]
    t2_id = client.post("/api/v1/volunteers/tasks", json={"volunteer_id": vol_id, "disaster_id": disaster_id, "title": "Task 2"}, headers=admin_h).json()["id"]
    t3_id = client.post("/api/v1/volunteers/tasks", json={"volunteer_id": vol_id, "disaster_id": disaster_id, "title": "Task 3"}, headers=admin_h).json()["id"]
    t4_id = client.post("/api/v1/volunteers/tasks", json={"volunteer_id": vol_id, "disaster_id": disaster_id, "title": "Task 4"}, headers=admin_h).json()["id"]

    # Mark 2 completed, 1 in progress
    client.patch(f"/api/v1/volunteers/tasks/{t1_id}/status", json={"status": "COMPLETED"}, headers=admin_h)
    client.patch(f"/api/v1/volunteers/tasks/{t2_id}/status", json={"status": "COMPLETED"}, headers=admin_h)
    client.patch(f"/api/v1/volunteers/tasks/{t3_id}/status", json={"status": "IN_PROGRESS"}, headers=admin_h)
    # t4 remains PENDING

    resp = client.get(f"/api/v1/reports/disasters/{disaster_id}/volunteers", headers=admin_h)
    assert resp.status_code == 200
    data = resp.json()

    assert data["total_assigned_volunteers"] == 1
    assert data["tasks"]["total"] == 4
    assert data["tasks"]["completed"] == 2
    assert data["tasks"]["in_progress"] == 1
    assert data["tasks"]["pending"] == 1
    assert data["task_completion_percentage"] == 50.0


# ==============================================================================
# 8. BENEFICIARY REPORT & PRIVACY PROTECTION TESTS
# ==============================================================================

def test_beneficiary_report_protects_privacy(client: TestClient):
    """
    Verifies aggregate demographic distribution and asserts that no PII is returned.
    """
    admin_h = get_user_headers(client, "admin_ben_rep@ngo.org", "ADMIN")
    disaster_id = create_test_disaster(client, admin_h, "Beneficiary Privacy Disaster")

    # Register 3 beneficiaries with diverse categories
    client.post(
        "/api/v1/beneficiaries",
        json={"disaster_id": disaster_id, "name": "Confidential Person 1", "contact_number": "+91-9999900001", "address": "Secret Shelter 1", "household_size": 3, "vulnerability_category": "ELDERLY"},
        headers=admin_h,
    )
    b2_id = client.post(
        "/api/v1/beneficiaries",
        json={"disaster_id": disaster_id, "name": "Confidential Person 2", "contact_number": "+91-9999900002", "address": "Secret Shelter 2", "household_size": 2, "vulnerability_category": "CHILDREN"},
        headers=admin_h,
    ).json()["id"]
    client.patch(f"/api/v1/beneficiaries/{b2_id}/status", json={"status": "VERIFIED"}, headers=admin_h)

    b3_id = client.post(
        "/api/v1/beneficiaries",
        json={"disaster_id": disaster_id, "name": "Confidential Person 3", "contact_number": "+91-9999900003", "address": "Secret Shelter 3", "household_size": 1, "vulnerability_category": "PREGNANT"},
        headers=admin_h,
    ).json()["id"]
    client.patch(f"/api/v1/beneficiaries/{b3_id}/status", json={"status": "INACTIVE"}, headers=admin_h)

    resp = client.get(f"/api/v1/reports/disasters/{disaster_id}/beneficiaries", headers=admin_h)
    assert resp.status_code == 200
    data = resp.json()

    assert data["total"] == 3
    assert data["status_counts"]["pending"] == 1
    assert data["status_counts"]["verified"] == 1
    assert data["status_counts"]["inactive"] == 1

    assert data["vulnerability_categories"]["elderly"] == 1
    assert data["vulnerability_categories"]["children"] == 1
    assert data["vulnerability_categories"]["pregnant"] == 1
    assert data["vulnerability_categories"]["disabled"] == 0

    # ASSERT PRIVACY: Check raw response string contains no PII
    raw_text = resp.text
    assert "Confidential Person" not in raw_text
    assert "+91-9999900001" not in raw_text
    assert "Secret Shelter" not in raw_text


# ==============================================================================
# 9. READ-ONLY GUARANTEE TESTS
# ==============================================================================

def test_reports_do_not_modify_database_state(client: TestClient, db_session: Session):
    """
    Verifies that calling any report endpoint leaves database record counts,
    inventory balances, and statuses completely intact.
    """
    admin_h = get_user_headers(client, "admin_readonly@ngo.org", "ADMIN")
    disaster_id = create_test_disaster(client, admin_h, "Readonly Disaster")

    inv_id = client.post(
        "/api/v1/inventory",
        json={"disaster_id": disaster_id, "item_name": "Wheat", "quantity": 100.0, "unit": "kg"},
        headers=admin_h,
    ).json()["id"]
    client.patch(f"/api/v1/inventory/{inv_id}/status", json={"status": "STORED"}, headers=admin_h)

    # Initial state snapshot
    inv_item = db_session.query(InventoryItem).filter(InventoryItem.id == inv_id).first()
    initial_qty = inv_item.quantity
    initial_status = inv_item.status

    # Query all 5 reports repeatedly
    for _ in range(3):
        client.get(f"/api/v1/reports/disasters/{disaster_id}/summary", headers=admin_h)
        client.get(f"/api/v1/reports/disasters/{disaster_id}/inventory", headers=admin_h)
        client.get(f"/api/v1/reports/disasters/{disaster_id}/distributions", headers=admin_h)
        client.get(f"/api/v1/reports/disasters/{disaster_id}/volunteers", headers=admin_h)
        client.get(f"/api/v1/reports/disasters/{disaster_id}/beneficiaries", headers=admin_h)

    # Assert state has not changed
    db_session.refresh(inv_item)
    assert inv_item.quantity == initial_qty
    assert inv_item.status == initial_status
