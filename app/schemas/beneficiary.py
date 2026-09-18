"""
Beneficiary Pydantic Schemas.

Defines request validation and response models for beneficiary registration,
demographic data updates, and verification status lifecycle.
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict, field_validator
from app.models.beneficiary import VulnerabilityCategory, RegistrationStatus


class BeneficiaryBase(BaseModel):
    """Shared attributes for beneficiary records."""
    name: str = Field(..., min_length=1, max_length=150, examples=["Sunita Devi"])
    contact_number: str = Field(..., min_length=5, max_length=50, examples=["+91-9876543210"])
    address: str = Field(..., min_length=1, max_length=500, examples=["Village Rampur, Ward 3"])
    household_size: int = Field(..., gt=0, description="Household size must be at least 1", examples=[4])
    vulnerability_category: VulnerabilityCategory = Field(
        default=VulnerabilityCategory.GENERAL,
        examples=[VulnerabilityCategory.GENERAL],
    )

    @field_validator("name", "contact_number", "address")
    @classmethod
    def validate_non_empty_strings(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Field cannot be empty or whitespace only")
        return v.strip()


class BeneficiaryCreate(BeneficiaryBase):
    """
    Schema for registering a new beneficiary under a disaster relief operation.
    Initial registration status is automatically set to PENDING by the server.
    """
    disaster_id: int = Field(..., description="ID of the disaster this beneficiary is registered under")


class BeneficiaryUpdate(BaseModel):
    """
    Schema for updating existing beneficiary information.
    All fields are optional for partial updates.
    """
    name: Optional[str] = Field(None, min_length=1, max_length=150)
    contact_number: Optional[str] = Field(None, min_length=5, max_length=50)
    address: Optional[str] = Field(None, min_length=1, max_length=500)
    household_size: Optional[int] = Field(None, gt=0)
    vulnerability_category: Optional[VulnerabilityCategory] = None

    @field_validator("name", "contact_number", "address")
    @classmethod
    def validate_optional_strings(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            if not v.strip():
                raise ValueError("Field cannot be empty or whitespace only")
            return v.strip()
        return v


class BeneficiaryStatusUpdate(BaseModel):
    """
    Schema for updating the verification lifecycle status of a beneficiary.
    Valid transitions:
    - PENDING -> VERIFIED
    - PENDING -> INACTIVE
    - VERIFIED -> INACTIVE
    """
    status: RegistrationStatus = Field(..., description="Target registration status")


class BeneficiaryResponse(BeneficiaryBase):
    """
    Public response representation of a registered beneficiary.
    Includes calculated eligibility (True only when VERIFIED).
    """
    id: int
    disaster_id: int
    registration_status: RegistrationStatus
    registered_by_id: Optional[int] = None
    is_eligible: bool = Field(
        ...,
        description="True only if registration_status == VERIFIED; gates resource allocation",
    )
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
