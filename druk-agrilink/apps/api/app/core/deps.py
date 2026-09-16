"""FastAPI dependencies: DB session, current user, role guards."""

import uuid
from typing import Annotated

import jwt as pyjwt
from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.errors import ForbiddenError, UnauthorizedError
from app.core.security import decode_access_token
from app.db.session import get_db
from app.domain.enums import Role
from app.models import User

bearer_scheme = HTTPBearer(auto_error=False)

DbSession = Annotated[Session, Depends(get_db)]


def get_current_user(
    request: Request,
    db: DbSession,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)] = None,
) -> User:
    if credentials is None:
        raise UnauthorizedError("Authentication required.", code="AUTH_REQUIRED")
    try:
        payload = decode_access_token(credentials.credentials)
    except pyjwt.ExpiredSignatureError as exc:
        raise UnauthorizedError("Access token expired.", code="TOKEN_EXPIRED") from exc
    except pyjwt.InvalidTokenError as exc:
        raise UnauthorizedError("Invalid access token.", code="TOKEN_INVALID") from exc
    if payload.get("type") != "access":
        raise UnauthorizedError("Invalid token type.", code="TOKEN_INVALID")
    user = db.get(User, uuid.UUID(payload["sub"]))
    if user is None or not user.is_active:
        raise UnauthorizedError("Account is not active.", code="ACCOUNT_INACTIVE")
    request.state.user_id = str(user.id)
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def require_roles(*roles: Role):
    def checker(user: CurrentUser) -> User:
        if user.role not in roles:
            raise ForbiddenError("You do not have permission to perform this action.", code="ROLE_FORBIDDEN")
        return user

    return checker
