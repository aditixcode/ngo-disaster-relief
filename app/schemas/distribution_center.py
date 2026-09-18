"""
Distribution Center Pydantic Schemas.

Defines request validation and response models for physical relief distribution centers,
facility capacity declaration, and operational availability status.
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict, field_validator
from app.models.distribution_center import CenterStatus


class DistributionCenterBase(BaseModel):
    """Shared attributes for distribution center resources."""
    name: str = Field(..., min_length=1, max_length=150, examples=["Central Camp Relief Hub"])
    address: str = Field(..., min_length=1, max_length=500, examples=["Community Stadium, Gate 3"])
    contact_number: str = Field(..., min_length=5, max_length=50, examples=["+91-9876543210"])
    capacity: int = Field(..., gt=0, description="Target recipient handling capacity", examples=[1500])
    operating_hours: Optional[str] = Field(None, max_length=100, examples=["08:00 - 18:00 Daily"])

    @field_validator("name", "address", "contact_number")
    @classmethod
    def validate_non_empty_strings(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Field cannot be empty or whitespace only")
        return v.strip()


class DistributionCenterCreate(DistributionCenterBase):
    """
    Schema for registering a new physical distribution center under a disaster operation.
    Initial status is set to ACTIVE automatically by the server.
    """
    disaster_id: int = Field(..., description="ID of the disaster this center serves")


class DistributionCenterUpdate(BaseModel):
    """
    Schema for modifying distribution center configuration or capacity.
    All fields are optional for partial updates.
    """
    name: Optional[str] = Field(None, min_length=1, max_length=150)
    address: Optional[str] = Field(None, min_length=1, max_length=500)
    contact_number: Optional[str] = Field(None, min_length=5, max_length=50)
    capacity: Optional[int] = Field(None, gt=0)
    operating_hours: Optional[str] = Field(None, max_length=100)

    @field_validator("name", "address", "contact_number")
    @classmethod
    def validate_optional_strings(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            if not v.strip():
                raise ValueError("Field cannot be empty or whitespace only")
            return v.strip()
        return v


class DistributionCenterStatusUpdate(BaseModel):
    """
    Schema for updating the operational availability status of a center.
    Valid transitions:
    - ACTIVE -> FULL / INACTIVE
    - FULL -> ACTIVE / INACTIVE
    - INACTIVE -> ACTIVE
    """
    status: CenterStatus = Field(..., description="Target center status: ACTIVE, INACTIVE, or FULL")


class DistributionCenterResponse(DistributionCenterBase):
    """
    Public response representation of a distribution center.
    Includes calculated operational readiness (True only when status == ACTIVE).
    """
    id: int
    disaster_id: int
    status: CenterStatus
    created_by_id: Optional[int] = None
    is_operational: bool = Field(
        ...,
        description="True only if status == ACTIVE; gates Stage 10 resource distribution dispatches",
    )
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
