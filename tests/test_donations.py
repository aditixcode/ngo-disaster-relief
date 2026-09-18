"""
Automated Tests for Donation Management Endpoints.
"""

from datetime import datetime, timezone
import pytest
from fastapi.testclient import TestClient


# Helper to register user and obtain Bearer auth headers
def get_user_headers(client: TestClient, email: str, role: str):
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
def create_test_disaster(client: TestClient, admin_headers: dict, name: str = "Disaster Alpha"):
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


# Helper to get user ID
def get_user_id(client: TestClient, headers: dict):
    resp = client.get("/api/v1/auth/me", headers=headers)
    assert resp.status_code == 200
    return resp.json()["id"]


def test_donor_creates_money_donation(client: TestClient):
    """
    Test that a DONOR can pledge a MONEY donation (201 Created).
    """
    admin_h = get_user_headers(client, "admin_d1@relief.org", "ADMIN")
    donor_h = get_user_headers(client, "donor_d1@relief.org", "DONOR")

    disaster_id = create_test_disaster(client, admin_h, "Flood Relief D1")
    donor_id = get_user_id(client, donor_h)

    response = client.post(
        "/api/v1/donations",
        json={
            "disaster_id": disaster_id,
            "donation_type": "MONEY",
            "amount": 2500.0,
            "notes": "Pledge for medical aid fund",
        },
        headers=donor_h,
    )
    assert response.status_code == 201
    data = response.json()
    assert data["donation_type"] == "MONEY"
    assert data["amount"] == 2500.0
    assert data["status"] == "PLEDGED"
    assert data["donor_id"] == donor_id
    assert data["disaster_id"] == disaster_id
    assert data["item_name"] is None


def test_donor_creates_material_donation(client: TestClient):
    """
    Test that a DONOR can pledge a MATERIAL donation (201 Created).
    """
    admin_h = get_user_headers(client, "admin_d2@relief.org", "ADMIN")
    donor_h = get_user_headers(client, "donor_d2@relief.org", "DONOR")

    disaster_id = create_test_disaster(client, admin_h, "Cyclone Relief D2")

    response = client.post(
        "/api/v1/donations",
        json={
            "disaster_id": disaster_id,
            "donation_type": "MATERIAL",
            "item_name": "Blankets and Tarpaulins",
            "quantity": 150.0,
            "unit": "bundles",
            "notes": "Arriving at logistics depot tomorrow morning",
        },
        headers=donor_h,
    )
    assert response.status_code == 201
    data = response.json()
    assert data["donation_type"] == "MATERIAL"
    assert data["item_name"] == "Blankets and Tarpaulins"
    assert data["quantity"] == 150.0
    assert data["unit"] == "bundles"
    assert data["amount"] is None
    assert data["status"] == "PLEDGED"


def test_admin_and_staff_create_donation_for_donor(client: TestClient):
    """
    Test that ADMIN and NGO_STAFF can create donations on behalf of a registered donor.
    """
    admin_h = get_user_headers(client, "admin_d3@relief.org", "ADMIN")
    staff_h = get_user_headers(client, "staff_d3@relief.org", "NGO_STAFF")
    donor_h = get_user_headers(client, "donor_d3@relief.org", "DONOR")

    disaster_id = create_test_disaster(client, admin_h, "Earthquake D3")
    donor_id = get_user_id(client, donor_h)

    # Staff creates donation for donor
    staff_resp = client.post(
        "/api/v1/donations",
        json={
            "donor_id": donor_id,
            "disaster_id": disaster_id,
            "donation_type": "MONEY",
            "amount": 1000.0,
        },
        headers=staff_h,
    )
    assert staff_resp.status_code == 201
    assert staff_resp.json()["donor_id"] == donor_id

    # Admin creates donation for donor
    admin_resp = client.post(
        "/api/v1/donations",
        json={
            "donor_id": donor_id,
            "disaster_id": disaster_id,
            "donation_type": "MATERIAL",
            "item_name": "Rice Sacks",
            "quantity": 50.0,
            "unit": "bags",
        },
        headers=admin_h,
    )
    assert admin_resp.status_code == 201
    assert admin_resp.json()["donor_id"] == donor_id


def test_donor_cannot_impersonate_another_donor(client: TestClient):
    """
    Test that a DONOR cannot create a donation under another user's donor_id (HTTP 403).
    """
    admin_h = get_user_headers(client, "admin_d4@relief.org", "ADMIN")
    donor_a_h = get_user_headers(client, "donor_a@relief.org", "DONOR")
    donor_b_h = get_user_headers(client, "donor_b@relief.org", "DONOR")

    disaster_id = create_test_disaster(client, admin_h, "Disaster D4")
    donor_b_id = get_user_id(client, donor_b_h)

    # Donor A tries to submit a donation pretending to be Donor B
    resp = client.post(
        "/api/v1/donations",
        json={
            "donor_id": donor_b_id,
            "disaster_id": disaster_id,
            "donation_type": "MONEY",
            "amount": 500.0,
        },
        headers=donor_a_h,
    )
    assert resp.status_code == 403
    assert "cannot create donations on behalf of another user" in resp.json()["detail"]


