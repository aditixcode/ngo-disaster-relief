"""
Stage 9: Automated Tests for Distribution Center Management.

Verifies:
1. Center registration (ADMIN, NGO_STAFF permissions, initial ACTIVE status).
2. RBAC guards (Volunteer/Donor forbidden, unauthenticated rejected).
3. Input validation (non-empty strings, positive capacity > 0, valid disaster).
4. Unique center name enforcement within the same disaster event.
5. Operational status lifecycle (ACTIVE, FULL, INACTIVE).
6. State transition rules (e.g. INACTIVE cannot jump directly to FULL).
7. Operational eligibility check (is_center_eligible_for_distribution).
8. Detail retrieval, listing, and multi-field filtering.
9. Configuration updates and admin-only deletion.
"""

from datetime import datetime, timezone
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.distribution_center import DistributionCenter, CenterStatus
from app.services.distribution_center_service import is_center_eligible_for_distribution


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
def create_test_disaster(client: TestClient, admin_headers: dict, name: str = "Disaster Hub") -> int:
    now = datetime.now(timezone.utc)
    resp = client.post(
        "/api/v1/disasters",
        json={
            "name": name,
            "location": "Coastal Zone Alpha",
            "status": "ACTIVE",
            "start_date": now.isoformat(),
        },
        headers=admin_headers,
    )
    assert resp.status_code == 201
    return resp.json()["id"]


# ==============================================================================
# 1. REGISTRATION & RBAC TESTS
# ==============================================================================

def test_admin_and_staff_can_create_center(client: TestClient):
    """Admin and NGO Staff can register distribution centers in ACTIVE status."""
    admin_h = get_user_headers(client, "admin_dc1@relief.org", "ADMIN")
    staff_h = get_user_headers(client, "staff_dc1@relief.org", "NGO_STAFF")
    disaster_id = create_test_disaster(client, admin_h, "Cyclone Alpha")

    # Admin registers center
    admin_payload = {
        "disaster_id": disaster_id,
        "name": "Community Stadium Hub",
        "address": "Stadium Complex Gate 2, City Center",
        "contact_number": "+91-9876543210",
        "capacity": 2000,
        "operating_hours": "08:00 - 18:00 Daily",
    }
    resp1 = client.post("/api/v1/distribution-centers", json=admin_payload, headers=admin_h)
    assert resp1.status_code == 201
    data1 = resp1.json()
    assert data1["name"] == "Community Stadium Hub"
    assert data1["status"] == "ACTIVE"
    assert data1["capacity"] == 2000
    assert data1["is_operational"] is True
    assert data1["created_by_id"] is not None

    # Staff registers center
    staff_payload = {
        "disaster_id": disaster_id,
        "name": "North Ward Relief Point",
        "address": "Town Hall Auditorium",
        "contact_number": "+91-9876543211",
        "capacity": 800,
    }
    resp2 = client.post("/api/v1/distribution-centers", json=staff_payload, headers=staff_h)
    assert resp2.status_code == 201
    assert resp2.json()["status"] == "ACTIVE"
    assert resp2.json()["is_operational"] is True


def test_volunteer_and_donor_forbidden(client: TestClient):
    """Volunteers and Donors cannot register or modify distribution centers (403 Forbidden)."""
    admin_h = get_user_headers(client, "admin_dc2@relief.org", "ADMIN")
    vol_h = get_user_headers(client, "vol_dc2@relief.org", "VOLUNTEER")
    donor_h = get_user_headers(client, "donor_dc2@relief.org", "DONOR")
    disaster_id = create_test_disaster(client, admin_h, "Flood Bravo")

    payload = {
        "disaster_id": disaster_id,
        "name": "Unauthorized Hub",
        "address": "Camp 3",
        "contact_number": "+91-9876543212",
        "capacity": 500,
    }

    # Volunteer attempt
    assert client.post("/api/v1/distribution-centers", json=payload, headers=vol_h).status_code == 403
    assert client.get("/api/v1/distribution-centers", headers=vol_h).status_code == 403

    # Donor attempt
    assert client.post("/api/v1/distribution-centers", json=payload, headers=donor_h).status_code == 403
    assert client.get("/api/v1/distribution-centers", headers=donor_h).status_code == 403


def test_unauthenticated_cannot_access(client: TestClient):
    """Unauthenticated requests must return 401 Unauthorized."""
    assert client.post("/api/v1/distribution-centers", json={}).status_code == 401
    assert client.get("/api/v1/distribution-centers").status_code == 401
    assert client.get("/api/v1/distribution-centers/1").status_code == 401
    assert client.put("/api/v1/distribution-centers/1", json={}).status_code == 401
    assert client.patch("/api/v1/distribution-centers/1/status", json={}).status_code == 401
    assert client.delete("/api/v1/distribution-centers/1").status_code == 401


