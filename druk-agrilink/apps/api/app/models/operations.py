"""Collection, delivery, payments, notifications, disputes, audit."""

import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import JSON, Boolean, Date, DateTime, ForeignKey, Integer, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, SafeNumeric, TimestampMixin, UUIDPrimaryKeyMixin, utcnow
from app.domain.enums import (
    DisputeCategory,
    DisputeStatus,
    NotificationChannel,
    NotificationStatus,
    PartyType,
    PaymentStatus,
)


class CollectionRecord(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "collection_records"

    shipment_stop_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("shipment_stops.id"), index=True, nullable=False
    )
    farmer_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("farmer_profiles.id"), index=True, nullable=False
    )
    harvest_listing_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("harvest_listings.id"), index=True, nullable=False
    )
    expected_quantity: Mapped[Decimal] = mapped_column(SafeNumeric(12, 2), nullable=False)
    presented_quantity: Mapped[Decimal] = mapped_column(SafeNumeric(12, 2), nullable=False)
    accepted_quantity: Mapped[Decimal] = mapped_column(SafeNumeric(12, 2), nullable=False)
    rejected_quantity: Mapped[Decimal] = mapped_column(SafeNumeric(12, 2), nullable=False)
    quality_grade_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("quality_grades.id"))
    unit_price: Mapped[Decimal] = mapped_column(SafeNumeric(10, 2), nullable=False)
    gross_amount: Mapped[Decimal] = mapped_column(SafeNumeric(14, 2), nullable=False)
    transport_deduction: Mapped[Decimal] = mapped_column(
        SafeNumeric(12, 2), default=Decimal("0"), nullable=False
    )
    platform_fee: Mapped[Decimal] = mapped_column(SafeNumeric(12, 2), default=Decimal("0"), nullable=False)
    other_deduction: Mapped[Decimal] = mapped_column(SafeNumeric(12, 2), default=Decimal("0"), nullable=False)
    other_deduction_reason: Mapped[str | None] = mapped_column(String(200))
    net_amount_due: Mapped[Decimal] = mapped_column(SafeNumeric(14, 2), nullable=False)
    rejection_reason: Mapped[str | None] = mapped_column(String(300))
    farmer_confirmation: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    coordinator_confirmation: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    photo_urls: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    receipt_number: Mapped[str] = mapped_column(String(24), unique=True, index=True, nullable=False)
    row_version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)


class DeliveryRecord(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "delivery_records"

    shipment_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("shipments.id"), index=True, nullable=False
    )
    buyer_order_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("buyer_orders.id"), index=True, nullable=False
    )
    delivered_quantity: Mapped[Decimal] = mapped_column(SafeNumeric(12, 2), nullable=False)
    accepted_quantity: Mapped[Decimal] = mapped_column(SafeNumeric(12, 2), nullable=False)
    rejected_quantity: Mapped[Decimal] = mapped_column(SafeNumeric(12, 2), nullable=False)
    arrival_condition: Mapped[str | None] = mapped_column(String(200))
    rejection_reason: Mapped[str | None] = mapped_column(String(300))
    buyer_confirmation: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    transporter_confirmation: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    proof_of_delivery_urls: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    discrepancy_flag: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    discrepancy_note: Mapped[str | None] = mapped_column(String(300))
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class PaymentRecord(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "payment_records"

    payer_type: Mapped[PartyType] = mapped_column(String(30), nullable=False)
    payer_id: Mapped[uuid.UUID | None] = mapped_column(Uuid)
    recipient_type: Mapped[PartyType] = mapped_column(String(30), nullable=False)
    recipient_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, index=True)
    related_order_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("buyer_orders.id"), index=True
    )
    related_collection_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("collection_records.id"), index=True
    )
    amount: Mapped[Decimal] = mapped_column(SafeNumeric(14, 2), nullable=False)
    amount_paid: Mapped[Decimal] = mapped_column(SafeNumeric(14, 2), default=Decimal("0"), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="BTN", nullable=False)
    due_date: Mapped[date | None] = mapped_column(Date)
    status: Mapped[PaymentStatus] = mapped_column(
        String(20), default=PaymentStatus.PENDING, index=True, nullable=False
    )
    payment_method: Mapped[str | None] = mapped_column(String(40))
    payment_reference: Mapped[str | None] = mapped_column(String(120))
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    recorded_by: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("users.id"))


class Notification(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "notifications"

    user_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("users.id"), index=True, nullable=False)
    channel: Mapped[NotificationChannel] = mapped_column(String(12), nullable=False)
    template_key: Mapped[str] = mapped_column(String(60), index=True, nullable=False)
    subject: Mapped[str] = mapped_column(String(200), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[NotificationStatus] = mapped_column(
        String(12), default=NotificationStatus.QUEUED, nullable=False
    )
    scheduled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    failure_reason: Mapped[str | None] = mapped_column(String(200))


class NotificationPreference(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "notification_preferences"

    user_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("users.id"), unique=True, nullable=False)
    email_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    sms_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    push_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    # in-app and essential security/transaction notifications cannot be disabled


class Dispute(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "disputes"

    raised_by: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("users.id"), index=True, nullable=False)
    related_entity_type: Mapped[str] = mapped_column(String(40), nullable=False)
    related_entity_id: Mapped[uuid.UUID] = mapped_column(Uuid, index=True, nullable=False)
    category: Mapped[DisputeCategory] = mapped_column(String(30), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[DisputeStatus] = mapped_column(
        String(20), default=DisputeStatus.OPEN, index=True, nullable=False
    )
    assigned_to: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("users.id"))
    resolution: Mapped[str | None] = mapped_column(Text)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class AuditLog(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "audit_logs"

    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("users.id"), index=True)
    action: Mapped[str] = mapped_column(String(60), index=True, nullable=False)
    entity_type: Mapped[str] = mapped_column(String(40), nullable=False)
    entity_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, index=True)
    before_state: Mapped[dict | None] = mapped_column(JSON)
    after_state: Mapped[dict | None] = mapped_column(JSON)
    reason: Mapped[str | None] = mapped_column(String(300))
    ip_address: Mapped[str | None] = mapped_column(String(45))
    user_agent: Mapped[str | None] = mapped_column(String(200))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
