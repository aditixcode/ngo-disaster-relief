"""
Volunteer Disaster Deployment and Task Management Endpoints.

Implements the relief workflow:
1. Deploy registered volunteers to a disaster operation.
2. Delegate specific tasks to volunteers.
3. Volunteers track and update task progress (PENDING -> IN_PROGRESS -> COMPLETED).
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query, Response
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_current_user, require_roles
from app.models.user import User, UserRole
from app.models.disaster import Disaster
from app.models.volunteer import (
    VolunteerAssignment,
    VolunteerTask,
    AssignmentStatus,
    TaskStatus,
)
from app.schemas.volunteer import (
    AssignmentCreate,
    AssignmentStatusUpdate,
    AssignmentResponse,
    TaskCreate,
    TaskUpdate,
    TaskStatusUpdate,
    TaskResponse,
)

router = APIRouter()


# -----------------------------------------------------------------------------
# 1. Volunteer Disaster Deployment / Assignments
# -----------------------------------------------------------------------------

@router.post(
    "/assignments",
    response_model=AssignmentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Assign a volunteer to a disaster",
    description="Deploys a registered volunteer to a disaster operation. Restricted to ADMIN and NGO_STAFF.",
)
def assign_volunteer_to_disaster(
    assignment_in: AssignmentCreate,
    current_user: User = Depends(require_roles([UserRole.ADMIN, UserRole.NGO_STAFF])),
    db: Session = Depends(get_db),
) -> VolunteerAssignment:
    """
    Deploys a volunteer to a disaster.
    Validates that:
    - Target user exists and has the VOLUNTEER role.
    - Target disaster exists.
    - Volunteer is not already actively assigned to this disaster.
    """
    # 1. Validate target user
    volunteer = db.query(User).filter(User.id == assignment_in.volunteer_id).first()
    if not volunteer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with ID {assignment_in.volunteer_id} not found",
        )
    if volunteer.role != UserRole.VOLUNTEER:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"User '{volunteer.name}' does not have the VOLUNTEER role (current role: {volunteer.role.value})",
        )

    # 2. Validate disaster
    disaster = db.query(Disaster).filter(Disaster.id == assignment_in.disaster_id).first()
    if not disaster:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Disaster with ID {assignment_in.disaster_id} not found",
        )

    # 3. Check for existing active assignment
    existing_assignment = (
        db.query(VolunteerAssignment)
        .filter(
            VolunteerAssignment.volunteer_id == assignment_in.volunteer_id,
            VolunteerAssignment.disaster_id == assignment_in.disaster_id,
        )
        .first()
    )
    if existing_assignment:
        if existing_assignment.status == AssignmentStatus.ACTIVE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Volunteer is already actively deployed to this disaster",
            )
        # If previously completed, reactivate
        existing_assignment.status = AssignmentStatus.ACTIVE
        existing_assignment.assigned_by_id = current_user.id
        db.commit()
        db.refresh(existing_assignment)
        return existing_assignment

    # 4. Create new deployment record
    new_assignment = VolunteerAssignment(
        volunteer_id=assignment_in.volunteer_id,
        disaster_id=assignment_in.disaster_id,
        assigned_by_id=current_user.id,
        status=AssignmentStatus.ACTIVE,
    )
    db.add(new_assignment)
    db.commit()
    db.refresh(new_assignment)
    return new_assignment


@router.get(
    "/assignments",
    response_model=List[AssignmentResponse],
    summary="List volunteer disaster assignments",
    description="Returns volunteer deployment records. Restricted to ADMIN and NGO_STAFF.",
)
def list_assignments(
    disaster_id: Optional[int] = Query(None, description="Filter by disaster ID"),
    volunteer_id: Optional[int] = Query(None, description="Filter by volunteer ID"),
    current_user: User = Depends(require_roles([UserRole.ADMIN, UserRole.NGO_STAFF])),
    db: Session = Depends(get_db),
) -> List[VolunteerAssignment]:
    query = db.query(VolunteerAssignment)
    if disaster_id:
        query = query.filter(VolunteerAssignment.disaster_id == disaster_id)
    if volunteer_id:
        query = query.filter(VolunteerAssignment.volunteer_id == volunteer_id)
    return query.order_by(VolunteerAssignment.created_at.desc()).all()


@router.get(
    "/my-assignments",
    response_model=List[AssignmentResponse],
    summary="List disasters assigned to logged-in volunteer",
    description="Returns all disaster deployments for the currently authenticated volunteer.",
)
def get_my_assignments(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> List[VolunteerAssignment]:
    return (
        db.query(VolunteerAssignment)
        .filter(VolunteerAssignment.volunteer_id == current_user.id)
        .order_by(VolunteerAssignment.created_at.desc())
        .all()
    )


# -----------------------------------------------------------------------------
# 2. Operational Task Delegation & Tracking
# -----------------------------------------------------------------------------

@router.post(
    "/tasks",
    response_model=TaskResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Assign an operational task to a volunteer",
    description="Creates a task under a disaster and assigns it to a volunteer. Restricted to ADMIN and NGO_STAFF.",
)
def create_volunteer_task(
    task_in: TaskCreate,
    current_user: User = Depends(require_roles([UserRole.ADMIN, UserRole.NGO_STAFF])),
    db: Session = Depends(get_db),
) -> VolunteerTask:
    """
    Creates a new operational task for a volunteer.
    Validates that:
    - Target disaster exists.
    - Target volunteer exists and has role VOLUNTEER.
    """
    # 1. Validate disaster
    disaster = db.query(Disaster).filter(Disaster.id == task_in.disaster_id).first()
    if not disaster:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Disaster with ID {task_in.disaster_id} not found",
        )

    # 2. Validate volunteer
    volunteer = db.query(User).filter(User.id == task_in.volunteer_id).first()
    if not volunteer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Volunteer with ID {task_in.volunteer_id} not found",
        )
    if volunteer.role != UserRole.VOLUNTEER:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"User '{volunteer.name}' is not registered as a VOLUNTEER",
        )

    # 3. Create task
    new_task = VolunteerTask(
        title=task_in.title,
        description=task_in.description,
        disaster_id=task_in.disaster_id,
        volunteer_id=task_in.volunteer_id,
        assigned_by_id=current_user.id,
        status=TaskStatus.PENDING,
        due_date=task_in.due_date,
    )
    db.add(new_task)
    db.commit()
    db.refresh(new_task)
    return new_task


@router.get(
    "/tasks",
    response_model=List[TaskResponse],
    summary="List all volunteer tasks",
    description="Returns all tasks with optional filtering by disaster, volunteer, or status. Restricted to ADMIN and NGO_STAFF.",
)
def list_tasks(
    disaster_id: Optional[int] = Query(None, description="Filter by disaster ID"),
    volunteer_id: Optional[int] = Query(None, description="Filter by volunteer ID"),
    task_status: Optional[TaskStatus] = Query(None, alias="status", description="Filter by task status"),
    current_user: User = Depends(require_roles([UserRole.ADMIN, UserRole.NGO_STAFF])),
    db: Session = Depends(get_db),
) -> List[VolunteerTask]:
    query = db.query(VolunteerTask)
    if disaster_id:
        query = query.filter(VolunteerTask.disaster_id == disaster_id)
    if volunteer_id:
        query = query.filter(VolunteerTask.volunteer_id == volunteer_id)
    if task_status:
        query = query.filter(VolunteerTask.status == task_status)
    return query.order_by(VolunteerTask.created_at.desc()).all()


@router.get(
    "/my-tasks",
    response_model=List[TaskResponse],
    summary="List tasks assigned to the current volunteer",
    description="Returns all tasks assigned to the currently authenticated volunteer.",
)
def get_my_tasks(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> List[VolunteerTask]:
    return (
        db.query(VolunteerTask)
        .filter(VolunteerTask.volunteer_id == current_user.id)
        .order_by(VolunteerTask.created_at.desc())
        .all()
    )


@router.get(
    "/tasks/{task_id}",
    response_model=TaskResponse,
    summary="Get task details by ID",
    description="Retrieves a task by ID. Accessible to ADMIN, NGO_STAFF, or the assigned volunteer.",
)
def get_task(
    task_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> VolunteerTask:
    task = db.query(VolunteerTask).filter(VolunteerTask.id == task_id).first()
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task with ID {task_id} not found",
        )

    # Authorization: Admins/Staff can view any task; Volunteers can only view their own
    if (
        current_user.role not in [UserRole.ADMIN, UserRole.NGO_STAFF]
        and task.volunteer_id != current_user.id
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to view this task",
        )

    return task


# Valid VolunteerTask lifecycle transitions
ALLOWED_TASK_TRANSITIONS = {
    TaskStatus.PENDING: {
        TaskStatus.PENDING,
        TaskStatus.IN_PROGRESS,
        TaskStatus.COMPLETED,
        TaskStatus.CANCELLED,
    },
    TaskStatus.IN_PROGRESS: {
        TaskStatus.IN_PROGRESS,
        TaskStatus.COMPLETED,
        TaskStatus.CANCELLED,
    },
    TaskStatus.COMPLETED: {
        TaskStatus.COMPLETED,
    },
    TaskStatus.CANCELLED: {
        TaskStatus.CANCELLED,
    },
}


@router.patch(
    "/tasks/{task_id}/status",
    response_model=TaskResponse,
    summary="Update task status (Volunteer progress tracking)",
    description=(
        "Updates the operational status of a task (PENDING -> IN_PROGRESS -> COMPLETED). "
        "Can be called by the assigned volunteer or by ADMIN/NGO_STAFF."
    ),
)
def update_task_status(
    task_id: int,
    status_in: TaskStatusUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> VolunteerTask:
    """
    Allows the assigned volunteer to report progress by updating status.
    Guards ensure volunteers cannot tamper with other volunteers' tasks
    and enforces strict state machine lifecycle transitions.
    """
    task = db.query(VolunteerTask).filter(VolunteerTask.id == task_id).first()
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task with ID {task_id} not found",
        )

    # Verify authorization
    if (
        current_user.role not in [UserRole.ADMIN, UserRole.NGO_STAFF]
        and task.volunteer_id != current_user.id
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to update this task",
        )

    # Enforce task status state machine
    current_status = task.status
    target_status = status_in.status
    if target_status not in ALLOWED_TASK_TRANSITIONS.get(current_status, set()):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid task status transition from '{current_status.value}' to '{target_status.value}'.",
        )

    task.status = target_status
    db.commit()
    db.refresh(task)
    return task


@router.put(
    "/tasks/{task_id}",
    response_model=TaskResponse,
    summary="Update task details",
    description="Updates task properties (title, description, assignee, due date). Restricted to ADMIN and NGO_STAFF.",
)
def update_task_details(
    task_id: int,
    task_in: TaskUpdate,
    current_user: User = Depends(require_roles([UserRole.ADMIN, UserRole.NGO_STAFF])),
    db: Session = Depends(get_db),
) -> VolunteerTask:
    task = db.query(VolunteerTask).filter(VolunteerTask.id == task_id).first()
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task with ID {task_id} not found",
        )

    update_data = task_in.model_dump(exclude_unset=True)

    # If reassigning volunteer, verify target volunteer
    if "volunteer_id" in update_data and update_data["volunteer_id"] != task.volunteer_id:
        target_vol = db.query(User).filter(User.id == update_data["volunteer_id"]).first()
        if not target_vol or target_vol.role != UserRole.VOLUNTEER:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Target assignee must be a registered VOLUNTEER",
            )

    # If updating status, enforce state machine transitions
    if "status" in update_data and update_data["status"] is not None:
        target_status = update_data["status"]
        if target_status not in ALLOWED_TASK_TRANSITIONS.get(task.status, set()):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid task status transition from '{task.status.value}' to '{target_status.value}'.",
            )

    for field, val in update_data.items():
        setattr(task, field, val)

    db.commit()
    db.refresh(task)
    return task


@router.delete(
    "/tasks/{task_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a task",
    description="Removes a task from the system. Restricted to ADMIN and NGO_STAFF.",
)
def delete_task(
    task_id: int,
    current_user: User = Depends(require_roles([UserRole.ADMIN, UserRole.NGO_STAFF])),
    db: Session = Depends(get_db),
):
    task = db.query(VolunteerTask).filter(VolunteerTask.id == task_id).first()
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task with ID {task_id} not found",
        )
    db.delete(task)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
