"""Transport providers, vehicles, shipment planning, and trip lifecycle."""

import uuid
from datetime import datetime
from decimal import Decimal

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import select

from app.core import policies
from app.core.deps import CurrentUser, DbSession, require_roles
from app.core.errors import ConflictError, NotFoundError, ValidationFailure
from app.db.base import utcnow
from app.domain.enums import (
    ProposalStatus,
    Role,
    ShipmentStatus,
    StopStatus,
    StopType,
    StorageCategory,
    VehicleType,
    VerificationStatus,
)
from app.domain.state_machine import transition_shipment
from app.models import (
    BuyerOrder,
    BuyerOrderItem,
    Farm,
    FarmerProfile,
    HarvestListing,
    Location,
    MatchAllocation,
    MatchProposal,
    Product,
    Shipment,
    ShipmentStop,
    TransportProvider,
    User,
    Vehicle,
)
from app.services.notifications import notify
from app.services.routing import (
    RoutePoint,
    estimate_transport_cost,
    get_router,
    sequence_stops_nearest_neighbour,
)

router = APIRouter(tags=["transport"])


# ---------- providers & vehicles ----------


class ProviderCreate(BaseModel):
    organization_name: str = Field(min_length=2, max_length=160)
    contact_name: str | None = Field(default=None, max_length=120)
    phone: str | None = Field(default=None, max_length=32)
    registration_reference: str | None = Field(default=None, max_length=80)
    service_dzongkhags: list[str] = Field(default_factory=list, max_length=20)


class VehicleCreate(BaseModel):
    registration_number: str = Field(min_length=3, max_length=20)
    vehicle_type: VehicleType
    capacity_kg: Decimal = Field(gt=0, le=Decimal("40000"))
    capacity_volume_m3: Decimal | None = Field(default=None, gt=0)
    has_refrigeration: bool = False
    supported_product_categories: list[str] = Field(default_factory=list)


class VehicleAvailability(BaseModel):
    is_available: bool


def _provider_out(provider: TransportProvider) -> dict:
    return {
        "id": str(provider.id),
        "organization_name": provider.organization_name,
        "contact_name": provider.contact_name,
        "phone": provider.phone,
        "verification_status": str(provider.verification_status),
        "service_dzongkhags": provider.service_dzongkhags,
        "is_active": provider.is_active,
    }


def _vehicle_out(vehicle: Vehicle) -> dict:
    return {
        "id": str(vehicle.id),
        "transport_provider_id": str(vehicle.transport_provider_id),
        "registration_number": vehicle.registration_number,
        "vehicle_type": str(vehicle.vehicle_type),
        "capacity_kg": str(vehicle.capacity_kg),
        "has_refrigeration": vehicle.has_refrigeration,
        "supported_product_categories": vehicle.supported_product_categories,
        "is_available": vehicle.is_available,
        "verification_status": str(vehicle.verification_status),
    }


@router.post("/transport-providers", status_code=201)
def create_provider(
    payload: ProviderCreate,
    db: DbSession,
    user: User = Depends(require_roles(Role.TRANSPORTER)),
):
    existing = db.scalars(select(TransportProvider).where(TransportProvider.owner_user_id == user.id)).first()
    if existing:
        raise ConflictError("Provider profile already exists.", code="PROVIDER_EXISTS")
    provider = TransportProvider(owner_user_id=user.id, **payload.model_dump())
    db.add(provider)
    db.commit()
    return _provider_out(provider)


@router.get("/transport-providers/me")
def my_provider(db: DbSession, user: User = Depends(require_roles(Role.TRANSPORTER))):
    return _provider_out(policies.get_transport_provider(db, user))


@router.post("/vehicles", status_code=201)
def create_vehicle(
    payload: VehicleCreate,
    db: DbSession,
    user: User = Depends(require_roles(Role.TRANSPORTER)),
):
    provider = policies.get_transport_provider(db, user)
    vehicle = Vehicle(transport_provider_id=provider.id, **payload.model_dump())
    db.add(vehicle)
    db.commit()
    return _vehicle_out(vehicle)


@router.get("/vehicles")
def my_vehicles(db: DbSession, user: User = Depends(require_roles(Role.TRANSPORTER, Role.ADMIN))):
    if user.role == Role.ADMIN:
        vehicles = db.scalars(select(Vehicle)).all()
    else:
        provider = policies.get_transport_provider(db, user)
        vehicles = db.scalars(select(Vehicle).where(Vehicle.transport_provider_id == provider.id)).all()
    return [_vehicle_out(v) for v in vehicles]


