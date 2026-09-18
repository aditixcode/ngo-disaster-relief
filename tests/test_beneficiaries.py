"""
Stage 8: Automated Tests for Beneficiary Management.

Verifies:
1. Beneficiary registration (ADMIN, NGO_STAFF permissions, initial PENDING status).
2. RBAC guards (Volunteer/Donor forbidden, unauthenticated rejected).
3. Input validation (non-empty strings, positive household size, valid disaster).
4. Duplicate protection on (disaster_id, name, contact_number).
5. Lifecycle state machine transitions (PENDING -> VERIFIED / INACTIVE, VERIFIED -> INACTIVE).
6. Backward / invalid state transition rejections (VERIFIED -> PENDING, INACTIVE -> VERIFIED).
7. Eligibility service rules (VERIFIED = True, PENDING/INACTIVE = False).
8. Detail retrieval, listing, and multi-field filtering.
9. Information update and admin-only deletion.
"""

from datetime import datetime, timezone
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.beneficiary import Beneficiary, VulnerabilityCategory, RegistrationStatus
from app.services.beneficiary_service import is_beneficiary_eligible


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
# 1. REGISTRATION & RBAC TESTS
# ==============================================================================

def test_admin_and_staff_can_create_beneficiary(client: TestClient):
    """Admin and NGO Staff can register beneficiaries in PENDING status."""
    admin_h = get_user_headers(client, "admin_b1@relief.org", "ADMIN")
    staff_h = get_user_headers(client, "staff_b1@relief.org", "NGO_STAFF")
    disaster_id = create_test_disaster(client, admin_h, "Flood Bravo")

    # Admin registers beneficiary
    admin_payload = {
        "disaster_id": disaster_id,
        "name": "Sunita Devi",
        "contact_number": "+91-9876543210",
        "address": "Camp 4, Shelter 12",
        "household_size": 5,
        "vulnerability_category": "ELDERLY",
    }
    resp1 = client.post("/api/v1/beneficiaries", json=admin_payload, headers=admin_h)
    assert resp1.status_code == 201
    data1 = resp1.json()
    assert data1["name"] == "Sunita Devi"
    assert data1["registration_status"] == "PENDING"
    assert data1["registered_by_id"] is not None
    assert data1["is_eligible"] is False
    assert data1["vulnerability_category"] == "ELDERLY"

    # Staff registers beneficiary
    staff_payload = {
        "disaster_id": disaster_id,
        "name": "Ramesh Kumar",
        "contact_number": "+91-9876543211",
        "address": "Camp 2, Shelter 05",
        "household_size": 3,
        "vulnerability_category": "DISABLED",
    }
    resp2 = client.post("/api/v1/beneficiaries", json=staff_payload, headers=staff_h)
    assert resp2.status_code == 201
    assert resp2.json()["registration_status"] == "PENDING"


def test_volunteer_and_donor_cannot_create_or_view_beneficiary(client: TestClient):
    """Volunteers and Donors have no access to beneficiary endpoints (403 Forbidden)."""
    admin_h = get_user_headers(client, "admin_b2@relief.org", "ADMIN")
    vol_h = get_user_headers(client, "vol_b2@relief.org", "VOLUNTEER")
    donor_h = get_user_headers(client, "donor_b2@relief.org", "DONOR")
    disaster_id = create_test_disaster(client, admin_h, "Cyclone Charlie")

    payload = {
        "disaster_id": disaster_id,
        "name": "Anil Verma",
        "contact_number": "+91-9876543212",
        "address": "Sector 9",
        "household_size": 2,
    }

    # Volunteer attempts create and view
    assert client.post("/api/v1/beneficiaries", json=payload, headers=vol_h).status_code == 403
    assert client.get("/api/v1/beneficiaries", headers=vol_h).status_code == 403

    # Donor attempts create and view
    assert client.post("/api/v1/beneficiaries", json=payload, headers=donor_h).status_code == 403
    assert client.get("/api/v1/beneficiaries", headers=donor_h).status_code == 403


