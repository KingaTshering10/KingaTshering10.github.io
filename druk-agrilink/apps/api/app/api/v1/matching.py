"""Match proposals and the three-party approval chain.

generated → coordinator_review → farmer_confirmation → buyer_confirmation →
approved. Availability is decremented only at final approval, with a
re-check so competing proposals cannot double-book a listing.
"""

import uuid
from decimal import Decimal

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import select

from app.core import policies
from app.core.deps import CurrentUser, DbSession, require_roles
from app.core.errors import ConflictError, NotFoundError
from app.db.base import utcnow
from app.domain.enums import (
    FarmerResponse,
    HarvestStatus,
    OrderStatus,
    ProposalStatus,
    Role,
)
from app.domain.state_machine import transition_harvest, transition_order, transition_proposal
from app.models import (
    BuyerOrder,
    BuyerOrderItem,
    BuyerOrganization,
    FarmerProfile,
    HarvestListing,
    MatchAllocation,
    MatchProposal,
    Product,
    User,
)
from app.services.audit import record_audit
from app.services.matching import MatchingEngine
from app.services.notifications import notify

router = APIRouter(prefix="/match-proposals", tags=["matching"])


class GenerateRequest(BaseModel):
    buyer_order_item_id: uuid.UUID


class RejectRequest(BaseModel):
    reason: str = Field(min_length=3, max_length=300)


class FarmerDecision(BaseModel):
    accept: bool


def _proposal_out(db, proposal: MatchProposal) -> dict:
    allocations = db.scalars(
        select(MatchAllocation).where(MatchAllocation.match_proposal_id == proposal.id)
    ).all()
    item = db.get(BuyerOrderItem, proposal.buyer_order_item_id)
    product = db.get(Product, item.product_id) if item else None
    return {
        "id": str(proposal.id),
        "buyer_order_item_id": str(proposal.buyer_order_item_id),
        "buyer_order_id": str(item.buyer_order_id) if item else None,
        "product_name": product.name if product else None,
        "proposed_quantity": str(proposal.proposed_quantity),
        "unit": str(item.unit) if item else "kg",
        "estimated_transport_cost": (
            str(proposal.estimated_transport_cost) if proposal.estimated_transport_cost is not None else None
        ),
        "estimated_delivery_time_hours": (
            str(proposal.estimated_delivery_time_hours)
            if proposal.estimated_delivery_time_hours is not None
            else None
        ),
        "estimated_spoilage_risk": proposal.estimated_spoilage_risk,
        "matching_method": proposal.matching_method,
        "score": proposal.score,
        "score_factors": proposal.score_factors,
        "score_explanation": proposal.score_explanation,
        "status": str(proposal.status),
        "created_at": proposal.created_at.isoformat(),
        "allocations": [
            {
                "id": str(a.id),
                "harvest_listing_id": str(a.harvest_listing_id),
                "allocated_quantity": str(a.allocated_quantity),
                "agreed_unit_price": str(a.agreed_unit_price),
                "farmer_response": str(a.farmer_response),
            }
            for a in allocations
        ],
    }


@router.post("/generate", status_code=201)
def generate(
    payload: GenerateRequest,
    db: DbSession,
    user: User = Depends(require_roles(Role.COORDINATOR, Role.ADMIN)),
):
    engine = MatchingEngine(db)
    proposals = engine.generate_proposals(payload.buyer_order_item_id, created_by=user.id)
    db.commit()
    return {"proposals": [_proposal_out(db, p) for p in proposals], "count": len(proposals)}


@router.get("")
def list_proposals(db: DbSession, user: CurrentUser, status: ProposalStatus | None = None):
    query = select(MatchProposal)
    if user.role in (Role.COORDINATOR, Role.ADMIN):
        pass  # coordinators review all open proposals
    elif user.role == Role.BUYER:
        org = policies.get_buyer_organization(db, user)
        order_ids = select(BuyerOrder.id).where(BuyerOrder.buyer_organization_id == org.id)
        item_ids = select(BuyerOrderItem.id).where(BuyerOrderItem.buyer_order_id.in_(order_ids))
        query = query.where(MatchProposal.buyer_order_item_id.in_(item_ids))
    elif user.role == Role.FARMER:
        profile = policies.get_farmer_profile(db, user)
        listing_ids = select(HarvestListing.id).where(HarvestListing.farmer_id == profile.id)
        prop_ids = select(MatchAllocation.match_proposal_id).where(
            MatchAllocation.harvest_listing_id.in_(listing_ids)
        )
        query = query.where(MatchProposal.id.in_(prop_ids))
    else:
        return []
    if status:
        query = query.where(MatchProposal.status == status)
    proposals = db.scalars(query.order_by(MatchProposal.created_at.desc())).all()
    return [_proposal_out(db, p) for p in proposals]


