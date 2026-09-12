"""Collection records (with digital receipts) and delivery records."""

import uuid
from decimal import Decimal

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import select

from app.core import policies
from app.core.deps import CurrentUser, DbSession, require_roles
from app.core.errors import ConflictError, NotFoundError, ValidationFailure
from app.db.base import utcnow
from app.domain.enums import (
    HarvestStatus,
    OrderStatus,
    PartyType,
    PaymentStatus,
    Role,
    ShipmentStatus,
    StopStatus,
    StopType,
)
from app.domain.state_machine import transition_order, transition_shipment
from app.models import (
    BuyerOrder,
    BuyerOrderItem,
    BuyerOrganization,
    CollectionRecord,
    DeliveryRecord,
    FarmerGroup,
    FarmerProfile,
    HarvestListing,
    MatchAllocation,
    MatchProposal,
    PaymentRecord,
    Product,
    Shipment,
    ShipmentStop,
    TransportProvider,
    User,
    Vehicle,
)
from app.services.audit import record_audit
from app.services.notifications import notify
from app.services.settlement import compute_receipt, next_receipt_number, q2

router = APIRouter(tags=["operations"])


# ---------- collection ----------


class CollectionCreate(BaseModel):
    shipment_stop_id: uuid.UUID
    harvest_listing_id: uuid.UUID
    presented_quantity: Decimal = Field(ge=0)
    accepted_quantity: Decimal = Field(ge=0)
    rejected_quantity: Decimal = Field(ge=0)
    quality_grade_id: uuid.UUID | None = None
    unit_price: Decimal = Field(gt=0)
    transport_deduction: Decimal = Field(default=Decimal("0"), ge=0)
    other_deduction: Decimal = Field(default=Decimal("0"), ge=0)
    other_deduction_reason: str | None = Field(default=None, max_length=200)
    rejection_reason: str | None = Field(default=None, max_length=300)
    photo_urls: list[str] = Field(default_factory=list, max_length=5)


def _collection_out(db, record: CollectionRecord) -> dict:
    profile = db.get(FarmerProfile, record.farmer_id)
    listing = db.get(HarvestListing, record.harvest_listing_id)
    product = db.get(Product, listing.product_id) if listing else None
    return {
        "id": str(record.id),
        "receipt_number": record.receipt_number,
        "shipment_stop_id": str(record.shipment_stop_id),
        "farmer_id": str(record.farmer_id),
        "farmer_display_name": profile.display_name if profile else None,
        "harvest_listing_id": str(record.harvest_listing_id),
        "product_name": product.name if product else None,
        "unit": str(listing.unit) if listing else "kg",
        "expected_quantity": str(record.expected_quantity),
        "presented_quantity": str(record.presented_quantity),
        "accepted_quantity": str(record.accepted_quantity),
        "rejected_quantity": str(record.rejected_quantity),
        "unit_price": str(record.unit_price),
        "gross_amount": str(record.gross_amount),
        "transport_deduction": str(record.transport_deduction),
        "platform_fee": str(record.platform_fee),
        "other_deduction": str(record.other_deduction),
        "other_deduction_reason": record.other_deduction_reason,
        "net_amount_due": str(record.net_amount_due),
        "currency": "BTN",
        "rejection_reason": record.rejection_reason,
        "farmer_confirmation": record.farmer_confirmation,
        "coordinator_confirmation": record.coordinator_confirmation,
        "photo_urls": record.photo_urls,
        "created_at": record.created_at.isoformat(),
    }


