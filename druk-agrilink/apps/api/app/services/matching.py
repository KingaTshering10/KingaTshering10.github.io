"""Deterministic, explainable supply–demand matching engine.

Pipeline (each stage is a separate function so it can be tested alone):

1. hard constraints  — filter listings that could never satisfy the item
2. grouping          — cluster candidates by collection area (dzongkhag)
3. allocation        — greedy fill: cheapest asking price first, then larger
                       available quantity, then older listing (deterministic)
4. scoring           — weighted 0–100 factors
5. explanation       — plain-language sentences for every proposal

Nothing here auto-approves: generated proposals still require coordinator,
farmer, and buyer confirmation plus transport feasibility.
"""

import uuid
from dataclasses import dataclass
from datetime import date
from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import ConflictError, NotFoundError
from app.domain.enums import (
    HarvestStatus,
    OrderStatus,
    ProposalStatus,
    VerificationStatus,
)
from app.models import (
    BuyerOrder,
    BuyerOrderItem,
    BuyerOrganization,
    Farm,
    FarmerProfile,
    HarvestListing,
    Location,
    MatchAllocation,
    MatchProposal,
    QualityGrade,
)
from app.services.routing import RoutePoint, estimate_transport_cost, get_router

MATCHABLE_STATUSES = (HarvestStatus.CONFIRMED, HarvestStatus.PARTIALLY_ALLOCATED)


@dataclass
class Candidate:
    listing: HarvestListing
    farm: Farm
    profile: FarmerProfile


@dataclass
class AllocationPlan:
    listing: HarvestListing
    quantity: Decimal
    unit_price: Decimal


