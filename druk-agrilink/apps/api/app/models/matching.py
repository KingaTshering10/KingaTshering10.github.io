import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import JSON, DateTime, ForeignKey, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, SafeNumeric, TimestampMixin, UUIDPrimaryKeyMixin
from app.domain.enums import FarmerResponse, ProposalStatus


class MatchProposal(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "match_proposals"

    buyer_order_item_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("buyer_order_items.id"), index=True, nullable=False
    )
    proposed_quantity: Mapped[Decimal] = mapped_column(SafeNumeric(12, 2), nullable=False)
    estimated_transport_cost: Mapped[Decimal | None] = mapped_column(SafeNumeric(12, 2))
    estimated_delivery_time_hours: Mapped[Decimal | None] = mapped_column(SafeNumeric(6, 1))
    estimated_spoilage_risk: Mapped[str | None] = mapped_column(String(10))  # low|medium|high
    matching_method: Mapped[str] = mapped_column(String(40), default="deterministic_v1", nullable=False)
    score: Mapped[int] = mapped_column(nullable=False)  # 0–100
    score_factors: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    score_explanation: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    status: Mapped[ProposalStatus] = mapped_column(
        String(30), default=ProposalStatus.GENERATED, index=True, nullable=False
    )
    created_by: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("users.id"), nullable=False)
    approved_by: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("users.id"))


class MatchAllocation(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "match_allocations"

    match_proposal_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("match_proposals.id"), index=True, nullable=False
    )
    harvest_listing_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("harvest_listings.id"), index=True, nullable=False
    )
    allocated_quantity: Mapped[Decimal] = mapped_column(SafeNumeric(12, 2), nullable=False)
    agreed_unit_price: Mapped[Decimal] = mapped_column(SafeNumeric(10, 2), nullable=False)
    farmer_response: Mapped[FarmerResponse] = mapped_column(
        String(12), default=FarmerResponse.PENDING, nullable=False
    )
    farmer_response_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
