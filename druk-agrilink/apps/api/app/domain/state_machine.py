"""Strict state-transition validation for every stateful entity.

A transition not present in the map raises :class:`InvalidTransition`, which the
API layer turns into ``409 INVALID_STATE_TRANSITION`` with the attempted and
allowed transitions spelled out.
"""

from app.domain.enums import HarvestStatus, OrderStatus, ProposalStatus, ShipmentStatus


class InvalidTransition(Exception):
    def __init__(self, entity: str, current: str, target: str, allowed: list[str]) -> None:
        self.entity = entity
        self.current = current
        self.target = target
        self.allowed = allowed
        next_states = ", ".join(allowed) if allowed else "none (terminal state)"
        super().__init__(
            f"{entity}: cannot move from '{current}' to '{target}'. Allowed next states: {next_states}"
        )


HARVEST_TRANSITIONS: dict[HarvestStatus, set[HarvestStatus]] = {
    HarvestStatus.DRAFT: {HarvestStatus.FORECAST, HarvestStatus.CANCELLED},
    HarvestStatus.FORECAST: {HarvestStatus.CONFIRMED, HarvestStatus.CANCELLED, HarvestStatus.EXPIRED},
    HarvestStatus.CONFIRMED: {
        HarvestStatus.PARTIALLY_ALLOCATED,
        HarvestStatus.FULLY_ALLOCATED,
        HarvestStatus.CANCELLED,
        HarvestStatus.EXPIRED,
    },
    HarvestStatus.PARTIALLY_ALLOCATED: {
        HarvestStatus.CONFIRMED,  # allocation released
        HarvestStatus.FULLY_ALLOCATED,
        HarvestStatus.COLLECTED,
        HarvestStatus.CANCELLED,
    },
    HarvestStatus.FULLY_ALLOCATED: {
        HarvestStatus.PARTIALLY_ALLOCATED,  # allocation released
        HarvestStatus.COLLECTED,
        HarvestStatus.CANCELLED,
    },
    HarvestStatus.COLLECTED: set(),
    HarvestStatus.CANCELLED: set(),
    HarvestStatus.EXPIRED: set(),
}

ORDER_TRANSITIONS: dict[OrderStatus, set[OrderStatus]] = {
    OrderStatus.DRAFT: {OrderStatus.PUBLISHED, OrderStatus.CANCELLED},
    OrderStatus.PUBLISHED: {OrderStatus.MATCHING, OrderStatus.CANCELLED, OrderStatus.EXPIRED},
    OrderStatus.MATCHING: {
        OrderStatus.PROPOSED,
        OrderStatus.PUBLISHED,
        OrderStatus.CANCELLED,
        OrderStatus.EXPIRED,
    },
    OrderStatus.PROPOSED: {
        OrderStatus.CONFIRMED,
        OrderStatus.MATCHING,
        OrderStatus.CANCELLED,
        OrderStatus.EXPIRED,
    },
    OrderStatus.CONFIRMED: {OrderStatus.COLLECTION_IN_PROGRESS, OrderStatus.CANCELLED, OrderStatus.DISPUTED},
    OrderStatus.COLLECTION_IN_PROGRESS: {OrderStatus.IN_TRANSIT, OrderStatus.DISPUTED, OrderStatus.CANCELLED},
    OrderStatus.IN_TRANSIT: {OrderStatus.DELIVERED, OrderStatus.DISPUTED},
    OrderStatus.DELIVERED: {OrderStatus.ACCEPTED, OrderStatus.PARTIALLY_FULFILLED, OrderStatus.DISPUTED},
    OrderStatus.ACCEPTED: {OrderStatus.PAYMENT_PENDING, OrderStatus.DISPUTED},
    OrderStatus.PARTIALLY_FULFILLED: {OrderStatus.PAYMENT_PENDING, OrderStatus.DISPUTED},
    OrderStatus.PAYMENT_PENDING: {OrderStatus.COMPLETED, OrderStatus.DISPUTED},
    OrderStatus.COMPLETED: set(),
    OrderStatus.CANCELLED: set(),
    OrderStatus.EXPIRED: set(),
    OrderStatus.DISPUTED: {OrderStatus.PAYMENT_PENDING, OrderStatus.COMPLETED, OrderStatus.CANCELLED},
}

