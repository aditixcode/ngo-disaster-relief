"""
Stage 7: Automated Tests for Relief Inventory Management.

Verifies:
1. Inventory intake (RECEIVED status, timestamps).
2. Role-based access control (Admin/Staff only for mutations, all authenticated for viewing).
3. Input validation (positive quantity, non-empty fields, valid disaster reference).
4. Lifecycle state machine (RECEIVED -> STORED via /store and /status endpoints).
5. State lock & transition validation (cannot revert to RECEIVED, cannot double-store).
6. Distributable stock calculation (ONLY STORED items count toward available stock).
7. Filtering, retrieval, and error cases (404, 422, 400, 401, 403).
"""

from datetime import datetime, timezone
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.inventory import InventoryItem, InventoryStatus
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
def create_test_disaster(client: TestClient, admin_headers: dict, name: str = "Disaster Alpha") -> int:
    now = datetime.now(timezone.utc)
    resp = client.post(
        "/api/v1/disasters",
        json={
            "name": name,
            "location": "Relief Zone 1",
            "status": "ACTIVE",
            "start_date": now.isoformat(),
        },
        headers=admin_headers,
    )
    assert resp.status_code == 201
    return resp.json()["id"]


# ==============================================================================
# 1. INTAKE & RBAC TESTS
# ==============================================================================

def test_admin_and_staff_can_intake_inventory(client: TestClient):
    """Admin and NGO Staff can intake relief inventory items into RECEIVED status."""
    admin_h = get_user_headers(client, "admin_inv1@relief.org", "ADMIN")
    staff_h = get_user_headers(client, "staff_inv1@relief.org", "NGO_STAFF")
    disaster_id = create_test_disaster(client, admin_h, "Flood Relief Alpha")

    # Admin intake
    admin_payload = {
        "disaster_id": disaster_id,
        "item_name": "Basmati Rice",
        "quantity": 500.0,
        "unit": "kg",
    }
    response = client.post(
        "/api/v1/inventory",
        json=admin_payload,
        headers=admin_h,
    )
    assert response.status_code == 201
    data = response.json()
    assert data["item_name"] == "Basmati Rice"
    assert data["quantity"] == 500.0
    assert data["unit"] == "kg"
    assert data["status"] == "RECEIVED"
    assert data["received_at"] is not None
    assert data["stored_at"] is None

    # Staff intake
    staff_payload = {
        "disaster_id": disaster_id,
        "item_name": "First Aid Kits",
        "quantity": 100.0,
        "unit": "boxes",
    }
    response = client.post(
        "/api/v1/inventory",
        json=staff_payload,
        headers=staff_h,
    )
    assert response.status_code == 201
    assert response.json()["status"] == "RECEIVED"


def test_volunteer_and_donor_forbidden_from_intake(client: TestClient):
    """Volunteers and Donors cannot intake inventory (403 Forbidden)."""
    admin_h = get_user_headers(client, "admin_inv2@relief.org", "ADMIN")
    vol_h = get_user_headers(client, "vol_inv2@relief.org", "VOLUNTEER")
    donor_h = get_user_headers(client, "donor_inv2@relief.org", "DONOR")
    disaster_id = create_test_disaster(client, admin_h, "Earthquake Bravo")

    payload = {
        "disaster_id": disaster_id,
        "item_name": "Blankets",
        "quantity": 50.0,
        "unit": "pieces",
    }

    # Volunteer attempt
    resp_vol = client.post(
        "/api/v1/inventory",
        json=payload,
        headers=vol_h,
    )
    assert resp_vol.status_code == 403

    # Donor attempt
    resp_don = client.post(
        "/api/v1/inventory",
        json=payload,
        headers=donor_h,
    )
    assert resp_don.status_code == 403


def test_unauthenticated_cannot_access_inventory(client: TestClient):
    """Unauthenticated requests must be rejected with 401 Unauthorized."""
    assert client.post("/api/v1/inventory", json={}).status_code == 401
    assert client.get("/api/v1/inventory").status_code == 401
    assert client.get("/api/v1/inventory/available?disaster_id=1&item_name=rice&unit=kg").status_code == 401
    assert client.get("/api/v1/inventory/1").status_code == 401
    assert client.patch("/api/v1/inventory/1/store").status_code == 401


