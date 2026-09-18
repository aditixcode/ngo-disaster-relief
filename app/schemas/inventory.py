"""
Relief Inventory Pydantic Schemas.

Defines request validation and response models for inventory tracking and available stock calculations.
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict, field_validator
from app.models.inventory import InventoryStatus


class InventoryCreate(BaseModel):
    """
    Schema to record a new batch of physical relief supplies delivered to a warehouse.
    Initial status will automatically be set to RECEIVED.
    """
    disaster_id: int = Field(..., description="ID of the disaster operation receiving the goods")
    item_name: str = Field(..., min_length=1, max_length=150, examples=["Basmati Rice"])
    quantity: float = Field(..., gt=0, description="Quantity must be strictly positive", examples=[500.0])
    unit: str = Field(..., min_length=1, max_length=50, examples=["kg"])

    @field_validator("item_name", "unit")
    @classmethod
    def validate_non_empty_str(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Field cannot be empty or whitespace only")
        return v.strip()


class InventoryStatusUpdate(BaseModel):
    """Schema for changing inventory lifecycle status."""
    status: InventoryStatus = Field(..., description="Target status: STORED")


class InventoryResponse(BaseModel):
    """Public representation of an inventory item batch."""
    id: int
    disaster_id: int
    item_name: str
    quantity: float
    unit: str
    status: InventoryStatus
    received_at: datetime
    stored_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class InventoryAvailabilityResponse(BaseModel):
    """Schema reporting current distributable stock for a specific resource."""
    disaster_id: int
    item_name: str
    unit: str
    available_quantity: float = Field(
        ...,
        description="Total quantity currently in STORED status and eligible for distribution",
    )