# ==============================================================================
# 2. VALIDATION & DUPLICATE CHECKS
# ==============================================================================

def test_nonexistent_disaster_rejected(client: TestClient):
    """Attempting center registration under nonexistent disaster returns 404."""
    admin_h = get_user_headers(client, "admin_dc3@relief.org", "ADMIN")
    payload = {
        "disaster_id": 999999,
        "name": "Ghost Center",
        "address": "Unknown Road",
        "contact_number": "+91-9876543213",
        "capacity": 1000,
    }
    resp = client.post("/api/v1/distribution-centers", json=payload, headers=admin_h)
    assert resp.status_code == 404
    assert "not found" in resp.json()["detail"].lower()


def test_validation_rules_rejected(client: TestClient):
    """Validation checks: blank name/address/contact, capacity <= 0."""
    admin_h = get_user_headers(client, "admin_dc4@relief.org", "ADMIN")
    disaster_id = create_test_disaster(client, admin_h, "Storm Charlie")

    base = {
        "disaster_id": disaster_id,
        "name": "Valid Center Name",
        "address": "Valid Address",
        "contact_number": "+91-9876543214",
        "capacity": 500,
    }

    # Blank name
    p_name = {**base, "name": "   "}
    assert client.post("/api/v1/distribution-centers", json=p_name, headers=admin_h).status_code == 422

    # Blank address
    p_addr = {**base, "address": "   "}
    assert client.post("/api/v1/distribution-centers", json=p_addr, headers=admin_h).status_code == 422

    # Blank contact number
    p_contact = {**base, "contact_number": "   "}
    assert client.post("/api/v1/distribution-centers", json=p_contact, headers=admin_h).status_code == 422

    # Zero capacity
    p_zero_cap = {**base, "capacity": 0}
    assert client.post("/api/v1/distribution-centers", json=p_zero_cap, headers=admin_h).status_code == 422

    # Negative capacity
    p_neg_cap = {**base, "capacity": -100}
    assert client.post("/api/v1/distribution-centers", json=p_neg_cap, headers=admin_h).status_code == 422


def test_duplicate_center_name_rejected(client: TestClient):
    """
    Prevents duplicate center names under the same disaster event.
    Same center name under a DIFFERENT disaster is allowed.
    """
    admin_h = get_user_headers(client, "admin_dc5@relief.org", "ADMIN")
    disaster1_id = create_test_disaster(client, admin_h, "Disaster 5A")
    disaster2_id = create_test_disaster(client, admin_h, "Disaster 5B")

    payload = {
        "disaster_id": disaster1_id,
        "name": "Red Cross Shelter Point",
        "address": "Sector 4",
        "contact_number": "+91-9988776655",
        "capacity": 1000,
    }

    # 1. First registration -> 201 Created
    resp1 = client.post("/api/v1/distribution-centers", json=payload, headers=admin_h)
    assert resp1.status_code == 201

    # 2. Duplicate registration under same disaster -> 400 Bad Request
    resp2 = client.post("/api/v1/distribution-centers", json=payload, headers=admin_h)
    assert resp2.status_code == 400
    assert "already exists" in resp2.json()["detail"].lower()

    # 3. Same name under different disaster -> 201 Created (allowed)
    payload_diff_disaster = {**payload, "disaster_id": disaster2_id}
    resp3 = client.post("/api/v1/distribution-centers", json=payload_diff_disaster, headers=admin_h)
    assert resp3.status_code == 201


# ==============================================================================
# 3. OPERATIONAL STATUS & ELIGIBILITY TESTS
# ==============================================================================

