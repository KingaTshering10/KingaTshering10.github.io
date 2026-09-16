"""Notification service: templates rendered per-user language, fanned out
through channel adapters.

In-app notifications are DB rows (always on). Email/SMS/push use mock
adapters in the MVP — they mark the notification row as sent and keep an
in-memory delivery log so tests and the dev UI can inspect them. Replacing a
mock with a real gateway means implementing ``ChannelAdapter.send`` for that
channel — see docs/DEPLOYMENT.md.

Essential templates (security/transaction) ignore user channel preferences.
"""

from dataclasses import dataclass, field
from typing import Any, Protocol

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.base import utcnow
from app.domain.enums import Language, NotificationChannel, NotificationStatus
from app.models import Notification, NotificationPreference, User

# template_key -> {language -> (subject, body)}; {placeholders} filled from context.
# Dzongkha strings pending human verification are prefixed with the review marker
# and fall back to English at render time so no invented translation ships.
DZ_REVIEW = "[DZ REVIEW]"

TEMPLATES: dict[str, dict[str, tuple[str, str]]] = {
    "registration_received": {
        "en": (
            "Registration received",
            "Your DrukAgriLink registration was received and is awaiting verification.",
        ),
        "dz": (f"{DZ_REVIEW} Registration received", f"{DZ_REVIEW} pending translation"),
    },
    "account_verified": {
        "en": (
            "Account verified",
            "Your account has been verified. You can now use all features for your role.",
        ),
        "dz": (f"{DZ_REVIEW} Account verified", f"{DZ_REVIEW} pending translation"),
    },
    "account_rejected": {
        "en": ("Verification unsuccessful", "Your verification was not approved. Reason: {reason}"),
        "dz": (f"{DZ_REVIEW} Verification unsuccessful", f"{DZ_REVIEW} pending translation"),
    },
    "harvest_confirmation_reminder": {
        "en": ("Confirm your harvest", "Please confirm the expected quantity for your {product} harvest."),
        "dz": (f"{DZ_REVIEW} Confirm your harvest", f"{DZ_REVIEW} pending translation"),
    },
    "new_buyer_opportunity": {
        "en": ("New buyer opportunity", "A buyer needs {product}. Check Opportunities for details."),
        "dz": (f"{DZ_REVIEW} New buyer opportunity", f"{DZ_REVIEW} pending translation"),
    },
    "match_proposal_created": {
        "en": (
            "Match proposal created",
            "A match proposal for {product} has been generated and awaits review.",
        ),
        "dz": (f"{DZ_REVIEW} Match proposal created", f"{DZ_REVIEW} pending translation"),
    },
    "farmer_response_required": {
        "en": (
            "Your response is needed",
            "You have an allocation offer: {quantity} {unit} of {product} at "
            "Nu. {price}/{unit}. Please accept or decline.",
        ),
        "dz": (f"{DZ_REVIEW} Your response is needed", f"{DZ_REVIEW} pending translation"),
    },
    "buyer_response_required": {
        "en": ("Proposal awaiting your approval", "A supply proposal for your order is ready for review."),
        "dz": (f"{DZ_REVIEW} Proposal awaiting your approval", f"{DZ_REVIEW} pending translation"),
    },
    "match_approved": {
        "en": ("Match approved", "The match for {product} has been approved by all parties."),
        "dz": (f"{DZ_REVIEW} Match approved", f"{DZ_REVIEW} pending translation"),
    },
    "match_rejected": {
        "en": ("Match not approved", "The match proposal for {product} was rejected. Reason: {reason}"),
        "dz": (f"{DZ_REVIEW} Match not approved", f"{DZ_REVIEW} pending translation"),
    },
    "transport_trip_available": {
        "en": ("Trip available", "A transport trip is available: {route} on {date}."),
        "dz": (f"{DZ_REVIEW} Trip available", f"{DZ_REVIEW} pending translation"),
    },
    "shipment_assigned": {
        "en": ("Shipment assigned", "Shipment {shipment} has been assigned to vehicle {vehicle}."),
        "dz": (f"{DZ_REVIEW} Shipment assigned", f"{DZ_REVIEW} pending translation"),
    },
    "collection_reminder": {
        "en": ("Collection scheduled", "Collection for your {product} is planned on {date} at {location}."),
        "dz": (f"{DZ_REVIEW} Collection scheduled", f"{DZ_REVIEW} pending translation"),
    },
    "shipment_delayed": {
        "en": ("Shipment delayed", "Shipment {shipment} is delayed. {note}"),
        "dz": (f"{DZ_REVIEW} Shipment delayed", f"{DZ_REVIEW} pending translation"),
    },
    "delivery_completed": {
        "en": ("Delivery completed", "Delivery for order {order} is complete. Accepted: {accepted} {unit}."),
        "dz": (f"{DZ_REVIEW} Delivery completed", f"{DZ_REVIEW} pending translation"),
    },
    "payment_due": {
        "en": ("Payment due", "A payment of Nu. {amount} is due on {due_date}."),
        "dz": (f"{DZ_REVIEW} Payment due", f"{DZ_REVIEW} pending translation"),
    },
    "payment_overdue": {
        "en": ("Payment overdue", "A payment of Nu. {amount} is overdue (was due {due_date})."),
        "dz": (f"{DZ_REVIEW} Payment overdue", f"{DZ_REVIEW} pending translation"),
    },
    "payment_received": {
        "en": ("Payment recorded", "A payment of Nu. {amount} has been recorded (reference {reference})."),
        "dz": (f"{DZ_REVIEW} Payment recorded", f"{DZ_REVIEW} pending translation"),
    },
    "dispute_opened": {
        "en": ("Dispute opened", "A dispute has been opened: {category}."),
        "dz": (f"{DZ_REVIEW} Dispute opened", f"{DZ_REVIEW} pending translation"),
    },
    "dispute_updated": {
        "en": ("Dispute updated", "Dispute {dispute} status changed to {status}."),
        "dz": (f"{DZ_REVIEW} Dispute updated", f"{DZ_REVIEW} pending translation"),
    },
    "dispute_resolved": {
        "en": ("Dispute resolved", "Dispute {dispute} was resolved: {resolution}"),
        "dz": (f"{DZ_REVIEW} Dispute resolved", f"{DZ_REVIEW} pending translation"),
    },
    "security_alert": {
        "en": ("Security alert", "{message}"),
        "dz": (f"{DZ_REVIEW} Security alert", f"{DZ_REVIEW} pending translation"),
    },
}

