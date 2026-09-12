"""AI-ready extension points.

The MVP does not depend on any generative model. These interfaces define
where future capabilities plug in; each ships with a simple, deterministic
baseline (or an explicit not-implemented stub). Every AI-produced value must
be labelled, reviewable, overridable, and — when operationally used — logged.
"""

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Protocol

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import CollectionRecord, MatchAllocation
from app.services.settlement import q2

# ---------- 1. voice harvest extraction ----------


@dataclass
class HarvestDraftExtraction:
    """Structured draft from a voice/text utterance. All fields require
    human confirmation before a listing is created."""

    product: str | None = None
    quantity: Decimal | None = None
    unit: str | None = None
    harvest_window_start: date | None = None
    harvest_window_end: date | None = None
    requires_confirmation: bool = True
    source: str = "unimplemented"
    warnings: list[str] = field(default_factory=list)


class VoiceHarvestExtractor(Protocol):
    def extract(self, utterance: str, language: str) -> HarvestDraftExtraction: ...


class UnavailableVoiceExtractor:
    """Baseline: no model available; returns an empty draft that forces
    manual entry rather than inventing values."""

    def extract(self, utterance: str, language: str) -> HarvestDraftExtraction:
        return HarvestDraftExtraction(
            warnings=["Voice extraction is not available in this deployment; enter details manually."]
        )


# ---------- 2. demand forecasting ----------


class DemandForecaster(Protocol):
    def forecast_weekly_demand(self, db: Session, product_id, weeks: int) -> list[Decimal]: ...


class MovingAverageForecaster:
    """Baseline: trailing average of accepted collection quantities."""

    def forecast_weekly_demand(self, db: Session, product_id, weeks: int = 4) -> list[Decimal]:
        from app.models import HarvestListing

        listing_ids = select(HarvestListing.id).where(HarvestListing.product_id == product_id)
        records = db.scalars(
            select(CollectionRecord).where(CollectionRecord.harvest_listing_id.in_(listing_ids))
        ).all()
        if not records:
            return [Decimal("0")] * weeks
        average = q2(sum((r.accepted_quantity for r in records), Decimal("0")) / Decimal(len(records)))
        return [average] * weeks


# ---------- 3. forecast-realisation modelling ----------


def forecast_realisation_dataset(db: Session) -> list[dict]:
    """Training-ready rows: forecast vs confirmed vs presented vs accepted.
    The MVP only exposes the dataset; prediction is future work."""

    from app.models import HarvestListing

    rows: list[dict] = []
    for listing in db.scalars(select(HarvestListing)):
        collections = db.scalars(
            select(CollectionRecord).where(CollectionRecord.harvest_listing_id == listing.id)
        ).all()
        rows.append(
            {
                "listing_id": str(listing.id),
                "forecast_quantity": str(listing.forecast_quantity),
                "confirmed_quantity": (
                    str(listing.confirmed_quantity) if listing.confirmed_quantity is not None else None
                ),
                "presented_quantity": str(sum((c.presented_quantity for c in collections), Decimal("0"))),
                "accepted_quantity": str(sum((c.accepted_quantity for c in collections), Decimal("0"))),
                "confidence_level": str(listing.confidence_level),
            }
        )
    return rows


# ---------- 4. price anomaly warnings (advisory only) ----------


@dataclass
class PriceAdvisory:
    is_anomalous: bool
    message: str
    reference_price: Decimal | None
    label: str = "advisory_estimate"  # never blocks a transaction


def check_price_anomaly(db: Session, product_id, proposed_price: Decimal) -> PriceAdvisory:
    """Compare against recent platform transactions for the same product."""
    prices = [
        a.agreed_unit_price
        for a in db.scalars(
            select(MatchAllocation).join(
                CollectionRecord,
                CollectionRecord.harvest_listing_id == MatchAllocation.harvest_listing_id,
            )
        ).all()
    ]
    if len(prices) < 3:
        return PriceAdvisory(False, "Not enough platform history for a price comparison.", None)
    reference = q2(sum(prices, Decimal("0")) / Decimal(len(prices)))
    deviation = abs(proposed_price - reference) / reference if reference else Decimal("0")
    if deviation > Decimal("0.5"):
        return PriceAdvisory(
            True,
            f"Proposed price deviates {q2(deviation * 100)}% from the recent platform "
            f"average of Nu. {reference}. This is advisory only.",
            reference,
        )
    return PriceAdvisory(False, "Price is within the typical recent range.", reference)


# ---------- 5. produce quality assistance (interface only) ----------


@dataclass
class QualityAssessment:
    suggested_grade_code: str | None
    confidence: Decimal | None
    label: str = "ai_suggestion_requires_human_grading"
    notes: str = "Images never determine final quality; a human records the grade."


class ImageQualityAssistant(Protocol):
    def assess(self, image_bytes: bytes, product_name: str) -> QualityAssessment: ...


class UnavailableImageQualityAssistant:
    def assess(self, image_bytes: bytes, product_name: str) -> QualityAssessment:
        return QualityAssessment(suggested_grade_code=None, confidence=None)
