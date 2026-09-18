"""
Automated Tests for Volunteer Disaster Assignment and Task Management.
"""

from datetime import datetime, timedelta, timezone
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
def create_test_disaster(client: TestClient, admin_headers: dict, name: str = "Test Disaster"):
    now = datetime.now(timezone.utc)
    resp = client.post(
        "/api/v1/disasters",
        json={
            "name": name,
            "location": "District 9",
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


def test_staff_can_assign_volunteer_to_disaster(client: TestClient):
    """
    Test that NGO_STAFF can deploy a registered VOLUNTEER to an active disaster (201 Created).
    """
    admin_h = get_user_headers(client, "admin_v1@relief.org", "ADMIN")
    staff_h = get_user_headers(client, "staff_v1@relief.org", "NGO_STAFF")
    vol_h = get_user_headers(client, "volunteer_v1@relief.org", "VOLUNTEER")

    disaster_id = create_test_disaster(client, admin_h, "Flood Event Alpha")
    volunteer_id = get_user_id(client, vol_h)

    # Deploy volunteer
    assign_resp = client.post(
        "/api/v1/volunteers/assignments",
        json={"volunteer_id": volunteer_id, "disaster_id": disaster_id},
        headers=staff_h,
    )
    assert assign_resp.status_code == 201
    data = assign_resp.json()
    assert data["volunteer_id"] == volunteer_id
    assert data["disaster_id"] == disaster_id
    assert data["status"] == "ACTIVE"


def test_assign_non_volunteer_fails(client: TestClient):
    """
    Test that assigning a user who is NOT a volunteer (e.g. Donor) returns HTTP 400.
    """
    admin_h = get_user_headers(client, "admin_v2@relief.org", "ADMIN")
    donor_h = get_user_headers(client, "donor_v2@relief.org", "DONOR")

    disaster_id = create_test_disaster(client, admin_h, "Earthquake Bravo")
    donor_id = get_user_id(client, donor_h)

    assign_resp = client.post(
        "/api/v1/volunteers/assignments",
        json={"volunteer_id": donor_id, "disaster_id": disaster_id},
        headers=admin_h,
    )
    assert assign_resp.status_code == 400
    assert "does not have the VOLUNTEER role" in assign_resp.json()["detail"]


def test_duplicate_active_assignment_rejected(client: TestClient):
    """
    Test that deploying the same volunteer to the same disaster twice returns HTTP 400.
    """
    admin_h = get_user_headers(client, "admin_v3@relief.org", "ADMIN")
    vol_h = get_user_headers(client, "volunteer_v3@relief.org", "VOLUNTEER")

    disaster_id = create_test_disaster(client, admin_h, "Storm Charlie")
    volunteer_id = get_user_id(client, vol_h)

    # First deployment
    resp1 = client.post(
        "/api/v1/volunteers/assignments",
        json={"volunteer_id": volunteer_id, "disaster_id": disaster_id},
        headers=admin_h,
    )
    assert resp1.status_code == 201

    # Second duplicate deployment
    resp2 = client.post(
        "/api/v1/volunteers/assignments",
        json={"volunteer_id": volunteer_id, "disaster_id": disaster_id},
        headers=admin_h,
    )
    assert resp2.status_code == 400
    assert "already actively deployed" in resp2.json()["detail"]


def test_volunteer_can_view_my_assignments(client: TestClient):
    """
    Test that a volunteer can view all disasters they are deployed to (/my-assignments).
    """
    admin_h = get_user_headers(client, "admin_v4@relief.org", "ADMIN")
    vol_h = get_user_headers(client, "volunteer_v4@relief.org", "VOLUNTEER")

    disaster_id = create_test_disaster(client, admin_h, "Landslide Delta")
    volunteer_id = get_user_id(client, vol_h)

    client.post(
        "/api/v1/volunteers/assignments",
        json={"volunteer_id": volunteer_id, "disaster_id": disaster_id},
        headers=admin_h,
    )

    my_resp = client.get("/api/v1/volunteers/my-assignments", headers=vol_h)
    assert my_resp.status_code == 200
    assignments = my_resp.json()
    assert len(assignments) >= 1
    assert any(a["disaster_id"] == disaster_id for a in assignments)


def test_staff_create_task_and_volunteer_lifecycle(client: TestClient):
    """
    Complete task lifecycle test:
    1. Staff creates and assigns task to volunteer (status: PENDING).
    2. Volunteer views task under /my-tasks.
    3. Volunteer starts task (status: IN_PROGRESS).
    4. Volunteer completes task (status: COMPLETED).
    """
    staff_h = get_user_headers(client, "staff_task@relief.org", "NGO_STAFF")
    vol_h = get_user_headers(client, "vol_task@relief.org", "VOLUNTEER")

    disaster_id = create_test_disaster(client, staff_h, "Wildfire Echo")
    volunteer_id = get_user_id(client, vol_h)

    # 1. Staff creates task
    due = datetime.now(timezone.utc) + timedelta(days=2)
    task_resp = client.post(
        "/api/v1/volunteers/tasks",
        json={
            "title": "Distribute Water Packets",
            "description": "Distribute 500 packs of clean water to Shelter 4.",
            "disaster_id": disaster_id,
            "volunteer_id": volunteer_id,
            "due_date": due.isoformat(),
        },
        headers=staff_h,
    )
    assert task_resp.status_code == 201
    task = task_resp.json()
    task_id = task["id"]
    assert task["status"] == "PENDING"
    assert task["title"] == "Distribute Water Packets"

    # 2. Volunteer views /my-tasks
    my_tasks_resp = client.get("/api/v1/volunteers/my-tasks", headers=vol_h)
    assert my_tasks_resp.status_code == 200
    my_tasks = my_tasks_resp.json()
    assert any(t["id"] == task_id for t in my_tasks)

    # 3. Volunteer updates status to IN_PROGRESS
    prog_resp = client.patch(
        f"/api/v1/volunteers/tasks/{task_id}/status",
        json={"status": "IN_PROGRESS"},
        headers=vol_h,
    )
    assert prog_resp.status_code == 200
    assert prog_resp.json()["status"] == "IN_PROGRESS"

    # 4. Volunteer updates status to COMPLETED
    comp_resp = client.patch(
        f"/api/v1/volunteers/tasks/{task_id}/status",
        json={"status": "COMPLETED"},
        headers=vol_h,
    )
    assert comp_resp.status_code == 200
    assert comp_resp.json()["status"] == "COMPLETED"


def test_volunteer_cannot_tamper_with_other_volunteer_task(client: TestClient):
    """
    Test that Volunteer B cannot update status or view details of a task assigned to Volunteer A.
    """
    admin_h = get_user_headers(client, "admin_tamper@relief.org", "ADMIN")
    vol_a_h = get_user_headers(client, "vol_a@relief.org", "VOLUNTEER")
    vol_b_h = get_user_headers(client, "vol_b@relief.org", "VOLUNTEER")

    disaster_id = create_test_disaster(client, admin_h, "Tsunami Fox")
    vol_a_id = get_user_id(client, vol_a_h)

    # Admin assigns task to Volunteer A
    task_resp = client.post(
        "/api/v1/volunteers/tasks",
        json={
            "title": "Private Task for A",
            "disaster_id": disaster_id,
            "volunteer_id": vol_a_id,
        },
        headers=admin_h,
    )
    task_id = task_resp.json()["id"]

    # Volunteer B tries to view Volunteer A's task
    view_resp = client.get(f"/api/v1/volunteers/tasks/{task_id}", headers=vol_b_h)
    assert view_resp.status_code == 403

    # Volunteer B tries to update Volunteer A's task
    patch_resp = client.patch(
        f"/api/v1/volunteers/tasks/{task_id}/status",
        json={"status": "COMPLETED"},
        headers=vol_b_h,
    )
    assert patch_resp.status_code == 403


def test_unauthorized_role_cannot_assign_tasks(client: TestClient):
    """
    Test that Volunteers and Donors cannot create tasks or assignments (HTTP 403).
    """
    donor_h = get_user_headers(client, "donor_unauth@relief.org", "DONOR")
    vol_h = get_user_headers(client, "vol_unauth@relief.org", "VOLUNTEER")

    # Donor attempt
    assert client.post("/api/v1/volunteers/assignments", json={}, headers=donor_h).status_code == 403
    assert client.post("/api/v1/volunteers/tasks", json={}, headers=donor_h).status_code == 403

    # Volunteer attempt
    assert client.post("/api/v1/volunteers/assignments", json={}, headers=vol_h).status_code == 403
    assert client.post("/api/v1/volunteers/tasks", json={}, headers=vol_h).status_code == 403


def test_staff_can_update_and_delete_task(client: TestClient):
    """
    Test that NGO_STAFF can update task details (PUT) and delete a task (DELETE).
    """
    staff_h = get_user_headers(client, "staff_manage@relief.org", "NGO_STAFF")
    vol_h = get_user_headers(client, "vol_manage@relief.org", "VOLUNTEER")

    disaster_id = create_test_disaster(client, staff_h, "Blizzard Golf")
    vol_id = get_user_id(client, vol_h)

    # Create task
    task_resp = client.post(
        "/api/v1/volunteers/tasks",
        json={"title": "Original Title", "disaster_id": disaster_id, "volunteer_id": vol_id},
        headers=staff_h,
    )
    task_id = task_resp.json()["id"]

    # Update task details
    put_resp = client.put(
        f"/api/v1/volunteers/tasks/{task_id}",
        json={"title": "Updated Task Title", "description": "New description added"},
        headers=staff_h,
    )
    assert put_resp.status_code == 200
    assert put_resp.json()["title"] == "Updated Task Title"

    # Delete task
    del_resp = client.delete(f"/api/v1/volunteers/tasks/{task_id}", headers=staff_h)
    assert del_resp.status_code == 204

    # Verify 404
    assert client.get(f"/api/v1/volunteers/tasks/{task_id}", headers=staff_h).status_code == 404


def test_task_status_state_machine_transitions(client: TestClient):
    """
    Test that VolunteerTask enforces strict state machine lifecycle transitions:
    - PENDING -> IN_PROGRESS -> COMPLETED (Valid)
    - COMPLETED -> PENDING rejected (HTTP 400)
    - COMPLETED -> IN_PROGRESS rejected (HTTP 400)
    - COMPLETED -> CANCELLED rejected (HTTP 400)
    - CANCELLED -> PENDING rejected (HTTP 400)
    - CANCELLED -> IN_PROGRESS rejected (HTTP 400)
    - CANCELLED -> COMPLETED rejected (HTTP 400)
    """
    staff_h = get_user_headers(client, "staff_sm@relief.org", "NGO_STAFF")
    vol_h = get_user_headers(client, "vol_sm@relief.org", "VOLUNTEER")
    disaster_id = create_test_disaster(client, staff_h, "State Machine Event")
    vol_id = get_user_id(client, vol_h)

    # 1. Create Task 1 and advance to COMPLETED
    t1_resp = client.post(
        "/api/v1/volunteers/tasks",
        json={"title": "Deliver Supplies", "disaster_id": disaster_id, "volunteer_id": vol_id},
        headers=staff_h,
    )
    assert t1_resp.status_code == 201
    t1_id = t1_resp.json()["id"]

    # PENDING -> IN_PROGRESS (allowed)
    r = client.patch(f"/api/v1/volunteers/tasks/{t1_id}/status", json={"status": "IN_PROGRESS"}, headers=vol_h)
    assert r.status_code == 200
    assert r.json()["status"] == "IN_PROGRESS"

    # IN_PROGRESS -> COMPLETED (allowed)
    r = client.patch(f"/api/v1/volunteers/tasks/{t1_id}/status", json={"status": "COMPLETED"}, headers=vol_h)
    assert r.status_code == 200
    assert r.json()["status"] == "COMPLETED"

    # COMPLETED -> PENDING (rejected 400)
    r_rev_pending = client.patch(f"/api/v1/volunteers/tasks/{t1_id}/status", json={"status": "PENDING"}, headers=vol_h)
    assert r_rev_pending.status_code == 400
    assert "Invalid task status transition" in r_rev_pending.json()["detail"]

    # COMPLETED -> IN_PROGRESS (rejected 400)
    r_rev_prog = client.patch(f"/api/v1/volunteers/tasks/{t1_id}/status", json={"status": "IN_PROGRESS"}, headers=vol_h)
    assert r_rev_prog.status_code == 400
    assert "Invalid task status transition" in r_rev_prog.json()["detail"]

    # COMPLETED -> CANCELLED (rejected 400)
    r_rev_cancel = client.patch(f"/api/v1/volunteers/tasks/{t1_id}/status", json={"status": "CANCELLED"}, headers=vol_h)
    assert r_rev_cancel.status_code == 400
    assert "Invalid task status transition" in r_rev_cancel.json()["detail"]

    # 2. Create Task 2 and cancel it
    t2_resp = client.post(
        "/api/v1/volunteers/tasks",
        json={"title": "Cancelled Task", "disaster_id": disaster_id, "volunteer_id": vol_id},
        headers=staff_h,
    )
    assert t2_resp.status_code == 201
    t2_id = t2_resp.json()["id"]

    # PENDING -> CANCELLED (allowed)
    r_cancel = client.patch(f"/api/v1/volunteers/tasks/{t2_id}/status", json={"status": "CANCELLED"}, headers=vol_h)
    assert r_cancel.status_code == 200
    assert r_cancel.json()["status"] == "CANCELLED"

    # CANCELLED -> PENDING (rejected 400)
    r_c_pending = client.patch(f"/api/v1/volunteers/tasks/{t2_id}/status", json={"status": "PENDING"}, headers=vol_h)
    assert r_c_pending.status_code == 400
    assert "Invalid task status transition" in r_c_pending.json()["detail"]

    # CANCELLED -> IN_PROGRESS (rejected 400)
    r_c_prog = client.patch(f"/api/v1/volunteers/tasks/{t2_id}/status", json={"status": "IN_PROGRESS"}, headers=vol_h)
    assert r_c_prog.status_code == 400
    assert "Invalid task status transition" in r_c_prog.json()["detail"]

    # CANCELLED -> COMPLETED (rejected 400)
    r_c_comp = client.patch(f"/api/v1/volunteers/tasks/{t2_id}/status", json={"status": "COMPLETED"}, headers=vol_h)
    assert r_c_comp.status_code == 400
    assert "Invalid task status transition" in r_c_comp.json()["detail"]

