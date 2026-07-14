"""Administrator endpoints: verification queues, suspension, audit log, config."""

import uuid

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy import func, select

from app.core.config import get_settings
from app.core.deps import CurrentUser, DbSession, require_roles
from app.core.errors import NotFoundError
from app.domain.enums import Role, VerificationStatus
from app.models import (
    AuditLog,
    BuyerOrganization,
    FarmerGroup,
    FarmerProfile,
    RefreshToken,
    TransportProvider,
    User,
    Vehicle,
)
from app.schemas.common import Page, PageParams
from app.services.audit import record_audit
from app.services.notifications import notify

router = APIRouter(
    prefix="/admin",
    tags=["admin"],
    dependencies=[Depends(require_roles(Role.ADMIN))],
)


class Decision(BaseModel):
    approve: bool
    reason: str | None = Field(default=None, max_length=300)


class SuspendRequest(BaseModel):
    reason: str = Field(min_length=3, max_length=300)


@router.get("/verification-queue")
def verification_queue(db: DbSession):
    pending = VerificationStatus.PENDING
    farmers = db.scalars(select(FarmerProfile).where(FarmerProfile.verification_status == pending)).all()
    buyers = db.scalars(
        select(BuyerOrganization).where(BuyerOrganization.verification_status == pending)
    ).all()
    transporters = db.scalars(
        select(TransportProvider).where(TransportProvider.verification_status == pending)
    ).all()
    groups = db.scalars(select(FarmerGroup).where(FarmerGroup.verification_status == pending)).all()
    vehicles = db.scalars(select(Vehicle).where(Vehicle.verification_status == pending)).all()
    return {
        "farmers": [{"id": str(f.id), "display_name": f.display_name} for f in farmers],
        "buyer_organizations": [{"id": str(b.id), "name": b.name} for b in buyers],
        "transport_providers": [{"id": str(t.id), "name": t.organization_name} for t in transporters],
        "farmer_groups": [{"id": str(g.id), "name": g.name} for g in groups],
        "vehicles": [{"id": str(v.id), "registration_number": v.registration_number} for v in vehicles],
    }


def _decide(entity, decision: Decision) -> None:
    entity.verification_status = (
        VerificationStatus.VERIFIED if decision.approve else VerificationStatus.REJECTED
    )


@router.post("/buyer-organizations/{org_id}/verify")
def verify_buyer_org(
    org_id: uuid.UUID, payload: Decision, db: DbSession, user: CurrentUser, request: Request
):
    org = db.get(BuyerOrganization, org_id)
    if org is None:
        raise NotFoundError("Organization not found.")
    before = str(org.verification_status)
    _decide(org, payload)
    owner = db.get(User, org.owner_user_id)
    if owner is not None:
        owner.is_verified = payload.approve
        notify(
            db,
            owner,
            "account_verified" if payload.approve else "account_rejected",
            {"reason": payload.reason or "not specified"},
        )
    record_audit(
        db,
        actor_user_id=user.id,
        action="buyer_organization.verification",
        entity_type="BuyerOrganization",
        entity_id=org.id,
        before={"verification_status": before},
        after={"verification_status": str(org.verification_status)},
        reason=payload.reason,
        request=request,
    )
    db.commit()
    return {"id": str(org.id), "verification_status": str(org.verification_status)}


@router.post("/transport-providers/{provider_id}/verify")
def verify_transport_provider(
    provider_id: uuid.UUID, payload: Decision, db: DbSession, user: CurrentUser, request: Request
):
    provider = db.get(TransportProvider, provider_id)
    if provider is None:
        raise NotFoundError("Transport provider not found.")
    before = str(provider.verification_status)
    _decide(provider, payload)
    owner = db.get(User, provider.owner_user_id)
    if owner is not None:
        owner.is_verified = payload.approve
        notify(
            db,
            owner,
            "account_verified" if payload.approve else "account_rejected",
            {"reason": payload.reason or "not specified"},
        )
    record_audit(
        db,
        actor_user_id=user.id,
        action="transport_provider.verification",
        entity_type="TransportProvider",
        entity_id=provider.id,
        before={"verification_status": before},
        after={"verification_status": str(provider.verification_status)},
        reason=payload.reason,
        request=request,
    )
    db.commit()
    return {"id": str(provider.id), "verification_status": str(provider.verification_status)}


@router.post("/vehicles/{vehicle_id}/verify")
def verify_vehicle(
    vehicle_id: uuid.UUID, payload: Decision, db: DbSession, user: CurrentUser, request: Request
):
    vehicle = db.get(Vehicle, vehicle_id)
    if vehicle is None:
        raise NotFoundError("Vehicle not found.")
    before = str(vehicle.verification_status)
    _decide(vehicle, payload)
    record_audit(
        db,
        actor_user_id=user.id,
        action="vehicle.verification",
        entity_type="Vehicle",
        entity_id=vehicle.id,
        before={"verification_status": before},
        after={"verification_status": str(vehicle.verification_status)},
        reason=payload.reason,
        request=request,
    )
    db.commit()
    return {"id": str(vehicle.id), "verification_status": str(vehicle.verification_status)}