@router.post("/collections", status_code=201)
def record_collection(
    payload: CollectionCreate,
    db: DbSession,
    user: User = Depends(require_roles(Role.COORDINATOR, Role.ADMIN)),
):
    stop = db.get(ShipmentStop, payload.shipment_stop_id)
    if stop is None or stop.stop_type != StopType.PICKUP:
        raise NotFoundError("Pickup stop not found.")
    shipment = db.get(Shipment, stop.shipment_id)
    assert shipment is not None
    if shipment.status not in (
        ShipmentStatus.COLLECTION_IN_PROGRESS,
        ShipmentStatus.CONFIRMED,
    ):
        raise ConflictError(
            "Collection can only be recorded once the shipment collection has started.",
            code="SHIPMENT_NOT_COLLECTING",
        )
    listing = db.get(HarvestListing, payload.harvest_listing_id)
    if listing is None or (stop.farmer_id is not None and listing.farmer_id != stop.farmer_id):
        raise NotFoundError("Harvest listing not found for this stop.")
    if user.role == Role.COORDINATOR:
        profile = db.get(FarmerProfile, listing.farmer_id)
        group = db.get(FarmerGroup, profile.farmer_group_id) if profile and profile.farmer_group_id else None
        policies.require_group_coordinator(db, user, group)

    if payload.presented_quantity != payload.accepted_quantity + payload.rejected_quantity:
        raise ValidationFailure(
            "presented_quantity must equal accepted_quantity + rejected_quantity.",
            code="QUANTITY_MISMATCH",
            field="presented_quantity",
        )
    existing = db.scalars(
        select(CollectionRecord).where(
            CollectionRecord.shipment_stop_id == stop.id,
            CollectionRecord.harvest_listing_id == listing.id,
        )
    ).first()
    if existing:
        raise ConflictError("A collection record already exists for this stop.", code="ALREADY_RECORDED")

    allocation = db.scalars(
        select(MatchAllocation)
        .join(MatchProposal, MatchAllocation.match_proposal_id == MatchProposal.id)
        .join(Shipment, Shipment.match_proposal_id == MatchProposal.id)
        .where(
            Shipment.id == shipment.id,
            MatchAllocation.harvest_listing_id == listing.id,
        )
    ).first()
    expected = allocation.allocated_quantity if allocation else (stop.planned_quantity or Decimal("0"))

    try:
        amounts = compute_receipt(
            payload.accepted_quantity,
            payload.unit_price,
            payload.transport_deduction,
            payload.other_deduction,
        )
    except ValueError as exc:
        raise ValidationFailure(str(exc), code="DEDUCTIONS_EXCEED_GROSS") from exc

    record = CollectionRecord(
        shipment_stop_id=stop.id,
        farmer_id=listing.farmer_id,
        harvest_listing_id=listing.id,
        expected_quantity=expected,
        presented_quantity=payload.presented_quantity,
        accepted_quantity=payload.accepted_quantity,
        rejected_quantity=payload.rejected_quantity,
        quality_grade_id=payload.quality_grade_id,
        unit_price=payload.unit_price,
        gross_amount=amounts.gross_amount,
        transport_deduction=amounts.transport_deduction,
        platform_fee=amounts.platform_fee,
        other_deduction=amounts.other_deduction,
        other_deduction_reason=payload.other_deduction_reason,
        net_amount_due=amounts.net_amount_due,
        rejection_reason=payload.rejection_reason,
        coordinator_confirmation=True,
        photo_urls=payload.photo_urls,
        receipt_number=next_receipt_number(db, utcnow().year),
    )
    db.add(record)

    stop.collected_quantity = payload.accepted_quantity
    stop.actual_arrival = stop.actual_arrival or utcnow()
    stop.status = StopStatus.COMPLETED

    listing.collected_quantity = (listing.collected_quantity or Decimal("0")) + payload.accepted_quantity
    if listing.status in (HarvestStatus.PARTIALLY_ALLOCATED, HarvestStatus.FULLY_ALLOCATED):
        listing.status = HarvestStatus.COLLECTED
    listing.row_version += 1

    record_audit(
        db,
        actor_user_id=user.id,
        action="collection.recorded",
        entity_type="CollectionRecord",
        entity_id=record.id,
        after={
            "receipt_number": record.receipt_number,
            "accepted_quantity": str(record.accepted_quantity),
            "net_amount_due": str(record.net_amount_due),
        },
    )
    db.commit()
    db.refresh(record)
    return _collection_out(db, record)