def test_unauthenticated_cannot_access_beneficiaries(client: TestClient):
    """Unauthenticated requests must return 401 Unauthorized."""
    assert client.post("/api/v1/beneficiaries", json={}).status_code == 401
    assert client.get("/api/v1/beneficiaries").status_code == 401
    assert client.get("/api/v1/beneficiaries/1").status_code == 401
    assert client.put("/api/v1/beneficiaries/1", json={}).status_code == 401
    assert client.patch("/api/v1/beneficiaries/1/status", json={}).status_code == 401
    assert client.delete("/api/v1/beneficiaries/1").status_code == 401


# ==============================================================================
# 2. VALIDATION & DUPLICATE CHECKS
# ==============================================================================

def test_nonexistent_disaster_rejected(client: TestClient):
    """Attempting registration under a nonexistent disaster returns 404."""
    admin_h = get_user_headers(client, "admin_b3@relief.org", "ADMIN")
    payload = {
        "disaster_id": 999999,
        "name": "Priya Sharma",
        "contact_number": "+91-9876543213",
        "address": "Relief Camp 1",
        "household_size": 4,
    }
    resp = client.post("/api/v1/beneficiaries", json=payload, headers=admin_h)
    assert resp.status_code == 404
    assert "not found" in resp.json()["detail"].lower()


def test_validation_rules_rejected(client: TestClient):
    """Validation checks: blank name/address/contact, household size <= 0."""
    admin_h = get_user_headers(client, "admin_b4@relief.org", "ADMIN")
    disaster_id = create_test_disaster(client, admin_h, "Landslide Delta")

    base = {
        "disaster_id": disaster_id,
        "name": "Test Name",
        "contact_number": "+91-9876543214",
        "address": "Address Line",
        "household_size": 2,
    }

    # Blank name
    p_name = {**base, "name": "   "}
    assert client.post("/api/v1/beneficiaries", json=p_name, headers=admin_h).status_code == 422

    # Blank address
    p_addr = {**base, "address": "   "}
    assert client.post("/api/v1/beneficiaries", json=p_addr, headers=admin_h).status_code == 422

    # Blank contact number
    p_contact = {**base, "contact_number": "   "}
    assert client.post("/api/v1/beneficiaries", json=p_contact, headers=admin_h).status_code == 422

    # Zero household size
    p_zero_hh = {**base, "household_size": 0}
    assert client.post("/api/v1/beneficiaries", json=p_zero_hh, headers=admin_h).status_code == 422

    # Negative household size
    p_neg_hh = {**base, "household_size": -3}
    assert client.post("/api/v1/beneficiaries", json=p_neg_hh, headers=admin_h).status_code == 422


def test_duplicate_beneficiary_rejected(client: TestClient):
    """
    Prevents registering the exact same person/contact under the same disaster event.
    Cross-disaster registration of the same person is allowed.
    """
    admin_h = get_user_headers(client, "admin_b5@relief.org", "ADMIN")
    disaster1_id = create_test_disaster(client, admin_h, "Disaster Event 1")
    disaster2_id = create_test_disaster(client, admin_h, "Disaster Event 2")

    payload = {
        "disaster_id": disaster1_id,
        "name": "Meena Patel",
        "contact_number": "+91-9988776655",
        "address": "Camp North",
        "household_size": 4,
    }

    # First registration -> 201 Created
    resp1 = client.post("/api/v1/beneficiaries", json=payload, headers=admin_h)
    assert resp1.status_code == 201

    # Exact duplicate under disaster 1 -> 400 Bad Request
    resp2 = client.post("/api/v1/beneficiaries", json=payload, headers=admin_h)
    assert resp2.status_code == 400
    assert "already registered" in resp2.json()["detail"].lower()

    # Same person under a DIFFERENT disaster -> 201 Created (allowed)
    payload_diff_disaster = {**payload, "disaster_id": disaster2_id}
    resp3 = client.post("/api/v1/beneficiaries", json=payload_diff_disaster, headers=admin_h)
    assert resp3.status_code == 201