# Users cannot turn these off on any channel that is enabled for them.
ESSENTIAL_TEMPLATES = {
    "security_alert",
    "payment_due",
    "payment_overdue",
    "payment_received",
    "farmer_response_required",
    "account_verified",
    "account_rejected",
}


class ChannelAdapter(Protocol):
    channel: NotificationChannel

    def send(self, user: User, subject: str, body: str) -> None: ...


@dataclass
class MockDelivery:
    channel: str
    recipient: str
    subject: str
    body: str


@dataclass
class MockChannelAdapter:
    """Records deliveries in memory instead of calling a gateway."""

    channel: NotificationChannel
    outbox: list[MockDelivery] = field(default_factory=list)

    def send(self, user: User, subject: str, body: str) -> None:
        recipient = user.email if self.channel == NotificationChannel.EMAIL else (user.phone or "")
        self.outbox.append(MockDelivery(str(self.channel), recipient, subject, body))


mock_email = MockChannelAdapter(NotificationChannel.EMAIL)
mock_sms = MockChannelAdapter(NotificationChannel.SMS)
mock_push = MockChannelAdapter(NotificationChannel.PUSH)

_ADAPTERS: dict[NotificationChannel, MockChannelAdapter] = {
    NotificationChannel.EMAIL: mock_email,
    NotificationChannel.SMS: mock_sms,
    NotificationChannel.PUSH: mock_push,
}


def render(template_key: str, language: Language, context: dict[str, Any]) -> tuple[str, str]:
    template = TEMPLATES.get(template_key)
    if template is None:
        raise KeyError(f"Unknown notification template: {template_key}")
    subject, body = template.get(str(language), template["en"])
    if DZ_REVIEW in subject or DZ_REVIEW in body:
        # Unverified Dzongkha → fall back to English rather than shipping a placeholder.
        subject, body = template["en"]
    try:
        return subject.format(**context), body.format(**context)
    except KeyError:
        return subject, body


def notify(db: Session, user: User, template_key: str, context: dict[str, Any]) -> list[Notification]:
    """Create the in-app notification and fan out to enabled channels."""
    subject, body = render(template_key, user.preferred_language, context)
    now = utcnow()
    created: list[Notification] = []

    in_app = Notification(
        user_id=user.id,
        channel=NotificationChannel.IN_APP,
        template_key=template_key,
        subject=subject,
        body=body,
        status=NotificationStatus.SENT,
        sent_at=now,
    )
    db.add(in_app)
    created.append(in_app)

    prefs = db.scalars(
        select(NotificationPreference).where(NotificationPreference.user_id == user.id)
    ).first()
    essential = template_key in ESSENTIAL_TEMPLATES
    enabled = {
        NotificationChannel.EMAIL: essential or prefs is None or prefs.email_enabled,
        NotificationChannel.SMS: essential or prefs is None or prefs.sms_enabled,
        NotificationChannel.PUSH: (prefs.push_enabled if prefs is not None else False) or essential,
    }
    for channel, adapter in _ADAPTERS.items():
        if not enabled[channel]:
            continue
        row = Notification(
            user_id=user.id,
            channel=channel,
            template_key=template_key,
            subject=subject,
            body=body,
            status=NotificationStatus.SENT,
            sent_at=now,
        )
        adapter.send(user, subject, body)
        db.add(row)
        created.append(row)
    return created