@router.get("/collections")
def list_collections(db: DbSession, user: CurrentUser):
    if user.role == Role.FARMER:
        profile = policies.get_farmer_profile(db, user)
        records = db.scalars(select(CollectionRecord).where(CollectionRecord.farmer_id == profile.id)).all()
    elif user.role in (Role.COORDINATOR, Role.ADMIN):
        records = db.scalars(select(CollectionRecord)).all()
        if user.role == Role.COORDINATOR:
            group_ids = [g.id for g in policies.coordinator_groups(db, user)]
            member_ids = {
                p.id
                for p in db.scalars(select(FarmerProfile).where(FarmerProfile.farmer_group_id.in_(group_ids)))
            }
            records = [r for r in records if r.farmer_id in member_ids]
    else:
        return []
    return [_collection_out(db, r) for r in records]


@router.get("/collections/{record_id}")
def get_collection(record_id: uuid.UUID, db: DbSession, user: CurrentUser):
    record = policies.can_view_collection(db, user, db.get(CollectionRecord, record_id))
    return _collection_out(db, record)


@router.post("/collections/{record_id}/farmer-confirm")
def farmer_confirm_collection(
    record_id: uuid.UUID,
    db: DbSession,
    user: User = Depends(require_roles(Role.FARMER)),
):
    record = db.get(CollectionRecord, record_id)
    profile = policies.get_farmer_profile(db, user)
    if record is None or record.farmer_id != profile.id:
        raise NotFoundError("Receipt not found.")
    record.farmer_confirmation = True
    db.commit()
    return _collection_out(db, record)


# ---------- delivery ----------


class DeliveryCreate(BaseModel):
    shipment_id: uuid.UUID
    delivered_quantity: Decimal = Field(ge=0)
    accepted_quantity: Decimal = Field(ge=0)
    rejected_quantity: Decimal = Field(ge=0)
    arrival_condition: str | None = Field(default=None, max_length=200)
    rejection_reason: str | None = Field(default=None, max_length=300)
    proof_of_delivery_urls: list[str] = Field(default_factory=list, max_length=5)


def _delivery_out(record: DeliveryRecord) -> dict:
    return {
        "id": str(record.id),
        "shipment_id": str(record.shipment_id),
        "buyer_order_id": str(record.buyer_order_id),
        "delivered_quantity": str(record.delivered_quantity),
        "accepted_quantity": str(record.accepted_quantity),
        "rejected_quantity": str(record.rejected_quantity),
        "arrival_condition": record.arrival_condition,
        "rejection_reason": record.rejection_reason,
        "buyer_confirmation": record.buyer_confirmation,
        "transporter_confirmation": record.transporter_confirmation,
        "discrepancy_flag": record.discrepancy_flag,
        "discrepancy_note": record.discrepancy_note,
        "proof_of_delivery_urls": record.proof_of_delivery_urls,
        "confirmed_at": record.confirmed_at.isoformat() if record.confirmed_at else None,
    }


