"""
Donation Pydantic Schemas.

Defines request validation and response models for monetary and material donations.
Enforces conditional business rules based on donation_type.
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict, model_validator
from app.models.donation import DonationType, DonationStatus


class DonationCreate(BaseModel):
    """
    Schema for pledging or recording a new donation.
    Enforces required fields based on whether donation_type is MONEY or MATERIAL.
    """
    disaster_id: int = Field(..., description="Target disaster operation ID")
    donor_id: Optional[int] = Field(None, description="Donor user ID (optional for donors, set by staff/admin)")
    donation_type: DonationType = Field(..., description="Type of donation: MONEY or MATERIAL")

    # Monetary fields
    amount: Optional[float] = Field(None, description="Monetary contribution amount", examples=[500.0])

    # Material fields
    item_name: Optional[str] = Field(None, description="Name of the physical goods", examples=["First Aid Kits"])
    quantity: Optional[float] = Field(None, description="Quantity of physical goods", examples=[100.0])
    unit: Optional[str] = Field(None, description="Unit of measurement", examples=["boxes"])

    notes: Optional[str] = Field(None, description="Optional delivery or pledge notes")

    @model_validator(mode="after")
    def validate_donation_fields(self) -> "DonationCreate":
        if self.donation_type == DonationType.MONEY:
            if self.amount is None or self.amount <= 0:
                raise ValueError("For MONEY donations, amount is required and must be greater than 0")
        elif self.donation_type == DonationType.MATERIAL:
            if not self.item_name or not self.item_name.strip():
                raise ValueError("For MATERIAL donations, item_name is required")
            if self.quantity is None or self.quantity <= 0:
                raise ValueError("For MATERIAL donations, quantity is required and must be greater than 0")
            if not self.unit or not self.unit.strip():
                raise ValueError("For MATERIAL donations, unit is required")
        return self


class DonationUpdate(BaseModel):
    """
    Schema for updating donation details while in PLEDGED status.
    """
    amount: Optional[float] = Field(None, description="Updated monetary amount")
    item_name: Optional[str] = Field(None, min_length=1)
    quantity: Optional[float] = Field(None, description="Updated item quantity")
    unit: Optional[str] = Field(None, min_length=1)
    notes: Optional[str] = None

    @model_validator(mode="after")
    def validate_positive_values(self) -> "DonationUpdate":
        if self.amount is not None and self.amount <= 0:
            raise ValueError("Amount must be greater than 0")
        if self.quantity is not None and self.quantity <= 0:
            raise ValueError("Quantity must be greater than 0")
        return self


class DonationStatusUpdate(BaseModel):
    """
    Schema for Staff/Admin to transition donation lifecycle status.
    """
    status: DonationStatus = Field(..., description="Target status: RECEIVED or CANCELLED")


class DonationResponse(BaseModel):
    """
    Public representation of a donation record.
    """
    id: int
    donor_id: int
    disaster_id: int
    donation_type: DonationType
    amount: Optional[float] = None
    item_name: Optional[str] = None
    quantity: Optional[float] = None
    unit: Optional[str] = None
    status: DonationStatus
    notes: Optional[str] = None
    received_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