@router.patch("/vehicles/{vehicle_id}/availability")
def set_vehicle_availability(
    vehicle_id: uuid.UUID, payload: VehicleAvailability, db: DbSession, user: CurrentUser
):
    vehicle = policies.can_manage_vehicle(db, user, db.get(Vehicle, vehicle_id))
    vehicle.is_available = payload.is_available
    db.commit()
    return _vehicle_out(vehicle)


# ---------- shipment planning ----------


class ShipmentPlanRequest(BaseModel):
    match_proposal_id: uuid.UUID
    vehicle_id: uuid.UUID
    planned_pickup_at: datetime
    planned_delivery_at: datetime
    driver_name: str | None = Field(default=None, max_length=120)
    driver_phone: str | None = Field(default=None, max_length=32)


class StopReorder(BaseModel):
    stop_ids_in_order: list[uuid.UUID] = Field(min_length=1)


class StatusUpdate(BaseModel):
    status: ShipmentStatus
    note: str | None = Field(default=None, max_length=300)


def _stop_out(db, stop: ShipmentStop) -> dict:
    location = db.get(Location, stop.location_id) if stop.location_id else None
    profile = db.get(FarmerProfile, stop.farmer_id) if stop.farmer_id else None
    return {
        "id": str(stop.id),
        "stop_type": str(stop.stop_type),
        "sequence_number": stop.sequence_number,
        "location_name": location.name if location else None,
        "farmer_display_name": profile.display_name if profile else None,
        "planned_quantity": str(stop.planned_quantity) if stop.planned_quantity is not None else None,
        "collected_quantity": (str(stop.collected_quantity) if stop.collected_quantity is not None else None),
        "status": str(stop.status),
        "planned_arrival": stop.planned_arrival.isoformat() if stop.planned_arrival else None,
        "actual_arrival": stop.actual_arrival.isoformat() if stop.actual_arrival else None,
    }


def _shipment_out(db, shipment: Shipment) -> dict:
    stops = db.scalars(
        select(ShipmentStop)
        .where(ShipmentStop.shipment_id == shipment.id)
        .order_by(ShipmentStop.sequence_number)
    ).all()
    vehicle = db.get(Vehicle, shipment.vehicle_id) if shipment.vehicle_id else None
    return {
        "id": str(shipment.id),
        "match_proposal_id": str(shipment.match_proposal_id),
        "vehicle": _vehicle_out(vehicle) if vehicle else None,
        "driver_name": shipment.driver_name,
        "driver_phone": shipment.driver_phone,
        "planned_pickup_at": (shipment.planned_pickup_at.isoformat() if shipment.planned_pickup_at else None),
        "planned_delivery_at": (
            shipment.planned_delivery_at.isoformat() if shipment.planned_delivery_at else None
        ),
        "actual_pickup_at": shipment.actual_pickup_at.isoformat() if shipment.actual_pickup_at else None,
        "actual_delivery_at": (
            shipment.actual_delivery_at.isoformat() if shipment.actual_delivery_at else None
        ),
        "planned_distance_km": (
            str(shipment.planned_distance_km) if shipment.planned_distance_km is not None else None
        ),
        "route_estimate_method": shipment.route_estimate_method,
        "route_estimate_is_approximate": shipment.route_estimate_method != "external",
        "estimated_transport_cost": (
            str(shipment.estimated_transport_cost) if shipment.estimated_transport_cost is not None else None
        ),
        "actual_transport_cost": (
            str(shipment.actual_transport_cost) if shipment.actual_transport_cost is not None else None
        ),
        "status": str(shipment.status),
        "incident_notes": shipment.incident_notes,
        "stops": [_stop_out(db, s) for s in stops],
    }