def test_status_transitions_and_eligibility(client: TestClient, db_session: Session):
    """
    Tests status lifecycle and operational eligibility:
    - Starts ACTIVE (eligible)
    - ACTIVE -> FULL (ineligible for new distributions)
    - FULL -> ACTIVE (eligible again)
    - ACTIVE -> INACTIVE (ineligible)
    - INACTIVE -> ACTIVE (eligible again)
    - FULL -> INACTIVE (ineligible)
    - INACTIVE -> FULL (rejected: must open as ACTIVE first)
    """
    admin_h = get_user_headers(client, "admin_dc6@relief.org", "ADMIN")
    staff_h = get_user_headers(client, "staff_dc6@relief.org", "NGO_STAFF")
    disaster_id = create_test_disaster(client, admin_h, "Earthquake Delta")

    # 1. Create center -> starts ACTIVE
    create_resp = client.post(
        "/api/v1/distribution-centers",
        json={
            "disaster_id": disaster_id,
            "name": "Central Distribution Camp",
            "address": "Main Highway Hub",
            "contact_number": "+91-9123456789",
            "capacity": 1200,
        },
        headers=staff_h,
    )
    assert create_resp.status_code == 201
    c_id = create_resp.json()["id"]
    assert create_resp.json()["status"] == "ACTIVE"
    assert create_resp.json()["is_operational"] is True

    # Unit service check
    center_obj = db_session.query(DistributionCenter).filter(DistributionCenter.id == c_id).first()
    assert is_center_eligible_for_distribution(center_obj) is True

    # 2. Transition ACTIVE -> FULL
    full_resp = client.patch(
        f"/api/v1/distribution-centers/{c_id}/status",
        json={"status": "FULL"},
        headers=staff_h,
    )
    assert full_resp.status_code == 200
    assert full_resp.json()["status"] == "FULL"
    assert full_resp.json()["is_operational"] is False

    db_session.refresh(center_obj)
    assert is_center_eligible_for_distribution(center_obj) is False

    # 3. Transition FULL -> ACTIVE
    active_resp = client.patch(
        f"/api/v1/distribution-centers/{c_id}/status",
        json={"status": "ACTIVE"},
        headers=staff_h,
    )
    assert active_resp.status_code == 200
    assert active_resp.json()["status"] == "ACTIVE"
    assert active_resp.json()["is_operational"] is True

    db_session.refresh(center_obj)
    assert is_center_eligible_for_distribution(center_obj) is True

    # 4. Transition ACTIVE -> INACTIVE
    inact_resp = client.patch(
        f"/api/v1/distribution-centers/{c_id}/status",
        json={"status": "INACTIVE"},
        headers=staff_h,
    )
    assert inact_resp.status_code == 200
    assert inact_resp.json()["status"] == "INACTIVE"
    assert inact_resp.json()["is_operational"] is False

    db_session.refresh(center_obj)
    assert is_center_eligible_for_distribution(center_obj) is False

    # 5. Invalid transition: INACTIVE -> FULL rejected (400)
    invalid_jump = client.patch(
        f"/api/v1/distribution-centers/{c_id}/status",
        json={"status": "FULL"},
        headers=staff_h,
    )
    assert invalid_jump.status_code == 400
    assert "reopen it as active first" in invalid_jump.json()["detail"].lower()

    # 6. Reopen INACTIVE -> ACTIVE
    reopen_resp = client.patch(
        f"/api/v1/distribution-centers/{c_id}/status",
        json={"status": "ACTIVE"},
        headers=staff_h,
    )
    assert reopen_resp.status_code == 200
    assert reopen_resp.json()["status"] == "ACTIVE"

    # 7. Transition FULL -> INACTIVE
    client.patch(f"/api/v1/distribution-centers/{c_id}/status", json={"status": "FULL"}, headers=staff_h)
    full_to_inact = client.patch(
        f"/api/v1/distribution-centers/{c_id}/status",
        json={"status": "INACTIVE"},
        headers=staff_h,
    )
    assert full_to_inact.status_code == 200
    assert full_to_inact.json()["status"] == "INACTIVE"


# ==============================================================================
# 4. RETRIEVAL, FILTERING, UPDATES & DELETION
# ==============================================================================

def test_get_and_list_distribution_centers_with_filters(client: TestClient):
    """Retrieve center details, list, and filter by disaster and status."""
    admin_h = get_user_headers(client, "admin_dc7@relief.org", "ADMIN")
    staff_h = get_user_headers(client, "staff_dc7@relief.org", "NGO_STAFF")
    disaster1_id = create_test_disaster(client, admin_h, "Disaster 7A")
    disaster2_id = create_test_disaster(client, admin_h, "Disaster 7B")

    # Center 1: Disaster 1, ACTIVE
    c1 = client.post(
        "/api/v1/distribution-centers",
        json={
            "disaster_id": disaster1_id,
            "name": "Center Alpha",
            "address": "Sector 1",
            "contact_number": "+91-9111111111",
            "capacity": 500,
        },
        headers=admin_h,
    ).json()

    # Center 2: Disaster 1, marked FULL
    c2 = client.post(
        "/api/v1/distribution-centers",
        json={
            "disaster_id": disaster1_id,
            "name": "Center Beta",
            "address": "Sector 2",
            "contact_number": "+91-9222222222",
            "capacity": 300,
        },
        headers=admin_h,
    ).json()
    client.patch(f"/api/v1/distribution-centers/{c2['id']}/status", json={"status": "FULL"}, headers=staff_h)

    # Center 3: Disaster 2, ACTIVE
    client.post(
        "/api/v1/distribution-centers",
        json={
            "disaster_id": disaster2_id,
            "name": "Center Gamma",
            "address": "Sector 3",
            "contact_number": "+91-9333333333",
            "capacity": 700,
        },
        headers=admin_h,
    )

    # 1. Detail view
    get_resp = client.get(f"/api/v1/distribution-centers/{c1['id']}", headers=staff_h)
    assert get_resp.status_code == 200
    assert get_resp.json()["id"] == c1["id"]
    assert get_resp.json()["name"] == "Center Alpha"

    # Detail view of nonexistent -> 404
    assert client.get("/api/v1/distribution-centers/99999", headers=staff_h).status_code == 404

    # 2. Filter by disaster_id
    filter_d1 = client.get(f"/api/v1/distribution-centers?disaster_id={disaster1_id}", headers=staff_h)
    assert filter_d1.status_code == 200
    assert len(filter_d1.json()) == 2
    assert all(c["disaster_id"] == disaster1_id for c in filter_d1.json())

    # 3. Filter by status=FULL
    filter_full = client.get("/api/v1/distribution-centers?status=FULL", headers=staff_h)
    assert filter_full.status_code == 200
    assert any(c["id"] == c2["id"] for c in filter_full.json())
    assert all(c["status"] == "FULL" for c in filter_full.json())


