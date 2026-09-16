"""Every status enum in one place. String-valued for API/DB portability."""

from enum import StrEnum


class Role(StrEnum):
    FARMER = "farmer"
    COORDINATOR = "coordinator"
    BUYER = "buyer"
    TRANSPORTER = "transporter"
    ADMIN = "admin"


class Language(StrEnum):
    EN = "en"
    DZ = "dz"


class VerificationStatus(StrEnum):
    PENDING = "pending"
    VERIFIED = "verified"
    REJECTED = "rejected"


class ContactMethod(StrEnum):
    PHONE = "phone"
    SMS = "sms"
    IN_APP = "in_app"


class LocationType(StrEnum):
    COLLECTION_POINT = "collection_point"
    DELIVERY_POINT = "delivery_point"
    FARM = "farm"
    DEPOT = "depot"
    OTHER = "other"


class StorageCategory(StrEnum):
    AMBIENT = "ambient"
    COOL_DRY = "cool_dry"
    REFRIGERATED = "refrigerated"


class Unit(StrEnum):
    KG = "kg"
    CRATE = "crate"
    BUNDLE = "bundle"
    PIECE = "piece"


class ConfidenceLevel(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class HarvestStatus(StrEnum):
    DRAFT = "draft"
    FORECAST = "forecast"
    CONFIRMED = "confirmed"
    PARTIALLY_ALLOCATED = "partially_allocated"
    FULLY_ALLOCATED = "fully_allocated"
    COLLECTED = "collected"
    CANCELLED = "cancelled"
    EXPIRED = "expired"


class BuyerOrgType(StrEnum):
    HOTEL = "hotel"
    RESTAURANT = "restaurant"
    SCHOOL = "school"
    HOSPITAL = "hospital"
    RETAILER = "retailer"
    WHOLESALER = "wholesaler"
    PROCESSOR = "processor"
    GOVERNMENT = "government_institution"
    EXPORTER = "exporter"
    OTHER = "other"


class OrderStatus(StrEnum):
    DRAFT = "draft"
    PUBLISHED = "published"
    MATCHING = "matching"
    PROPOSED = "proposed"
    CONFIRMED = "confirmed"
    COLLECTION_IN_PROGRESS = "collection_in_progress"
    IN_TRANSIT = "in_transit"
    DELIVERED = "delivered"
    ACCEPTED = "accepted"
    PAYMENT_PENDING = "payment_pending"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    EXPIRED = "expired"
    PARTIALLY_FULFILLED = "partially_fulfilled"
    DISPUTED = "disputed"


class ProposalStatus(StrEnum):
    GENERATED = "generated"
    COORDINATOR_REVIEW = "coordinator_review"
    FARMER_CONFIRMATION = "farmer_confirmation"
    BUYER_CONFIRMATION = "buyer_confirmation"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"
    SUPERSEDED = "superseded"


class FarmerResponse(StrEnum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    DECLINED = "declined"


class VehicleType(StrEnum):
    PICKUP = "pickup"
    LIGHT_TRUCK = "light_truck"
    TRUCK = "truck"
    REFRIGERATED_TRUCK = "refrigerated_truck"
    UTILITY = "utility"


class ShipmentStatus(StrEnum):
    PLANNING = "planning"
    OFFERED = "offered"
    ASSIGNED = "assigned"
    CONFIRMED = "confirmed"
    COLLECTION_IN_PROGRESS = "collection_in_progress"
    IN_TRANSIT = "in_transit"
    ARRIVED = "arrived"
    DELIVERED = "delivered"
    COMPLETED = "completed"
    DELAYED = "delayed"
    CANCELLED = "cancelled"
    INCIDENT_REPORTED = "incident_reported"


class StopType(StrEnum):
    PICKUP = "pickup"
    DELIVERY = "delivery"


class StopStatus(StrEnum):
    PLANNED = "planned"
    ARRIVED = "arrived"
    COMPLETED = "completed"
    SKIPPED = "skipped"


class PaymentStatus(StrEnum):
    PENDING = "pending"
    PARTIALLY_PAID = "partially_paid"
    PAID = "paid"
    OVERDUE = "overdue"
    DISPUTED = "disputed"
    WAIVED = "waived"
    CANCELLED = "cancelled"


class PartyType(StrEnum):
    BUYER_ORGANIZATION = "buyer_organization"
    FARMER_GROUP = "farmer_group"
    FARMER = "farmer"
    TRANSPORT_PROVIDER = "transport_provider"
    PLATFORM = "platform"


class NotificationChannel(StrEnum):
    IN_APP = "in_app"
    EMAIL = "email"
    SMS = "sms"
    PUSH = "push"


class NotificationStatus(StrEnum):
    QUEUED = "queued"
    SENT = "sent"
    FAILED = "failed"


class DisputeCategory(StrEnum):
    OVERDUE_PAYMENT = "overdue_payment"
    INCORRECT_AMOUNT = "incorrect_amount"
    MISSING_PAYMENT = "missing_payment"
    UNEXPLAINED_DEDUCTION = "unexplained_deduction"
    DELIVERY_REJECTION = "delivery_rejection"
    QUANTITY_MISMATCH = "quantity_mismatch"
    OTHER = "other"


class DisputeStatus(StrEnum):
    OPEN = "open"
    UNDER_REVIEW = "under_review"
    RESOLVED = "resolved"
    CLOSED = "closed"
