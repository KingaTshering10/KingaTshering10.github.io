"""Role-scoped analytics.

Measured values come straight from platform records. Anything derived from
assumptions (transport savings, loss reduction) is returned under
``estimated`` with its calculation method spelled out — never presented as
a measured fact.
"""

from decimal import Decimal

from fastapi import APIRouter, Depends
from sqlalchemy import func, select

from app.core import policies
from app.core.deps import DbSession, require_roles
from app.domain.enums import (
    DisputeStatus,
    OrderStatus,
    PaymentStatus,
    Role,
    ShipmentStatus,
    VerificationStatus,
)
from app.models import (
    BuyerOrder,
    BuyerOrderItem,
    BuyerOrganization,
    CollectionRecord,
    DeliveryRecord,
    Dispute,
    Farm,
    FarmerGroup,
    FarmerProfile,
    HarvestListing,
    PaymentRecord,
    Shipment,
    TransportProvider,
    User,
    Vehicle,
)
from app.services.settlement import q2

router = APIRouter(prefix="/analytics", tags=["analytics"])

ZERO = Decimal("0")


def _dsum(values) -> Decimal:
    return sum(values, ZERO)


@router.get("/farmer")
def farmer_analytics(db: DbSession, user=Depends(require_roles(Role.FARMER))):
    profile = policies.get_farmer_profile(db, user)
    listings = db.scalars(select(HarvestListing).where(HarvestListing.farmer_id == profile.id)).all()
    collections = db.scalars(select(CollectionRecord).where(CollectionRecord.farmer_id == profile.id)).all()
    payments = db.scalars(select(PaymentRecord).where(PaymentRecord.recipient_id == profile.id)).all()

    listed = _dsum(ls.forecast_quantity for ls in listings)
    confirmed = _dsum(ls.confirmed_quantity or ZERO for ls in listings)
    sold = _dsum(c.accepted_quantity for c in collections)
    presented = _dsum(c.presented_quantity for c in collections)
    rejected = _dsum(c.rejected_quantity for c in collections)
    gross = _dsum(c.gross_amount for c in collections)
    net = _dsum(c.net_amount_due for c in collections)
    paid = _dsum(p.amount_paid for p in payments)

    return {
        "measured": {
            "listed_quantity": str(listed),
            "confirmed_quantity": str(confirmed),
            "quantity_sold": str(sold),
            "percentage_sold": str(q2(sold / confirmed * 100)) if confirmed else None,
            "average_unit_price": (str(q2(gross / sold)) if sold else None),
            "gross_revenue": str(gross),
            "net_revenue": str(net),
            "rejection_rate_percent": (str(q2(rejected / presented * 100)) if presented else None),
            "amount_due": str(_dsum(p.amount - p.amount_paid for p in payments)),
            "amount_paid": str(paid),
            "overdue_payments": sum(1 for p in payments if p.status == PaymentStatus.OVERDUE),
        },
        "currency": "BTN",
    }


@router.get("/buyer")
def buyer_analytics(db: DbSession, user=Depends(require_roles(Role.BUYER))):
    org = policies.get_buyer_organization(db, user)
    orders = db.scalars(select(BuyerOrder).where(BuyerOrder.buyer_organization_id == org.id)).all()
    order_ids = [o.id for o in orders]
    items = (
        db.scalars(select(BuyerOrderItem).where(BuyerOrderItem.buyer_order_id.in_(order_ids))).all()
        if order_ids
        else []
    )
    deliveries = (
        db.scalars(select(DeliveryRecord).where(DeliveryRecord.buyer_order_id.in_(order_ids))).all()
        if order_ids
        else []
    )
    payments = db.scalars(select(PaymentRecord).where(PaymentRecord.payer_id == org.id)).all()

    required = _dsum(i.required_quantity for i in items)
    accepted = _dsum(i.accepted_quantity or ZERO for i in items)
    delivered = _dsum(d.delivered_quantity for d in deliveries)
    rejected = _dsum(d.rejected_quantity for d in deliveries)
    spend = _dsum(p.amount for p in payments)

    return {
        "measured": {
            "orders_created": len(orders),
            "fulfilment_rate_percent": str(q2(accepted / required * 100)) if required else None,
            "average_procurement_cost_per_unit": str(q2(spend / accepted)) if accepted else None,
            "delivery_rejection_rate_percent": (str(q2(rejected / delivered * 100)) if delivered else None),
            "payment_obligations_outstanding": str(_dsum(p.amount - p.amount_paid for p in payments)),
            "completed_orders": sum(1 for o in orders if o.order_status == OrderStatus.COMPLETED),
        },
        "currency": "BTN",
    }


@router.get("/transporter")
def transporter_analytics(db: DbSession, user=Depends(require_roles(Role.TRANSPORTER))):
    provider = policies.get_transport_provider(db, user)
    vehicles = db.scalars(select(Vehicle).where(Vehicle.transport_provider_id == provider.id)).all()
    vehicle_ids = [v.id for v in vehicles]
    shipments = (
        db.scalars(select(Shipment).where(Shipment.vehicle_id.in_(vehicle_ids))).all() if vehicle_ids else []
    )
    payments = db.scalars(select(PaymentRecord).where(PaymentRecord.recipient_id == provider.id)).all()

    completed = [s for s in shipments if s.status == ShipmentStatus.COMPLETED]
    total_capacity = _dsum(v.capacity_kg for v in vehicles)

    return {
        "measured": {
            "completed_trips": len(completed),
            "active_trips": sum(
                1
                for s in shipments
                if s.status
                not in (ShipmentStatus.COMPLETED, ShipmentStatus.CANCELLED, ShipmentStatus.PLANNING)
            ),
            "total_planned_distance_km": str(_dsum(s.planned_distance_km or ZERO for s in shipments)),
            "fleet_capacity_kg": str(total_capacity),
            "pending_payment": str(_dsum(p.amount - p.amount_paid for p in payments)),
        },
        "currency": "BTN",
    }


