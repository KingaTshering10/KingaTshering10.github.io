import uuid
from datetime import timedelta

from fastapi import APIRouter, Request
from sqlalchemy import select

from app.core.config import get_settings
from app.core.deps import CurrentUser, DbSession
from app.core.errors import ConflictError, UnauthorizedError, ValidationFailure
from app.core.ratelimit import enforce_rate_limit
from app.core.security import (
    create_access_token,
    generate_refresh_token,
    hash_password,
    hash_refresh_token,
    password_policy_error,
    verify_password,
)
from app.db.base import utcnow
from app.models import RefreshToken, User
from app.schemas.auth import LoginRequest, RefreshRequest, RegisterRequest, TokenPair, UserOut
from app.services.audit import record_audit
from app.services.notifications import notify

router = APIRouter(prefix="/auth", tags=["auth"])


def _client_key(request: Request) -> str:
    return request.client.host if request.client else "unknown"


def _issue_tokens(db: DbSession, user: User, family_id: uuid.UUID | None = None) -> TokenPair:
    settings = get_settings()
    refresh_value = generate_refresh_token()
    db.add(
        RefreshToken(
            user_id=user.id,
            token_hash=hash_refresh_token(refresh_value),
            family_id=family_id or uuid.uuid4(),
            expires_at=utcnow() + timedelta(days=settings.refresh_token_days),
        )
    )
    return TokenPair(
        access_token=create_access_token(user.id, str(user.role)),
        refresh_token=refresh_value,
    )


@router.post("/register", response_model=UserOut, status_code=201)
def register(payload: RegisterRequest, request: Request, db: DbSession) -> User:
    enforce_rate_limit(f"register:{_client_key(request)}", limit=10, window_seconds=3600)
    if payload.role == "admin":
        raise ValidationFailure("Administrator accounts cannot be self-registered.", field="role")
    policy_error = password_policy_error(payload.password)
    if policy_error:
        raise ValidationFailure(policy_error, code="PASSWORD_POLICY", field="password")
    existing = db.scalars(select(User).where(User.email == payload.email.lower())).first()
    if existing:
        raise ConflictError("An account with this email already exists.", code="EMAIL_TAKEN", field="email")
    user = User(
        email=payload.email.lower(),
        phone=payload.phone,
        password_hash=hash_password(payload.password),
        role=payload.role,
        preferred_language=payload.preferred_language,
    )
    db.add(user)
    db.flush()
    record_audit(
        db,
        actor_user_id=user.id,
        action="user.register",
        entity_type="User",
        entity_id=user.id,
        after={"email_domain": payload.email.split("@")[-1], "role": str(payload.role)},
        request=request,
    )
    notify(db, user, "registration_received", {})
    db.commit()
    return user


@router.post("/login", response_model=TokenPair)
def login(payload: LoginRequest, request: Request, db: DbSession) -> TokenPair:
    enforce_rate_limit(f"login:{_client_key(request)}", limit=20, window_seconds=900)
    enforce_rate_limit(f"login:{payload.email.lower()}", limit=8, window_seconds=900)
    user = db.scalars(select(User).where(User.email == payload.email.lower())).first()
    if user is None or not verify_password(payload.password, user.password_hash):
        raise UnauthorizedError("Invalid email or password.", code="INVALID_CREDENTIALS")
    if not user.is_active:
        raise UnauthorizedError("This account has been suspended.", code="ACCOUNT_SUSPENDED")
    user.last_login_at = utcnow()
    tokens = _issue_tokens(db, user)
    db.commit()
    return tokens


@router.post("/refresh", response_model=TokenPair)
def refresh(payload: RefreshRequest, request: Request, db: DbSession) -> TokenPair:
    enforce_rate_limit(f"refresh:{_client_key(request)}", limit=60, window_seconds=900)
    token_hash = hash_refresh_token(payload.refresh_token)
    stored = db.scalars(select(RefreshToken).where(RefreshToken.token_hash == token_hash)).first()
    if stored is None:
        raise UnauthorizedError("Invalid refresh token.", code="REFRESH_INVALID")
    now = utcnow()
    if stored.revoked_at is not None or stored.used_at is not None:
        # Reuse of a rotated/revoked token → possible theft: revoke the whole family.
        family_tokens = db.scalars(
            select(RefreshToken).where(RefreshToken.family_id == stored.family_id)
        ).all()
        for t in family_tokens:
            t.revoked_at = t.revoked_at or now
        record_audit(
            db,
            actor_user_id=stored.user_id,
            action="auth.refresh_reuse_detected",
            entity_type="RefreshToken",
            entity_id=stored.id,
            reason="Rotated refresh token was presented again; token family revoked.",
            request=request,
        )
        db.commit()
        raise UnauthorizedError("Refresh token is no longer valid.", code="REFRESH_REUSED")
    expires_at = stored.expires_at
    if expires_at.tzinfo is None:
        from datetime import UTC

        expires_at = expires_at.replace(tzinfo=UTC)
    if expires_at < now:
        raise UnauthorizedError("Refresh token expired.", code="REFRESH_EXPIRED")
    user = db.get(User, stored.user_id)
    if user is None or not user.is_active:
        raise UnauthorizedError("Account is not active.", code="ACCOUNT_INACTIVE")
    stored.used_at = now
    tokens = _issue_tokens(db, user, family_id=stored.family_id)
    db.commit()
    return tokens


@router.post("/logout", status_code=204)
def logout(payload: RefreshRequest, user: CurrentUser, db: DbSession) -> None:
    token_hash = hash_refresh_token(payload.refresh_token)
    stored = db.scalars(select(RefreshToken).where(RefreshToken.token_hash == token_hash)).first()
    if stored is not None and stored.user_id == user.id:
        for t in db.scalars(select(RefreshToken).where(RefreshToken.family_id == stored.family_id)):
            t.revoked_at = t.revoked_at or utcnow()
        db.commit()
