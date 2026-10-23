"""Payment obligation tracking and dispute management. No money moves here —
status changes require evidence (method, reference, date, authorised recorder)."""

import uuid
from datetime import date, datetime
from decimal import Decimal

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import select

from app.core import policies
from app.core.deps import CurrentUser, DbSession, require_roles
from app.core.errors import ConflictError, NotFoundError, ValidationFailure
from app.db.base import utcnow
from app.domain.enums import (
    DisputeCategory,
    DisputeStatus,
    OrderStatus,
    PartyType,
    PaymentStatus,
    Role,
)
from app.domain.state_machine import transition_order
from app.models import (
    BuyerOrder,
    BuyerOrganization,
    Dispute,
    FarmerProfile,
    PaymentRecord,
    TransportProvider,
    User,
)
from app.services.audit import record_audit
from app.services.notifications import notify

router = APIRouter(tags=["payments"])


class PaymentReceipt(BaseModel):
    amount: Decimal = Field(gt=0)
    payment_method: str = Field(min_length=2, max_length=40)
    payment_reference: str = Field(min_length=2, max_length=120)
    paid_at: datetime


def _payment_out(payment: PaymentRecord) -> dict:
    return {
        "id": str(payment.id),
        "payer_type": str(payment.payer_type),
        "payer_id": str(payment.payer_id) if payment.payer_id else None,
        "recipient_type": str(payment.recipient_type),
        "recipient_id": str(payment.recipient_id) if payment.recipient_id else None,
        "related_order_id": str(payment.related_order_id) if payment.related_order_id else None,
        "related_collection_id": (
            str(payment.related_collection_id) if payment.related_collection_id else None
        ),
        "amount": str(payment.amount),
        "amount_paid": str(payment.amount_paid),
        "currency": payment.currency,
        "due_date": payment.due_date.isoformat() if payment.due_date else None,
        "status": str(payment.status),
        "payment_method": payment.payment_method,
        "payment_reference": payment.payment_reference,
        "paid_at": payment.paid_at.isoformat() if payment.paid_at else None,
    }


def _refresh_overdue(db, payments: list[PaymentRecord]) -> None:
    today = date.today()
    for payment in payments:
        if (
            payment.status == PaymentStatus.PENDING
            and payment.due_date is not None
            and payment.due_date < today
        ):
            payment.status = PaymentStatus.OVERDUE


@router.get("/payments")
def list_payments(db: DbSession, user: CurrentUser, status: PaymentStatus | None = None):
    query = select(PaymentRecord)
    if user.role == Role.FARMER:
        profile = policies.get_farmer_profile(db, user)
        query = query.where(
            PaymentRecord.recipient_type == PartyType.FARMER,
            PaymentRecord.recipient_id == profile.id,
        )
    elif user.role == Role.BUYER:
        org = policies.get_buyer_organization(db, user)
        query = query.where(PaymentRecord.payer_id == org.id)
    elif user.role == Role.TRANSPORTER:
        provider = policies.get_transport_provider(db, user)
        query = query.where(
            PaymentRecord.recipient_type == PartyType.TRANSPORT_PROVIDER,
            PaymentRecord.recipient_id == provider.id,
        )
    elif user.role not in (Role.COORDINATOR, Role.ADMIN):
        return []
    payments = list(db.scalars(query.order_by(PaymentRecord.due_date)))
    _refresh_overdue(db, payments)
    db.commit()
    if status:
        payments = [p for p in payments if p.status == status]
    return [_payment_out(p) for p in payments]


@router.get("/payments/{payment_id}")
def get_payment(payment_id: uuid.UUID, db: DbSession, user: CurrentUser):
    payment = policies.can_view_payment(db, user, db.get(PaymentRecord, payment_id))
    _refresh_overdue(db, [payment])
    db.commit()
    return _payment_out(payment)


