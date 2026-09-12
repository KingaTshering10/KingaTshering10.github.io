"""Routing abstraction.

Never use straight-line distance as a final logistics measure: the local
implementation applies a configurable mountain-road circuity factor and every
estimate is labelled with its method so the UI can display "approximate".

Implementations:
- ``MockRouter``       — fixed values for tests.
- ``LocalApproxRouter``— haversine × circuity factor; the MVP default.
- External adapter     — implement ``RoutingService.estimate_route`` against
  OSRM/Valhalla/Google Routes and register it in ``get_router()``; requires
  credentials/self-hosting (documented in docs/DEPLOYMENT.md).
"""

import math
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from typing import Protocol

from app.core.config import get_settings


@dataclass(frozen=True)
class RoutePoint:
    latitude: Decimal
    longitude: Decimal
    name: str = ""


@dataclass(frozen=True)
class RouteEstimate:
    distance_km: Decimal
    duration_hours: Decimal
    method: str  # "mock" | "approximate_local" | "external"
    is_approximate: bool
    legs_km: tuple[Decimal, ...] = ()


class RoutingService(Protocol):
    def estimate_route(self, stops: list[RoutePoint]) -> RouteEstimate: ...


class MockRouter:
    """Deterministic fixed estimate for tests."""

    def __init__(self, distance_km: str = "42.0", duration_hours: str = "1.5") -> None:
        self.distance_km = Decimal(distance_km)
        self.duration_hours = Decimal(duration_hours)

    def estimate_route(self, stops: list[RoutePoint]) -> RouteEstimate:
        return RouteEstimate(
            distance_km=self.distance_km,
            duration_hours=self.duration_hours,
            method="mock",
            is_approximate=True,
        )


def _haversine_km(a: RoutePoint, b: RoutePoint) -> float:
    lat1, lon1, lat2, lon2 = map(
        math.radians, (float(a.latitude), float(a.longitude), float(b.latitude), float(b.longitude))
    )
    dlat, dlon = lat2 - lat1, lon2 - lon1
    h = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return 6371.0 * 2 * math.asin(math.sqrt(h))


class LocalApproxRouter:
    """Haversine distance scaled by a mountain-road circuity factor.

    Bhutan's road network winds through valleys, so straight-line distance
    badly underestimates travel; the default factor (1.6) comes from typical
    Bhutanese road-vs-crow-flies ratios and is configurable per deployment.
    """

    def estimate_route(self, stops: list[RoutePoint]) -> RouteEstimate:
        settings = get_settings()
        factor = Decimal(settings.road_circuity_factor)
        speed = Decimal(settings.average_speed_kmh)
        legs: list[Decimal] = []
        for prev, nxt in zip(stops, stops[1:], strict=False):
            straight = Decimal(str(_haversine_km(prev, nxt)))
            legs.append((straight * factor).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP))
        total = sum(legs, Decimal("0"))
        duration = (total / speed).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP) if speed else Decimal("0")
        return RouteEstimate(
            distance_km=total,
            duration_hours=duration,
            method="approximate_local",
            is_approximate=True,
            legs_km=tuple(legs),
        )


def sequence_stops_nearest_neighbour(origin: RoutePoint, stops: list[RoutePoint]) -> list[int]:
    """Deterministic pickup ordering: repeatedly visit the nearest remaining stop.

    Returns indices into ``stops``. Coordinators can always reorder manually —
    the manual override wins. OR-Tools VRP is the documented upgrade path
    behind this same call signature.
    """
    remaining = list(range(len(stops)))
    order: list[int] = []
    current = origin
    while remaining:
        best = min(remaining, key=lambda i: (_haversine_km(current, stops[i]), i))
        order.append(best)
        current = stops[best]
        remaining.remove(best)
    return order


_router: RoutingService | None = None


def get_router() -> RoutingService:
    global _router
    if _router is None:
        _router = LocalApproxRouter()
    return _router


def set_router(router: RoutingService) -> None:
    """Test/deployment hook to swap the routing implementation."""
    global _router
    _router = router


def estimate_transport_cost(distance_km: Decimal) -> Decimal:
    settings = get_settings()
    per_km = Decimal(settings.transport_cost_per_km_nu)
    return (distance_km * per_km).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
