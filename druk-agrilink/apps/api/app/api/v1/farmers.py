"""Farmer profiles, farms, farmer groups, and membership."""

import uuid

from fastapi import APIRouter, Depends, Request
from sqlalchemy import select

from app.core import policies
from app.core.deps import CurrentUser, DbSession, require_roles
from app.core.errors import ConflictError, NotFoundError
from app.domain.enums import Role, VerificationStatus
from app.models import Farm, FarmerGroup, FarmerProfile, User
from app.schemas.farmer import (
    FarmCreate,
    FarmerGroupCreate,
    FarmerGroupOut,
    FarmerProfileCreate,
    FarmerProfileOut,
    FarmOut,
    MembershipRequest,
    VerificationDecision,
)
from app.services.audit import record_audit
from app.services.notifications import notify

router = APIRouter(tags=["farmers"])


# ---------- farmer profile ----------


@router.post("/farmers/profile", response_model=FarmerProfileOut, status_code=201)
def create_profile(
    payload: FarmerProfileCreate,
    db: DbSession,
    user: User = Depends(require_roles(Role.FARMER)),
):
    existing = db.scalars(select(FarmerProfile).where(FarmerProfile.user_id == user.id)).first()
    if existing:
        raise ConflictError("Farmer profile already exists.", code="PROFILE_EXISTS")
    profile = FarmerProfile(user_id=user.id, **payload.model_dump())
    db.add(profile)
    db.commit()
    return profile


@router.get("/farmers/profile", response_model=FarmerProfileOut)
def my_profile(db: DbSession, user: User = Depends(require_roles(Role.FARMER))):
    return policies.get_farmer_profile(db, user)


@router.get("/farmers/{profile_id}", response_model=FarmerProfileOut)
def get_profile(profile_id: uuid.UUID, db: DbSession, user: CurrentUser):
    profile = db.get(FarmerProfile, profile_id)
    return policies.can_view_farmer_profile(db, user, profile)


# ---------- farms ----------


@router.post("/farms", response_model=FarmOut, status_code=201)
def create_farm(
    payload: FarmCreate,
    db: DbSession,
    user: User = Depends(require_roles(Role.FARMER)),
):
    profile = policies.get_farmer_profile(db, user)
    farm = Farm(farmer_id=profile.id, **payload.model_dump())
    db.add(farm)
    db.commit()
    return farm


@router.get("/farms", response_model=list[FarmOut])
def my_farms(db: DbSession, user: User = Depends(require_roles(Role.FARMER))):
    profile = policies.get_farmer_profile(db, user)
    return db.scalars(select(Farm).where(Farm.farmer_id == profile.id, Farm.is_active.is_(True))).all()


@router.patch("/farms/{farm_id}", response_model=FarmOut)
def update_farm(farm_id: uuid.UUID, payload: FarmCreate, db: DbSession, user: CurrentUser):
    farm = policies.can_manage_farm(db, user, db.get(Farm, farm_id))
    for key, value in payload.model_dump().items():
        setattr(farm, key, value)
    db.commit()
    return farm


# ---------- farmer groups ----------


@router.post(
    "/farmer-groups",
    response_model=FarmerGroupOut,
    status_code=201,
)
def create_group(
    payload: FarmerGroupCreate,
    db: DbSession,
    request: Request,
    user: User = Depends(require_roles(Role.COORDINATOR, Role.ADMIN)),
):
    group = FarmerGroup(coordinator_user_id=user.id, **payload.model_dump())
    db.add(group)
    db.flush()
    record_audit(
        db,
        actor_user_id=user.id,
        action="farmer_group.create",
        entity_type="FarmerGroup",
        entity_id=group.id,
        after={"name": group.name, "dzongkhag": group.dzongkhag},
        request=request,
    )
    db.commit()
    return group


@router.get("/farmer-groups", response_model=list[FarmerGroupOut])
def list_groups(db: DbSession, user: CurrentUser):
    # Groups are discoverable (farmers must find groups to join).
    return db.scalars(select(FarmerGroup).where(FarmerGroup.is_active.is_(True))).all()


@router.get("/farmer-groups/mine", response_model=list[FarmerGroupOut])
def my_groups(db: DbSession, user: User = Depends(require_roles(Role.COORDINATOR))):
    return policies.coordinator_groups(db, user)


@router.get("/farmer-groups/{group_id}/members", response_model=list[FarmerProfileOut])
def group_members(
    group_id: uuid.UUID,
    db: DbSession,
    user: User = Depends(require_roles(Role.COORDINATOR, Role.ADMIN)),
):
    group = policies.require_group_coordinator(db, user, db.get(FarmerGroup, group_id))
    return db.scalars(select(FarmerProfile).where(FarmerProfile.farmer_group_id == group.id)).all()


@router.post("/farmers/membership-request", response_model=FarmerProfileOut)
def request_membership(
    payload: MembershipRequest,
    db: DbSession,
    user: User = Depends(require_roles(Role.FARMER)),
):
    profile = policies.get_farmer_profile(db, user)
    group = db.get(FarmerGroup, payload.farmer_group_id)
    if group is None or not group.is_active:
        raise NotFoundError("Farmer group not found.")
    profile.farmer_group_id = group.id
    profile.membership_status = "requested"
    db.commit()
    return profile


@router.post("/farmer-groups/{group_id}/members/{profile_id}/approve", response_model=FarmerProfileOut)
def approve_membership(
    group_id: uuid.UUID,
    profile_id: uuid.UUID,
    db: DbSession,
    request: Request,
    user: User = Depends(require_roles(Role.COORDINATOR, Role.ADMIN)),
):
    group = policies.require_group_coordinator(db, user, db.get(FarmerGroup, group_id))
    profile = db.get(FarmerProfile, profile_id)
    if profile is None or profile.farmer_group_id != group.id:
        raise NotFoundError("Membership request not found.")
    profile.membership_status = "member"
    record_audit(
        db,
        actor_user_id=user.id,
        action="farmer_group.membership_approved",
        entity_type="FarmerProfile",
        entity_id=profile.id,
        request=request,
    )
    db.commit()
    return profile


# ---------- farmer verification (coordinator of the farmer's group, or admin) ----------


@router.post("/farmers/{profile_id}/verify", response_model=FarmerProfileOut)
def verify_farmer(
    profile_id: uuid.UUID,
    payload: VerificationDecision,
    db: DbSession,
    request: Request,
    user: User = Depends(require_roles(Role.COORDINATOR, Role.ADMIN)),
):
    profile = db.get(FarmerProfile, profile_id)
    if profile is None:
        raise NotFoundError("Farmer profile not found.")
    if user.role == Role.COORDINATOR:
        group = db.get(FarmerGroup, profile.farmer_group_id) if profile.farmer_group_id else None
        policies.require_group_coordinator(db, user, group)
    before = str(profile.verification_status)
    profile.verification_status = (
        VerificationStatus.VERIFIED if payload.approve else VerificationStatus.REJECTED
    )
    farmer_user = db.get(User, profile.user_id)
    if farmer_user is not None:
        farmer_user.is_verified = payload.approve
        notify(
            db,
            farmer_user,
            "account_verified" if payload.approve else "account_rejected",
            {"reason": payload.reason or "not specified"},
        )
    record_audit(
        db,
        actor_user_id=user.id,
        action="farmer.verification",
        entity_type="FarmerProfile",
        entity_id=profile.id,
        before={"verification_status": before},
        after={"verification_status": str(profile.verification_status)},
        reason=payload.reason,
        request=request,
    )
    db.commit()
    return profile