@router.post("/deliveries", status_code=201)
def record_delivery(
    payload: DeliveryCreate,
    db: DbSession,
    user: User = Depends(require_roles(Role.BUYER, Role.COORDINATOR, Role.ADMIN)),
):
    shipment = db.get(Shipment, payload.shipment_id)
    if shipment is None:
        raise NotFoundError("Shipment not found.")
    proposal = db.get(MatchProposal, shipment.match_proposal_id)
    item = db.get(BuyerOrderItem, proposal.buyer_order_item_id) if proposal else None
    order = db.get(BuyerOrder, item.buyer_order_id) if item else None
    if order is None:
        raise NotFoundError("Order not found for shipment.")
    org = db.get(BuyerOrganization, order.buyer_organization_id)
    if user.role == Role.BUYER and (org is None or org.owner_user_id != user.id):
        raise NotFoundError("Shipment not found.")
    if shipment.status != ShipmentStatus.ARRIVED:
        raise ConflictError(
            "Delivery can only be recorded after the shipment has arrived.",
            code="SHIPMENT_NOT_ARRIVED",
        )
    if payload.delivered_quantity != payload.accepted_quantity + payload.rejected_quantity:
        raise ValidationFailure(
            "delivered_quantity must equal accepted_quantity + rejected_quantity.",
            code="QUANTITY_MISMATCH",
            field="delivered_quantity",
        )
    existing = db.scalars(select(DeliveryRecord).where(DeliveryRecord.shipment_id == shipment.id)).first()
    if existing:
        raise ConflictError("A delivery record already exists for this shipment.", code="ALREADY_RECORDED")

    # discrepancy check against total collected quantity
    stop_ids = select(ShipmentStop.id).where(ShipmentStop.shipment_id == shipment.id)
    collections = db.scalars(
        select(CollectionRecord).where(CollectionRecord.shipment_stop_id.in_(stop_ids))
    ).all()
    total_collected = sum((c.accepted_quantity for c in collections), Decimal("0"))
    from app.core.config import get_settings

    tolerance = Decimal(get_settings().delivery_discrepancy_tolerance_percent) / Decimal("100")
    discrepancy = False
    note = None
    if total_collected > 0:
        transit_deviation = abs(payload.delivered_quantity - total_collected) / total_collected
        acceptance_deviation = abs(payload.accepted_quantity - total_collected) / total_collected
        if transit_deviation > tolerance:
            discrepancy = True
            note = (
                f"Delivered {payload.delivered_quantity} vs collected {total_collected} "
                f"({q2(transit_deviation * 100)}% deviation, tolerance {q2(tolerance * 100)}%)."
            )
        elif acceptance_deviation > tolerance:
            # heavy buyer rejection: not lost in transit, but flagged for review
            discrepancy = True
            note = (
                f"Buyer accepted {payload.accepted_quantity} of {total_collected} collected "
                f"({q2(acceptance_deviation * 100)}% below collection, tolerance "
                f"{q2(tolerance * 100)}%)."
            )

    record = DeliveryRecord(
        shipment_id=shipment.id,
        buyer_order_id=order.id,
        delivered_quantity=payload.delivered_quantity,
        accepted_quantity=payload.accepted_quantity,
        rejected_quantity=payload.rejected_quantity,
        arrival_condition=payload.arrival_condition,
        rejection_reason=payload.rejection_reason,
        buyer_confirmation=user.role == Role.BUYER,
        proof_of_delivery_urls=payload.proof_of_delivery_urls,
        discrepancy_flag=discrepancy,
        discrepancy_note=note,
        confirmed_at=utcnow(),
    )
    db.add(record)

    transition_shipment(shipment.status, ShipmentStatus.DELIVERED)
    shipment.status = ShipmentStatus.DELIVERED
    shipment.actual_delivery_at = utcnow()

    if item is not None:
        item.accepted_quantity = payload.accepted_quantity
    target = OrderStatus.ACCEPTED if payload.rejected_quantity == 0 else OrderStatus.PARTIALLY_FULFILLED
    transition_order(order.order_status, OrderStatus.DELIVERED)
    order.order_status = OrderStatus.DELIVERED
    transition_order(order.order_status, target)
    order.order_status = target

    _generate_payment_obligations(db, user, order, org, shipment, collections, payload)

    transition_order(order.order_status, OrderStatus.PAYMENT_PENDING)
    order.order_status = OrderStatus.PAYMENT_PENDING

    record_audit(
        db,
        actor_user_id=user.id,
        action="delivery.recorded",
        entity_type="DeliveryRecord",
        entity_id=record.id,
        after={
            "accepted_quantity": str(record.accepted_quantity),
            "rejected_quantity": str(record.rejected_quantity),
            "discrepancy_flag": record.discrepancy_flag,
        },
    )
    db.commit()
    db.refresh(record)
    return _delivery_out(record)


