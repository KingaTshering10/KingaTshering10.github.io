"""In-app notification centre."""

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select

from app.core.deps import CurrentUser, DbSession
from app.core.errors import NotFoundError
from app.db.base import utcnow
from app.domain.enums import NotificationChannel
from app.models import Notification
from app.schemas.common import Page, PageParams

router = APIRouter(prefix="/notifications", tags=["notifications"])


def _out(n: Notification) -> dict:
    return {
        "id": str(n.id),
        "template_key": n.template_key,
        "subject": n.subject,
        "body": n.body,
        "channel": str(n.channel),
        "status": str(n.status),
        "sent_at": n.sent_at.isoformat() if n.sent_at else None,
        "read_at": n.read_at.isoformat() if n.read_at else None,
        "created_at": n.created_at.isoformat(),
    }


@router.get("")
def my_notifications(
    db: DbSession,
    user: CurrentUser,
    params: PageParams = Depends(),
    unread_only: bool = Query(False),
):
    query = select(Notification).where(
        Notification.user_id == user.id,
        Notification.channel == NotificationChannel.IN_APP,
    )
    if unread_only:
        query = query.where(Notification.read_at.is_(None))
    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    items = db.scalars(
        query.order_by(Notification.created_at.desc()).offset(params.offset).limit(params.page_size)
    ).all()
    return Page(items=[_out(n) for n in items], total=total, page=params.page, page_size=params.page_size)


@router.get("/unread-count")
def unread_count(db: DbSession, user: CurrentUser):
    count = (
        db.scalar(
            select(func.count())
            .select_from(Notification)
            .where(
                Notification.user_id == user.id,
                Notification.channel == NotificationChannel.IN_APP,
                Notification.read_at.is_(None),
            )
        )
        or 0
    )
    return {"unread": count}


@router.post("/{notification_id}/read")
def mark_read(notification_id: uuid.UUID, db: DbSession, user: CurrentUser):
    notification = db.get(Notification, notification_id)
    if notification is None or notification.user_id != user.id:
        raise NotFoundError("Notification not found.")
    notification.read_at = notification.read_at or utcnow()
    db.commit()
    return _out(notification)


@router.post("/read-all")
def mark_all_read(db: DbSession, user: CurrentUser):
    now = utcnow()
    unread = db.scalars(
        select(Notification).where(
            Notification.user_id == user.id,
            Notification.channel == NotificationChannel.IN_APP,
            Notification.read_at.is_(None),
        )
    ).all()
    for n in unread:
        n.read_at = now
    db.commit()
    return {"marked_read": len(unread)}