# ==============================================================================
# 3. LIFECYCLE STATUS TRANSITIONS & ELIGIBILITY
# ==============================================================================

def test_status_transitions_and_eligibility_lifecycle(client: TestClient, db_session: Session):
    """
    Tests the verification state machine:
    - Initial status is PENDING (is_eligible = False)
    - PENDING -> VERIFIED (is_eligible = True)
    - VERIFIED -> INACTIVE (is_eligible = False)
    - Disallows invalid / backward transitions (VERIFIED -> PENDING, INACTIVE -> VERIFIED)
    """
    staff_h = get_user_headers(client, "staff_b6@relief.org", "NGO_STAFF")
    admin_h = get_user_headers(client, "admin_b6@relief.org", "ADMIN")
    disaster_id = create_test_disaster(client, admin_h, "Tsunami Echo")

    # 1. Register beneficiary -> starts as PENDING
    reg_resp = client.post(
        "/api/v1/beneficiaries",
        json={
            "disaster_id": disaster_id,
            "name": "Kavita Roy",
            "contact_number": "+91-9123456789",
            "address": "Shelter Point 5",
            "household_size": 2,
            "vulnerability_category": "PREGNANT",
        },
        headers=staff_h,
    )
    assert reg_resp.status_code == 201
    b_id = reg_resp.json()["id"]
    assert reg_resp.json()["registration_status"] == "PENDING"
    assert reg_resp.json()["is_eligible"] is False

    # Check direct unit service
    b_obj = db_session.query(Beneficiary).filter(Beneficiary.id == b_id).first()
    assert is_beneficiary_eligible(b_obj) is False

    # 2. Staff verifies beneficiary -> PENDING -> VERIFIED
    verify_resp = client.patch(
        f"/api/v1/beneficiaries/{b_id}/status",
        json={"status": "VERIFIED"},
        headers=staff_h,
    )
    assert verify_resp.status_code == 200
    assert verify_resp.json()["registration_status"] == "VERIFIED"
    assert verify_resp.json()["is_eligible"] is True

    # Check direct unit service
    db_session.refresh(b_obj)
    assert is_beneficiary_eligible(b_obj) is True

    # 3. Reverting VERIFIED back to PENDING is forbidden (400)
    revert_resp = client.patch(
        f"/api/v1/beneficiaries/{b_id}/status",
        json={"status": "PENDING"},
        headers=staff_h,
    )
    assert revert_resp.status_code == 400
    assert "cannot revert" in revert_resp.json()["detail"].lower()

    # 4. Deactivate beneficiary -> VERIFIED -> INACTIVE
    deact_resp = client.patch(
        f"/api/v1/beneficiaries/{b_id}/status",
        json={"status": "INACTIVE"},
        headers=staff_h,
    )
    assert deact_resp.status_code == 200
    assert deact_resp.json()["registration_status"] == "INACTIVE"
    assert deact_resp.json()["is_eligible"] is False

    # Check direct unit service
    db_session.refresh(b_obj)
    assert is_beneficiary_eligible(b_obj) is False

    # 5. Reactivating an INACTIVE record is forbidden (400)
    reactivate_resp = client.patch(
        f"/api/v1/beneficiaries/{b_id}/status",
        json={"status": "VERIFIED"},
        headers=staff_h,
    )
    assert reactivate_resp.status_code == 400
    assert "cannot modify or reactivate" in reactivate_resp.json()["detail"].lower()


