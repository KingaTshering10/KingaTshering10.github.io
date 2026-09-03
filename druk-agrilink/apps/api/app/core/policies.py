"""Object-level authorization — the single place where ownership rules live.

Cross-tenant reads raise :class:`NotFoundError` (404) so resource existence is
not leaked; role failures on resources whose existence is public raise 403.
"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import ForbiddenError, NotFoundError
from app.domain.enums import Role
from app.models import (
    BuyerOrder,
    BuyerOrganization,
    CollectionRecord,
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


def _not_found() -> NotFoundError:
    return NotFoundError("Resource not found.", code="NOT_FOUND")


def get_farmer_profile(db: Session, user: User) -> FarmerProfile:
    profile = db.scalars(select(FarmerProfile).where(FarmerProfile.user_id == user.id)).first()
    if profile is None:
        raise NotFoundError("Complete your farmer profile first.", code="PROFILE_MISSING")
    return profile


def coordinator_groups(db: Session, user: User) -> list[FarmerGroup]:
    return list(db.scalars(select(FarmerGroup).where(FarmerGroup.coordinator_user_id == user.id)))


def require_group_coordinator(db: Session, user: User, group: FarmerGroup | None) -> FarmerGroup:
    if group is None:
        raise _not_found()
    if user.role == Role.ADMIN:
        return group
    if user.role != Role.COORDINATOR or group.coordinator_user_id != user.id:
        raise _not_found()
    return group


def can_view_farmer_profile(db: Session, user: User, profile: FarmerProfile | None) -> FarmerProfile:
    if profile is None:
        raise _not_found()
    if user.role == Role.ADMIN or profile.user_id == user.id:
        return profile
    if user.role == Role.COORDINATOR and profile.farmer_group_id is not None:
        group = db.get(FarmerGroup, profile.farmer_group_id)
        if group is not None and group.coordinator_user_id == user.id:
            return profile
    raise _not_found()


def can_manage_farm(db: Session, user: User, farm: Farm | None) -> Farm:
    if farm is None:
        raise _not_found()
    if user.role == Role.ADMIN:
        return farm
    profile = db.get(FarmerProfile, farm.farmer_id)
    if profile is not None and profile.user_id == user.id:
        return farm
    raise _not_found()


def can_view_listing(db: Session, user: User, listing: HarvestListing | None) -> HarvestListing:
    if listing is None:
        raise _not_found()
    if user.role == Role.ADMIN:
        return listing
    profile = db.get(FarmerProfile, listing.farmer_id)
    if profile is None:
        raise _not_found()
    if profile.user_id == user.id:
        return listing
    if user.role == Role.COORDINATOR and profile.farmer_group_id is not None:
        group = db.get(FarmerGroup, profile.farmer_group_id)
        if group is not None and group.coordinator_user_id == user.id:
            return listing
    raise _not_found()


def can_edit_listing(db: Session, user: User, listing: HarvestListing | None) -> HarvestListing:
    listing = can_view_listing(db, user, listing)
    return listing


def get_buyer_organization(db: Session, user: User) -> BuyerOrganization:
    org = db.scalars(select(BuyerOrganization).where(BuyerOrganization.owner_user_id == user.id)).first()
    if org is None:
        raise NotFoundError("Create your buyer organization first.", code="ORGANIZATION_MISSING")
    return org


def can_manage_order(db: Session, user: User, order: BuyerOrder | None) -> BuyerOrder:
    if order is None:
        raise _not_found()
    if user.role in (Role.ADMIN, Role.COORDINATOR):
        return order
    org = db.get(BuyerOrganization, order.buyer_organization_id)
    if org is not None and org.owner_user_id == user.id:
        return order
    raise _not_found()


def can_edit_order(db: Session, user: User, order: BuyerOrder | None) -> BuyerOrder:
    if order is None:
        raise _not_found()
    if user.role == Role.ADMIN:
        return order
    org = db.get(BuyerOrganization, order.buyer_organization_id)
    if org is not None and org.owner_user_id == user.id:
        return order
    raise _not_found()


def get_transport_provider(db: Session, user: User) -> TransportProvider:
    provider = db.scalars(select(TransportProvider).where(TransportProvider.owner_user_id == user.id)).first()
    if provider is None:
        raise NotFoundError("Create your transport provider profile first.", code="PROVIDER_MISSING")
    return provider


def can_manage_vehicle(db: Session, user: User, vehicle: Vehicle | None) -> Vehicle:
    if vehicle is None:
        raise _not_found()
    if user.role == Role.ADMIN:
        return vehicle
    provider = db.get(TransportProvider, vehicle.transport_provider_id)
    if provider is not None and provider.owner_user_id == user.id:
        return vehicle
    raise _not_found()


def can_view_shipment(db: Session, user: User, shipment: Shipment | None) -> Shipment:
    if shipment is None:
        raise _not_found()
    if user.role in (Role.ADMIN, Role.COORDINATOR):
        return shipment
    if user.role == Role.TRANSPORTER and shipment.vehicle_id is not None:
        vehicle = db.get(Vehicle, shipment.vehicle_id)
        if vehicle is not None:
            provider = db.get(TransportProvider, vehicle.transport_provider_id)
            if provider is not None and provider.owner_user_id == user.id:
                return shipment
    raise _not_found()


def can_view_collection(db: Session, user: User, record: CollectionRecord | None) -> CollectionRecord:
    if record is None:
        raise _not_found()
    if user.role == Role.ADMIN:
        return record
    profile = db.get(FarmerProfile, record.farmer_id)
    if profile is not None and profile.user_id == user.id:
        return record
    if user.role == Role.COORDINATOR and profile is not None and profile.farmer_group_id is not None:
        group = db.get(FarmerGroup, profile.farmer_group_id)
        if group is not None and group.coordinator_user_id == user.id:
            return record
    raise _not_found()


def can_view_payment(db: Session, user: User, payment: PaymentRecord | None) -> PaymentRecord:
    if payment is None:
        raise _not_found()
    if user.role in (Role.ADMIN, Role.COORDINATOR):
        return payment
    if user.role == Role.FARMER:
        profile = db.scalars(select(FarmerProfile).where(FarmerProfile.user_id == user.id)).first()
        if profile is not None and payment.recipient_id == profile.id:
            return payment
    if user.role == Role.BUYER:
        org = db.scalars(select(BuyerOrganization).where(BuyerOrganization.owner_user_id == user.id)).first()
        if org is not None and (payment.payer_id == org.id or payment.recipient_id == org.id):
            return payment
    if user.role == Role.TRANSPORTER:
        provider = db.scalars(
            select(TransportProvider).where(TransportProvider.owner_user_id == user.id)
        ).first()
        if provider is not None and payment.recipient_id == provider.id:
            return payment
    raise _not_found()


def require_verified(entity_status: str, what: str) -> None:
    if entity_status != "verified":
        raise ForbiddenError(
            f"{what} must be verified before performing this action.", code="VERIFICATION_REQUIRED"
        )
