"""Buyer organizations and procurement orders."""

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select

from app.core import policies
from app.core.deps import CurrentUser, DbSession, require_roles
from app.core.errors import ConflictError, NotFoundError, ValidationFailure
from app.domain.enums import OrderStatus, Role
from app.domain.state_machine import transition_order
from app.models import BuyerOrder, BuyerOrderItem, BuyerOrganization, Location, Product, User
from app.schemas.buyer import BuyerOrgCreate, BuyerOrgOut, OrderCreate, OrderDetailOut, OrderOut

router = APIRouter(tags=["buyers"])


@router.post("/buyers/organization", response_model=BuyerOrgOut, status_code=201)
def create_organization(
    payload: BuyerOrgCreate,
    db: DbSession,
    user: User = Depends(require_roles(Role.BUYER)),
):
    existing = db.scalars(select(BuyerOrganization).where(BuyerOrganization.owner_user_id == user.id)).first()
    if existing:
        raise ConflictError("Organization already exists for this account.", code="ORGANIZATION_EXISTS")
    org = BuyerOrganization(owner_user_id=user.id, **payload.model_dump())
    db.add(org)
    db.commit()
    return org


@router.get("/buyers/organization", response_model=BuyerOrgOut)
def my_organization(db: DbSession, user: User = Depends(require_roles(Role.BUYER))):
    return policies.get_buyer_organization(db, user)


@router.post("/buyer-orders", response_model=OrderDetailOut, status_code=201)
def create_order(
    payload: OrderCreate,
    db: DbSession,
    user: User = Depends(require_roles(Role.BUYER)),
):
    org = policies.get_buyer_organization(db, user)
    if db.get(Location, payload.delivery_location_id) is None:
        raise ValidationFailure("Unknown delivery location.", field="delivery_location_id")
    for index, item in enumerate(payload.items):
        if db.get(Product, item.product_id) is None:
            raise ValidationFailure("Unknown product.", field=f"items.{index}.product_id")

    status = OrderStatus.DRAFT
    if not payload.save_as_draft:
        policies.require_verified(str(org.verification_status), "Buyer organization")
        status = OrderStatus.PUBLISHED

    order = BuyerOrder(
        buyer_organization_id=org.id,
        delivery_location_id=payload.delivery_location_id,
        required_delivery_date=payload.required_delivery_date,
        order_status=status,
        payment_terms=payload.payment_terms,
        special_instructions=payload.special_instructions,
        created_by=user.id,
    )
    db.add(order)
    db.flush()
    for item in payload.items:
        db.add(BuyerOrderItem(buyer_order_id=order.id, **item.model_dump()))
    db.commit()
    return _order_detail(db, order)


def _order_detail(db, order: BuyerOrder) -> dict:
    items = db.scalars(select(BuyerOrderItem).where(BuyerOrderItem.buyer_order_id == order.id)).all()
    data = {c: getattr(order, c) for c in OrderOut.model_fields}
    data["items"] = items
    return data


@router.get("/buyer-orders", response_model=list[OrderOut])
def list_orders(
    db: DbSession,
    user: CurrentUser,
    status: OrderStatus | None = Query(None),
):
    if user.role == Role.BUYER:
        org = policies.get_buyer_organization(db, user)
        query = select(BuyerOrder).where(BuyerOrder.buyer_organization_id == org.id)
    elif user.role in (Role.COORDINATOR, Role.ADMIN):
        # Coordinators see published demand so they can aggregate supply.
        query = select(BuyerOrder).where(BuyerOrder.order_status != OrderStatus.DRAFT)
    else:
        return []
    if status:
        query = query.where(BuyerOrder.order_status == status)
    return db.scalars(query.order_by(BuyerOrder.required_delivery_date)).all()


@router.get("/buyer-orders/{order_id}", response_model=OrderDetailOut)
def get_order(order_id: uuid.UUID, db: DbSession, user: CurrentUser):
    order = policies.can_manage_order(db, user, db.get(BuyerOrder, order_id))
    if user.role == Role.COORDINATOR and order.order_status == OrderStatus.DRAFT:
        raise NotFoundError("Resource not found.")
    return _order_detail(db, order)


@router.post("/buyer-orders/{order_id}/publish", response_model=OrderDetailOut)
def publish_order(order_id: uuid.UUID, db: DbSession, user: User = Depends(require_roles(Role.BUYER))):
    order = policies.can_edit_order(db, user, db.get(BuyerOrder, order_id))
    org = db.get(BuyerOrganization, order.buyer_organization_id)
    assert org is not None
    policies.require_verified(str(org.verification_status), "Buyer organization")
    transition_order(order.order_status, OrderStatus.PUBLISHED)
    order.order_status = OrderStatus.PUBLISHED
    db.commit()
    return _order_detail(db, order)


@router.post("/buyer-orders/{order_id}/cancel", response_model=OrderDetailOut)
def cancel_order(order_id: uuid.UUID, db: DbSession, user: CurrentUser):
    order = policies.can_edit_order(db, user, db.get(BuyerOrder, order_id))
    transition_order(order.order_status, OrderStatus.CANCELLED)
    order.order_status = OrderStatus.CANCELLED
    db.commit()
    return _order_detail(db, order)