# ==============================================================================
# 2. VALIDATION & ERROR HANDLING
# ==============================================================================

def test_nonexistent_disaster_rejected(client: TestClient):
    """Attempting intake for a nonexistent disaster returns 404."""
    admin_h = get_user_headers(client, "admin_inv3@relief.org", "ADMIN")
    payload = {
        "disaster_id": 999999,
        "item_name": "Water Bottles",
        "quantity": 100.0,
        "unit": "litres",
    }
    response = client.post(
        "/api/v1/inventory",
        json=payload,
        headers=admin_h,
    )
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_invalid_inventory_payload_rejected(client: TestClient):
    """Validation checks: non-positive quantity, empty strings, missing fields."""
    admin_h = get_user_headers(client, "admin_inv4@relief.org", "ADMIN")
    disaster_id = create_test_disaster(client, admin_h, "Storm Charlie")

    # Zero quantity
    resp_zero = client.post(
        "/api/v1/inventory",
        json={"disaster_id": disaster_id, "item_name": "Tents", "quantity": 0, "unit": "pieces"},
        headers=admin_h,
    )
    assert resp_zero.status_code == 422

    # Negative quantity
    resp_neg = client.post(
        "/api/v1/inventory",
        json={"disaster_id": disaster_id, "item_name": "Tents", "quantity": -20.5, "unit": "pieces"},
        headers=admin_h,
    )
    assert resp_neg.status_code == 422

    # Empty item_name
    resp_empty_name = client.post(
        "/api/v1/inventory",
        json={"disaster_id": disaster_id, "item_name": "   ", "quantity": 10.0, "unit": "pieces"},
        headers=admin_h,
    )
    assert resp_empty_name.status_code == 422

    # Empty unit
    resp_empty_unit = client.post(
        "/api/v1/inventory",
        json={"disaster_id": disaster_id, "item_name": "Tents", "quantity": 10.0, "unit": "  "},
        headers=admin_h,
    )
    assert resp_empty_unit.status_code == 422


# ==============================================================================
# 3. LIFECYCLE TRANSITIONS & STATE MACHINE LOCKS
# ==============================================================================

def test_store_inventory_item_success(client: TestClient):
    """Moving item from RECEIVED to STORED records stored_at and updates status."""
    admin_h = get_user_headers(client, "admin_inv5@relief.org", "ADMIN")
    staff_h = get_user_headers(client, "staff_inv5@relief.org", "NGO_STAFF")
    disaster_id = create_test_disaster(client, admin_h, "Tsunami Delta")

    # Intake
    create_resp = client.post(
        "/api/v1/inventory",
        json={"disaster_id": disaster_id, "item_name": "Tarpaulins", "quantity": 250.0, "unit": "sheets"},
        headers=staff_h,
    )
    item_id = create_resp.json()["id"]

    # Transition to STORED via /store
    store_resp = client.patch(
        f"/api/v1/inventory/{item_id}/store",
        headers=staff_h,
    )
    assert store_resp.status_code == 200
    stored_data = store_resp.json()
    assert stored_data["status"] == "STORED"
    assert stored_data["stored_at"] is not None