def _q2(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


class MatchingEngine:
    def __init__(self, db: Session) -> None:
        self.db = db

    # ---------- stage 1: hard constraints ----------

    def find_candidates(self, item: BuyerOrderItem, order: BuyerOrder) -> list[Candidate]:
        max_price = item.maximum_unit_price or item.offered_unit_price
        query = (
            select(HarvestListing, Farm, FarmerProfile)
            .join(Farm, HarvestListing.farm_id == Farm.id)
            .join(FarmerProfile, HarvestListing.farmer_id == FarmerProfile.id)
            .where(
                HarvestListing.product_id == item.product_id,
                HarvestListing.status.in_(MATCHABLE_STATUSES),
                HarvestListing.available_quantity > 0,
                HarvestListing.unit == item.unit,
                # price compatibility: farmer's minimum within buyer's ceiling
                HarvestListing.minimum_unit_price <= max_price,
                # delivery-date compatibility: harvest completes before delivery
                HarvestListing.harvest_start_date <= order.required_delivery_date,
                # verified farmers only
                FarmerProfile.verification_status == VerificationStatus.VERIFIED,
            )
        )
        if item.variety_id is not None:
            query = query.where(HarvestListing.variety_id == item.variety_id)
        rows = self.db.execute(query).all()

        min_grade = self.db.get(QualityGrade, item.minimum_grade_id) if item.minimum_grade_id else None
        candidates: list[Candidate] = []
        for listing, farm, profile in rows:
            # non-expired: harvest window has not already closed
            if listing.harvest_end_date < date.today():
                continue
            # grade compatibility: expected grade at least as good (lower sort_order)
            if min_grade is not None:
                if listing.expected_grade_id is None:
                    continue
                grade = self.db.get(QualityGrade, listing.expected_grade_id)
                if grade is None or grade.sort_order > min_grade.sort_order:
                    continue
            # packaging compatibility (exact match when the buyer demands one)
            if (
                item.packaging_requirement
                and listing.packaging_type
                and item.packaging_requirement.lower() != listing.packaging_type.lower()
            ):
                continue
            candidates.append(Candidate(listing, farm, profile))
        return candidates

    # ---------- stage 2: grouping ----------

    @staticmethod
    def group_by_area(candidates: list[Candidate]) -> dict[str, list[Candidate]]:
        groups: dict[str, list[Candidate]] = {}
        for cand in candidates:
            groups.setdefault(cand.farm.dzongkhag, []).append(cand)
        return groups

    # ---------- stage 3: allocation ----------

    @staticmethod
    def allocate(
        candidates: list[Candidate], required: Decimal, offered_price: Decimal
    ) -> list[AllocationPlan]:
        ordered = sorted(
            candidates,
            key=lambda c: (
                c.listing.minimum_unit_price,
                -c.listing.available_quantity,
                c.listing.created_at,
                str(c.listing.id),
            ),
        )
        plans: list[AllocationPlan] = []
        remaining = required
        for cand in ordered:
            if remaining <= 0:
                break
            take = min(cand.listing.available_quantity, remaining)
            # agreed price: the buyer's offer, never below the farmer's minimum
            price = max(cand.listing.minimum_unit_price, offered_price)
            plans.append(AllocationPlan(cand.listing, take, _q2(price)))
            remaining -= take
        return plans

    # ---------- stage 4: scoring ----------

    def score(
        self,
        item: BuyerOrderItem,
        order: BuyerOrder,
        plans: list[AllocationPlan],
        candidates: list[Candidate],
        transport_cost: Decimal | None,
        product_shelf_life_days: int,
    ) -> tuple[int, dict[str, int]]:
        total_quantity = sum((p.quantity for p in plans), Decimal("0"))
        fill_ratio = min(total_quantity / item.required_quantity, Decimal("1"))
        quantity_fit = int(fill_ratio * 100)

        # date fit: all harvest windows end on/before the delivery date = 100
        listings = [p.listing for p in plans]
        late = [ls for ls in listings if ls.harvest_end_date > order.required_delivery_date]
        date_fit = 100 if not late else max(0, 100 - 30 * len(late))

        # price fit: average agreed price vs buyer's offered price
        if plans:
            avg_price = sum((p.unit_price * p.quantity for p in plans), Decimal("0")) / total_quantity
            over = max(Decimal("0"), avg_price - item.offered_unit_price)
            ceiling = (item.maximum_unit_price or item.offered_unit_price) - item.offered_unit_price
            price_fit = (
                100 if over == 0 else int(max(Decimal("0"), Decimal("100") - (over / (ceiling or over)) * 40))
            )
        else:
            price_fit = 0

        # quality fit: all planned listings meet the minimum grade (constraint
        # already filtered) → 100 when a grade was demanded and matched
        quality_fit = 100

        # geographic concentration: single-dzongkhag supply is cheapest to collect
        areas = {p.listing.farm_id for p in plans}
        dzongkhags = {c.farm.dzongkhag for c in candidates if c.listing in listings}
        transport_efficiency = 100 if len(dzongkhags) <= 1 else max(40, 100 - 20 * (len(dzongkhags) - 1))
        if len(areas) > 6:
            transport_efficiency = max(30, transport_efficiency - 10)

        # spoilage: days between earliest harvest start and delivery vs shelf life
        if listings:
            earliest = min(ls.harvest_start_date for ls in listings)
            holding_days = (order.required_delivery_date - earliest).days
            ratio = holding_days / max(product_shelf_life_days, 1)
            spoilage_risk = 100 if ratio <= 0.5 else 70 if ratio <= 1 else 40
        else:
            spoilage_risk = 0

        factors = {
            "quantity_fit": quantity_fit,
            "date_fit": date_fit,
            "price_fit": price_fit,
            "quality_fit": quality_fit,
            "transport_efficiency": transport_efficiency,
            "spoilage_risk": spoilage_risk,
        }
        weights = {
            "quantity_fit": 30,
            "date_fit": 20,
            "price_fit": 20,
            "quality_fit": 10,
            "transport_efficiency": 12,
            "spoilage_risk": 8,
        }
        total = round(sum(factors[k] * weights[k] for k in factors) / sum(weights.values()))
        return total, factors

    # ---------- stage 5: explanation ----------

    @staticmethod
    def explain(
        item: BuyerOrderItem,
        order: BuyerOrder,
        plans: list[AllocationPlan],
        factors: dict[str, int],
        transport_cost: Decimal | None,
        estimate_is_approximate: bool,
    ) -> list[str]:
        total_quantity = sum((p.quantity for p in plans), Decimal("0"))
        pct = _q2(total_quantity / item.required_quantity * 100)
        sentences = [
            f"The proposed supply covers {pct}% of the requested "
            f"{item.required_quantity} {item.unit} ({len(plans)} farmer "
            f"listing{'s' if len(plans) != 1 else ''} aggregated).",
        ]
        if factors["date_fit"] == 100:
            sentences.append("All harvest windows finish on or before the required delivery date.")
        else:
            sentences.append(
                "Some harvest windows extend past the required delivery date; "
                "collection must happen within the overlapping days."
            )
        if plans:
            avg_price = _q2(sum((p.unit_price * p.quantity for p in plans), Decimal("0")) / total_quantity)
            sentences.append(
                f"The average agreed price is Nu. {avg_price}/{item.unit} against the "
                f"buyer's offer of Nu. {item.offered_unit_price}/{item.unit}."
            )
        if factors["transport_efficiency"] >= 100:
            sentences.append("All supplying farms are in one dzongkhag, keeping the pickup route short.")
        else:
            sentences.append("Supplying farms span multiple dzongkhags, which lengthens the pickup route.")
        if transport_cost is not None:
            label = "approximate " if estimate_is_approximate else ""
            sentences.append(f"Estimated {label}transport cost: Nu. {transport_cost}.")
        if factors["spoilage_risk"] < 70:
            sentences.append(
                "The gap between harvest and delivery is long relative to the product's "
                "shelf life; prioritise a prompt collection schedule."
            )
        return sentences

    # ---------- orchestration ----------

    def generate_proposals(self, order_item_id: uuid.UUID, created_by: uuid.UUID) -> list[MatchProposal]:
        item = self.db.get(BuyerOrderItem, order_item_id)
        if item is None:
            raise NotFoundError("Order item not found.")
        order = self.db.get(BuyerOrder, item.buyer_order_id)
        assert order is not None
        org = self.db.get(BuyerOrganization, order.buyer_organization_id)
        assert org is not None
        if org.verification_status != VerificationStatus.VERIFIED:
            raise ConflictError("Buyer organization is not verified.", code="BUYER_UNVERIFIED")
        if order.order_status not in (OrderStatus.PUBLISHED, OrderStatus.MATCHING):
            raise ConflictError("Order must be published before matching.", code="ORDER_NOT_PUBLISHED")

        candidates = self.find_candidates(item, order)
        if not candidates:
            return []

        # supersede previous open proposals for this item
        previous = self.db.scalars(
            select(MatchProposal).where(
                MatchProposal.buyer_order_item_id == item.id,
                MatchProposal.status.in_(
                    (
                        ProposalStatus.GENERATED,
                        ProposalStatus.COORDINATOR_REVIEW,
                        ProposalStatus.FARMER_CONFIRMATION,
                        ProposalStatus.BUYER_CONFIRMATION,
                    )
                ),
            )
        ).all()
        for prop in previous:
            prop.status = ProposalStatus.SUPERSEDED

        groups = self.group_by_area(candidates)
        proposals: list[MatchProposal] = []
        # one proposal per area group (plus one combined if no single group suffices)
        plans_by_group = {
            area: self.allocate(cands, item.required_quantity, item.offered_unit_price)
            for area, cands in sorted(groups.items())
        }
        full_groups = [
            (area, plans)
            for area, plans in plans_by_group.items()
            if sum((p.quantity for p in plans), Decimal("0")) >= item.required_quantity
        ]
        selected: list[tuple[str, list[AllocationPlan]]] = full_groups or [
            ("combined", self.allocate(candidates, item.required_quantity, item.offered_unit_price))
        ]

        from app.models import Product

        product = self.db.get(Product, item.product_id)
        shelf_life = product.shelf_life_days if product else 7

        delivery_loc = self.db.get(Location, order.delivery_location_id)
        for _area, plans in selected:
            if not plans:
                continue
            transport_cost: Decimal | None = None
            duration_hours: Decimal | None = None
            approximate = True
            points: list[RoutePoint] = []
            for plan in plans:
                farm = self.db.get(Farm, plan.listing.farm_id)
                if farm is not None and farm.latitude is not None and farm.longitude is not None:
                    points.append(RoutePoint(farm.latitude, farm.longitude, farm.farm_name))
            if (
                delivery_loc is not None
                and delivery_loc.latitude is not None
                and delivery_loc.longitude is not None
            ):
                points.append(RoutePoint(delivery_loc.latitude, delivery_loc.longitude, delivery_loc.name))
            if len(points) >= 2:
                estimate = get_router().estimate_route(points)
                transport_cost = estimate_transport_cost(estimate.distance_km)
                duration_hours = estimate.duration_hours
                approximate = estimate.is_approximate

            total_score, factors = self.score(item, order, plans, candidates, transport_cost, shelf_life)
            explanation = self.explain(item, order, plans, factors, transport_cost, approximate)
            proposal = MatchProposal(
                buyer_order_item_id=item.id,
                proposed_quantity=sum((p.quantity for p in plans), Decimal("0")),
                estimated_transport_cost=transport_cost,
                estimated_delivery_time_hours=duration_hours,
                estimated_spoilage_risk=(
                    "low"
                    if factors["spoilage_risk"] >= 100
                    else "medium"
                    if factors["spoilage_risk"] >= 70
                    else "high"
                ),
                matching_method="deterministic_v1",
                score=total_score,
                score_factors=factors,
                score_explanation=explanation,
                status=ProposalStatus.GENERATED,
                created_by=created_by,
            )
            self.db.add(proposal)
            self.db.flush()
            for plan in plans:
                self.db.add(
                    MatchAllocation(
                        match_proposal_id=proposal.id,
                        harvest_listing_id=plan.listing.id,
                        allocated_quantity=plan.quantity,
                        agreed_unit_price=plan.unit_price,
                    )
                )
            proposals.append(proposal)

        if order.order_status == OrderStatus.PUBLISHED and proposals:
            order.order_status = OrderStatus.MATCHING
        return proposals
