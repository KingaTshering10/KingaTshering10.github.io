from datetime import datetime, timedelta

from tests import helpers
from tests.conftest import auth_headers, register_user

NOW = datetime.now()


def make_verified_transporter(client, admin_headers, capacity="1000", refrigerated=False):
    transporter = register_user(client, "transporter")
    headers = auth_headers(client, transporter["email"])
    provider = client.post(
        "/api/v1/transport-providers",
        json={"organization_name": f"Trans-{transporter['id'][:6]}", "service_dzongkhags": ["Paro"]},
        headers=headers,
    ).json()
    client.post(
        f"/api/v1/admin/transport-providers/{provider['id']}/verify",
        json={"approve": True},
        headers=admin_headers,
    )
    vehicle = client.post(
        "/api/v1/vehicles",
        json={
            "registration_number": f"BP-{transporter['id'][:8]}",
            "vehicle_type": "light_truck",
            "capacity_kg": capacity,
            "has_refrigeration": refrigerated,
        },
        headers=headers,
    ).json()
    client.post(
        f"/api/v1/admin/vehicles/{vehicle['id']}/verify",
        json={"approve": True},
        headers=admin_headers,
    )
    return transporter, headers, provider, vehicle


def approved_proposal(client, admin_headers, n_farmers=2, quantity="400"):
    """Drive a proposal to APPROVED and return context."""
    coord, coord_headers, group = helpers.make_coordinator_with_group(client)
    product, _, _ = helpers.make_product(client, admin_headers)
    farmers = []
    for _ in range(n_farmers):
        farmer, headers, profile, farm = helpers.make_verified_farmer(client, coord_headers, group)
        listing = helpers.make_listing(client, headers, farm, product, quantity="300")
        listing = helpers.confirm_listing(client, headers, listing["id"], 300)
        farmers.append({"headers": headers, "listing": listing, "profile": profile})
    buyer, buyer_headers, org = helpers.make_verified_buyer(client, admin_headers)
    location = helpers.make_location(client, admin_headers, location_type="delivery_point")
    order = helpers.make_order(client, buyer_headers, location, product, quantity=quantity)
    item_id = order["items"][0]["id"]
    proposal = client.post(
        "/api/v1/match-proposals/generate",
        json={"buyer_order_item_id": item_id},
        headers=coord_headers,
    ).json()["proposals"][0]
    client.post(f"/api/v1/match-proposals/{proposal['id']}/send-to-review", headers=coord_headers)
    client.post(f"/api/v1/match-proposals/{proposal['id']}/send-to-farmers", headers=coord_headers)
    for farmer in farmers:
        mine = client.get("/api/v1/match-proposals", headers=farmer["headers"]).json()
        for p in mine:
            if p["id"] != proposal["id"]:
                continue
            for a in p["allocations"]:
                if a["harvest_listing_id"] == farmer["listing"]["id"]:
                    client.post(
                        f"/api/v1/match-proposals/allocations/{a['id']}/respond",
                        json={"accept": True},
                        headers=farmer["headers"],
                    )
    resp = client.post(f"/api/v1/match-proposals/{proposal['id']}/buyer-approve", headers=buyer_headers)
    assert resp.status_code == 200, resp.text
    return {
        "proposal": proposal,
        "coord_headers": coord_headers,
        "buyer_headers": buyer_headers,
        "farmers": farmers,
        "order": order,
        "product": product,
    }


def plan(client, ctx, vehicle, coord_headers):
    return client.post(
        "/api/v1/shipments/plan",
        json={
            "match_proposal_id": ctx["proposal"]["id"],
            "vehicle_id": vehicle["id"],
            "planned_pickup_at": (NOW + timedelta(days=8)).isoformat(),
            "planned_delivery_at": (NOW + timedelta(days=9)).isoformat(),
            "driver_name": "Karma",
            "driver_phone": "+97517400001",
        },
        headers=coord_headers,
    )


def test_shipment_planning_sequenced_stops_and_route_estimate(client, admin_headers):
    ctx = approved_proposal(client, admin_headers, n_farmers=2, quantity="400")
    _, t_headers, provider, vehicle = make_verified_transporter(client, admin_headers)

    resp = plan(client, ctx, vehicle, ctx["coord_headers"])
    assert resp.status_code == 201, resp.text
    shipment = resp.json()

    # sequenced pickup stops + final delivery stop
    stop_types = [s["stop_type"] for s in shipment["stops"]]
    assert stop_types == ["pickup", "pickup", "delivery"]
    assert [s["sequence_number"] for s in shipment["stops"]] == [1, 2, 3]

    # route estimate is labelled approximate
    assert shipment["route_estimate_method"] == "approximate_local"
    assert shipment["route_estimate_is_approximate"] is True
    assert shipment["estimated_transport_cost"] is not None


def test_capacity_check_blocks_overload(client, admin_headers):
    ctx = approved_proposal(client, admin_headers, n_farmers=2, quantity="600")
    _, t_headers, provider, vehicle = make_verified_transporter(client, admin_headers, capacity="500")
    resp = plan(client, ctx, vehicle, ctx["coord_headers"])
    assert resp.status_code == 409
    assert resp.json()["error"]["code"] == "VEHICLE_CAPACITY_EXCEEDED"