@router.post("/shipments/plan", status_code=201)
def plan_shipment(
    payload: ShipmentPlanRequest,
    db: DbSession,
    user: User = Depends(require_roles(Role.COORDINATOR, Role.ADMIN)),
):
    proposal = db.get(MatchProposal, payload.match_proposal_id)
    if proposal is None:
        raise NotFoundError("Match proposal not found.")
    if proposal.status != ProposalStatus.APPROVED:
        raise ConflictError("Only approved proposals can be shipped.", code="PROPOSAL_NOT_APPROVED")
    existing = db.scalars(
        select(Shipment).where(
            Shipment.match_proposal_id == proposal.id,
            Shipment.status.notin_((ShipmentStatus.CANCELLED,)),
        )
    ).first()
    if existing:
        raise ConflictError("A shipment already exists for this proposal.", code="SHIPMENT_EXISTS")

    vehicle = db.get(Vehicle, payload.vehicle_id)
    if vehicle is None:
        raise NotFoundError("Vehicle not found.")
    if vehicle.verification_status != VerificationStatus.VERIFIED:
        raise ConflictError("Vehicle is not verified.", code="VEHICLE_UNVERIFIED")
    if not vehicle.is_available:
        raise ConflictError("Vehicle is not available.", code="VEHICLE_UNAVAILABLE")
    if payload.planned_delivery_at <= payload.planned_pickup_at:
        raise ValidationFailure(
            "planned_delivery_at must be after planned_pickup_at", field="planned_delivery_at"
        )

    # load & capacity check
    if proposal.proposed_quantity > vehicle.capacity_kg:
        raise ConflictError(
            f"Load of {proposal.proposed_quantity} kg exceeds vehicle capacity of {vehicle.capacity_kg} kg.",
            code="VEHICLE_CAPACITY_EXCEEDED",
        )

    # refrigeration check
    item = db.get(BuyerOrderItem, proposal.buyer_order_item_id)
    assert item is not None
    product = db.get(Product, item.product_id)
    if (
        product is not None
        and product.storage_category == StorageCategory.REFRIGERATED
        and not vehicle.has_refrigeration
    ):
        raise ConflictError("This product requires a refrigerated vehicle.", code="REFRIGERATION_REQUIRED")

    order = db.get(BuyerOrder, item.buyer_order_id)
    assert order is not None
    delivery_loc = db.get(Location, order.delivery_location_id)

    allocations = db.scalars(
        select(MatchAllocation).where(MatchAllocation.match_proposal_id == proposal.id)
    ).all()

    shipment = Shipment(
        match_proposal_id=proposal.id,
        vehicle_id=vehicle.id,
        driver_name=payload.driver_name,
        driver_phone=payload.driver_phone,
        planned_pickup_at=payload.planned_pickup_at,
        planned_delivery_at=payload.planned_delivery_at,
        status=ShipmentStatus.PLANNING,
    )
    db.add(shipment)
    db.flush()

    # pickup stops: one per allocation's farm, sequenced nearest-neighbour
    pickups: list[tuple[MatchAllocation, Farm | None]] = []
    for allocation in allocations:
        listing = db.get(HarvestListing, allocation.harvest_listing_id)
        farm = db.get(Farm, listing.farm_id) if listing else None
        pickups.append((allocation, farm))

    routable = [
        (i, RoutePoint(farm.latitude, farm.longitude, farm.farm_name))
        for i, (_, farm) in enumerate(pickups)
        if farm is not None and farm.latitude is not None and farm.longitude is not None
    ]
    order_indices = list(range(len(pickups)))
    if (
        routable
        and delivery_loc is not None
        and delivery_loc.latitude is not None
        and delivery_loc.longitude is not None
    ):
        origin = RoutePoint(delivery_loc.latitude, delivery_loc.longitude, delivery_loc.name)
        seq = sequence_stops_nearest_neighbour(origin, [pt for _, pt in routable])
        sequenced = [routable[j][0] for j in seq]
        rest = [i for i in order_indices if i not in sequenced]
        order_indices = sequenced + rest

    points: list[RoutePoint] = []
    for seq_no, idx in enumerate(order_indices, start=1):
        allocation, farm = pickups[idx]
        listing = db.get(HarvestListing, allocation.harvest_listing_id)
        db.add(
            ShipmentStop(
                shipment_id=shipment.id,
                stop_type=StopType.PICKUP,
                sequence_number=seq_no,
                farmer_id=listing.farmer_id if listing else None,
                planned_quantity=allocation.allocated_quantity,
                status=StopStatus.PLANNED,
            )
        )
        if farm is not None and farm.latitude is not None and farm.longitude is not None:
            points.append(RoutePoint(farm.latitude, farm.longitude, farm.farm_name))

    db.add(
        ShipmentStop(
            shipment_id=shipment.id,
            stop_type=StopType.DELIVERY,
            sequence_number=len(pickups) + 1,
            location_id=order.delivery_location_id,
            planned_quantity=proposal.proposed_quantity,
            status=StopStatus.PLANNED,
        )
    )
    if delivery_loc is not None and delivery_loc.latitude is not None and delivery_loc.longitude is not None:
        points.append(RoutePoint(delivery_loc.latitude, delivery_loc.longitude, delivery_loc.name))

    if len(points) >= 2:
        estimate = get_router().estimate_route(points)
        shipment.planned_distance_km = estimate.distance_km
        shipment.route_estimate_method = estimate.method
        shipment.estimated_transport_cost = estimate_transport_cost(estimate.distance_km)

    db.commit()
    return _shipment_out(db, shipment)