def _get_proposal_for(db, user, proposal_id: uuid.UUID) -> MatchProposal:
    proposal = db.get(MatchProposal, proposal_id)
    if proposal is None:
        raise NotFoundError("Proposal not found.")
    if user.role in (Role.COORDINATOR, Role.ADMIN):
        return proposal
    if user.role == Role.BUYER:
        item = db.get(BuyerOrderItem, proposal.buyer_order_item_id)
        order = db.get(BuyerOrder, item.buyer_order_id) if item else None
        if order is not None:
            org = db.get(BuyerOrganization, order.buyer_organization_id)
            if org is not None and org.owner_user_id == user.id:
                return proposal
    if user.role == Role.FARMER:
        profile = db.scalars(select(FarmerProfile).where(FarmerProfile.user_id == user.id)).first()
        if profile is not None:
            allocation = db.scalars(
                select(MatchAllocation)
                .join(HarvestListing, MatchAllocation.harvest_listing_id == HarvestListing.id)
                .where(
                    MatchAllocation.match_proposal_id == proposal.id,
                    HarvestListing.farmer_id == profile.id,
                )
            ).first()
            if allocation is not None:
                return proposal
    raise NotFoundError("Proposal not found.")


@router.get("/{proposal_id}")
def get_proposal(proposal_id: uuid.UUID, db: DbSession, user: CurrentUser):
    return _proposal_out(db, _get_proposal_for(db, user, proposal_id))


@router.post("/{proposal_id}/send-to-review")
def send_to_review(
    proposal_id: uuid.UUID,
    db: DbSession,
    user: User = Depends(require_roles(Role.COORDINATOR, Role.ADMIN)),
):
    proposal = _get_proposal_for(db, user, proposal_id)
    transition_proposal(proposal.status, ProposalStatus.COORDINATOR_REVIEW)
    proposal.status = ProposalStatus.COORDINATOR_REVIEW
    db.commit()
    return _proposal_out(db, proposal)


@router.post("/{proposal_id}/send-to-farmers")
def send_to_farmers(
    proposal_id: uuid.UUID,
    db: DbSession,
    user: User = Depends(require_roles(Role.COORDINATOR, Role.ADMIN)),
):
    proposal = _get_proposal_for(db, user, proposal_id)
    transition_proposal(proposal.status, ProposalStatus.FARMER_CONFIRMATION)
    proposal.status = ProposalStatus.FARMER_CONFIRMATION
    item = db.get(BuyerOrderItem, proposal.buyer_order_item_id)
    product = db.get(Product, item.product_id) if item else None
    allocations = db.scalars(
        select(MatchAllocation).where(MatchAllocation.match_proposal_id == proposal.id)
    ).all()
    for allocation in allocations:
        listing = db.get(HarvestListing, allocation.harvest_listing_id)
        profile = db.get(FarmerProfile, listing.farmer_id) if listing else None
        farmer_user = db.get(User, profile.user_id) if profile else None
        if farmer_user is not None:
            notify(
                db,
                farmer_user,
                "farmer_response_required",
                {
                    "quantity": allocation.allocated_quantity,
                    "unit": str(item.unit) if item else "kg",
                    "product": product.name if product else "produce",
                    "price": allocation.agreed_unit_price,
                },
            )
    db.commit()
    return _proposal_out(db, proposal)


@router.post("/allocations/{allocation_id}/respond")
def farmer_respond(
    allocation_id: uuid.UUID,
    payload: FarmerDecision,
    db: DbSession,
    user: User = Depends(require_roles(Role.FARMER)),
):
    allocation = db.get(MatchAllocation, allocation_id)
    if allocation is None:
        raise NotFoundError("Allocation not found.")
    profile = policies.get_farmer_profile(db, user)
    listing = db.get(HarvestListing, allocation.harvest_listing_id)
    if listing is None or listing.farmer_id != profile.id:
        raise NotFoundError("Allocation not found.")
    proposal = db.get(MatchProposal, allocation.match_proposal_id)
    assert proposal is not None
    if proposal.status != ProposalStatus.FARMER_CONFIRMATION:
        raise ConflictError("This proposal is not awaiting farmer confirmation.", code="PROPOSAL_NOT_OPEN")
    if allocation.farmer_response != FarmerResponse.PENDING:
        raise ConflictError("You have already responded.", code="ALREADY_RESPONDED")

    allocation.farmer_response = FarmerResponse.ACCEPTED if payload.accept else FarmerResponse.DECLINED
    allocation.farmer_response_at = utcnow()

    siblings = db.scalars(
        select(MatchAllocation).where(MatchAllocation.match_proposal_id == proposal.id)
    ).all()
    if any(a.farmer_response == FarmerResponse.DECLINED for a in siblings):
        transition_proposal(proposal.status, ProposalStatus.REJECTED)
        proposal.status = ProposalStatus.REJECTED
    elif all(a.farmer_response == FarmerResponse.ACCEPTED for a in siblings):
        transition_proposal(proposal.status, ProposalStatus.BUYER_CONFIRMATION)
        proposal.status = ProposalStatus.BUYER_CONFIRMATION
        item = db.get(BuyerOrderItem, proposal.buyer_order_item_id)
        order = db.get(BuyerOrder, item.buyer_order_id) if item else None
        if order is not None:
            transition_order(order.order_status, OrderStatus.PROPOSED)
            order.order_status = OrderStatus.PROPOSED
            org = db.get(BuyerOrganization, order.buyer_organization_id)
            owner = db.get(User, org.owner_user_id) if org else None
            if owner is not None:
                notify(db, owner, "buyer_response_required", {})
    db.commit()
    return _proposal_out(db, proposal)


