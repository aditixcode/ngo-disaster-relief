"""
Resource Distribution Pydantic Schemas.

Defines request validation and audit response models for resource distribution transactions.
"""

from datetime import datetime, timezone
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict, field_validator


class ResourceDistributionBase(BaseModel):
    """Base fields shared across resource distribution models."""
    disaster_id: int = Field(..., description="Target disaster relief operation ID")
    inventory_item_id: int = Field(..., description="Target inventory batch to distribute from")
    beneficiary_id: int = Field(..., description="Verified recipient beneficiary ID")
    distribution_center_id: int = Field(..., description="Active distribution hub ID")
    quantity: float = Field(..., gt=0.0, description="Quantity of items distributed (> 0)")
    unit: str = Field(..., min_length=1, max_length=50, examples=["kg", "packets", "bottles"])
    item_name: Optional[str] = Field(None, max_length=150, description="Optional safeguard name to verify batch identity")
    notes: Optional[str] = Field(None, max_length=1000, description="Field distribution notes or remarks")

    @field_validator("unit")
    @classmethod
    def validate_unit(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Unit cannot be empty or whitespace only.")
        return v.strip()

    @field_validator("item_name", "notes")
    @classmethod
    def validate_optional_text(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            if not v.strip():
                return None
            return v.strip()
        return v


class ResourceDistributionCreate(ResourceDistributionBase):
    """
    Schema for creating an atomic resource distribution transaction.
    """
    distributed_at: Optional[datetime] = Field(
        None,
        description="Optional distribution timestamp. Defaults to UTC server time if omitted.",
    )

    @field_validator("distributed_at")
    @classmethod
    def validate_distributed_at(cls, v: Optional[datetime]) -> Optional[datetime]:
        if v is not None:
            now = datetime.now(timezone.utc)
            v_cmp = v if v.tzinfo is not None else v.replace(tzinfo=timezone.utc)
            if v_cmp > now:
                raise ValueError("distributed_at timestamp cannot be in the future.")
        return v


class ResourceDistributionResponse(BaseModel):
    """
    Schema for immutable resource distribution audit records returned by the API.
    """
    id: int
    disaster_id: int
    inventory_item_id: int
    beneficiary_id: int
    distribution_center_id: int
    quantity: float
    unit: str
    item_name: str
    distributed_by_id: Optional[int] = None
    distributed_at: datetime
    notes: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
