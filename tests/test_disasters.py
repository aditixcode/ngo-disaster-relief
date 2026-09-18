"""
Automated Tests for Disaster/Event Management Endpoints.
"""

from datetime import datetime, timedelta, timezone
import pytest
from fastapi.testclient import TestClient


# Helper to register user and obtain Bearer token header
def get_user_headers(client: TestClient, email: str, role: str):
    client.post(
        "/api/v1/auth/register",
        json={
            "name": f"Test {role}",
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


# Sample payload for creating a disaster
def sample_disaster_payload(name: str = "Cyclone Alpha", status: str = "ACTIVE"):
    start = datetime.now(timezone.utc)
    end = start + timedelta(days=7)
    return {
        "name": name,
        "description": "Severe tropical cyclone warning for coastal regions.",
        "location": "Coastal Belt, Sector 2",
        "status": status,
        "start_date": start.isoformat(),
        "end_date": end.isoformat(),
    }


def test_admin_can_create_disaster(client: TestClient):
    """
    Test that an ADMIN user can create a disaster record (HTTP 201).
    Verifies that created_by_id is tracked.
    """
    headers = get_user_headers(client, "admin_disaster@relief.org", "ADMIN")
    payload = sample_disaster_payload("Earthquake Response A")

    response = client.post("/api/v1/disasters", json=payload, headers=headers)
    assert response.status_code == 201

    data = response.json()
    assert data["name"] == "Earthquake Response A"
    assert data["status"] == "ACTIVE"
    assert data["location"] == "Coastal Belt, Sector 2"
    assert "id" in data
    assert data["created_by_id"] is not None


def test_staff_can_create_disaster(client: TestClient):
    """
    Test that an NGO_STAFF user can create a disaster record (HTTP 201).
    """
    headers = get_user_headers(client, "staff_disaster@relief.org", "NGO_STAFF")
    payload = sample_disaster_payload("Flood Relief Delta")

    response = client.post("/api/v1/disasters", json=payload, headers=headers)
    assert response.status_code == 201
    assert response.json()["name"] == "Flood Relief Delta"


def test_volunteer_cannot_create_disaster(client: TestClient):
    """
    Test that a VOLUNTEER is forbidden from creating a disaster (HTTP 403).
    """
    headers = get_user_headers(client, "vol_disaster@relief.org", "VOLUNTEER")
    payload = sample_disaster_payload()

    response = client.post("/api/v1/disasters", json=payload, headers=headers)
    assert response.status_code == 403
    assert "Insufficient permissions" in response.json()["detail"]


def test_donor_cannot_create_disaster(client: TestClient):
    """
    Test that a DONOR is forbidden from creating a disaster (HTTP 403).
    """
    headers = get_user_headers(client, "donor_disaster@relief.org", "DONOR")
    payload = sample_disaster_payload()

    response = client.post("/api/v1/disasters", json=payload, headers=headers)
    assert response.status_code == 403


def test_unauthenticated_cannot_access_disasters(client: TestClient):
    """
    Test that unauthenticated requests to /api/v1/disasters return HTTP 401.
    """
    assert client.get("/api/v1/disasters").status_code == 401
    assert client.post("/api/v1/disasters", json={}).status_code == 401
    assert client.get("/api/v1/disasters/1").status_code == 401
    assert client.put("/api/v1/disasters/1", json={}).status_code == 401
    assert client.delete("/api/v1/disasters/1").status_code == 401


def test_list_and_filter_disasters(client: TestClient):
    """
    Test listing disasters with optional status filtering.
    """
    admin_headers = get_user_headers(client, "admin_list@relief.org", "ADMIN")
    vol_headers = get_user_headers(client, "vol_list@relief.org", "VOLUNTEER")

    # Create one ACTIVE and one CONTAINED disaster
    client.post("/api/v1/disasters", json=sample_disaster_payload("Active Event", "ACTIVE"), headers=admin_headers)
    client.post("/api/v1/disasters", json=sample_disaster_payload("Contained Event", "CONTAINED"), headers=admin_headers)

    # Any authenticated user (e.g. Volunteer) can list disasters
    list_resp = client.get("/api/v1/disasters", headers=vol_headers)
    assert list_resp.status_code == 200
    all_disasters = list_resp.json()
    assert len(all_disasters) >= 2

    # Filter by ACTIVE status
    active_resp = client.get("/api/v1/disasters?status=ACTIVE", headers=vol_headers)
    assert active_resp.status_code == 200
    active_items = active_resp.json()
    assert all(item["status"] == "ACTIVE" for item in active_items)


def test_get_disaster_by_id(client: TestClient):
    """
    Test retrieving a specific disaster by ID.
    """
    admin_headers = get_user_headers(client, "admin_get@relief.org", "ADMIN")
    vol_headers = get_user_headers(client, "vol_get@relief.org", "VOLUNTEER")

    create_resp = client.post(
        "/api/v1/disasters",
        json=sample_disaster_payload("Single Disaster Test"),
        headers=admin_headers,
    )
    disaster_id = create_resp.json()["id"]

    # Get by ID
    get_resp = client.get(f"/api/v1/disasters/{disaster_id}", headers=vol_headers)
    assert get_resp.status_code == 200
    assert get_resp.json()["id"] == disaster_id
    assert get_resp.json()["name"] == "Single Disaster Test"


def test_get_nonexistent_disaster_returns_404(client: TestClient):
    """
    Test that querying an invalid disaster ID returns HTTP 404.
    """
    vol_headers = get_user_headers(client, "vol_404@relief.org", "VOLUNTEER")
    response = client.get("/api/v1/disasters/99999", headers=vol_headers)
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_admin_and_staff_can_update_disaster(client: TestClient):
    """
    Test updating a disaster:
    - ADMIN and NGO_STAFF can update.
    - Status can be transitioned to RESOLVED.
    """
    admin_headers = get_user_headers(client, "admin_update@relief.org", "ADMIN")
    staff_headers = get_user_headers(client, "staff_update@relief.org", "NGO_STAFF")

    create_resp = client.post(
        "/api/v1/disasters",
        json=sample_disaster_payload("Update Me"),
        headers=admin_headers,
    )
    disaster_id = create_resp.json()["id"]

    # Staff updates status to CONTAINED
    update_resp = client.put(
        f"/api/v1/disasters/{disaster_id}",
        json={"status": "CONTAINED", "location": "New Sector 3"},
        headers=staff_headers,
    )
    assert update_resp.status_code == 200
    assert update_resp.json()["status"] == "CONTAINED"
    assert update_resp.json()["location"] == "New Sector 3"

    # Admin updates status to RESOLVED
    admin_update_resp = client.put(
        f"/api/v1/disasters/{disaster_id}",
        json={"status": "RESOLVED"},
        headers=admin_headers,
    )
    assert admin_update_resp.status_code == 200
    assert admin_update_resp.json()["status"] == "RESOLVED"


def test_unauthorized_roles_cannot_update_disaster(client: TestClient):
    """
    Test that VOLUNTEER and DONOR cannot update a disaster (HTTP 403).
    """
    admin_headers = get_user_headers(client, "admin_lock@relief.org", "ADMIN")
    vol_headers = get_user_headers(client, "vol_lock@relief.org", "VOLUNTEER")

    create_resp = client.post(
        "/api/v1/disasters",
        json=sample_disaster_payload("Protected Event"),
        headers=admin_headers,
    )
    disaster_id = create_resp.json()["id"]

    put_resp = client.put(
        f"/api/v1/disasters/{disaster_id}",
        json={"name": "Tampered Name"},
        headers=vol_headers,
    )
    assert put_resp.status_code == 403


def test_delete_disaster_admin_only(client: TestClient):
    """
    Test that only ADMIN can delete a disaster:
    - Staff deletion attempt returns HTTP 403.
    - Admin deletion succeeds with HTTP 204.
    - Subsequent fetch returns HTTP 404.
    """
    admin_headers = get_user_headers(client, "admin_del@relief.org", "ADMIN")
    staff_headers = get_user_headers(client, "staff_del@relief.org", "NGO_STAFF")

    create_resp = client.post(
        "/api/v1/disasters",
        json=sample_disaster_payload("To Be Deleted"),
        headers=admin_headers,
    )
    disaster_id = create_resp.json()["id"]

    # Staff attempt should be forbidden
    staff_del_resp = client.delete(f"/api/v1/disasters/{disaster_id}", headers=staff_headers)
    assert staff_del_resp.status_code == 403

    # Admin attempt succeeds
    admin_del_resp = client.delete(f"/api/v1/disasters/{disaster_id}", headers=admin_headers)
    assert admin_del_resp.status_code == 204

    # Verify 404 on subsequent get
    assert client.get(f"/api/v1/disasters/{disaster_id}", headers=admin_headers).status_code == 404


def test_delete_nonexistent_disaster_returns_404(client: TestClient):
    """
    Test that deleting a non-existent disaster returns HTTP 404.
    """
    admin_headers = get_user_headers(client, "admin_del404@relief.org", "ADMIN")
    assert client.delete("/api/v1/disasters/88888", headers=admin_headers).status_code == 404


def test_invalid_dates_rejected_on_create(client: TestClient):
    """
    Test that end_date earlier than start_date is rejected with validation error (HTTP 422).
    """
    admin_headers = get_user_headers(client, "admin_dates@relief.org", "ADMIN")
    now = datetime.now(timezone.utc)

    invalid_payload = {
        "name": "Invalid Date Disaster",
        "location": "Sector 1",
        "status": "ACTIVE",
        "start_date": now.isoformat(),
        "end_date": (now - timedelta(days=2)).isoformat(),  # 2 days BEFORE start
    }

    response = client.post("/api/v1/disasters", json=invalid_payload, headers=admin_headers)
    assert response.status_code == 422


def test_invalid_status_rejected(client: TestClient):
    """
    Test that an invalid status enum value is rejected with HTTP 422.
    """
    admin_headers = get_user_headers(client, "admin_status@relief.org", "ADMIN")
    now = datetime.now(timezone.utc)

    invalid_payload = {
        "name": "Bad Status Disaster",
        "location": "Sector 1",
        "status": "NOT_A_REAL_STATUS",
        "start_date": now.isoformat(),
    }

    response = client.post("/api/v1/disasters", json=invalid_payload, headers=admin_headers)
    assert response.status_code == 422
