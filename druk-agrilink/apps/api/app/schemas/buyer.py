import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.domain.enums import BuyerOrgType, OrderStatus, Unit, VerificationStatus


class BuyerOrgCreate(BaseModel):
    name: str = Field(min_length=2, max_length=160)
    organization_type: BuyerOrgType
    registration_reference: str | None = Field(default=None, max_length=80)
    billing_contact: str | None = Field(default=None, max_length=200)
    delivery_contact: str | None = Field(default=None, max_length=200)
    payment_terms_days: int = Field(default=30, ge=0, le=180)


class BuyerOrgOut(BuyerOrgCreate):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    verification_status: VerificationStatus
    is_active: bool


class OrderItemCreate(BaseModel):
    product_id: uuid.UUID
    variety_id: uuid.UUID | None = None
    required_quantity: Decimal = Field(gt=0, le=Decimal("1000000"))
    unit: Unit = Unit.KG
    minimum_grade_id: uuid.UUID | None = None
    offered_unit_price: Decimal = Field(gt=0, le=Decimal("100000"))
    maximum_unit_price: Decimal | None = Field(default=None, gt=0, le=Decimal("100000"))
    packaging_requirement: str | None = Field(default=None, max_length=120)

    @model_validator(mode="after")
    def validate_prices(self) -> "OrderItemCreate":
        if self.maximum_unit_price is not None and self.maximum_unit_price < self.offered_unit_price:
            raise ValueError("maximum_unit_price must be at least offered_unit_price")
        return self


class OrderCreate(BaseModel):
    delivery_location_id: uuid.UUID
    required_delivery_date: date
    payment_terms: str | None = Field(default=None, max_length=120)
    special_instructions: str | None = None
    items: list[OrderItemCreate] = Field(min_length=1, max_length=20)
    save_as_draft: bool = True


class OrderItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    product_id: uuid.UUID
    variety_id: uuid.UUID | None
    required_quantity: Decimal
    unit: Unit
    minimum_grade_id: uuid.UUID | None
    offered_unit_price: Decimal
    maximum_unit_price: Decimal | None
    packaging_requirement: str | None
    accepted_quantity: Decimal | None


class OrderOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    buyer_organization_id: uuid.UUID
    delivery_location_id: uuid.UUID
    required_delivery_date: date
    order_status: OrderStatus
    payment_terms: str | None
    special_instructions: str | None
    created_at: datetime
    updated_at: datetime


class OrderDetailOut(OrderOut):
    items: list[OrderItemOut] = []