def test_pending_directly_to_inactive_transition(client: TestClient):
    """Direct deactivation of unverified claim (PENDING -> INACTIVE) is permitted."""
    admin_h = get_user_headers(client, "admin_b7@relief.org", "ADMIN")
    disaster_id = create_test_disaster(client, admin_h, "Monsoon Floods Foxtrot")

    reg_resp = client.post(
        "/api/v1/beneficiaries",
        json={
            "disaster_id": disaster_id,
            "name": "Invalid Claim Record",
            "contact_number": "+91-9900000000",
            "address": "Unverified Location",
            "household_size": 1,
        },
        headers=admin_h,
    )
    b_id = reg_resp.json()["id"]

    # PENDING -> INACTIVE
    inact_resp = client.patch(
        f"/api/v1/beneficiaries/{b_id}/status",
        json={"status": "INACTIVE"},
        headers=admin_h,
    )
    assert inact_resp.status_code == 200
    assert inact_resp.json()["registration_status"] == "INACTIVE"


# ==============================================================================
# 4. RETRIEVAL, FILTERING, UPDATES & DELETION
# ==============================================================================

def test_get_and_list_beneficiaries_with_filters(client: TestClient):
    """Test retrieving detail view, listing, and filtering by disaster, vulnerability, and status."""
    admin_h = get_user_headers(client, "admin_b8@relief.org", "ADMIN")
    staff_h = get_user_headers(client, "staff_b8@relief.org", "NGO_STAFF")
    disaster1_id = create_test_disaster(client, admin_h, "Disaster 8A")
    disaster2_id = create_test_disaster(client, admin_h, "Disaster 8B")

    # Beneficiary 1: Disaster 1, ELDERLY
    b1 = client.post(
        "/api/v1/beneficiaries",
        json={
            "disaster_id": disaster1_id,
            "name": "Elderly Resident",
            "contact_number": "+91-9111111111",
            "address": "Camp 1",
            "household_size": 2,
            "vulnerability_category": "ELDERLY",
        },
        headers=admin_h,
    ).json()

    # Beneficiary 2: Disaster 1, CHILDREN
    b2 = client.post(
        "/api/v1/beneficiaries",
        json={
            "disaster_id": disaster1_id,
            "name": "Family With Infants",
            "contact_number": "+91-9222222222",
            "address": "Camp 1",
            "household_size": 5,
            "vulnerability_category": "CHILDREN",
        },
        headers=admin_h,
    ).json()

    # Beneficiary 3: Disaster 2, LOW_INCOME
    b3 = client.post(
        "/api/v1/beneficiaries",
        json={
            "disaster_id": disaster2_id,
            "name": "Low Income Worker",
            "contact_number": "+91-9333333333",
            "address": "Camp 2",
            "household_size": 4,
            "vulnerability_category": "LOW_INCOME",
        },
        headers=admin_h,
    ).json()

    # Verify beneficiary 1
    client.patch(f"/api/v1/beneficiaries/{b1['id']}/status", json={"status": "VERIFIED"}, headers=staff_h)

    # 1. Detail view
    get_resp = client.get(f"/api/v1/beneficiaries/{b1['id']}", headers=staff_h)
    assert get_resp.status_code == 200
    assert get_resp.json()["id"] == b1["id"]
    assert get_resp.json()["name"] == "Elderly Resident"

    # Detail view of nonexistent -> 404
    assert client.get("/api/v1/beneficiaries/99999", headers=staff_h).status_code == 404

    # 2. Filter by disaster_id
    filter_d1 = client.get(f"/api/v1/beneficiaries?disaster_id={disaster1_id}", headers=staff_h)
    assert filter_d1.status_code == 200
    assert len(filter_d1.json()) == 2
    assert all(b["disaster_id"] == disaster1_id for b in filter_d1.json())

    # 3. Filter by vulnerability_category
    filter_vuln = client.get("/api/v1/beneficiaries?vulnerability_category=ELDERLY", headers=staff_h)
    assert filter_vuln.status_code == 200
    assert any(b["name"] == "Elderly Resident" for b in filter_vuln.json())
    assert all(b["vulnerability_category"] == "ELDERLY" for b in filter_vuln.json())

    # 4. Filter by registration_status
    filter_verif = client.get("/api/v1/beneficiaries?status=VERIFIED", headers=staff_h)
    assert filter_verif.status_code == 200
    assert any(b["id"] == b1["id"] for b in filter_verif.json())
    assert all(b["registration_status"] == "VERIFIED" for b in filter_verif.json())