@router.get("/platform")
def platform_analytics(db: DbSession, user=Depends(require_roles(Role.ADMIN, Role.COORDINATOR))):
    users_by_role: dict[str, int] = {
        str(row[0]): row[1]
        for row in db.execute(
            select(User.role, func.count()).where(User.is_active.is_(True)).group_by(User.role)
        ).all()
    }
    listings = db.scalars(select(HarvestListing)).all()
    collections = db.scalars(select(CollectionRecord)).all()
    payments = db.scalars(select(PaymentRecord)).all()
    disputes = db.scalars(select(Dispute)).all()
    orders = db.scalars(select(BuyerOrder)).all()
    shipments = db.scalars(select(Shipment)).all()

    listed = _dsum(ls.forecast_quantity for ls in listings)
    confirmed = _dsum(ls.confirmed_quantity or ZERO for ls in listings)
    sold = _dsum(c.accepted_quantity for c in collections)
    presented = _dsum(c.presented_quantity for c in collections)
    rejected_collection = _dsum(c.rejected_quantity for c in collections)
    gross_value = _dsum(c.gross_amount for c in collections)
    completed_shipments = [s for s in shipments if s.status == ShipmentStatus.COMPLETED]
    transport_cost = _dsum((s.actual_transport_cost or s.estimated_transport_cost or ZERO) for s in shipments)
    settled = [p for p in payments if p.status == PaymentStatus.PAID]

    # --- estimates: assumptions documented inline, labelled estimated ---
    # Baseline assumption: without aggregation each participating farmer would
    # have paid for an individual trip; shared trips replace N pickups with 1.
    pickups_saved = max(0, len(collections) - len(shipments)) if shipments else 0
    avg_trip_cost = transport_cost / Decimal(len(shipments)) if shipments and transport_cost else ZERO
    estimated_transport_savings = q2(avg_trip_cost * Decimal(pickups_saved) * Decimal("0.6"))
    # Baseline assumption: 20% typical post-harvest loss for uncoordinated sales
    # (FAO smallholder range); coordinated collection loses only what was rejected.
    baseline_loss = q2(sold * Decimal("0.20"))
    actual_loss = rejected_collection
    estimated_loss_reduction_kg = max(ZERO, q2(baseline_loss - actual_loss))

    dzongkhag_activity: dict[str, int] = {
        row[0]: row[1]
        for row in db.execute(select(Farm.dzongkhag, func.count()).group_by(Farm.dzongkhag)).all()
    }

    return {
        "measured": {
            "active_users_by_role": users_by_role,
            "pending_verifications": db.scalar(
                select(func.count())
                .select_from(FarmerProfile)
                .where(FarmerProfile.verification_status == VerificationStatus.PENDING)
            ),
            "farmer_groups": db.scalar(select(func.count()).select_from(FarmerGroup)),
            "verified_buyers": db.scalar(
                select(func.count())
                .select_from(BuyerOrganization)
                .where(BuyerOrganization.verification_status == VerificationStatus.VERIFIED)
            ),
            "transport_providers": db.scalar(select(func.count()).select_from(TransportProvider)),
            "total_produce_listed_kg": str(listed),
            "total_produce_confirmed_kg": str(confirmed),
            "total_produce_sold_kg": str(sold),
            "gross_transaction_value": str(gross_value),
            "orders_total": len(orders),
            "orders_completed": sum(1 for o in orders if o.order_status == OrderStatus.COMPLETED),
            "completed_shipments": len(completed_shipments),
            "payment_completion_rate_percent": (
                str(q2(Decimal(len(settled)) / Decimal(len(payments)) * 100)) if payments else None
            ),
            "dispute_count": len(disputes),
            "disputes_resolved": sum(1 for d in disputes if d.status == DisputeStatus.RESOLVED),
            "collection_rejection_rate_percent": (
                str(q2(rejected_collection / presented * 100)) if presented else None
            ),
            "average_transport_cost_per_kg": (
                str(q2(transport_cost / sold)) if sold and transport_cost else None
            ),
            "activity_by_dzongkhag": dzongkhag_activity,
        },
        "estimated": {
            "transport_savings_nu": str(estimated_transport_savings),
            "transport_savings_method": (
                "Assumes each collection stop replaced an individual trip at 60% of the "
                "average shared-trip cost. Requires pilot baseline data to validate."
            ),
            "produce_loss_reduction_kg": str(estimated_loss_reduction_kg),
            "produce_loss_reduction_method": (
                "Assumes a 20% baseline post-harvest loss for uncoordinated sales "
                "(FAO smallholder range) versus actual rejected quantities. "
                "Requires pilot baseline data to validate."
            ),
        },
        "currency": "BTN",
    }
