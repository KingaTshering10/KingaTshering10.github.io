"""Append-only audit trail for sensitive actions.

Snapshots are sanitised: secret-like keys are stripped so passwords, tokens,
and hashes can never enter the audit table.
"""

import uuid
from typing import Any

from fastapi import Request
from sqlalchemy.orm import Session

from app.models import AuditLog

_SENSITIVE_KEYS = {"password", "password_hash", "token", "token_hash", "secret", "authorization"}


def _sanitise(state: dict[str, Any] | None) -> dict[str, Any] | None:
    if state is None:
        return None
    return {
        k: ("[redacted]" if any(s in k.lower() for s in _SENSITIVE_KEYS) else _to_plain(v))
        for k, v in state.items()
    }


def _to_plain(value: Any) -> Any:
    if isinstance(value, str | int | float | bool) or value is None:
        return value
    return str(value)


def record_audit(
    db: Session,
    *,
    actor_user_id: uuid.UUID | None,
    action: str,
    entity_type: str,
    entity_id: uuid.UUID | None,
    before: dict[str, Any] | None = None,
    after: dict[str, Any] | None = None,
    reason: str | None = None,
    request: Request | None = None,
) -> AuditLog:
    entry = AuditLog(
        actor_user_id=actor_user_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        before_state=_sanitise(before),
        after_state=_sanitise(after),
        reason=reason,
        ip_address=request.client.host if request is not None and request.client else None,
        user_agent=(request.headers.get("user-agent", "")[:200] or None) if request is not None else None,
    )
    db.add(entry)
    return entry