def test_update_beneficiary_details(client: TestClient):
    """Updating beneficiary information and enforcing duplicate protection on modified names."""
    admin_h = get_user_headers(client, "admin_b9@relief.org", "ADMIN")
    staff_h = get_user_headers(client, "staff_b9@relief.org", "NGO_STAFF")
    disaster_id = create_test_disaster(client, admin_h, "Disaster 9")

    # Create two beneficiaries
    b1 = client.post(
        "/api/v1/beneficiaries",
        json={
            "disaster_id": disaster_id,
            "name": "Original Name",
            "contact_number": "+91-9444444444",
            "address": "Initial Address",
            "household_size": 3,
        },
        headers=admin_h,
    ).json()

    client.post(
        "/api/v1/beneficiaries",
        json={
            "disaster_id": disaster_id,
            "name": "Existing Person",
            "contact_number": "+91-9555555555",
            "address": "Camp North",
            "household_size": 2,
        },
        headers=admin_h,
    )

    # 1. Valid partial update
    update_payload = {
        "address": "Updated Tent Block 7",
        "household_size": 4,
        "vulnerability_category": "CHILDREN",
    }
    upd_resp = client.put(f"/api/v1/beneficiaries/{b1['id']}", json=update_payload, headers=staff_h)
    assert upd_resp.status_code == 200
    upd_data = upd_resp.json()
    assert upd_data["address"] == "Updated Tent Block 7"
    assert upd_data["household_size"] == 4
    assert upd_data["vulnerability_category"] == "CHILDREN"
    assert upd_data["name"] == "Original Name"

    # 2. Update colliding with existing beneficiary -> 400
    collision_payload = {
        "name": "Existing Person",
        "contact_number": "+91-9555555555",
    }
    col_resp = client.put(f"/api/v1/beneficiaries/{b1['id']}", json=collision_payload, headers=staff_h)
    assert col_resp.status_code == 400
    assert "already exists" in col_resp.json()["detail"].lower()

    # 3. Update nonexistent beneficiary -> 404
    assert client.put("/api/v1/beneficiaries/99999", json={"household_size": 5}, headers=staff_h).status_code == 404


def test_delete_beneficiary_admin_only(client: TestClient):
    """Deletion is strictly restricted to ADMIN role."""
    admin_h = get_user_headers(client, "admin_b10@relief.org", "ADMIN")
    staff_h = get_user_headers(client, "staff_b10@relief.org", "NGO_STAFF")
    vol_h = get_user_headers(client, "vol_b10@relief.org", "VOLUNTEER")
    disaster_id = create_test_disaster(client, admin_h, "Disaster 10")

    b = client.post(
        "/api/v1/beneficiaries",
        json={
            "disaster_id": disaster_id,
            "name": "Record To Delete",
            "contact_number": "+91-9666666666",
            "address": "Sector 3",
            "household_size": 3,
        },
        headers=admin_h,
    ).json()

    # Staff attempts delete -> 403 Forbidden
    assert client.delete(f"/api/v1/beneficiaries/{b['id']}", headers=staff_h).status_code == 403

    # Volunteer attempts delete -> 403 Forbidden
    assert client.delete(f"/api/v1/beneficiaries/{b['id']}", headers=vol_h).status_code == 403

    # Admin deletes -> 204 No Content
    del_resp = client.delete(f"/api/v1/beneficiaries/{b['id']}", headers=admin_h)
    assert del_resp.status_code == 204

    # Record no longer exists -> 404 Not Found
    assert client.get(f"/api/v1/beneficiaries/{b['id']}", headers=admin_h).status_code == 404

    # Deleting nonexistent -> 404 Not Found
    assert client.delete("/api/v1/beneficiaries/99999", headers=admin_h).status_code == 404