@router.post("/payments/{payment_id}/record")
def record_payment(
    payment_id: uuid.UUID,
    payload: PaymentReceipt,
    db: DbSession,
    user: User = Depends(require_roles(Role.COORDINATOR, Role.ADMIN, Role.BUYER)),
):
    payment = policies.can_view_payment(db, user, db.get(PaymentRecord, payment_id))
    if user.role == Role.BUYER:
        org = policies.get_buyer_organization(db, user)
        if payment.payer_id != org.id:
            raise NotFoundError("Resource not found.")
    if payment.status in (PaymentStatus.PAID, PaymentStatus.CANCELLED, PaymentStatus.WAIVED):
        raise ConflictError("This payment is already settled.", code="PAYMENT_SETTLED")
    if payload.amount > payment.amount - payment.amount_paid:
        raise ValidationFailure(
            "Recorded amount exceeds the outstanding balance.",
            code="AMOUNT_EXCEEDS_BALANCE",
            field="amount",
        )
    payment.amount_paid = payment.amount_paid + payload.amount
    payment.payment_method = payload.payment_method
    payment.payment_reference = payload.payment_reference
    payment.paid_at = payload.paid_at
    payment.recorded_by = user.id
    payment.status = (
        PaymentStatus.PAID if payment.amount_paid == payment.amount else PaymentStatus.PARTIALLY_PAID
    )
    record_audit(
        db,
        actor_user_id=user.id,
        action="payment.recorded",
        entity_type="PaymentRecord",
        entity_id=payment.id,
        after={
            "amount": str(payload.amount),
            "method": payload.payment_method,
            "reference": payload.payment_reference,
            "status": str(payment.status),
        },
    )
    _notify_recipient(db, payment, payload)
    _maybe_complete_order(db, payment)
    db.commit()
    return _payment_out(payment)


def _notify_recipient(db, payment: PaymentRecord, payload: PaymentReceipt) -> None:
    target_user: User | None = None
    if payment.recipient_type == PartyType.FARMER and payment.recipient_id:
        profile = db.get(FarmerProfile, payment.recipient_id)
        target_user = db.get(User, profile.user_id) if profile else None
    elif payment.recipient_type == PartyType.TRANSPORT_PROVIDER and payment.recipient_id:
        provider = db.get(TransportProvider, payment.recipient_id)
        target_user = db.get(User, provider.owner_user_id) if provider else None
    elif payment.recipient_type == PartyType.BUYER_ORGANIZATION and payment.recipient_id:
        org = db.get(BuyerOrganization, payment.recipient_id)
        target_user = db.get(User, org.owner_user_id) if org else None
    if target_user is not None:
        notify(
            db,
            target_user,
            "payment_received",
            {"amount": payload.amount, "reference": payload.payment_reference},
        )


def _maybe_complete_order(db, payment: PaymentRecord) -> None:
    if payment.related_order_id is None:
        return
    siblings = db.scalars(
        select(PaymentRecord).where(PaymentRecord.related_order_id == payment.related_order_id)
    ).all()
    if all(s.status in (PaymentStatus.PAID, PaymentStatus.WAIVED, PaymentStatus.CANCELLED) for s in siblings):
        order = db.get(BuyerOrder, payment.related_order_id)
        if order is not None and order.order_status == OrderStatus.PAYMENT_PENDING:
            transition_order(order.order_status, OrderStatus.COMPLETED)
            order.order_status = OrderStatus.COMPLETED


# ---------- disputes ----------


class DisputeCreate(BaseModel):
    related_entity_type: str = Field(min_length=2, max_length=40)
    related_entity_id: uuid.UUID
    category: DisputeCategory
    description: str = Field(min_length=10, max_length=2000)


class DisputeResolve(BaseModel):
    resolution: str = Field(min_length=5, max_length=2000)