@router.get("/shipments")
def list_shipments(db: DbSession, user: CurrentUser, status: ShipmentStatus | None = None):
    query = select(Shipment)
    if user.role in (Role.COORDINATOR, Role.ADMIN):
        pass
    elif user.role == Role.TRANSPORTER:
        provider = policies.get_transport_provider(db, user)
        vehicle_ids = select(Vehicle.id).where(Vehicle.transport_provider_id == provider.id)
        query = query.where(Shipment.vehicle_id.in_(vehicle_ids))
    elif user.role == Role.BUYER:
        org = policies.get_buyer_organization(db, user)
        order_ids = select(BuyerOrder.id).where(BuyerOrder.buyer_organization_id == org.id)
        item_ids = select(BuyerOrderItem.id).where(BuyerOrderItem.buyer_order_id.in_(order_ids))
        prop_ids = select(MatchProposal.id).where(MatchProposal.buyer_order_item_id.in_(item_ids))
        query = query.where(Shipment.match_proposal_id.in_(prop_ids))
    else:
        return []
    if status:
        query = query.where(Shipment.status == status)
    shipments = db.scalars(query.order_by(Shipment.created_at.desc())).all()
    return [_shipment_out(db, s) for s in shipments]


@router.get("/shipments/{shipment_id}")
def get_shipment(shipment_id: uuid.UUID, db: DbSession, user: CurrentUser):
    shipment = db.get(Shipment, shipment_id)
    if shipment is not None and user.role == Role.BUYER:
        # buyers may monitor shipments for their own orders
        item_ok = False
        proposal = db.get(MatchProposal, shipment.match_proposal_id)
        if proposal is not None:
            item = db.get(BuyerOrderItem, proposal.buyer_order_item_id)
            order = db.get(BuyerOrder, item.buyer_order_id) if item else None
            if order is not None:
                org = policies.get_buyer_organization(db, user)
                item_ok = order.buyer_organization_id == org.id
        if not item_ok:
            raise NotFoundError("Resource not found.")
        return _shipment_out(db, shipment)
    shipment = policies.can_view_shipment(db, user, shipment)
    return _shipment_out(db, shipment)


@router.post("/shipments/{shipment_id}/offer")
def offer_shipment(
    shipment_id: uuid.UUID,
    db: DbSession,
    user: User = Depends(require_roles(Role.COORDINATOR, Role.ADMIN)),
):
    shipment = db.get(Shipment, shipment_id)
    if shipment is None:
        raise NotFoundError("Shipment not found.")
    transition_shipment(shipment.status, ShipmentStatus.OFFERED)
    shipment.status = ShipmentStatus.OFFERED
    vehicle = db.get(Vehicle, shipment.vehicle_id) if shipment.vehicle_id else None
    if vehicle is not None:
        provider = db.get(TransportProvider, vehicle.transport_provider_id)
        owner = db.get(User, provider.owner_user_id) if provider else None
        if owner is not None:
            notify(
                db,
                owner,
                "transport_trip_available",
                {
                    "route": f"{shipment.planned_distance_km or '?'} km trip",
                    "date": shipment.planned_pickup_at.date().isoformat()
                    if shipment.planned_pickup_at
                    else "TBD",
                },
            )
    db.commit()
    return _shipment_out(db, shipment)


@router.post("/shipments/{shipment_id}/accept")
def accept_trip(
    shipment_id: uuid.UUID,
    db: DbSession,
    user: User = Depends(require_roles(Role.TRANSPORTER)),
):
    shipment = policies.can_view_shipment(db, user, db.get(Shipment, shipment_id))
    transition_shipment(shipment.status, ShipmentStatus.ASSIGNED)
    shipment.status = ShipmentStatus.ASSIGNED
    db.commit()
    return _shipment_out(db, shipment)