def test_invalid_status_transitions_and_locks(client: TestClient):
    """Enforces strict state transitions and prevents arbitrary tampering."""
    admin_h = get_user_headers(client, "admin_inv6@relief.org", "ADMIN")
    vol_h = get_user_headers(client, "vol_inv6@relief.org", "VOLUNTEER")
    disaster_id = create_test_disaster(client, admin_h, "Wildfire Echo")

    # Intake item
    create_resp = client.post(
        "/api/v1/inventory",
        json={"disaster_id": disaster_id, "item_name": "N95 Masks", "quantity": 1000.0, "unit": "pieces"},
        headers=admin_h,
    )
    item_id = create_resp.json()["id"]

    # 1. Volunteer cannot transition status
    vol_resp = client.patch(
        f"/api/v1/inventory/{item_id}/store",
        headers=vol_h,
    )
    assert vol_resp.status_code == 403

    # 2. Transition to STORED
    store_resp = client.patch(
        f"/api/v1/inventory/{item_id}/store",
        headers=admin_h,
    )
    assert store_resp.status_code == 200

    # 3. Double-store attempt must fail
    double_store = client.patch(
        f"/api/v1/inventory/{item_id}/store",
        headers=admin_h,
    )
    assert double_store.status_code == 400
    assert "already in 'STORED' status" in double_store.json()["detail"]

    # 4. Backward transition STORED -> RECEIVED must fail
    revert_resp = client.patch(
        f"/api/v1/inventory/{item_id}/status",
        json={"status": "RECEIVED"},
        headers=admin_h,
    )
    assert revert_resp.status_code == 400
    assert "cannot revert" in revert_resp.json()["detail"].lower()

    # 5. Direct manual jump to DISTRIBUTED without distribution module must fail
    distrib_resp = client.patch(
        f"/api/v1/inventory/{item_id}/status",
        json={"status": "DISTRIBUTED"},
        headers=admin_h,
    )
    assert distrib_resp.status_code == 400
    assert "distribution" in distrib_resp.json()["detail"].lower()


# ==============================================================================
# 4. DISTRIBUTABLE STOCK CALCULATION (CRITICAL REQUIREMENT)
# ==============================================================================

def test_available_quantity_calculation_stored_only(client: TestClient, db_session: Session):
    """
    CRITICAL: Available quantity must strictly sum ONLY items where status == STORED.
    Items in RECEIVED status are not yet inspected and CANNOT be distributed.
    """
    admin_h = get_user_headers(client, "admin_inv7@relief.org", "ADMIN")
    staff_h = get_user_headers(client, "staff_inv7@relief.org", "NGO_STAFF")
    disaster_id = create_test_disaster(client, admin_h, "Monsoon Floods Foxtrot")

    # 1. Intake 100 kg Rice (RECEIVED)
    resp1 = client.post(
        "/api/v1/inventory",
        json={"disaster_id": disaster_id, "item_name": "Wheat Flour", "quantity": 100.0, "unit": "kg"},
        headers=admin_h,
    )
    item1_id = resp1.json()["id"]

    # Stock check: Should be 0.0 because it's still RECEIVED
    avail_resp = client.get(
        f"/api/v1/inventory/available?disaster_id={disaster_id}&item_name=Wheat%20Flour&unit=kg",
        headers=staff_h,
    )
    assert avail_resp.status_code == 200
    assert avail_resp.json()["available_quantity"] == 0.0

    # Direct service check
    assert get_available_quantity(db_session, disaster_id, "Wheat Flour", "kg") == 0.0

    # 2. Store item 1 (100 kg) -> Available should now be 100.0
    client.patch(
        f"/api/v1/inventory/{item1_id}/store",
        headers=staff_h,
    )
    avail_resp2 = client.get(
        f"/api/v1/inventory/available?disaster_id={disaster_id}&item_name=Wheat%20Flour&unit=kg",
        headers=staff_h,
    )
    assert avail_resp2.json()["available_quantity"] == 100.0
    assert get_available_quantity(db_session, disaster_id, "Wheat Flour", "kg") == 100.0

    # 3. Intake an additional 50 kg Wheat Flour (RECEIVED)
    resp2 = client.post(
        "/api/v1/inventory",
        json={"disaster_id": disaster_id, "item_name": "Wheat Flour", "quantity": 50.0, "unit": "kg"},
        headers=admin_h,
    )
    item2_id = resp2.json()["id"]

    # Available stock must STILL be 100.0 (the 50 kg is unverified)
    avail_resp3 = client.get(
        f"/api/v1/inventory/available?disaster_id={disaster_id}&item_name=Wheat%20Flour&unit=kg",
        headers=staff_h,
    )
    assert avail_resp3.json()["available_quantity"] == 100.0

    # 4. Store item 2 (50 kg) -> Available stock becomes 150.0
    client.patch(
        f"/api/v1/inventory/{item2_id}/store",
        headers=staff_h,
    )
    avail_resp4 = client.get(
        f"/api/v1/inventory/available?disaster_id={disaster_id}&item_name=Wheat%20Flour&unit=kg",
        headers=staff_h,
    )
    assert avail_resp4.json()["available_quantity"] == 150.0
    assert get_available_quantity(db_session, disaster_id, "Wheat Flour", "kg") == 150.0

    # 5. Unit separation: 20 sacks Wheat Flour does not blend into 'kg'
    client.post(
        "/api/v1/inventory",
        json={"disaster_id": disaster_id, "item_name": "Wheat Flour", "quantity": 20.0, "unit": "sacks"},
        headers=admin_h,
    )
    avail_kg = client.get(
        f"/api/v1/inventory/available?disaster_id={disaster_id}&item_name=Wheat%20Flour&unit=kg",
        headers=staff_h,
    )
    assert avail_kg.json()["available_quantity"] == 150.0