PROPOSAL_TRANSITIONS: dict[ProposalStatus, set[ProposalStatus]] = {
    ProposalStatus.GENERATED: {
        ProposalStatus.COORDINATOR_REVIEW,
        ProposalStatus.REJECTED,
        ProposalStatus.EXPIRED,
        ProposalStatus.SUPERSEDED,
    },
    ProposalStatus.COORDINATOR_REVIEW: {
        ProposalStatus.FARMER_CONFIRMATION,
        ProposalStatus.REJECTED,
        ProposalStatus.EXPIRED,
        ProposalStatus.SUPERSEDED,
    },
    ProposalStatus.FARMER_CONFIRMATION: {
        ProposalStatus.BUYER_CONFIRMATION,
        ProposalStatus.REJECTED,
        ProposalStatus.EXPIRED,
        ProposalStatus.SUPERSEDED,
    },
    ProposalStatus.BUYER_CONFIRMATION: {
        ProposalStatus.APPROVED,
        ProposalStatus.REJECTED,
        ProposalStatus.EXPIRED,
        ProposalStatus.SUPERSEDED,
    },
    ProposalStatus.APPROVED: set(),
    ProposalStatus.REJECTED: set(),
    ProposalStatus.EXPIRED: set(),
    ProposalStatus.SUPERSEDED: set(),
}

SHIPMENT_TRANSITIONS: dict[ShipmentStatus, set[ShipmentStatus]] = {
    ShipmentStatus.PLANNING: {ShipmentStatus.OFFERED, ShipmentStatus.CANCELLED},
    ShipmentStatus.OFFERED: {ShipmentStatus.ASSIGNED, ShipmentStatus.PLANNING, ShipmentStatus.CANCELLED},
    ShipmentStatus.ASSIGNED: {ShipmentStatus.CONFIRMED, ShipmentStatus.OFFERED, ShipmentStatus.CANCELLED},
    ShipmentStatus.CONFIRMED: {
        ShipmentStatus.COLLECTION_IN_PROGRESS,
        ShipmentStatus.DELAYED,
        ShipmentStatus.CANCELLED,
    },
    ShipmentStatus.COLLECTION_IN_PROGRESS: {
        ShipmentStatus.IN_TRANSIT,
        ShipmentStatus.DELAYED,
        ShipmentStatus.INCIDENT_REPORTED,
        ShipmentStatus.CANCELLED,
    },
    ShipmentStatus.IN_TRANSIT: {
        ShipmentStatus.ARRIVED,
        ShipmentStatus.DELAYED,
        ShipmentStatus.INCIDENT_REPORTED,
    },
    ShipmentStatus.ARRIVED: {ShipmentStatus.DELIVERED, ShipmentStatus.INCIDENT_REPORTED},
    ShipmentStatus.DELIVERED: {ShipmentStatus.COMPLETED, ShipmentStatus.INCIDENT_REPORTED},
    ShipmentStatus.COMPLETED: set(),
    ShipmentStatus.DELAYED: {
        ShipmentStatus.COLLECTION_IN_PROGRESS,
        ShipmentStatus.IN_TRANSIT,
        ShipmentStatus.ARRIVED,
        ShipmentStatus.CANCELLED,
        ShipmentStatus.INCIDENT_REPORTED,
    },
    ShipmentStatus.CANCELLED: set(),
    ShipmentStatus.INCIDENT_REPORTED: {
        ShipmentStatus.IN_TRANSIT,
        ShipmentStatus.DELIVERED,
        ShipmentStatus.CANCELLED,
    },
}


def _transition(entity: str, table: dict, current, target) -> None:
    allowed = table.get(current, set())
    if target not in allowed:
        raise InvalidTransition(entity, str(current), str(target), sorted(str(s) for s in allowed))


def transition_harvest(current: HarvestStatus, target: HarvestStatus) -> None:
    _transition("HarvestListing", HARVEST_TRANSITIONS, current, target)


def transition_order(current: OrderStatus, target: OrderStatus) -> None:
    _transition("BuyerOrder", ORDER_TRANSITIONS, current, target)


def transition_proposal(current: ProposalStatus, target: ProposalStatus) -> None:
    _transition("MatchProposal", PROPOSAL_TRANSITIONS, current, target)


def transition_shipment(current: ShipmentStatus, target: ShipmentStatus) -> None:
    _transition("Shipment", SHIPMENT_TRANSITIONS, current, target)
