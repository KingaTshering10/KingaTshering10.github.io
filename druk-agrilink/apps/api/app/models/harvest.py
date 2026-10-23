import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Date, DateTime, ForeignKey, Integer, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, SafeNumeric, TimestampMixin, UUIDPrimaryKeyMixin, utcnow
from app.domain.enums import ConfidenceLevel, HarvestStatus, Unit


class HarvestListing(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "harvest_listings"

    farmer_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("farmer_profiles.id"), index=True, nullable=False
    )
    farm_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("farms.id"), index=True, nullable=False)
    product_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("products.id"), index=True, nullable=False)
    variety_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("product_varieties.id"))

    forecast_quantity: Mapped[Decimal] = mapped_column(SafeNumeric(12, 2), nullable=False)
    confirmed_quantity: Mapped[Decimal | None] = mapped_column(SafeNumeric(12, 2))
    available_quantity: Mapped[Decimal] = mapped_column(
        SafeNumeric(12, 2), default=Decimal("0"), nullable=False
    )
    collected_quantity: Mapped[Decimal | None] = mapped_column(SafeNumeric(12, 2))
    accepted_quantity: Mapped[Decimal | None] = mapped_column(SafeNumeric(12, 2))
    unit: Mapped[Unit] = mapped_column(String(12), default=Unit.KG, nullable=False)

    harvest_start_date: Mapped[date] = mapped_column(Date, nullable=False)
    harvest_end_date: Mapped[date] = mapped_column(Date, nullable=False)
    minimum_unit_price: Mapped[Decimal] = mapped_column(SafeNumeric(10, 2), nullable=False)
    expected_grade_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("quality_grades.id"))
    packaging_type: Mapped[str | None] = mapped_column(String(60))
    confidence_level: Mapped[ConfidenceLevel] = mapped_column(
        String(10), default=ConfidenceLevel.MEDIUM, nullable=False
    )
    status: Mapped[HarvestStatus] = mapped_column(
        String(30), default=HarvestStatus.DRAFT, index=True, nullable=False
    )
    notes: Mapped[str | None] = mapped_column(Text)
    created_by: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("users.id"), nullable=False)
    verified_by: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("users.id"))
    # optimistic concurrency for offline sync — incremented on every write
    row_version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)


class HarvestRevision(Base, UUIDPrimaryKeyMixin):
    """Append-only history of quantity/date changes."""

    __tablename__ = "harvest_revisions"

    harvest_listing_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("harvest_listings.id"), index=True, nullable=False
    )
    field: Mapped[str] = mapped_column(String(40), nullable=False)
    old_value: Mapped[str | None] = mapped_column(String(120))
    new_value: Mapped[str | None] = mapped_column(String(120))
    changed_by: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