# ==============================================================================
# 5. LIST, FILTER, AND DETAIL RETRIEVAL
# ==============================================================================

def test_list_and_filter_inventory(client: TestClient):
    """Authenticated users (including volunteers) can view and filter inventory."""
    admin_h = get_user_headers(client, "admin_inv8@relief.org", "ADMIN")
    vol_h = get_user_headers(client, "vol_inv8@relief.org", "VOLUNTEER")
    disaster_a_id = create_test_disaster(client, admin_h, "Disaster Alpha 8")
    disaster_b_id = create_test_disaster(client, admin_h, "Disaster Beta 8")

    # Create 3 items
    r1 = client.post(
        "/api/v1/inventory",
        json={"disaster_id": disaster_a_id, "item_name": "Medicines Box", "quantity": 10.0, "unit": "boxes"},
        headers=admin_h,
    )
    r2 = client.post(
        "/api/v1/inventory",
        json={"disaster_id": disaster_a_id, "item_name": "Surgical Masks", "quantity": 500.0, "unit": "pieces"},
        headers=admin_h,
    )
    r3 = client.post(
        "/api/v1/inventory",
        json={"disaster_id": disaster_b_id, "item_name": "Drinking Water", "quantity": 1000.0, "unit": "litres"},
        headers=admin_h,
    )

    # Store r1
    client.patch(f"/api/v1/inventory/{r1.json()['id']}/store", headers=admin_h)

    # Volunteer views list
    all_resp = client.get("/api/v1/inventory", headers=vol_h)
    assert all_resp.status_code == 200
    assert len(all_resp.json()) >= 3

    # Filter by disaster_id
    filter_a = client.get(
        f"/api/v1/inventory?disaster_id={disaster_a_id}",
        headers=vol_h,
    )
    assert filter_a.status_code == 200
    assert all(item["disaster_id"] == disaster_a_id for item in filter_a.json())

    # Filter by status=STORED
    filter_stored = client.get(
        "/api/v1/inventory?status=STORED",
        headers=vol_h,
    )
    assert filter_stored.status_code == 200
    assert all(item["status"] == "STORED" for item in filter_stored.json())

    # Filter by item_name search
    filter_name = client.get(
        "/api/v1/inventory?item_name=surgical",
        headers=vol_h,
    )
    assert filter_name.status_code == 200
    assert len(filter_name.json()) == 1
    assert filter_name.json()[0]["item_name"] == "Surgical Masks"


def test_get_inventory_by_id(client: TestClient):
    """Fetch inventory item by ID returns 200 or 404."""
    admin_h = get_user_headers(client, "admin_inv9@relief.org", "ADMIN")
    donor_h = get_user_headers(client, "donor_inv9@relief.org", "DONOR")
    disaster_id = create_test_disaster(client, admin_h, "Disaster Detail 9")

    create_resp = client.post(
        "/api/v1/inventory",
        json={"disaster_id": disaster_id, "item_name": "Milk Powder", "quantity": 80.0, "unit": "cans"},
        headers=admin_h,
    )
    item_id = create_resp.json()["id"]

    # Valid ID
    resp = client.get(f"/api/v1/inventory/{item_id}", headers=donor_h)
    assert resp.status_code == 200
    assert resp.json()["id"] == item_id
    assert resp.json()["item_name"] == "Milk Powder"

    # Nonexistent ID
    resp_404 = client.get("/api/v1/inventory/99999", headers=donor_h)
    assert resp_404.status_code == 404
