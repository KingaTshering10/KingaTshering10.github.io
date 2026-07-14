import uuid
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.domain.enums import ContactMethod, VerificationStatus


class FarmerProfileCreate(BaseModel):
    display_name: str = Field(min_length=2, max_length=120)
    farmer_registration_reference: str | None = Field(default=None, max_length=80)
    primary_phone: str | None = Field(default=None, max_length=32)
    preferred_contact_method: ContactMethod = ContactMethod.PHONE
    notes: str | None = None


class FarmerProfileOut(FarmerProfileCreate):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    farmer_group_id: uuid.UUID | None
    membership_status: str
    verification_status: VerificationStatus


class FarmCreate(BaseModel):
    farm_name: str = Field(min_length=2, max_length=120)
    dzongkhag: str = Field(min_length=2, max_length=60)
    gewog: str | None = Field(default=None, max_length=60)
    village: str | None = Field(default=None, max_length=120)
    latitude: Decimal | None = Field(default=None, ge=-90, le=90)
    longitude: Decimal | None = Field(default=None, ge=-180, le=180)
    road_access_notes: str | None = None


class FarmOut(FarmCreate):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    farmer_id: uuid.UUID
    is_active: bool


class FarmerGroupCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    registration_reference: str | None = Field(default=None, max_length=80)
    dzongkhag: str = Field(min_length=2, max_length=60)
    gewog: str | None = Field(default=None, max_length=60)
    default_collection_point_id: uuid.UUID | None = None


class FarmerGroupOut(FarmerGroupCreate):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    coordinator_user_id: uuid.UUID | None
    verification_status: VerificationStatus
    is_active: bool


class MembershipRequest(BaseModel):
    farmer_group_id: uuid.UUID


class VerificationDecision(BaseModel):
    approve: bool
    reason: str | None = Field(default=None, max_length=300)