def test_refrigeration_requirement(client, admin_headers):
    coord, coord_headers, group = helpers.make_coordinator_with_group(client)
    product, _, _ = helpers.make_product(
        client, admin_headers, storage_category="refrigerated", shelf_life_days=4
    )
    farmer, headers, profile, farm = helpers.make_verified_farmer(client, coord_headers, group)
    listing = helpers.make_listing(client, headers, farm, product, quantity="100", days_out=3)
    helpers.confirm_listing(client, headers, listing["id"], 100)
    buyer, buyer_headers, org = helpers.make_verified_buyer(client, admin_headers)
    location = helpers.make_location(client, admin_headers, location_type="delivery_point")
    order = helpers.make_order(client, buyer_headers, location, product, quantity="100", days_out=6)
    proposal = client.post(
        "/api/v1/match-proposals/generate",
        json={"buyer_order_item_id": order["items"][0]["id"]},
        headers=coord_headers,
    ).json()["proposals"][0]
    client.post(f"/api/v1/match-proposals/{proposal['id']}/send-to-review", headers=coord_headers)
    client.post(f"/api/v1/match-proposals/{proposal['id']}/send-to-farmers", headers=coord_headers)
    mine = client.get("/api/v1/match-proposals", headers=headers).json()
    allocation = next(a for p in mine if p["id"] == proposal["id"] for a in p["allocations"])
    client.post(
        f"/api/v1/match-proposals/allocations/{allocation['id']}/respond",
        json={"accept": True},
        headers=headers,
    )
    client.post(f"/api/v1/match-proposals/{proposal['id']}/buyer-approve", headers=buyer_headers)

    _, t_headers, provider, vehicle = make_verified_transporter(client, admin_headers, refrigerated=False)
    ctx = {"proposal": proposal}
    resp = plan(client, ctx, vehicle, coord_headers)
    assert resp.status_code == 409
    assert resp.json()["error"]["code"] == "REFRIGERATION_REQUIRED"


def test_trip_offer_accept_confirm_and_status_flow(client, admin_headers):
    ctx = approved_proposal(client, admin_headers)
    transporter, t_headers, provider, vehicle = make_verified_transporter(client, admin_headers)
    shipment = plan(client, ctx, vehicle, ctx["coord_headers"]).json()

    r = client.post(f"/api/v1/shipments/{shipment['id']}/offer", headers=ctx["coord_headers"])
    assert r.json()["status"] == "offered"

    # transporter sees and accepts the trip
    trips = client.get("/api/v1/shipments?status=offered", headers=t_headers).json()
    assert any(t["id"] == shipment["id"] for t in trips)
    r = client.post(f"/api/v1/shipments/{shipment['id']}/accept", headers=t_headers)
    assert r.json()["status"] == "assigned"

    r = client.post(f"/api/v1/shipments/{shipment['id']}/confirm", headers=ctx["coord_headers"])
    assert r.json()["status"] == "confirmed"

    # transporter drives the operational statuses
    for status in ("collection_in_progress", "in_transit", "arrived"):
        r = client.post(
            f"/api/v1/shipments/{shipment['id']}/status",
            json={"status": status},
            headers=t_headers,
        )
        assert r.status_code == 200, r.text
        assert r.json()["status"] == status

    # transporter cannot jump to completed
    r = client.post(
        f"/api/v1/shipments/{shipment['id']}/status",
        json={"status": "completed"},
        headers=t_headers,
    )
    assert r.status_code == 409


def test_invalid_shipment_transition_rejected(client, admin_headers):
    ctx = approved_proposal(client, admin_headers)
    _, t_headers, provider, vehicle = make_verified_transporter(client, admin_headers)
    shipment = plan(client, ctx, vehicle, ctx["coord_headers"]).json()

    # planning → in_transit is invalid
    r = client.post(
        f"/api/v1/shipments/{shipment['id']}/status",
        json={"status": "in_transit"},
        headers=ctx["coord_headers"],
    )
    assert r.status_code == 409
    assert r.json()["error"]["code"] == "INVALID_STATE_TRANSITION"


def test_manual_stop_reorder_override(client, admin_headers):
    ctx = approved_proposal(client, admin_headers, n_farmers=2)
    _, t_headers, provider, vehicle = make_verified_transporter(client, admin_headers)
    shipment = plan(client, ctx, vehicle, ctx["coord_headers"]).json()

    pickups = [s for s in shipment["stops"] if s["stop_type"] == "pickup"]
    reversed_ids = [s["id"] for s in reversed(pickups)]
    r = client.post(
        f"/api/v1/shipments/{shipment['id']}/stops/reorder",
        json={"stop_ids_in_order": reversed_ids},
        headers=ctx["coord_headers"],
    )
    assert r.status_code == 200
    new_pickups = [s for s in r.json()["stops"] if s["stop_type"] == "pickup"]
    assert [s["id"] for s in new_pickups] == reversed_ids


def test_transporter_cannot_see_unrelated_shipments(client, admin_headers):
    ctx = approved_proposal(client, admin_headers)
    _, t1_headers, p1, v1 = make_verified_transporter(client, admin_headers)
    _, t2_headers, p2, v2 = make_verified_transporter(client, admin_headers)
    shipment = plan(client, ctx, v1, ctx["coord_headers"]).json()

    r = client.get(f"/api/v1/shipments/{shipment['id']}", headers=t2_headers)
    assert r.status_code == 404
    r = client.get("/api/v1/shipments", headers=t2_headers)
    assert all(s["id"] != shipment["id"] for s in r.json())
