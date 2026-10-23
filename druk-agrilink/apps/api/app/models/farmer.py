import uuid
from decimal import Decimal

from sqlalchemy import Boolean, ForeignKey, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, SafeNumeric, TimestampMixin, UUIDPrimaryKeyMixin
from app.domain.enums import ContactMethod, VerificationStatus


class FarmerGroup(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "farmer_groups"

    name: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    registration_reference: Mapped[str | None] = mapped_column(String(80))
    dzongkhag: Mapped[str] = mapped_column(String(60), nullable=False)
    gewog: Mapped[str | None] = mapped_column(String(60))
    coordinator_user_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("users.id"), index=True)
    verification_status: Mapped[VerificationStatus] = mapped_column(
        String(20), default=VerificationStatus.PENDING, nullable=False
    )
    default_collection_point_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("locations.id"))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class FarmerProfile(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "farmer_profiles"

    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("users.id"), unique=True, index=True, nullable=False
    )
    display_name: Mapped[str] = mapped_column(String(120), nullable=False)
    farmer_registration_reference: Mapped[str | None] = mapped_column(String(80))
    farmer_group_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("farmer_groups.id"), index=True
    )
    membership_status: Mapped[str] = mapped_column(String(20), default="none", nullable=False)
    # none | requested | member
    primary_phone: Mapped[str | None] = mapped_column(String(32))
    preferred_contact_method: Mapped[ContactMethod] = mapped_column(
        String(12), default=ContactMethod.PHONE, nullable=False
    )
    verification_status: Mapped[VerificationStatus] = mapped_column(
        String(20), default=VerificationStatus.PENDING, nullable=False
    )
    notes: Mapped[str | None] = mapped_column(Text)


class Farm(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "farms"

    farmer_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("farmer_profiles.id"), index=True, nullable=False
    )
    farm_name: Mapped[str] = mapped_column(String(120), nullable=False)
    dzongkhag: Mapped[str] = mapped_column(String(60), nullable=False)
    gewog: Mapped[str | None] = mapped_column(String(60))
    village: Mapped[str | None] = mapped_column(String(120))
    latitude: Mapped[Decimal | None] = mapped_column(SafeNumeric(9, 6))
    longitude: Mapped[Decimal | None] = mapped_column(SafeNumeric(9, 6))
    road_access_notes: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
