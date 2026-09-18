"""
Stage 10: Automated Tests for Resource Distribution Tracking.

Verifies:
1. End-to-end atomic resource distribution (Disaster -> Inventory -> Beneficiary -> Center -> User).
2. RBAC guards (ADMIN, NGO_STAFF permitted; VOLUNTEER, DONOR rejected with 403; unauth rejected with 401).
3. Payload validation (positive quantity > 0, non-empty unit, required fields).
4. Disaster cross-entity integrity (beneficiary, center, inventory matching disaster ID).
5. Beneficiary eligibility gating (only VERIFIED status permitted; PENDING/INACTIVE rejected with 400).
6. Distribution center operational eligibility gating (only ACTIVE status permitted; FULL/INACTIVE rejected with 400).
7. Inventory batch validation (only STORED status allowed; RECEIVED/DISTRIBUTED rejected; unit/item name matching).
8. Partial inventory deduction (100 kg -> 30 kg distributed -> 70 kg remaining STORED).
9. Exact batch depletion (70 kg -> 70 kg distributed -> 0 kg remaining DISTRIBUTED).
10. Multi-batch allocation & deduction across sibling batches (100 kg batch A + 80 kg batch B: distribute 150 kg -> batch A depleted, batch B 30 kg remaining).
11. Overselling protection (requesting more than total available stock rejected with 400 without modifying inventory).
12. Audit record retrieval, filtering (by disaster, beneficiary, center, inventory item), and detail view.
"""

from datetime import datetime, timezone, timedelta
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.inventory import InventoryItem, InventoryStatus
from app.models.beneficiary import Beneficiary, RegistrationStatus
from app.models.distribution_center import DistributionCenter, CenterStatus
from app.models.distribution import ResourceDistribution
from app.services.inventory_service import get_available_quantity


# Helper to register user and obtain Bearer auth headers
def get_user_headers(client: TestClient, email: str, role: str) -> dict:
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


# Helper to create a test disaster
def create_test_disaster(client: TestClient, admin_headers: dict, name: str = "Disaster Flood") -> int:
    now = datetime.now(timezone.utc)
    resp = client.post(
        "/api/v1/disasters",
        json={
            "name": name,
            "location": "River Valley Sector 4",
            "status": "ACTIVE",
            "start_date": now.isoformat(),
        },
        headers=admin_headers,
    )
    assert resp.status_code == 201
    return resp.json()["id"]


# Helper to create a distribution center
def create_test_center(
    client: TestClient,
    admin_headers: dict,
    disaster_id: int,
    name: str = "Central Distribution Hub",
) -> int:
    resp = client.post(
        "/api/v1/distribution-centers",
        json={
            "disaster_id": disaster_id,
            "name": name,
            "address": "Main Ground Sector 1",
            "contact_number": "+91-9876543210",
            "capacity": 1000,
        },
        headers=admin_headers,
    )
    assert resp.status_code == 201
    return resp.json()["id"]


# Helper to create and verify a beneficiary
def create_test_beneficiary(
    client: TestClient,
    admin_headers: dict,
    disaster_id: int,
    name: str = "Rajesh Kumar",
    contact: str = "+91-9123456780",
    verify: bool = True,
) -> int:
    resp = client.post(
        "/api/v1/beneficiaries",
        json={
            "disaster_id": disaster_id,
            "name": name,
            "contact_number": contact,
            "address": "Camp 4, Tent 12",
            "household_size": 4,
            "vulnerability_category": "ELDERLY",
        },
        headers=admin_headers,
    )
    assert resp.status_code == 201
    b_id = resp.json()["id"]

    if verify:
        v_resp = client.patch(
            f"/api/v1/beneficiaries/{b_id}/status",
            json={"status": "VERIFIED"},
            headers=admin_headers,
        )
        assert v_resp.status_code == 200
        assert v_resp.json()["registration_status"] == "VERIFIED"

    return b_id