@router.post("/{proposal_id}/buyer-approve")
def buyer_approve(
    proposal_id: uuid.UUID,
    db: DbSession,
    user: User = Depends(require_roles(Role.BUYER)),
):
    proposal = _get_proposal_for(db, user, proposal_id)
    transition_proposal(proposal.status, ProposalStatus.APPROVED)

    # availability re-check + decrement inside the same transaction
    allocations = db.scalars(
        select(MatchAllocation).where(MatchAllocation.match_proposal_id == proposal.id)
    ).all()
    item = db.get(BuyerOrderItem, proposal.buyer_order_item_id)
    product = db.get(Product, item.product_id) if item else None
    for allocation in allocations:
        listing = db.get(HarvestListing, allocation.harvest_listing_id)
        assert listing is not None
        if listing.available_quantity < allocation.allocated_quantity:
            raise ConflictError(
                "A listing in this proposal no longer has enough available quantity; regenerate the match.",
                code="AVAILABILITY_CHANGED",
            )
    for allocation in allocations:
        listing = db.get(HarvestListing, allocation.harvest_listing_id)
        assert listing is not None
        listing.available_quantity = listing.available_quantity - allocation.allocated_quantity
        target = (
            HarvestStatus.FULLY_ALLOCATED
            if listing.available_quantity == Decimal("0")
            else HarvestStatus.PARTIALLY_ALLOCATED
        )
        if listing.status != target:
            transition_harvest(listing.status, target)
            listing.status = target
        listing.row_version += 1
        profile = db.get(FarmerProfile, listing.farmer_id)
        farmer_user = db.get(User, profile.user_id) if profile else None
        if farmer_user is not None:
            notify(db, farmer_user, "match_approved", {"product": product.name if product else "produce"})

    proposal.status = ProposalStatus.APPROVED
    proposal.approved_by = user.id
    order = db.get(BuyerOrder, item.buyer_order_id) if item else None
    if order is not None:
        transition_order(order.order_status, OrderStatus.CONFIRMED)
        order.order_status = OrderStatus.CONFIRMED
    record_audit(
        db,
        actor_user_id=user.id,
        action="match_proposal.approved",
        entity_type="MatchProposal",
        entity_id=proposal.id,
        after={"score": proposal.score, "proposed_quantity": str(proposal.proposed_quantity)},
    )
    db.commit()
    return _proposal_out(db, proposal)


@router.post("/{proposal_id}/reject")
def reject_proposal(
    proposal_id: uuid.UUID,
    payload: RejectRequest,
    db: DbSession,
    user: User = Depends(require_roles(Role.BUYER, Role.COORDINATOR, Role.ADMIN)),
):
    proposal = _get_proposal_for(db, user, proposal_id)
    transition_proposal(proposal.status, ProposalStatus.REJECTED)
    proposal.status = ProposalStatus.REJECTED
    item = db.get(BuyerOrderItem, proposal.buyer_order_item_id)
    product = db.get(Product, item.product_id) if item else None
    allocations = db.scalars(
        select(MatchAllocation).where(MatchAllocation.match_proposal_id == proposal.id)
    ).all()
    for allocation in allocations:
        listing = db.get(HarvestListing, allocation.harvest_listing_id)
        profile = db.get(FarmerProfile, listing.farmer_id) if listing else None
        farmer_user = db.get(User, profile.user_id) if profile else None
        if farmer_user is not None:
            notify(
                db,
                farmer_user,
                "match_rejected",
                {"product": product.name if product else "produce", "reason": payload.reason},
            )
    record_audit(
        db,
        actor_user_id=user.id,
        action="match_proposal.rejected",
        entity_type="MatchProposal",
        entity_id=proposal.id,
        reason=payload.reason,
    )
    db.commit()
    return _proposal_out(db, proposal)