@router.post("/shipments/{shipment_id}/decline")
def decline_trip(
    shipment_id: uuid.UUID,
    db: DbSession,
    user: User = Depends(require_roles(Role.TRANSPORTER)),
):
    shipment = policies.can_view_shipment(db, user, db.get(Shipment, shipment_id))
    transition_shipment(shipment.status, ShipmentStatus.PLANNING)
    shipment.status = ShipmentStatus.PLANNING
    shipment.vehicle_id = None  # release the vehicle so another can be assigned
    db.commit()
    return {"status": "declined", "shipment_id": str(shipment.id)}


@router.post("/shipments/{shipment_id}/confirm")
def confirm_assignment(
    shipment_id: uuid.UUID,
    db: DbSession,
    user: User = Depends(require_roles(Role.COORDINATOR, Role.ADMIN)),
):
    shipment = db.get(Shipment, shipment_id)
    if shipment is None:
        raise NotFoundError("Shipment not found.")
    transition_shipment(shipment.status, ShipmentStatus.CONFIRMED)
    shipment.status = ShipmentStatus.CONFIRMED
    vehicle = db.get(Vehicle, shipment.vehicle_id) if shipment.vehicle_id else None
    if vehicle is not None:
        provider = db.get(TransportProvider, vehicle.transport_provider_id)
        owner = db.get(User, provider.owner_user_id) if provider else None
        if owner is not None:
            notify(
                db,
                owner,
                "shipment_assigned",
                {"shipment": str(shipment.id)[:8], "vehicle": vehicle.registration_number},
            )
    db.commit()
    return _shipment_out(db, shipment)


ALLOWED_TRANSPORTER_TARGETS = {
    ShipmentStatus.COLLECTION_IN_PROGRESS,
    ShipmentStatus.IN_TRANSIT,
    ShipmentStatus.ARRIVED,
    ShipmentStatus.DELAYED,
    ShipmentStatus.INCIDENT_REPORTED,
}


@router.post("/shipments/{shipment_id}/status")
def update_status(
    shipment_id: uuid.UUID,
    payload: StatusUpdate,
    db: DbSession,
    user: User = Depends(require_roles(Role.TRANSPORTER, Role.COORDINATOR, Role.ADMIN)),
):
    shipment = policies.can_view_shipment(db, user, db.get(Shipment, shipment_id))
    if user.role == Role.TRANSPORTER and payload.status not in ALLOWED_TRANSPORTER_TARGETS:
        raise ConflictError(
            "Transporters can only report operational status changes.",
            code="STATUS_NOT_ALLOWED",
        )
    transition_shipment(shipment.status, payload.status)
    shipment.status = payload.status
    if payload.status == ShipmentStatus.COLLECTION_IN_PROGRESS and shipment.actual_pickup_at is None:
        shipment.actual_pickup_at = utcnow()
    if payload.status in (ShipmentStatus.DELAYED, ShipmentStatus.INCIDENT_REPORTED) and payload.note:
        shipment.incident_notes = payload.note
    db.commit()
    return _shipment_out(db, shipment)


@router.post("/shipments/{shipment_id}/stops/reorder")
def reorder_stops(
    shipment_id: uuid.UUID,
    payload: StopReorder,
    db: DbSession,
    user: User = Depends(require_roles(Role.COORDINATOR, Role.ADMIN)),
):
    """Manual route override — always available to the coordinator."""
    shipment = db.get(Shipment, shipment_id)
    if shipment is None:
        raise NotFoundError("Shipment not found.")
    if shipment.status not in (
        ShipmentStatus.PLANNING,
        ShipmentStatus.OFFERED,
        ShipmentStatus.ASSIGNED,
        ShipmentStatus.CONFIRMED,
    ):
        raise ConflictError("Stops can only be reordered before collection starts.")
    stops = db.scalars(select(ShipmentStop).where(ShipmentStop.shipment_id == shipment.id)).all()
    by_id = {s.id: s for s in stops}
    pickup_ids = [s.id for s in stops if s.stop_type == StopType.PICKUP]
    if sorted(payload.stop_ids_in_order) != sorted(pickup_ids):
        raise ValidationFailure(
            "stop_ids_in_order must contain exactly the pickup stops of this shipment.",
            field="stop_ids_in_order",
        )
    for seq, stop_id in enumerate(payload.stop_ids_in_order, start=1):
        by_id[stop_id].sequence_number = seq
    delivery = next(s for s in stops if s.stop_type == StopType.DELIVERY)
    delivery.sequence_number = len(payload.stop_ids_in_order) + 1
    db.commit()
    return _shipment_out(db, shipment)