def _dispute_out(dispute: Dispute) -> dict:
    return {
        "id": str(dispute.id),
        "raised_by": str(dispute.raised_by),
        "related_entity_type": dispute.related_entity_type,
        "related_entity_id": str(dispute.related_entity_id),
        "category": str(dispute.category),
        "description": dispute.description,
        "status": str(dispute.status),
        "assigned_to": str(dispute.assigned_to) if dispute.assigned_to else None,
        "resolution": dispute.resolution,
        "resolved_at": dispute.resolved_at.isoformat() if dispute.resolved_at else None,
        "created_at": dispute.created_at.isoformat(),
    }


@router.post("/disputes", status_code=201)
def open_dispute(payload: DisputeCreate, db: DbSession, user: CurrentUser):
    dispute = Dispute(raised_by=user.id, **payload.model_dump())
    db.add(dispute)
    db.flush()
    notify(db, user, "dispute_opened", {"category": str(payload.category)})
    record_audit(
        db,
        actor_user_id=user.id,
        action="dispute.opened",
        entity_type="Dispute",
        entity_id=dispute.id,
        after={"category": str(payload.category)},
    )
    db.commit()
    return _dispute_out(dispute)


@router.get("/disputes")
def list_disputes(db: DbSession, user: CurrentUser, status: DisputeStatus | None = None):
    query = select(Dispute)
    if user.role not in (Role.COORDINATOR, Role.ADMIN):
        query = query.where(Dispute.raised_by == user.id)
    if status:
        query = query.where(Dispute.status == status)
    return [_dispute_out(d) for d in db.scalars(query.order_by(Dispute.created_at.desc()))]


@router.get("/disputes/{dispute_id}")
def get_dispute(dispute_id: uuid.UUID, db: DbSession, user: CurrentUser):
    dispute = db.get(Dispute, dispute_id)
    if dispute is None:
        raise NotFoundError("Dispute not found.")
    if user.role not in (Role.COORDINATOR, Role.ADMIN) and dispute.raised_by != user.id:
        raise NotFoundError("Dispute not found.")
    return _dispute_out(dispute)


@router.post("/disputes/{dispute_id}/assign")
def assign_dispute(
    dispute_id: uuid.UUID,
    db: DbSession,
    user: User = Depends(require_roles(Role.COORDINATOR, Role.ADMIN)),
):
    dispute = db.get(Dispute, dispute_id)
    if dispute is None:
        raise NotFoundError("Dispute not found.")
    if dispute.status != DisputeStatus.OPEN:
        raise ConflictError("Only open disputes can be assigned.", code="DISPUTE_NOT_OPEN")
    dispute.status = DisputeStatus.UNDER_REVIEW
    dispute.assigned_to = user.id
    raiser = db.get(User, dispute.raised_by)
    if raiser is not None:
        notify(db, raiser, "dispute_updated", {"dispute": str(dispute.id)[:8], "status": "under review"})
    db.commit()
    return _dispute_out(dispute)


@router.post("/disputes/{dispute_id}/resolve")
def resolve_dispute(
    dispute_id: uuid.UUID,
    payload: DisputeResolve,
    db: DbSession,
    user: User = Depends(require_roles(Role.COORDINATOR, Role.ADMIN)),
):
    dispute = db.get(Dispute, dispute_id)
    if dispute is None:
        raise NotFoundError("Dispute not found.")
    if dispute.status not in (DisputeStatus.OPEN, DisputeStatus.UNDER_REVIEW):
        raise ConflictError("This dispute is already closed.", code="DISPUTE_CLOSED")
    dispute.status = DisputeStatus.RESOLVED
    dispute.resolution = payload.resolution
    dispute.resolved_at = utcnow()
    raiser = db.get(User, dispute.raised_by)
    if raiser is not None:
        notify(
            db,
            raiser,
            "dispute_resolved",
            {"dispute": str(dispute.id)[:8], "resolution": payload.resolution[:120]},
        )
    record_audit(
        db,
        actor_user_id=user.id,
        action="dispute.resolved",
        entity_type="Dispute",
        entity_id=dispute.id,
        reason=payload.resolution[:300],
    )
    db.commit()
    return _dispute_out(dispute)
