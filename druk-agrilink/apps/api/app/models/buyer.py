import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy import Boolean, Date, ForeignKey, Integer, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, SafeNumeric, TimestampMixin, UUIDPrimaryKeyMixin
from app.domain.enums import BuyerOrgType, OrderStatus, Unit, VerificationStatus


class BuyerOrganization(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "buyer_organizations"

    name: Mapped[str] = mapped_column(String(160), unique=True, nullable=False)
    organization_type: Mapped[BuyerOrgType] = mapped_column(String(30), nullable=False)
    registration_reference: Mapped[str | None] = mapped_column(String(80))
    verification_status: Mapped[VerificationStatus] = mapped_column(
        String(20), default=VerificationStatus.PENDING, nullable=False
    )
    billing_contact: Mapped[str | None] = mapped_column(String(200))
    delivery_contact: Mapped[str | None] = mapped_column(String(200))
    payment_terms_days: Mapped[int] = mapped_column(Integer, default=30, nullable=False)
    owner_user_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("users.id"), index=True, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class BuyerOrder(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "buyer_orders"

    buyer_organization_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("buyer_organizations.id"), index=True, nullable=False
    )
    delivery_location_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("locations.id"), nullable=False)
    required_delivery_date: Mapped[date] = mapped_column(Date, nullable=False)
    order_status: Mapped[OrderStatus] = mapped_column(
        String(30), default=OrderStatus.DRAFT, index=True, nullable=False
    )
    payment_terms: Mapped[str | None] = mapped_column(String(120))
    special_instructions: Mapped[str | None] = mapped_column(Text)
    created_by: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("users.id"), nullable=False)
    approved_by: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("users.id"))


class BuyerOrderItem(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "buyer_order_items"

    buyer_order_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("buyer_orders.id"), index=True, nullable=False
    )
    product_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("products.id"), index=True, nullable=False)
    variety_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("product_varieties.id"))
    required_quantity: Mapped[Decimal] = mapped_column(SafeNumeric(12, 2), nullable=False)
    unit: Mapped[Unit] = mapped_column(String(12), default=Unit.KG, nullable=False)
    minimum_grade_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("quality_grades.id"))
    offered_unit_price: Mapped[Decimal] = mapped_column(SafeNumeric(10, 2), nullable=False)
    maximum_unit_price: Mapped[Decimal | None] = mapped_column(SafeNumeric(10, 2))
    packaging_requirement: Mapped[str | None] = mapped_column(String(120))
    accepted_quantity: Mapped[Decimal | None] = mapped_column(SafeNumeric(12, 2))
