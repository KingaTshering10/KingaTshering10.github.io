import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, SafeNumeric, TimestampMixin, UUIDPrimaryKeyMixin
from app.domain.enums import ShipmentStatus, StopStatus, StopType, VehicleType, VerificationStatus


class TransportProvider(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "transport_providers"

    organization_name: Mapped[str] = mapped_column(String(160), unique=True, nullable=False)
    contact_name: Mapped[str | None] = mapped_column(String(120))
    phone: Mapped[str | None] = mapped_column(String(32))
    registration_reference: Mapped[str | None] = mapped_column(String(80))
    verification_status: Mapped[VerificationStatus] = mapped_column(
        String(20), default=VerificationStatus.PENDING, nullable=False
    )
    service_dzongkhags: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    owner_user_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("users.id"), index=True, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class Vehicle(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "vehicles"

    transport_provider_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("transport_providers.id"), index=True, nullable=False
    )
    registration_number: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    vehicle_type: Mapped[VehicleType] = mapped_column(String(30), nullable=False)
    capacity_kg: Mapped[Decimal] = mapped_column(SafeNumeric(10, 2), nullable=False)
    capacity_volume_m3: Mapped[Decimal | None] = mapped_column(SafeNumeric(8, 2))
    has_refrigeration: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    supported_product_categories: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    is_available: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    current_location_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("locations.id"))
    verification_status: Mapped[VerificationStatus] = mapped_column(
        String(20), default=VerificationStatus.PENDING, nullable=False
    )


class Shipment(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "shipments"

    match_proposal_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("match_proposals.id"), index=True, nullable=False
    )
    vehicle_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("vehicles.id"), index=True)
    driver_name: Mapped[str | None] = mapped_column(String(120))
    driver_phone: Mapped[str | None] = mapped_column(String(32))
    planned_pickup_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    planned_delivery_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    actual_pickup_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    actual_delivery_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    planned_distance_km: Mapped[Decimal | None] = mapped_column(SafeNumeric(8, 1))
    route_estimate_method: Mapped[str | None] = mapped_column(String(40))  # e.g. approximate_local
    estimated_transport_cost: Mapped[Decimal | None] = mapped_column(SafeNumeric(12, 2))
    actual_transport_cost: Mapped[Decimal | None] = mapped_column(SafeNumeric(12, 2))
    status: Mapped[ShipmentStatus] = mapped_column(
        String(30), default=ShipmentStatus.PLANNING, index=True, nullable=False
    )
    incident_notes: Mapped[str | None] = mapped_column(Text)


class ShipmentStop(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "shipment_stops"

    shipment_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("shipments.id"), index=True, nullable=False
    )
    stop_type: Mapped[StopType] = mapped_column(String(12), nullable=False)
    sequence_number: Mapped[int] = mapped_column(Integer, nullable=False)
    location_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("locations.id"))
    farmer_group_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("farmer_groups.id"))
    farmer_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("farmer_profiles.id"))
    planned_arrival: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    actual_arrival: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    planned_quantity: Mapped[Decimal | None] = mapped_column(SafeNumeric(12, 2))
    collected_quantity: Mapped[Decimal | None] = mapped_column(SafeNumeric(12, 2))
    status: Mapped[StopStatus] = mapped_column(String(12), default=StopStatus.PLANNED, nullable=False)
