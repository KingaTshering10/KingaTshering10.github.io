import uuid
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.domain.enums import LocationType, StorageCategory, Unit


class LocationCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    location_type: LocationType
    dzongkhag: str = Field(min_length=2, max_length=60)
    gewog: str | None = Field(default=None, max_length=60)
    village: str | None = Field(default=None, max_length=120)
    address: str | None = None
    landmark: str | None = Field(default=None, max_length=200)
    latitude: Decimal | None = Field(default=None, ge=-90, le=90)
    longitude: Decimal | None = Field(default=None, ge=-180, le=180)
    road_access_notes: str | None = None


class LocationOut(LocationCreate):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    country: str
    is_active: bool


class ProductCreate(BaseModel):
    name: str = Field(min_length=2, max_length=80)
    local_name: str | None = Field(default=None, max_length=120)
    category: str = Field(min_length=2, max_length=60)
    default_unit: Unit = Unit.KG
    storage_category: StorageCategory = StorageCategory.AMBIENT
    shelf_life_days: int = Field(default=7, ge=1, le=365)


class ProductOut(ProductCreate):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    is_active: bool


class VarietyCreate(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    description: str | None = None


class VarietyOut(VarietyCreate):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    product_id: uuid.UUID


class GradeCreate(BaseModel):
    code: str = Field(min_length=1, max_length=12)
    name: str = Field(min_length=1, max_length=60)
    description: str | None = None
    sort_order: int = Field(default=0, ge=0)


class GradeOut(GradeCreate):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    product_id: uuid.UUID