# Helper to intake inventory and advance it to STORED status
def create_test_inventory(
    client: TestClient,
    admin_headers: dict,
    disaster_id: int,
    item_name: str = "Rice",
    quantity: float = 100.0,
    unit: str = "kg",
    move_to_stored: bool = True,
) -> int:
    resp = client.post(
        "/api/v1/inventory",
        json={
            "disaster_id": disaster_id,
            "item_name": item_name,
            "quantity": quantity,
            "unit": unit,
        },
        headers=admin_headers,
    )
    assert resp.status_code == 201
    inv_id = resp.json()["id"]

    if move_to_stored:
        s_resp = client.patch(
            f"/api/v1/inventory/{inv_id}/status",
            json={"status": "STORED"},
            headers=admin_headers,
        )
        assert s_resp.status_code == 200
        assert s_resp.json()["status"] == "STORED"

    return inv_id


# ==============================================================================
# 1. RBAC & PERMISSION TESTS
# ==============================================================================

def test_rbac_for_distribution_recording(client: TestClient):
    """Admin and NGO_STAFF can distribute; Volunteer and Donor are forbidden."""
    admin_h = get_user_headers(client, "admin_dist1@ngo.org", "ADMIN")
    staff_h = get_user_headers(client, "staff_dist1@ngo.org", "NGO_STAFF")
    vol_h = get_user_headers(client, "vol_dist1@ngo.org", "VOLUNTEER")
    donor_h = get_user_headers(client, "donor_dist1@ngo.org", "DONOR")

    disaster_id = create_test_disaster(client, admin_h, "RBAC Disaster")
    center_id = create_test_center(client, admin_h, disaster_id, "RBAC Center")
    ben_id = create_test_beneficiary(client, admin_h, disaster_id, "Aarav Sharma", "+91-9988776655")
    inv_id = create_test_inventory(client, admin_h, disaster_id, "Rice", 100.0, "kg")

    payload = {
        "disaster_id": disaster_id,
        "inventory_item_id": inv_id,
        "beneficiary_id": ben_id,
        "distribution_center_id": center_id,
        "quantity": 10.0,
        "unit": "kg",
    }

    # 1. Unauthenticated -> 401
    resp_unauth = client.post("/api/v1/distributions", json=payload)
    assert resp_unauth.status_code == 401

    # 2. Volunteer -> 403
    resp_vol = client.post("/api/v1/distributions", json=payload, headers=vol_h)
    assert resp_vol.status_code == 403

    # 3. Donor -> 403
    resp_donor = client.post("/api/v1/distributions", json=payload, headers=donor_h)
    assert resp_donor.status_code == 403

    # 4. NGO Staff -> 201
    resp_staff = client.post("/api/v1/distributions", json=payload, headers=staff_h)
    assert resp_staff.status_code == 201
    assert resp_staff.json()["quantity"] == 10.0
    assert resp_staff.json()["distributed_by_id"] is not None

    # 5. Admin -> 201
    payload["quantity"] = 15.0
    resp_admin = client.post("/api/v1/distributions", json=payload, headers=admin_h)
    assert resp_admin.status_code == 201
    assert resp_admin.json()["quantity"] == 15.0


# ==============================================================================
# 2. PAYLOAD VALIDATION TESTS
# ==============================================================================

