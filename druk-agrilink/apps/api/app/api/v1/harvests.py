"""Harvest listings: forecast → confirm → allocate lifecycle with revision
history, availability accounting, and optimistic concurrency for offline sync."""

import uuid
from decimal import Decimal

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select

from app.core import policies
from app.core.deps import CurrentUser, DbSession, require_roles
from app.core.errors import ConflictError, NotFoundError, ValidationFailure
from app.domain.enums import HarvestStatus, Role
from app.domain.state_machine import transition_harvest
from app.models import Farm, FarmerProfile, HarvestListing, HarvestRevision, Product, User
from app.schemas.harvest import (
    HarvestConfirm,
    HarvestCreate,
    HarvestOut,
    HarvestRevisionOut,
    HarvestUpdate,
)

router = APIRouter(prefix="/harvest-listings", tags=["harvests"])


def _record_revision(db, listing, field: str, old, new, user_id) -> None:
    if str(old) != str(new):
        db.add(
            HarvestRevision(
                harvest_listing_id=listing.id,
                field=field,
                old_value=str(old) if old is not None else None,
                new_value=str(new) if new is not None else None,
                changed_by=user_id,
            )
        )


def _check_row_version(listing: HarvestListing, expected: int | None) -> None:
    if expected is not None and expected != listing.row_version:
        raise ConflictError(
            "This listing was changed elsewhere since you last loaded it.",
            code="CONFLICT_STALE_VERSION",
            extra={
                "server_row_version": listing.row_version,
                "server_state": {
                    "forecast_quantity": str(listing.forecast_quantity),
                    "confirmed_quantity": str(listing.confirmed_quantity)
                    if listing.confirmed_quantity is not None
                    else None,
                    "harvest_start_date": listing.harvest_start_date.isoformat(),
                    "harvest_end_date": listing.harvest_end_date.isoformat(),
                    "minimum_unit_price": str(listing.minimum_unit_price),
                    "status": str(listing.status),
                    "updated_at": listing.updated_at.isoformat(),
                },
            },
        )


@router.post("", response_model=HarvestOut, status_code=201)
def create_listing(
    payload: HarvestCreate,
    db: DbSession,
    user: User = Depends(require_roles(Role.FARMER, Role.COORDINATOR)),
):
    if user.role == Role.COORDINATOR:
        # Coordinators may assist farmers with listings for farms in their groups.
        farm = db.get(Farm, payload.farm_id)
        if farm is None:
            raise NotFoundError("Farm not found.")
        profile = db.get(FarmerProfile, farm.farmer_id)
        if profile is None:
            raise NotFoundError("Farm not found.")
        from app.models import FarmerGroup

        group = db.get(FarmerGroup, profile.farmer_group_id) if profile.farmer_group_id else None
        policies.require_group_coordinator(db, user, group)
    else:
        profile = policies.get_farmer_profile(db, user)
        farm = db.get(Farm, payload.farm_id)
        if farm is None or farm.farmer_id != profile.id:
            raise NotFoundError("Farm not found.")

    if db.get(Product, payload.product_id) is None:
        raise ValidationFailure("Unknown product.", field="product_id")

    # Publishing (beyond draft) requires a verified farmer.
    status = HarvestStatus.DRAFT
    if not payload.save_as_draft:
        policies.require_verified(str(profile.verification_status), "Farmer profile")
        status = HarvestStatus.FORECAST

    listing = HarvestListing(
        farmer_id=profile.id,
        farm_id=payload.farm_id,
        product_id=payload.product_id,
        variety_id=payload.variety_id,
        forecast_quantity=payload.forecast_quantity,
        available_quantity=Decimal("0"),
        unit=payload.unit,
        harvest_start_date=payload.harvest_start_date,
        harvest_end_date=payload.harvest_end_date,
        minimum_unit_price=payload.minimum_unit_price,
        expected_grade_id=payload.expected_grade_id,
        packaging_type=payload.packaging_type,
        confidence_level=payload.confidence_level,
        status=status,
        notes=payload.notes,
        created_by=user.id,
    )
    db.add(listing)
    db.commit()
    return listing


@router.get("", response_model=list[HarvestOut])
def my_listings(
    db: DbSession,
    user: CurrentUser,
    status: HarvestStatus | None = Query(None),
):
    if user.role == Role.FARMER:
        profile = policies.get_farmer_profile(db, user)
        query = select(HarvestListing).where(HarvestListing.farmer_id == profile.id)
    elif user.role in (Role.COORDINATOR, Role.ADMIN):
        query = select(HarvestListing)
        if user.role == Role.COORDINATOR:
            group_ids = [g.id for g in policies.coordinator_groups(db, user)]
            member_ids = select(FarmerProfile.id).where(FarmerProfile.farmer_group_id.in_(group_ids))
            query = query.where(HarvestListing.farmer_id.in_(member_ids))
    else:
        return []
    if status:
        query = query.where(HarvestListing.status == status)
    return db.scalars(query.order_by(HarvestListing.created_at.desc())).all()


