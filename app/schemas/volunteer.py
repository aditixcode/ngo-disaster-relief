"""
Volunteer Assignment and Task Pydantic Schemas.

Defines request validation and response models for:
- Deploying volunteers to disaster operations.
- Creating, delegating, and tracking operational task lifecycles.
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict
from app.models.volunteer import AssignmentStatus, TaskStatus


# -----------------------------------------------------------------------------
# Volunteer Assignment Schemas
# -----------------------------------------------------------------------------

class AssignmentCreate(BaseModel):
    """Schema to deploy a volunteer to a specific disaster."""
    volunteer_id: int = Field(..., description="ID of the user with VOLUNTEER role")
    disaster_id: int = Field(..., description="ID of the disaster event")


class AssignmentStatusUpdate(BaseModel):
    """Schema to transition assignment status (e.g. ACTIVE -> COMPLETED)."""
    status: AssignmentStatus


class AssignmentResponse(BaseModel):
    """Public representation of a volunteer disaster assignment."""
    id: int
    volunteer_id: int
    disaster_id: int
    assigned_by_id: Optional[int] = None
    status: AssignmentStatus
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# -----------------------------------------------------------------------------
# Volunteer Task Schemas
# -----------------------------------------------------------------------------

class TaskCreate(BaseModel):
    """Schema to create and assign an operational task to a volunteer."""
    title: str = Field(..., min_length=1, max_length=150, examples=["Deliver Emergency Medical Kits"])
    description: Optional[str] = Field(None, examples=["Distribute 50 first aid kits to evacuation center 3."])
    disaster_id: int = Field(..., description="Target disaster operation")
    volunteer_id: int = Field(..., description="Assigned volunteer ID")
    due_date: Optional[datetime] = Field(None, examples=["2026-09-22T18:00:00Z"])


class TaskUpdate(BaseModel):
    """Schema for Admin/Staff to update task details or reassign."""
    title: Optional[str] = Field(None, min_length=1, max_length=150)
    description: Optional[str] = None
    volunteer_id: Optional[int] = None
    status: Optional[TaskStatus] = None
    due_date: Optional[datetime] = None


class TaskStatusUpdate(BaseModel):
    """Simplified schema for volunteers to update the status of their own tasks."""
    status: TaskStatus = Field(..., description="New task status (PENDING, IN_PROGRESS, COMPLETED, CANCELLED)")


class TaskResponse(BaseModel):
    """Public representation of an assigned relief task."""
    id: int
    title: str
    description: Optional[str]
    disaster_id: int
    volunteer_id: int
    assigned_by_id: Optional[int] = None
    status: TaskStatus
    due_date: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