def test_payload_validation_rejects_invalid_inputs(client: TestClient):
    """Quantity must be > 0 and unit cannot be empty."""
    admin_h = get_user_headers(client, "admin_val@ngo.org", "ADMIN")
    disaster_id = create_test_disaster(client, admin_h, "Val Disaster")
    center_id = create_test_center(client, admin_h, disaster_id)
    ben_id = create_test_beneficiary(client, admin_h, disaster_id)
    inv_id = create_test_inventory(client, admin_h, disaster_id, "Rice", 50.0, "kg")

    # Zero quantity -> 422
    resp = client.post(
        "/api/v1/distributions",
        json={
            "disaster_id": disaster_id,
            "inventory_item_id": inv_id,
            "beneficiary_id": ben_id,
            "distribution_center_id": center_id,
            "quantity": 0.0,
            "unit": "kg",
        },
        headers=admin_h,
    )
    assert resp.status_code == 422

    # Negative quantity -> 422
    resp = client.post(
        "/api/v1/distributions",
        json={
            "disaster_id": disaster_id,
            "inventory_item_id": inv_id,
            "beneficiary_id": ben_id,
            "distribution_center_id": center_id,
            "quantity": -10.0,
            "unit": "kg",
        },
        headers=admin_h,
    )
    assert resp.status_code == 422

    # Empty unit -> 422
    resp = client.post(
        "/api/v1/distributions",
        json={
            "disaster_id": disaster_id,
            "inventory_item_id": inv_id,
            "beneficiary_id": ben_id,
            "distribution_center_id": center_id,
            "quantity": 10.0,
            "unit": "   ",
        },
        headers=admin_h,
    )
    assert resp.status_code == 422


def test_distribution_timestamp_validation(client: TestClient):
    """
    Verifies validation rules for distributed_at:
    - Future timestamps are rejected with HTTP 422 Unprocessable Entity.
    - Valid past timestamps are accepted and recorded accurately.
    """
    admin_h = get_user_headers(client, "admin_ts@ngo.org", "ADMIN")
    disaster_id = create_test_disaster(client, admin_h, "Timestamp Disaster")
    center_id = create_test_center(client, admin_h, disaster_id)
    ben_id = create_test_beneficiary(client, admin_h, disaster_id)
    inv_id = create_test_inventory(client, admin_h, disaster_id, "Rice", 100.0, "kg")

    now = datetime.now(timezone.utc)
    future_time = now + timedelta(days=2)
    past_time = now - timedelta(hours=3)

    # 1. Future timestamp -> HTTP 422
    resp_future = client.post(
        "/api/v1/distributions",
        json={
            "disaster_id": disaster_id,
            "inventory_item_id": inv_id,
            "beneficiary_id": ben_id,
            "distribution_center_id": center_id,
            "quantity": 10.0,
            "unit": "kg",
            "distributed_at": future_time.isoformat(),
        },
        headers=admin_h,
    )
    assert resp_future.status_code == 422
    assert "distributed_at timestamp cannot be in the future" in resp_future.text

    # 2. Past timestamp -> HTTP 201 Created
    resp_past = client.post(
        "/api/v1/distributions",
        json={
            "disaster_id": disaster_id,
            "inventory_item_id": inv_id,
            "beneficiary_id": ben_id,
            "distribution_center_id": center_id,
            "quantity": 10.0,
            "unit": "kg",
            "distributed_at": past_time.isoformat(),
        },
        headers=admin_h,
    )
    assert resp_past.status_code == 201
    created_data = resp_past.json()
    assert created_data["quantity"] == 10.0
    assert "distributed_at" in created_data
    # Compare ISO timestamps
    recorded_at = datetime.fromisoformat(created_data["distributed_at"])
    if recorded_at.tzinfo is None:
        recorded_at = recorded_at.replace(tzinfo=timezone.utc)
    assert abs((recorded_at - past_time).total_seconds()) < 2.0


# ==============================================================================
# 3. CROSS-ENTITY & DISASTER INTEGRITY TESTS
# ==============================================================================