def test_nonexistent_disaster_rejected(client: TestClient):
    """
    Test that creating a donation for a non-existent disaster returns HTTP 404.
    """
    donor_h = get_user_headers(client, "donor_d5@relief.org", "DONOR")
    resp = client.post(
        "/api/v1/donations",
        json={
            "disaster_id": 99999,
            "donation_type": "MONEY",
            "amount": 100.0,
        },
        headers=donor_h,
    )
    assert resp.status_code == 404


def test_invalid_money_donation_rejected(client: TestClient):
    """
    Test validation rules for MONEY donations:
    - Missing amount -> 422
    - Amount <= 0 -> 422
    """
    donor_h = get_user_headers(client, "donor_d6@relief.org", "DONOR")

    # Missing amount
    resp1 = client.post(
        "/api/v1/donations",
        json={"disaster_id": 1, "donation_type": "MONEY"},
        headers=donor_h,
    )
    assert resp1.status_code == 422

    # Negative amount
    resp2 = client.post(
        "/api/v1/donations",
        json={"disaster_id": 1, "donation_type": "MONEY", "amount": -50.0},
        headers=donor_h,
    )
    assert resp2.status_code == 422


def test_invalid_material_donation_rejected(client: TestClient):
    """
    Test validation rules for MATERIAL donations:
    - Missing item_name -> 422
    - Quantity <= 0 -> 422
    - Missing unit -> 422
    """
    donor_h = get_user_headers(client, "donor_d7@relief.org", "DONOR")

    # Missing item_name and unit
    resp1 = client.post(
        "/api/v1/donations",
        json={"disaster_id": 1, "donation_type": "MATERIAL", "quantity": 10.0},
        headers=donor_h,
    )
    assert resp1.status_code == 422

    # Zero quantity
    resp2 = client.post(
        "/api/v1/donations",
        json={
            "disaster_id": 1,
            "donation_type": "MATERIAL",
            "item_name": "Bottles",
            "quantity": 0.0,
            "unit": "boxes",
        },
        headers=donor_h,
    )
    assert resp2.status_code == 422


def test_donor_scoped_view_and_idor_protection(client: TestClient):
    """
    Test that donors can only see their own donations and are blocked from viewing others (HTTP 403).
    """
    admin_h = get_user_headers(client, "admin_idor@relief.org", "ADMIN")
    donor_1_h = get_user_headers(client, "donor_1@relief.org", "DONOR")
    donor_2_h = get_user_headers(client, "donor_2@relief.org", "DONOR")

    disaster_id = create_test_disaster(client, admin_h, "Tsunami IDOR")

    # Donor 1 creates donation
    d1_resp = client.post(
        "/api/v1/donations",
        json={"disaster_id": disaster_id, "donation_type": "MONEY", "amount": 200.0},
        headers=donor_1_h,
    )
    d1_id = d1_resp.json()["id"]

    # Donor 2 creates donation
    d2_resp = client.post(
        "/api/v1/donations",
        json={"disaster_id": disaster_id, "donation_type": "MONEY", "amount": 400.0},
        headers=donor_2_h,
    )
    d2_id = d2_resp.json()["id"]

    # Donor 1 lists donations: should ONLY see their own
    list_d1 = client.get("/api/v1/donations", headers=donor_1_h).json()
    assert all(d["donor_id"] == get_user_id(client, donor_1_h) for d in list_d1)

    # Donor 1 tries to fetch Donor 2's donation by ID -> 403 Forbidden
    idor_resp = client.get(f"/api/v1/donations/{d2_id}", headers=donor_1_h)
    assert idor_resp.status_code == 403


def test_staff_view_and_filter_donations(client: TestClient):
    """
    Test that staff can view all donations and filter by disaster_id, donation_type, and status.
    """
    admin_h = get_user_headers(client, "admin_filt@relief.org", "ADMIN")
    staff_h = get_user_headers(client, "staff_filt@relief.org", "NGO_STAFF")
    donor_h = get_user_headers(client, "donor_filt@relief.org", "DONOR")

    d_id = create_test_disaster(client, admin_h, "Filter Event")

    # Create one MONEY and one MATERIAL donation
    client.post(
        "/api/v1/donations",
        json={"disaster_id": d_id, "donation_type": "MONEY", "amount": 500.0},
        headers=donor_h,
    )
    client.post(
        "/api/v1/donations",
        json={
            "disaster_id": d_id,
            "donation_type": "MATERIAL",
            "item_name": "Tents",
            "quantity": 10.0,
            "unit": "units",
        },
        headers=donor_h,
    )

    # Staff filter by MONEY
    money_resp = client.get(f"/api/v1/donations?donation_type=MONEY&disaster_id={d_id}", headers=staff_h)
    assert money_resp.status_code == 200
    assert all(d["donation_type"] == "MONEY" for d in money_resp.json())

    # Staff filter by MATERIAL
    mat_resp = client.get(f"/api/v1/donations?donation_type=MATERIAL&disaster_id={d_id}", headers=staff_h)
    assert mat_resp.status_code == 200
    assert all(d["donation_type"] == "MATERIAL" for d in mat_resp.json())


