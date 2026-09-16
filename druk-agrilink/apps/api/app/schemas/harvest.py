import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.domain.enums import ConfidenceLevel, HarvestStatus, Unit


class HarvestCreate(BaseModel):
    farm_id: uuid.UUID
    product_id: uuid.UUID
    variety_id: uuid.UUID | None = None
    forecast_quantity: Decimal = Field(gt=0, le=Decimal("1000000"))
    unit: Unit = Unit.KG
    harvest_start_date: date
    harvest_end_date: date
    minimum_unit_price: Decimal = Field(ge=0, le=Decimal("100000"))
    expected_grade_id: uuid.UUID | None = None
    packaging_type: str | None = Field(default=None, max_length=60)
    confidence_level: ConfidenceLevel = ConfidenceLevel.MEDIUM
    notes: str | None = None
    save_as_draft: bool = False

    @model_validator(mode="after")
    def validate_dates(self) -> "HarvestCreate":
        if self.harvest_end_date < self.harvest_start_date:
            raise ValueError("harvest_end_date must not be before harvest_start_date")
        return self


class HarvestUpdate(BaseModel):
    forecast_quantity: Decimal | None = Field(default=None, gt=0, le=Decimal("1000000"))
    harvest_start_date: date | None = None
    harvest_end_date: date | None = None
    minimum_unit_price: Decimal | None = Field(default=None, ge=0)
    confidence_level: ConfidenceLevel | None = None
    packaging_type: str | None = Field(default=None, max_length=60)
    notes: str | None = None
    expected_row_version: int | None = Field(
        default=None,
        description="Optimistic-concurrency guard for offline sync; mismatch returns 409.",
    )


class HarvestConfirm(BaseModel):
    confirmed_quantity: Decimal = Field(gt=0, le=Decimal("1000000"))
    expected_row_version: int | None = None


class HarvestOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    farmer_id: uuid.UUID
    farm_id: uuid.UUID
    product_id: uuid.UUID
    variety_id: uuid.UUID | None
    forecast_quantity: Decimal
    confirmed_quantity: Decimal | None
    available_quantity: Decimal
    collected_quantity: Decimal | None
    accepted_quantity: Decimal | None
    unit: Unit
    harvest_start_date: date
    harvest_end_date: date
    minimum_unit_price: Decimal
    expected_grade_id: uuid.UUID | None
    packaging_type: str | None
    confidence_level: ConfidenceLevel
    status: HarvestStatus
    notes: str | None
    row_version: int
    created_at: datetime
    updated_at: datetime


class HarvestRevisionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    field: str
    old_value: str | None
    new_value: str | None
    changed_by: uuid.UUID
    created_at: datetime