def test_cross_disaster_integrity_enforcement(client: TestClient):
    """Entities must belong to the specified disaster."""
    admin_h = get_user_headers(client, "admin_cross@ngo.org", "ADMIN")
    disaster1_id = create_test_disaster(client, admin_h, "Disaster One")
    disaster2_id = create_test_disaster(client, admin_h, "Disaster Two")

    center_d1 = create_test_center(client, admin_h, disaster1_id, "Center D1")
    ben_d1 = create_test_beneficiary(client, admin_h, disaster1_id, "Ben D1", "+91-9876111111")
    inv_d1 = create_test_inventory(client, admin_h, disaster1_id, "Rice", 50.0, "kg")

    # Mismatch 1: Beneficiary from disaster2
    ben_d2 = create_test_beneficiary(client, admin_h, disaster2_id, "Ben D2", "+91-9876222222")
    resp = client.post(
        "/api/v1/distributions",
        json={
            "disaster_id": disaster1_id,
            "inventory_item_id": inv_d1,
            "beneficiary_id": ben_d2,
            "distribution_center_id": center_d1,
            "quantity": 10.0,
            "unit": "kg",
        },
        headers=admin_h,
    )
    assert resp.status_code == 400
    assert "registered under disaster" in resp.json()["detail"].lower()

    # Mismatch 2: Distribution center from disaster2
    center_d2 = create_test_center(client, admin_h, disaster2_id, "Center D2")
    resp = client.post(
        "/api/v1/distributions",
        json={
            "disaster_id": disaster1_id,
            "inventory_item_id": inv_d1,
            "beneficiary_id": ben_d1,
            "distribution_center_id": center_d2,
            "quantity": 10.0,
            "unit": "kg",
        },
        headers=admin_h,
    )
    assert resp.status_code == 400
    assert "assigned to disaster" in resp.json()["detail"].lower() or "belongs to disaster" in resp.json()["detail"].lower()

    # Mismatch 3: Inventory from disaster2
    inv_d2 = create_test_inventory(client, admin_h, disaster2_id, "Rice", 50.0, "kg")
    resp = client.post(
        "/api/v1/distributions",
        json={
            "disaster_id": disaster1_id,
            "inventory_item_id": inv_d2,
            "beneficiary_id": ben_d1,
            "distribution_center_id": center_d1,
            "quantity": 10.0,
            "unit": "kg",
        },
        headers=admin_h,
    )
    assert resp.status_code == 400
    assert "belongs to disaster" in resp.json()["detail"].lower()


# ==============================================================================
# 4. BENEFICIARY ELIGIBILITY GATING TESTS
# ==============================================================================

def test_beneficiary_eligibility_gating(client: TestClient):
    """Distributions only allowed for VERIFIED beneficiaries; PENDING/INACTIVE blocked."""
    admin_h = get_user_headers(client, "admin_elig@ngo.org", "ADMIN")
    disaster_id = create_test_disaster(client, admin_h, "Eligibility Disaster")
    center_id = create_test_center(client, admin_h, disaster_id)
    inv_id = create_test_inventory(client, admin_h, disaster_id, "Lentils", 50.0, "kg")

    # 1. PENDING beneficiary -> 400
    ben_pending_id = create_test_beneficiary(client, admin_h, disaster_id, "Pending Ben", "+91-9111222333", verify=False)
    resp = client.post(
        "/api/v1/distributions",
        json={
            "disaster_id": disaster_id,
            "inventory_item_id": inv_id,
            "beneficiary_id": ben_pending_id,
            "distribution_center_id": center_id,
            "quantity": 5.0,
            "unit": "kg",
        },
        headers=admin_h,
    )
    assert resp.status_code == 400
    assert "only verified beneficiaries" in resp.json()["detail"].lower()

    # 2. Transition PENDING -> VERIFIED -> 201 Success
    client.patch(
        f"/api/v1/beneficiaries/{ben_pending_id}/status",
        json={"status": "VERIFIED"},
        headers=admin_h,
    )
    resp = client.post(
        "/api/v1/distributions",
        json={
            "disaster_id": disaster_id,
            "inventory_item_id": inv_id,
            "beneficiary_id": ben_pending_id,
            "distribution_center_id": center_id,
            "quantity": 5.0,
            "unit": "kg",
        },
        headers=admin_h,
    )
    assert resp.status_code == 201

    # 3. Transition VERIFIED -> INACTIVE -> 400 Blocked
    client.patch(
        f"/api/v1/beneficiaries/{ben_pending_id}/status",
        json={"status": "INACTIVE"},
        headers=admin_h,
    )
    resp_inactive = client.post(
        "/api/v1/distributions",
        json={
            "disaster_id": disaster_id,
            "inventory_item_id": inv_id,
            "beneficiary_id": ben_pending_id,
            "distribution_center_id": center_id,
            "quantity": 5.0,
            "unit": "kg",
        },
        headers=admin_h,
    )
    assert resp_inactive.status_code == 400
    assert "only verified beneficiaries" in resp_inactive.json()["detail"].lower()



