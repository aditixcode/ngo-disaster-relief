"""
Automated Tests for Authentication & Role-Based Authorization.
"""

import pytest
from fastapi.testclient import TestClient
from app.models.user import UserRole


# Helper to register and return a user
def register_user(client: TestClient, email: str, role: str, name: str = "Test User"):
    return client.post(
        "/api/v1/auth/register",
        json={
            "name": name,
            "email": email,
            "password": "Password123!",
            "role": role,
        },
    )


# Helper to login and return auth headers
def get_auth_headers(client: TestClient, email: str, password: str = "Password123!"):
    response = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    assert response.status_code == 200
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_successful_registration(client: TestClient):
    """
    Test that a new user can register successfully and receive safe user info.
    """
    response = register_user(client, "alice@relief.org", "VOLUNTEER", "Alice Smith")
    assert response.status_code == 201

    data = response.json()
    assert data["email"] == "alice@relief.org"
    assert data["name"] == "Alice Smith"
    assert data["role"] == "VOLUNTEER"
    assert "id" in data
    assert "created_at" in data
    # Ensure sensitive fields are NEVER exposed
    assert "password" not in data
    assert "password_hash" not in data


def test_duplicate_registration_fails(client: TestClient):
    """
    Test that registering with an already existing email returns HTTP 400.
    """
    register_user(client, "duplicate@relief.org", "DONOR")
    response = register_user(client, "duplicate@relief.org", "DONOR")

    assert response.status_code == 400
    assert "Email already registered" in response.json()["detail"]


def test_successful_login_json(client: TestClient):
    """
    Test that logging in with valid JSON credentials returns a valid JWT token.
    """
    register_user(client, "bob@relief.org", "ADMIN", "Bob Admin")
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "bob@relief.org", "password": "Password123!"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert len(data["access_token"]) > 20


def test_successful_login_form_data(client: TestClient):
    """
    Test login via form data (OAuth2PasswordRequestForm compatibility for Swagger Authorize).
    """
    register_user(client, "swagger@relief.org", "NGO_STAFF", "Swagger User")
    response = client.post(
        "/api/v1/auth/login",
        data={"username": "swagger@relief.org", "password": "Password123!"},
    )
    assert response.status_code == 200
    assert "access_token" in response.json()


def test_login_invalid_password(client: TestClient):
    """
    Test that login with wrong password returns HTTP 401.
    """
    register_user(client, "charlie@relief.org", "VOLUNTEER")
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "charlie@relief.org", "password": "WrongPassword!"},
    )
    assert response.status_code == 401
    assert "Invalid email or password" in response.json()["detail"]


def test_login_nonexistent_user(client: TestClient):
    """
    Test that login with non-existent email returns HTTP 401.
    """
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "ghost@relief.org", "password": "Password123!"},
    )
    assert response.status_code == 401
    assert "Invalid email or password" in response.json()["detail"]


def test_get_me_with_valid_token(client: TestClient):
    """
    Test accessing /api/v1/auth/me with a valid Bearer token returns current user profile.
    """
    register_user(client, "me@relief.org", "NGO_STAFF", "Me User")
    headers = get_auth_headers(client, "me@relief.org")

    response = client.get("/api/v1/auth/me", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "me@relief.org"
    assert data["role"] == "NGO_STAFF"
    assert "password_hash" not in data


def test_get_me_without_token_fails(client: TestClient):
    """
    Test accessing /api/v1/auth/me without a token returns HTTP 401.
    """
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 401


def test_get_me_invalid_token_fails(client: TestClient):
    """
    Test accessing /api/v1/auth/me with an invalid token returns HTTP 401.
    """
    response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "Bearer this.is.an.invalid.token"},
    )
    assert response.status_code == 401


def test_role_authorization_admin_only(client: TestClient):
    """
    Test /auth/admin-test:
    - ADMIN has access (200 OK)
    - VOLUNTEER is denied (403 Forbidden)
    """
    register_user(client, "admin@relief.org", "ADMIN")
    register_user(client, "volunteer@relief.org", "VOLUNTEER")

    admin_headers = get_auth_headers(client, "admin@relief.org")
    volunteer_headers = get_auth_headers(client, "volunteer@relief.org")

    # Admin should succeed
    admin_resp = client.get("/api/v1/auth/admin-test", headers=admin_headers)
    assert admin_resp.status_code == 200
    assert "Access granted" in admin_resp.json()["message"]

    # Volunteer should be forbidden
    vol_resp = client.get("/api/v1/auth/admin-test", headers=volunteer_headers)
    assert vol_resp.status_code == 403
    assert "Insufficient permissions" in vol_resp.json()["detail"]


def test_role_authorization_matrix(client: TestClient):
    """
    Test role authorization across staff, volunteer, and donor endpoints.
    """
    register_user(client, "matrix_admin@relief.org", "ADMIN")
    register_user(client, "matrix_staff@relief.org", "NGO_STAFF")
    register_user(client, "matrix_vol@relief.org", "VOLUNTEER")
    register_user(client, "matrix_donor@relief.org", "DONOR")

    admin_h = get_auth_headers(client, "matrix_admin@relief.org")
    staff_h = get_auth_headers(client, "matrix_staff@relief.org")
    vol_h = get_auth_headers(client, "matrix_vol@relief.org")
    donor_h = get_auth_headers(client, "matrix_donor@relief.org")

    # 1. Staff endpoint: ADMIN & NGO_STAFF allowed, VOLUNTEER & DONOR forbidden
    assert client.get("/api/v1/auth/staff-test", headers=admin_h).status_code == 200
    assert client.get("/api/v1/auth/staff-test", headers=staff_h).status_code == 200
    assert client.get("/api/v1/auth/staff-test", headers=vol_h).status_code == 403
    assert client.get("/api/v1/auth/staff-test", headers=donor_h).status_code == 403

    # 2. Volunteer endpoint: ADMIN, NGO_STAFF, VOLUNTEER allowed, DONOR forbidden
    assert client.get("/api/v1/auth/volunteer-test", headers=admin_h).status_code == 200
    assert client.get("/api/v1/auth/volunteer-test", headers=staff_h).status_code == 200
    assert client.get("/api/v1/auth/volunteer-test", headers=vol_h).status_code == 200
    assert client.get("/api/v1/auth/volunteer-test", headers=donor_h).status_code == 403

    # 3. Donor endpoint: ADMIN, NGO_STAFF, DONOR allowed, VOLUNTEER forbidden
    assert client.get("/api/v1/auth/donor-test", headers=admin_h).status_code == 200
    assert client.get("/api/v1/auth/donor-test", headers=staff_h).status_code == 200
    assert client.get("/api/v1/auth/donor-test", headers=donor_h).status_code == 200
    assert client.get("/api/v1/auth/donor-test", headers=vol_h).status_code == 403