def test_update_distribution_center_details(client: TestClient):
    """Updating center configuration and enforcing duplicate name protection on update."""
    admin_h = get_user_headers(client, "admin_dc8@relief.org", "ADMIN")
    staff_h = get_user_headers(client, "staff_dc8@relief.org", "NGO_STAFF")
    disaster_id = create_test_disaster(client, admin_h, "Disaster 8")

    c1 = client.post(
        "/api/v1/distribution-centers",
        json={
            "disaster_id": disaster_id,
            "name": "Original Name Center",
            "address": "Initial Address",
            "contact_number": "+91-9444444444",
            "capacity": 1000,
        },
        headers=admin_h,
    ).json()

    client.post(
        "/api/v1/distribution-centers",
        json={
            "disaster_id": disaster_id,
            "name": "Existing Center Name",
            "address": "Camp North",
            "contact_number": "+91-9555555555",
            "capacity": 500,
        },
        headers=admin_h,
    )

    # 1. Valid partial update
    update_payload = {
        "address": "Expanded Distribution Warehouse, Bay 4",
        "capacity": 2500,
        "operating_hours": "07:00 - 20:00 Daily",
    }
    upd_resp = client.put(f"/api/v1/distribution-centers/{c1['id']}", json=update_payload, headers=staff_h)
    assert upd_resp.status_code == 200
    upd_data = upd_resp.json()
    assert upd_data["address"] == "Expanded Distribution Warehouse, Bay 4"
    assert upd_data["capacity"] == 2500
    assert upd_data["operating_hours"] == "07:00 - 20:00 Daily"
    assert upd_data["name"] == "Original Name Center"

    # 2. Update colliding with existing center name -> 400
    collision_payload = {"name": "Existing Center Name"}
    col_resp = client.put(f"/api/v1/distribution-centers/{c1['id']}", json=collision_payload, headers=staff_h)
    assert col_resp.status_code == 400
    assert "already exists" in col_resp.json()["detail"].lower()

    # 3. Update nonexistent center -> 404
    assert client.put("/api/v1/distribution-centers/99999", json={"capacity": 500}, headers=staff_h).status_code == 404


def test_delete_distribution_center_admin_only(client: TestClient):
    """Deletion is strictly restricted to ADMIN role."""
    admin_h = get_user_headers(client, "admin_dc9@relief.org", "ADMIN")
    staff_h = get_user_headers(client, "staff_dc9@relief.org", "NGO_STAFF")
    vol_h = get_user_headers(client, "vol_dc9@relief.org", "VOLUNTEER")
    disaster_id = create_test_disaster(client, admin_h, "Disaster 9")

    center = client.post(
        "/api/v1/distribution-centers",
        json={
            "disaster_id": disaster_id,
            "name": "Temporary Depot To Delete",
            "address": "Sector 9",
            "contact_number": "+91-9666666666",
            "capacity": 300,
        },
        headers=admin_h,
    ).json()

    # Staff attempts delete -> 403 Forbidden
    assert client.delete(f"/api/v1/distribution-centers/{center['id']}", headers=staff_h).status_code == 403

    # Volunteer attempts delete -> 403 Forbidden
    assert client.delete(f"/api/v1/distribution-centers/{center['id']}", headers=vol_h).status_code == 403

    # Admin deletes -> 204 No Content
    del_resp = client.delete(f"/api/v1/distribution-centers/{center['id']}", headers=admin_h)
    assert del_resp.status_code == 204

    # Record no longer exists -> 404 Not Found
    assert client.get(f"/api/v1/distribution-centers/{center['id']}", headers=admin_h).status_code == 404

    # Deleting nonexistent -> 404 Not Found
    assert client.delete("/api/v1/distribution-centers/99999", headers=admin_h).status_code == 404