# ==============================================================================
# 5. DISTRIBUTION CENTER OPERATIONAL GATING TESTS
# ==============================================================================

def test_distribution_center_operational_gating(client: TestClient):
    """Distributions only allowed from ACTIVE centers; FULL/INACTIVE blocked."""
    admin_h = get_user_headers(client, "admin_center_gate@ngo.org", "ADMIN")
    disaster_id = create_test_disaster(client, admin_h, "Center Gate Disaster")
    center_id = create_test_center(client, admin_h, disaster_id, "Gate Hub")
    ben_id = create_test_beneficiary(client, admin_h, disaster_id)
    inv_id = create_test_inventory(client, admin_h, disaster_id, "Blankets", 50.0, "pieces")

    # Set center to FULL
    client.patch(
        f"/api/v1/distribution-centers/{center_id}/status",
        json={"status": "FULL"},
        headers=admin_h,
    )
    resp_full = client.post(
        "/api/v1/distributions",
        json={
            "disaster_id": disaster_id,
            "inventory_item_id": inv_id,
            "beneficiary_id": ben_id,
            "distribution_center_id": center_id,
            "quantity": 2.0,
            "unit": "pieces",
        },
        headers=admin_h,
    )
    assert resp_full.status_code == 400
    assert "only be dispatched from active" in resp_full.json()["detail"].lower()

    # Set center to INACTIVE
    client.patch(
        f"/api/v1/distribution-centers/{center_id}/status",
        json={"status": "INACTIVE"},
        headers=admin_h,
    )
    resp_inact = client.post(
        "/api/v1/distributions",
        json={
            "disaster_id": disaster_id,
            "inventory_item_id": inv_id,
            "beneficiary_id": ben_id,
            "distribution_center_id": center_id,
            "quantity": 2.0,
            "unit": "pieces",
        },
        headers=admin_h,
    )
    assert resp_inact.status_code == 400

    # Reopen as ACTIVE -> 201 Success
    client.patch(
        f"/api/v1/distribution-centers/{center_id}/status",
        json={"status": "ACTIVE"},
        headers=admin_h,
    )
    resp_act = client.post(
        "/api/v1/distributions",
        json={
            "disaster_id": disaster_id,
            "inventory_item_id": inv_id,
            "beneficiary_id": ben_id,
            "distribution_center_id": center_id,
            "quantity": 2.0,
            "unit": "pieces",
        },
        headers=admin_h,
    )
    assert resp_act.status_code == 201


# ==============================================================================
# 6. INVENTORY STATUS, UNIT & NAME SAFEGUARDS
# ==============================================================================