def test_donation_status_transitions_and_locks(client: TestClient):
    """
    Test lifecycle state transitions:
    1. PLEDGED -> RECEIVED sets received_at.
    2. PLEDGED -> CANCELLED.
    3. Invalid transitions from terminal states rejected with HTTP 400.
    4. Donor cannot modify a RECEIVED donation (HTTP 400).
    """
    admin_h = get_user_headers(client, "admin_trans@relief.org", "ADMIN")
    staff_h = get_user_headers(client, "staff_trans@relief.org", "NGO_STAFF")
    donor_h = get_user_headers(client, "donor_trans@relief.org", "DONOR")

    d_id = create_test_disaster(client, admin_h, "Transition Event")

    # Donor pledges donation
    create_resp = client.post(
        "/api/v1/donations",
        json={"disaster_id": d_id, "donation_type": "MONEY", "amount": 750.0},
        headers=donor_h,
    )
    donation_id = create_resp.json()["id"]

    # 1. Staff transitions PLEDGED -> RECEIVED
    recv_resp = client.patch(
        f"/api/v1/donations/{donation_id}/status",
        json={"status": "RECEIVED"},
        headers=staff_h,
    )
    assert recv_resp.status_code == 200
    assert recv_resp.json()["status"] == "RECEIVED"
    assert recv_resp.json()["received_at"] is not None

    # 2. Reverting RECEIVED -> PLEDGED is rejected (HTTP 400)
    revert_resp = client.patch(
        f"/api/v1/donations/{donation_id}/status",
        json={"status": "PLEDGED"},
        headers=staff_h,
    )
    assert revert_resp.status_code == 400
    assert "terminal state" in revert_resp.json()["detail"].lower()

    # 3. Donor cannot modify a RECEIVED donation (HTTP 400)
    donor_mod_resp = client.put(
        f"/api/v1/donations/{donation_id}",
        json={"amount": 999.0},
        headers=donor_h,
    )
    assert donor_mod_resp.status_code == 400
    assert "cannot modify" in donor_mod_resp.json()["detail"].lower()

    # 4. Test PLEDGED -> CANCELLED on a new donation
    c_resp = client.post(
        "/api/v1/donations",
        json={"disaster_id": d_id, "donation_type": "MONEY", "amount": 100.0},
        headers=donor_h,
    )
    c_id = c_resp.json()["id"]

    cancel_resp = client.patch(
        f"/api/v1/donations/{c_id}/status",
        json={"status": "CANCELLED"},
        headers=staff_h,
    )
    assert cancel_resp.status_code == 200
    assert cancel_resp.json()["status"] == "CANCELLED"

    # Cancelled -> Received is rejected
    invalid_reactivate = client.patch(
        f"/api/v1/donations/{c_id}/status",
        json={"status": "RECEIVED"},
        headers=staff_h,
    )
    assert invalid_reactivate.status_code == 400


def test_admin_delete_donation_only(client: TestClient):
    """
    Test that only ADMIN can delete a donation (204).
    Staff, Volunteer, and Donor receive HTTP 403.
    """
    admin_h = get_user_headers(client, "admin_del_d@relief.org", "ADMIN")
    staff_h = get_user_headers(client, "staff_del_d@relief.org", "NGO_STAFF")
    donor_h = get_user_headers(client, "donor_del_d@relief.org", "DONOR")

    d_id = create_test_disaster(client, admin_h, "Delete Event")

    create_resp = client.post(
        "/api/v1/donations",
        json={"disaster_id": d_id, "donation_type": "MONEY", "amount": 300.0},
        headers=donor_h,
    )
    donation_id = create_resp.json()["id"]

    # Staff attempt -> 403
    assert client.delete(f"/api/v1/donations/{donation_id}", headers=staff_h).status_code == 403

    # Donor attempt -> 403
    assert client.delete(f"/api/v1/donations/{donation_id}", headers=donor_h).status_code == 403

    # Admin attempt -> 204
    assert client.delete(f"/api/v1/donations/{donation_id}", headers=admin_h).status_code == 204

    # Subsequent fetch -> 404
    assert client.get(f"/api/v1/donations/{donation_id}", headers=admin_h).status_code == 404