@router.post("/farmer-groups/{group_id}/verify")
def verify_group(group_id: uuid.UUID, payload: Decision, db: DbSession, user: CurrentUser, request: Request):
    group = db.get(FarmerGroup, group_id)
    if group is None:
        raise NotFoundError("Farmer group not found.")
    before = str(group.verification_status)
    _decide(group, payload)
    record_audit(
        db,
        actor_user_id=user.id,
        action="farmer_group.verification",
        entity_type="FarmerGroup",
        entity_id=group.id,
        before={"verification_status": before},
        after={"verification_status": str(group.verification_status)},
        reason=payload.reason,
        request=request,
    )
    db.commit()
    return {"id": str(group.id), "verification_status": str(group.verification_status)}


@router.post("/users/{user_id}/suspend")
def suspend_user(
    user_id: uuid.UUID, payload: SuspendRequest, db: DbSession, user: CurrentUser, request: Request
):
    target = db.get(User, user_id)
    if target is None:
        raise NotFoundError("User not found.")
    target.is_active = False
    # revoke all refresh-token families
    for token in db.scalars(select(RefreshToken).where(RefreshToken.user_id == target.id)):
        from app.db.base import utcnow

        token.revoked_at = token.revoked_at or utcnow()
    record_audit(
        db,
        actor_user_id=user.id,
        action="user.suspend",
        entity_type="User",
        entity_id=target.id,
        reason=payload.reason,
        request=request,
    )
    db.commit()
    return {"id": str(target.id), "is_active": target.is_active}


@router.post("/users/{user_id}/reinstate")
def reinstate_user(
    user_id: uuid.UUID, payload: SuspendRequest, db: DbSession, user: CurrentUser, request: Request
):
    target = db.get(User, user_id)
    if target is None:
        raise NotFoundError("User not found.")
    target.is_active = True
    record_audit(
        db,
        actor_user_id=user.id,
        action="user.reinstate",
        entity_type="User",
        entity_id=target.id,
        reason=payload.reason,
        request=request,
    )
    db.commit()
    return {"id": str(target.id), "is_active": target.is_active}


@router.get("/users")
def list_users(
    db: DbSession,
    params: PageParams = Depends(),
    role: Role | None = Query(None),
):
    query = select(User)
    if role:
        query = query.where(User.role == role)
    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    users = db.scalars(
        query.order_by(User.created_at.desc()).offset(params.offset).limit(params.page_size)
    ).all()
    return Page(
        items=[
            {
                "id": str(u.id),
                "email": u.email,
                "role": str(u.role),
                "is_active": u.is_active,
                "is_verified": u.is_verified,
                "created_at": u.created_at.isoformat(),
            }
            for u in users
        ],
        total=total,
        page=params.page,
        page_size=params.page_size,
    )


@router.get("/audit-logs")
def list_audit_logs(
    db: DbSession,
    params: PageParams = Depends(),
    action: str | None = Query(None),
    entity_type: str | None = Query(None),
):
    query = select(AuditLog)
    if action:
        query = query.where(AuditLog.action == action)
    if entity_type:
        query = query.where(AuditLog.entity_type == entity_type)
    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    logs = db.scalars(
        query.order_by(AuditLog.created_at.desc()).offset(params.offset).limit(params.page_size)
    ).all()
    return Page(
        items=[
            {
                "id": str(entry.id),
                "actor_user_id": str(entry.actor_user_id) if entry.actor_user_id else None,
                "action": entry.action,
                "entity_type": entry.entity_type,
                "entity_id": str(entry.entity_id) if entry.entity_id else None,
                "before_state": entry.before_state,
                "after_state": entry.after_state,
                "reason": entry.reason,
                "created_at": entry.created_at.isoformat(),
            }
            for entry in logs
        ],
        total=total,
        page=params.page,
        page_size=params.page_size,
    )


@router.get("/configuration")
def platform_configuration():
    settings = get_settings()
    return {
        "platform_fee_percent": settings.platform_fee_percent,
        "delivery_discrepancy_tolerance_percent": settings.delivery_discrepancy_tolerance_percent,
        "road_circuity_factor": settings.road_circuity_factor,
        "average_speed_kmh": settings.average_speed_kmh,
        "transport_cost_per_km_nu": settings.transport_cost_per_km_nu,
        "note": "Values are environment-configured; changes require redeploy in the MVP.",
    }