def test_inventory_safeguards_and_status(client: TestClient):
    """Items in RECEIVED status, unit mismatches, and name mismatches are rejected."""
    admin_h = get_user_headers(client, "admin_safe@ngo.org", "ADMIN")
    disaster_id = create_test_disaster(client, admin_h, "Safe Disaster")
    center_id = create_test_center(client, admin_h, disaster_id)
    ben_id = create_test_beneficiary(client, admin_h, disaster_id)

    # Inventory left in RECEIVED status (awaiting inspection)
    inv_received_id = create_test_inventory(
        client, admin_h, disaster_id, "Medical Kits", 30.0, "boxes", move_to_stored=False
    )

    resp = client.post(
        "/api/v1/distributions",
        json={
            "disaster_id": disaster_id,
            "inventory_item_id": inv_received_id,
            "beneficiary_id": ben_id,
            "distribution_center_id": center_id,
            "quantity": 1.0,
            "unit": "boxes",
        },
        headers=admin_h,
    )
    assert resp.status_code == 400
    assert "only inventory items in stored status" in resp.json()["detail"].lower()

    # Move to STORED for unit and name check
    client.patch(
        f"/api/v1/inventory/{inv_received_id}/status",
        json={"status": "STORED"},
        headers=admin_h,
    )

    # Unit mismatch: inventory is in "boxes", request says "kg"
    resp_unit = client.post(
        "/api/v1/distributions",
        json={
            "disaster_id": disaster_id,
            "inventory_item_id": inv_received_id,
            "beneficiary_id": ben_id,
            "distribution_center_id": center_id,
            "quantity": 1.0,
            "unit": "kg",
        },
        headers=admin_h,
    )
    assert resp_unit.status_code == 400
    assert "unit mismatch" in resp_unit.json()["detail"].lower()

    # Item name mismatch safeguard
    resp_name = client.post(
        "/api/v1/distributions",
        json={
            "disaster_id": disaster_id,
            "inventory_item_id": inv_received_id,
            "beneficiary_id": ben_id,
            "distribution_center_id": center_id,
            "quantity": 1.0,
            "unit": "boxes",
            "item_name": "Tents",  # Batch is 'Medical Kits'
        },
        headers=admin_h,
    )
    assert resp_name.status_code == 400
    assert "item name mismatch" in resp_name.json()["detail"].lower()


# ==============================================================================
# 7. PARTIAL DEDUCTION & EXACT BATCH DEPLETION
# ==============================================================================

def test_partial_and_exact_inventory_depletion(client: TestClient, db_session: Session):
    """
    1. Intake 100 kg Rice (STORED).
    2. Distribute 30 kg -> batch remaining is 70 kg, status is STORED.
    3. Distribute remaining 70 kg -> batch remaining is 0 kg, status is DISTRIBUTED.
    4. Next distribution attempt fails with 400 (depleted).
    """
    admin_h = get_user_headers(client, "admin_deduct@ngo.org", "ADMIN")
    disaster_id = create_test_disaster(client, admin_h, "Deduct Disaster")
    center_id = create_test_center(client, admin_h, disaster_id)
    ben_id = create_test_beneficiary(client, admin_h, disaster_id)
    inv_id = create_test_inventory(client, admin_h, disaster_id, "Rice", 100.0, "kg")

    # Initial available stock is 100.0
    assert get_available_quantity(db_session, disaster_id, "Rice", "kg") == 100.0

    # Step 1: Distribute 30 kg
    resp1 = client.post(
        "/api/v1/distributions",
        json={
            "disaster_id": disaster_id,
            "inventory_item_id": inv_id,
            "beneficiary_id": ben_id,
            "distribution_center_id": center_id,
            "quantity": 30.0,
            "unit": "kg",
            "notes": "First distribution tranche",
        },
        headers=admin_h,
    )
    assert resp1.status_code == 201
    dist1 = resp1.json()
    assert dist1["quantity"] == 30.0
    assert dist1["notes"] == "First distribution tranche"

    # Verify inventory state
    inv_item = db_session.query(InventoryItem).filter(InventoryItem.id == inv_id).first()
    assert inv_item.quantity == 70.0
    assert inv_item.status == InventoryStatus.STORED
    assert get_available_quantity(db_session, disaster_id, "Rice", "kg") == 70.0

    # Step 2: Distribute exact remaining 70 kg
    resp2 = client.post(
        "/api/v1/distributions",
        json={
            "disaster_id": disaster_id,
            "inventory_item_id": inv_id,
            "beneficiary_id": ben_id,
            "distribution_center_id": center_id,
            "quantity": 70.0,
            "unit": "kg",
            "notes": "Final batch clearance",
        },
        headers=admin_h,
    )
    assert resp2.status_code == 201

    # Verify inventory state transitions to DISTRIBUTED
    db_session.refresh(inv_item)
    assert inv_item.quantity == 0.0
    assert inv_item.status == InventoryStatus.DISTRIBUTED
    assert get_available_quantity(db_session, disaster_id, "Rice", "kg") == 0.0

    # Step 3: Attempt distribution from depleted item -> 400
    resp3 = client.post(
        "/api/v1/distributions",
        json={
            "disaster_id": disaster_id,
            "inventory_item_id": inv_id,
            "beneficiary_id": ben_id,
            "distribution_center_id": center_id,
            "quantity": 1.0,
            "unit": "kg",
        },
        headers=admin_h,
    )
    assert resp3.status_code == 400
    assert "status 'distributed'" in resp3.json()["detail"].lower()



