"""
Disaster Pydantic Schemas.

Defines request validation and response models for disaster/event management.
Enforces business rules such as non-empty names/locations and end_date >= start_date.
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict, model_validator
from app.models.disaster import DisasterStatus


class DisasterBase(BaseModel):
    """Shared fields for disaster resources."""
    name: str = Field(..., min_length=1, max_length=150, examples=["Flood Relief Operation Alpha"])
    description: Optional[str] = Field(None, examples=["Emergency relief operation for severe coastal flooding."])
    location: str = Field(..., min_length=1, max_length=255, examples=["Bay of Bengal Sector 4"])
    status: DisasterStatus = Field(default=DisasterStatus.ACTIVE, examples=[DisasterStatus.ACTIVE])
    start_date: datetime = Field(..., examples=["2026-09-18T10:00:00Z"])
    end_date: Optional[datetime] = Field(None, examples=["2026-09-25T18:00:00Z"])


class DisasterCreate(DisasterBase):
    """
    Schema for creating a disaster.
    Enforces business logic that end_date cannot be earlier than start_date.
    """
    @model_validator(mode="after")
    def validate_dates(self) -> "DisasterCreate":
        if self.end_date and self.end_date < self.start_date:
            raise ValueError("end_date cannot be earlier than start_date")
        return self


class DisasterUpdate(BaseModel):
    """
    Schema for updating an existing disaster.
    All fields are optional for partial updates.
    """
    name: Optional[str] = Field(None, min_length=1, max_length=150)
    description: Optional[str] = None
    location: Optional[str] = Field(None, min_length=1, max_length=255)
    status: Optional[DisasterStatus] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None

    @model_validator(mode="after")
    def validate_dates(self) -> "DisasterUpdate":
        if self.start_date and self.end_date and self.end_date < self.start_date:
            raise ValueError("end_date cannot be earlier than start_date")
        return self


class DisasterResponse(DisasterBase):
    """
    Public response schema for disaster details.
    Includes persistent ID, timestamp, and creator tracking.
    """
    id: int
    created_at: datetime
    created_by_id: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)