def _generate_payment_obligations(db, user, order, org, shipment, collections, payload) -> None:
    """Create the four obligation types. Amounts derive from receipts."""
    from datetime import timedelta

    due = order.required_delivery_date + timedelta(days=org.payment_terms_days if org else 30)

    farmer_group_id = None
    if collections:
        profile = db.get(FarmerProfile, collections[0].farmer_id)
        farmer_group_id = profile.farmer_group_id if profile else None

    # 1. buyer → cooperative: what the buyer accepted, valued at agreed prices
    total_collected = sum((c.accepted_quantity for c in collections), Decimal("0"))
    gross_total = sum((c.gross_amount for c in collections), Decimal("0"))
    if total_collected > 0 and payload.accepted_quantity != total_collected:
        # pro-rate by the buyer-accepted share
        gross_total = q2(gross_total * payload.accepted_quantity / total_collected)
    db.add(
        PaymentRecord(
            payer_type=PartyType.BUYER_ORGANIZATION,
            payer_id=org.id if org else None,
            recipient_type=PartyType.FARMER_GROUP,
            recipient_id=farmer_group_id,
            related_order_id=order.id,
            amount=q2(gross_total),
            due_date=due,
            status=PaymentStatus.PENDING,
        )
    )

    # 2. cooperative → each farmer: net amount due from their receipt
    for collection in collections:
        db.add(
            PaymentRecord(
                payer_type=PartyType.FARMER_GROUP,
                payer_id=farmer_group_id,
                recipient_type=PartyType.FARMER,
                recipient_id=collection.farmer_id,
                related_order_id=order.id,
                related_collection_id=collection.id,
                amount=collection.net_amount_due,
                due_date=due,
                status=PaymentStatus.PENDING,
            )
        )
        profile = db.get(FarmerProfile, collection.farmer_id)
        farmer_user = db.get(User, profile.user_id) if profile else None
        if farmer_user is not None:
            notify(
                db,
                farmer_user,
                "payment_due",
                {"amount": collection.net_amount_due, "due_date": due.isoformat()},
            )

    # 3. buyer → transporter: agreed transport cost
    transport_cost = shipment.actual_transport_cost or shipment.estimated_transport_cost
    vehicle = db.get(Vehicle, shipment.vehicle_id) if shipment.vehicle_id else None
    provider = db.get(TransportProvider, vehicle.transport_provider_id) if vehicle else None
    if transport_cost is not None and provider is not None:
        db.add(
            PaymentRecord(
                payer_type=PartyType.BUYER_ORGANIZATION,
                payer_id=org.id if org else None,
                recipient_type=PartyType.TRANSPORT_PROVIDER,
                recipient_id=provider.id,
                related_order_id=order.id,
                amount=q2(transport_cost),
                due_date=due,
                status=PaymentStatus.PENDING,
            )
        )

    # 4. cooperative → platform: the itemised platform fees from the receipts
    fee_total = sum((c.platform_fee for c in collections), Decimal("0"))
    if fee_total > 0:
        db.add(
            PaymentRecord(
                payer_type=PartyType.FARMER_GROUP,
                payer_id=farmer_group_id,
                recipient_type=PartyType.PLATFORM,
                recipient_id=None,
                related_order_id=order.id,
                amount=q2(fee_total),
                due_date=due,
                status=PaymentStatus.PENDING,
            )
        )


@router.get("/deliveries")
def list_deliveries(db: DbSession, user: CurrentUser):
    if user.role == Role.BUYER:
        org = policies.get_buyer_organization(db, user)
        order_ids = select(BuyerOrder.id).where(BuyerOrder.buyer_organization_id == org.id)
        records = db.scalars(select(DeliveryRecord).where(DeliveryRecord.buyer_order_id.in_(order_ids))).all()
    elif user.role in (Role.COORDINATOR, Role.ADMIN):
        records = db.scalars(select(DeliveryRecord)).all()
    else:
        return []
    return [_delivery_out(r) for r in records]


@router.post("/deliveries/{record_id}/transporter-confirm")
def transporter_confirm_delivery(
    record_id: uuid.UUID,
    db: DbSession,
    user: User = Depends(require_roles(Role.TRANSPORTER)),
):
    record = db.get(DeliveryRecord, record_id)
    if record is None:
        raise NotFoundError("Delivery record not found.")
    shipment = policies.can_view_shipment(db, user, db.get(Shipment, record.shipment_id))
    record.transporter_confirmation = True
    transition_shipment(shipment.status, ShipmentStatus.COMPLETED)
    shipment.status = ShipmentStatus.COMPLETED
    db.commit()
    return _delivery_out(record)