@router.get("/{listing_id}", response_model=HarvestOut)
def get_listing(listing_id: uuid.UUID, db: DbSession, user: CurrentUser):
    return policies.can_view_listing(db, user, db.get(HarvestListing, listing_id))


@router.get("/{listing_id}/revisions", response_model=list[HarvestRevisionOut])
def listing_revisions(listing_id: uuid.UUID, db: DbSession, user: CurrentUser):
    listing = policies.can_view_listing(db, user, db.get(HarvestListing, listing_id))
    return db.scalars(
        select(HarvestRevision)
        .where(HarvestRevision.harvest_listing_id == listing.id)
        .order_by(HarvestRevision.created_at)
    ).all()


@router.patch("/{listing_id}", response_model=HarvestOut)
def update_listing(listing_id: uuid.UUID, payload: HarvestUpdate, db: DbSession, user: CurrentUser):
    listing = policies.can_edit_listing(db, user, db.get(HarvestListing, listing_id))
    if listing.status not in (
        HarvestStatus.DRAFT,
        HarvestStatus.FORECAST,
        HarvestStatus.CONFIRMED,
    ):
        raise ConflictError("Listings can only be edited before allocation.", code="LISTING_LOCKED")
    _check_row_version(listing, payload.expected_row_version)

    updates = payload.model_dump(exclude_unset=True, exclude={"expected_row_version"})
    if "harvest_start_date" in updates or "harvest_end_date" in updates:
        start = updates.get("harvest_start_date", listing.harvest_start_date)
        end = updates.get("harvest_end_date", listing.harvest_end_date)
        if end < start:
            raise ValidationFailure(
                "harvest_end_date must not be before harvest_start_date", field="harvest_end_date"
            )
    for field, value in updates.items():
        _record_revision(db, listing, field, getattr(listing, field), value, user.id)
        setattr(listing, field, value)
    if (
        "forecast_quantity" in updates
        and listing.status == HarvestStatus.CONFIRMED
        and listing.confirmed_quantity is not None
        and listing.confirmed_quantity > listing.forecast_quantity
    ):
        raise ValidationFailure(
            "Confirmed quantity cannot exceed forecast quantity.",
            code="HARVEST_QUANTITY_INVALID",
            field="forecast_quantity",
        )
    listing.row_version += 1
    db.commit()
    return listing


@router.post("/{listing_id}/publish", response_model=HarvestOut)
def publish_listing(listing_id: uuid.UUID, db: DbSession, user: CurrentUser):
    listing = policies.can_edit_listing(db, user, db.get(HarvestListing, listing_id))
    profile = db.get(FarmerProfile, listing.farmer_id)
    assert profile is not None
    policies.require_verified(str(profile.verification_status), "Farmer profile")
    transition_harvest(listing.status, HarvestStatus.FORECAST)
    listing.status = HarvestStatus.FORECAST
    listing.row_version += 1
    db.commit()
    return listing


@router.post("/{listing_id}/confirm", response_model=HarvestOut)
def confirm_listing(listing_id: uuid.UUID, payload: HarvestConfirm, db: DbSession, user: CurrentUser):
    listing = policies.can_edit_listing(db, user, db.get(HarvestListing, listing_id))
    _check_row_version(listing, payload.expected_row_version)
    transition_harvest(listing.status, HarvestStatus.CONFIRMED)
    if payload.confirmed_quantity > listing.forecast_quantity * Decimal("1.5"):
        raise ValidationFailure(
            "Confirmed quantity is implausibly higher than the forecast; update the forecast first.",
            code="HARVEST_QUANTITY_INVALID",
            field="confirmed_quantity",
        )
    _record_revision(
        db, listing, "confirmed_quantity", listing.confirmed_quantity, payload.confirmed_quantity, user.id
    )
    listing.confirmed_quantity = payload.confirmed_quantity
    listing.available_quantity = payload.confirmed_quantity
    listing.status = HarvestStatus.CONFIRMED
    listing.verified_by = user.id if user.role in (Role.COORDINATOR, Role.ADMIN) else None
    listing.row_version += 1
    db.commit()
    return listing


@router.post("/{listing_id}/cancel", response_model=HarvestOut)
def cancel_listing(listing_id: uuid.UUID, db: DbSession, user: CurrentUser):
    listing = policies.can_edit_listing(db, user, db.get(HarvestListing, listing_id))
    transition_harvest(listing.status, HarvestStatus.CANCELLED)
    listing.status = HarvestStatus.CANCELLED
    listing.available_quantity = Decimal("0")
    listing.row_version += 1
    db.commit()
    return listing