# ==============================================================================
# 8. MULTI-BATCH ALLOCATION & OVERSELLING PROTECTION
# ==============================================================================

def test_multi_batch_allocation_and_overselling_protection(client: TestClient, db_session: Session):
    """
    Scenario:
    - Batch A: 100 kg Rice (STORED)
    - Batch B: 80 kg Rice (STORED)
    - Total available: 180 kg

    Actions:
    1. Distribute 150 kg referencing Batch A.
       Result: Batch A -> 0 kg (DISTRIBUTED), Batch B -> 30 kg (STORED). Total remaining: 30 kg.
    2. Attempt to distribute 31 kg referencing Batch B.
       Result: 400 Insufficient stock (31 > 30). Inventory untouched.
    3. Distribute 30 kg referencing Batch B.
       Result: Batch B -> 0 kg (DISTRIBUTED). Total remaining: 0 kg.
    """
    admin_h = get_user_headers(client, "admin_multi@ngo.org", "ADMIN")
    disaster_id = create_test_disaster(client, admin_h, "Multi Batch Disaster")
    center_id = create_test_center(client, admin_h, disaster_id)
    ben_id = create_test_beneficiary(client, admin_h, disaster_id)

    batch_a_id = create_test_inventory(client, admin_h, disaster_id, "Rice", 100.0, "kg")
    batch_b_id = create_test_inventory(client, admin_h, disaster_id, "Rice", 80.0, "kg")

    assert get_available_quantity(db_session, disaster_id, "Rice", "kg") == 180.0

    # 1. Distribute 150 kg
    resp1 = client.post(
        "/api/v1/distributions",
        json={
            "disaster_id": disaster_id,
            "inventory_item_id": batch_a_id,
            "beneficiary_id": ben_id,
            "distribution_center_id": center_id,
            "quantity": 150.0,
            "unit": "kg",
            "notes": "Multi-batch tranche distribution",
        },
        headers=admin_h,
    )
    assert resp1.status_code == 201

    batch_a = db_session.query(InventoryItem).filter(InventoryItem.id == batch_a_id).first()
    batch_b = db_session.query(InventoryItem).filter(InventoryItem.id == batch_b_id).first()

    assert batch_a.quantity == 0.0
    assert batch_a.status == InventoryStatus.DISTRIBUTED
    assert batch_b.quantity == 30.0
    assert batch_b.status == InventoryStatus.STORED
    assert get_available_quantity(db_session, disaster_id, "Rice", "kg") == 30.0

    # 2. Overselling attempt: request 31 kg when only 30 kg available
    resp_over = client.post(
        "/api/v1/distributions",
        json={
            "disaster_id": disaster_id,
            "inventory_item_id": batch_b_id,
            "beneficiary_id": ben_id,
            "distribution_center_id": center_id,
            "quantity": 31.0,
            "unit": "kg",
        },
        headers=admin_h,
    )
    assert resp_over.status_code == 400
    assert "insufficient inventory" in resp_over.json()["detail"].lower()

    # Verify inventory was untouched
    db_session.refresh(batch_b)
    assert batch_b.quantity == 30.0
    assert batch_b.status == InventoryStatus.STORED

    # 3. Distribute exact 30 kg
    resp2 = client.post(
        "/api/v1/distributions",
        json={
            "disaster_id": disaster_id,
            "inventory_item_id": batch_b_id,
            "beneficiary_id": ben_id,
            "distribution_center_id": center_id,
            "quantity": 30.0,
            "unit": "kg",
        },
        headers=admin_h,
    )
    assert resp2.status_code == 201

    db_session.refresh(batch_b)
    assert batch_b.quantity == 0.0
    assert batch_b.status == InventoryStatus.DISTRIBUTED
    assert get_available_quantity(db_session, disaster_id, "Rice", "kg") == 0.0


