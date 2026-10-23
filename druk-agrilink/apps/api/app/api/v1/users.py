from fastapi import APIRouter, Request
from sqlalchemy import select

from app.core.deps import CurrentUser, DbSession
from app.models import NotificationPreference
from app.schemas.auth import DeactivationRequest, UserOut, UserUpdate
from app.services.audit import record_audit

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserOut)
def me(user: CurrentUser):
    return user


@router.patch("/me", response_model=UserOut)
def update_me(payload: UserUpdate, user: CurrentUser, db: DbSession):
    if payload.phone is not None:
        user.phone = payload.phone
    if payload.preferred_language is not None:
        user.preferred_language = payload.preferred_language
    db.commit()
    return user


@router.post("/me/deactivation-request", status_code=202)
def request_deactivation(payload: DeactivationRequest, user: CurrentUser, db: DbSession, request: Request):
    record_audit(
        db,
        actor_user_id=user.id,
        action="user.deactivation_requested",
        entity_type="User",
        entity_id=user.id,
        reason=payload.reason,
        request=request,
    )
    db.commit()
    return {"status": "received", "message": "An administrator will review your deactivation request."}


@router.get("/me/notification-preferences")
def get_preferences(user: CurrentUser, db: DbSession):
    prefs = db.scalars(
        select(NotificationPreference).where(NotificationPreference.user_id == user.id)
    ).first()
    return {
        "email_enabled": prefs.email_enabled if prefs else True,
        "sms_enabled": prefs.sms_enabled if prefs else True,
        "push_enabled": prefs.push_enabled if prefs else False,
        "note": "Essential security and transaction notifications cannot be disabled.",
    }


@router.put("/me/notification-preferences")
def set_preferences(payload: dict, user: CurrentUser, db: DbSession):
    prefs = db.scalars(
        select(NotificationPreference).where(NotificationPreference.user_id == user.id)
    ).first()
    if prefs is None:
        prefs = NotificationPreference(user_id=user.id)
        db.add(prefs)
    prefs.email_enabled = bool(payload.get("email_enabled", prefs.email_enabled))
    prefs.sms_enabled = bool(payload.get("sms_enabled", prefs.sms_enabled))
    prefs.push_enabled = bool(payload.get("push_enabled", prefs.push_enabled))
    db.commit()
    return {"status": "saved"}
