"""Reference/master data: Bhutan locations, products, varieties, grades."""

import uuid
from decimal import Decimal

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, SafeNumeric, TimestampMixin, UUIDPrimaryKeyMixin
from app.domain.enums import LocationType, StorageCategory, Unit


class Location(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "locations"

    name: Mapped[str] = mapped_column(String(120), nullable=False)
    location_type: Mapped[LocationType] = mapped_column(String(30), nullable=False)
    country: Mapped[str] = mapped_column(String(60), default="Bhutan", nullable=False)
    dzongkhag: Mapped[str] = mapped_column(String(60), index=True, nullable=False)
    gewog: Mapped[str | None] = mapped_column(String(60), index=True)
    village: Mapped[str | None] = mapped_column(String(120))
    address: Mapped[str | None] = mapped_column(Text)
    landmark: Mapped[str | None] = mapped_column(String(200))
    latitude: Mapped[Decimal | None] = mapped_column(SafeNumeric(9, 6))
    longitude: Mapped[Decimal | None] = mapped_column(SafeNumeric(9, 6))
    road_access_notes: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class Product(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "products"

    name: Mapped[str] = mapped_column(String(80), unique=True, nullable=False)
    local_name: Mapped[str | None] = mapped_column(String(120))  # Dzongkha name where verified
    category: Mapped[str] = mapped_column(String(60), nullable=False)  # vegetable, fruit, grain, spice…
    default_unit: Mapped[Unit] = mapped_column(String(12), default=Unit.KG, nullable=False)
    storage_category: Mapped[StorageCategory] = mapped_column(
        String(20), default=StorageCategory.AMBIENT, nullable=False
    )
    shelf_life_days: Mapped[int] = mapped_column(Integer, default=7, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class ProductVariety(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "product_varieties"

    product_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("products.id"), index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)


class QualityGrade(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "quality_grades"

    product_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("products.id"), index=True, nullable=False)
    code: Mapped[str] = mapped_column(String(12), nullable=False)
    name: Mapped[str] = mapped_column(String(60), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)  # lower = better