# ==============================================================================
# 9. LISTING, FILTERING & DETAIL AUDIT ENDPOINTS
# ==============================================================================

def test_list_and_filter_distributions(client: TestClient):
    """Verifies listing and query param filtering across disaster, beneficiary, center, and batch."""
    admin_h = get_user_headers(client, "admin_audit@ngo.org", "ADMIN")
    disaster_id = create_test_disaster(client, admin_h, "Audit Disaster")
    center1_id = create_test_center(client, admin_h, disaster_id, "Audit Hub 1")
    center2_id = create_test_center(client, admin_h, disaster_id, "Audit Hub 2")

    ben1_id = create_test_beneficiary(client, admin_h, disaster_id, "Beneficiary One", "+91-9555111111")
    ben2_id = create_test_beneficiary(client, admin_h, disaster_id, "Beneficiary Two", "+91-9555222222")

    inv1_id = create_test_inventory(client, admin_h, disaster_id, "Water Cans", 100.0, "liters")
    inv2_id = create_test_inventory(client, admin_h, disaster_id, "Tarpaulins", 50.0, "sheets")

    # Distribute 1: Ben1 at Center1 with Inv1
    resp1 = client.post(
        "/api/v1/distributions",
        json={
            "disaster_id": disaster_id,
            "inventory_item_id": inv1_id,
            "beneficiary_id": ben1_id,
            "distribution_center_id": center1_id,
            "quantity": 20.0,
            "unit": "liters",
        },
        headers=admin_h,
    )
    dist1_id = resp1.json()["id"]

    # Distribute 2: Ben2 at Center2 with Inv2
    resp2 = client.post(
        "/api/v1/distributions",
        json={
            "disaster_id": disaster_id,
            "inventory_item_id": inv2_id,
            "beneficiary_id": ben2_id,
            "distribution_center_id": center2_id,
            "quantity": 5.0,
            "unit": "sheets",
        },
        headers=admin_h,
    )
    dist2_id = resp2.json()["id"]

    # 1. List all
    all_resp = client.get("/api/v1/distributions", headers=admin_h)
    assert all_resp.status_code == 200
    records = all_resp.json()
    assert len(records) >= 2

    # 2. Filter by beneficiary
    ben1_resp = client.get(f"/api/v1/distributions?beneficiary_id={ben1_id}", headers=admin_h)
    assert ben1_resp.status_code == 200
    ben1_records = ben1_resp.json()
    assert len(ben1_records) == 1
    assert ben1_records[0]["id"] == dist1_id

    # 3. Filter by distribution center
    center2_resp = client.get(f"/api/v1/distributions?distribution_center_id={center2_id}", headers=admin_h)
    assert center2_resp.status_code == 200
    center2_records = center2_resp.json()
    assert len(center2_records) == 1
    assert center2_records[0]["id"] == dist2_id

    # 4. Filter by inventory item
    inv1_resp = client.get(f"/api/v1/distributions?inventory_item_id={inv1_id}", headers=admin_h)
    assert inv1_resp.status_code == 200
    assert len(inv1_resp.json()) == 1

    # 5. Get by ID
    get_resp = client.get(f"/api/v1/distributions/{dist1_id}", headers=admin_h)
    assert get_resp.status_code == 200
    assert get_resp.json()["id"] == dist1_id
    assert get_resp.json()["quantity"] == 20.0
    assert get_resp.json()["item_name"] == "Water Cans"

    # 6. Get non-existent ID -> 404
    not_found_resp = client.get("/api/v1/distributions/999999", headers=admin_h)
    assert not_found_resp.status_code == 404
