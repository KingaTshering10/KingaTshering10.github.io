from tests import helpers
from tests.conftest import auth_headers, register_user


def _setup(client, admin_headers, n_farmers=2, confirm_qty=300):
    """Coordinator+group, N verified farmers with confirmed listings, verified buyer."""
    coord, coord_headers, group = helpers.make_coordinator_with_group(client)
    product, grade_a, grade_b = helpers.make_product(client, admin_headers)
    farmers = []
    for _ in range(n_farmers):
        farmer, headers, profile, farm = helpers.make_verified_farmer(client, coord_headers, group)
        listing = helpers.make_listing(client, headers, farm, product, quantity=str(confirm_qty))
        listing = helpers.confirm_listing(client, headers, listing["id"], confirm_qty)
        farmers.append({"headers": headers, "profile": profile, "farm": farm, "listing": listing})
    buyer, buyer_headers, org = helpers.make_verified_buyer(client, admin_headers)
    location = helpers.make_location(client, admin_headers, location_type="delivery_point")
    return coord_headers, product, grade_a, grade_b, farmers, buyer_headers, location


def _generate(client, coord_headers, order):
    item_id = order["items"][0]["id"]
    resp = client.post(
        "/api/v1/match-proposals/generate",
        json={"buyer_order_item_id": item_id},
        headers=coord_headers,
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


def test_multi_farmer_aggregation_with_explanation(client, admin_headers):
    coord_headers, product, _, _, farmers, buyer_headers, location = _setup(
        client, admin_headers, n_farmers=2, confirm_qty=300
    )
    order = helpers.make_order(client, buyer_headers, location, product, quantity="500", price="35")
    result = _generate(client, coord_headers, order)
    assert result["count"] == 1
    proposal = result["proposals"][0]

    # two farmers aggregated to cover 500kg
    assert proposal["proposed_quantity"] == "500.00"
    assert len(proposal["allocations"]) == 2
    quantities = sorted(a["allocated_quantity"] for a in proposal["allocations"])
    assert quantities == ["200.00", "300.00"]

    # explainable score
    assert 0 <= proposal["score"] <= 100
    assert set(proposal["score_factors"]) == {
        "quantity_fit",
        "date_fit",
        "price_fit",
        "quality_fit",
        "transport_efficiency",
        "spoilage_risk",
    }
    assert proposal["score_factors"]["quantity_fit"] == 100
    assert any("100.00%" in s or "covers" in s for s in proposal["score_explanation"])
    assert proposal["matching_method"] == "deterministic_v1"


def test_partial_fulfilment(client, admin_headers):
    coord_headers, product, _, _, farmers, buyer_headers, location = _setup(
        client, admin_headers, n_farmers=1, confirm_qty=200
    )
    order = helpers.make_order(client, buyer_headers, location, product, quantity="500")
    result = _generate(client, coord_headers, order)
    proposal = result["proposals"][0]
    assert proposal["proposed_quantity"] == "200.00"
    assert proposal["score_factors"]["quantity_fit"] == 40


def test_price_mismatch_excluded(client, admin_headers):
    coord_headers, product, _, _, farmers, buyer_headers, location = _setup(
        client, admin_headers, n_farmers=1
    )
    # farmer minimum (30) above buyer max (25) → no candidates
    order = helpers.make_order(client, buyer_headers, location, product, price="20", maximum_unit_price="25")
    result = _generate(client, coord_headers, order)
    assert result["count"] == 0


def test_date_mismatch_excluded(client, admin_headers):
    coord, coord_headers, group = helpers.make_coordinator_with_group(client)
    product, _, _ = helpers.make_product(client, admin_headers)
    farmer, headers, profile, farm = helpers.make_verified_farmer(client, coord_headers, group)
    # harvest starts 30 days out; delivery required in 5 days
    listing = helpers.make_listing(client, headers, farm, product, days_out=30)
    helpers.confirm_listing(client, headers, listing["id"], 300)
    buyer, buyer_headers, org = helpers.make_verified_buyer(client, admin_headers)
    location = helpers.make_location(client, admin_headers, location_type="delivery_point")
    order = helpers.make_order(client, buyer_headers, location, product, days_out=5)
    result = _generate(client, coord_headers, order)
    assert result["count"] == 0


def test_quality_mismatch_excluded(client, admin_headers):
    coord_headers, product, grade_a, grade_b, farmers, buyer_headers, location = _setup(
        client, admin_headers, n_farmers=0
    )
    coord, coord_headers2, group = helpers.make_coordinator_with_group(client)
    farmer, headers, profile, farm = helpers.make_verified_farmer(client, coord_headers2, group)
    listing = helpers.make_listing(client, headers, farm, product, expected_grade_id=grade_b["id"])
    helpers.confirm_listing(client, headers, listing["id"], 300)
    # buyer demands grade A minimum; farmer expects grade B → excluded
    order = helpers.make_order(client, buyer_headers, location, product, minimum_grade_id=grade_a["id"])
    result = _generate(client, coord_headers2, order)
    assert result["count"] == 0


def test_unverified_farmer_excluded(client, admin_headers):
    coord, coord_headers, group = helpers.make_coordinator_with_group(client)
    product, _, _ = helpers.make_product(client, admin_headers)

    # unverified farmer with a confirmed-quality listing cannot appear
    farmer = register_user(client, "farmer")
    headers = auth_headers(client, farmer["email"])
    client.post("/api/v1/farmers/profile", json={"display_name": "Unverified"}, headers=headers)
    farm = client.post(
        "/api/v1/farms", json={"farm_name": "Hidden Farm", "dzongkhag": "Paro"}, headers=headers
    ).json()
    helpers.make_listing(client, headers, farm, product, save_as_draft=True)

    buyer, buyer_headers, org = helpers.make_verified_buyer(client, admin_headers)
    location = helpers.make_location(client, admin_headers, location_type="delivery_point")
    order = helpers.make_order(client, buyer_headers, location, product)
    result = _generate(client, coord_headers, order)
    assert result["count"] == 0


def test_full_approval_chain_and_allocation_accounting(client, admin_headers):
    coord_headers, product, _, _, farmers, buyer_headers, location = _setup(
        client, admin_headers, n_farmers=2, confirm_qty=300
    )
    order = helpers.make_order(client, buyer_headers, location, product, quantity="450")
    proposal = _generate(client, coord_headers, order)["proposals"][0]

    # coordinator review → farmers
    r = client.post(f"/api/v1/match-proposals/{proposal['id']}/send-to-review", headers=coord_headers)
    assert r.status_code == 200
    r = client.post(f"/api/v1/match-proposals/{proposal['id']}/send-to-farmers", headers=coord_headers)
    assert r.status_code == 200

    # both farmers accept
    for farmer in farmers:
        mine = client.get("/api/v1/match-proposals", headers=farmer["headers"]).json()
        allocation = next(
            a
            for p in mine
            if p["id"] == proposal["id"]
            for a in p["allocations"]
            if a["harvest_listing_id"] == farmer["listing"]["id"]
        )
        r = client.post(
            f"/api/v1/match-proposals/allocations/{allocation['id']}/respond",
            json={"accept": True},
            headers=farmer["headers"],
        )
        assert r.status_code == 200, r.text

    # buyer approves → availability decremented, statuses updated
    r = client.post(f"/api/v1/match-proposals/{proposal['id']}/buyer-approve", headers=buyer_headers)
    assert r.status_code == 200
    assert r.json()["status"] == "approved"

    l1 = client.get(
        f"/api/v1/harvest-listings/{farmers[0]['listing']['id']}", headers=farmers[0]["headers"]
    ).json()
    l2 = client.get(
        f"/api/v1/harvest-listings/{farmers[1]['listing']['id']}", headers=farmers[1]["headers"]
    ).json()
    availabilities = sorted([l1["available_quantity"], l2["available_quantity"]])
    assert availabilities == ["0.00", "150.00"]
    statuses = sorted([l1["status"], l2["status"]])
    assert statuses == ["fully_allocated", "partially_allocated"]

    order_now = client.get(f"/api/v1/buyer-orders/{order['id']}", headers=buyer_headers).json()
    assert order_now["order_status"] == "confirmed"


def test_farmer_decline_rejects_proposal(client, admin_headers):
    coord_headers, product, _, _, farmers, buyer_headers, location = _setup(
        client, admin_headers, n_farmers=1
    )
    order = helpers.make_order(client, buyer_headers, location, product, quantity="200")
    proposal = _generate(client, coord_headers, order)["proposals"][0]
    client.post(f"/api/v1/match-proposals/{proposal['id']}/send-to-review", headers=coord_headers)
    client.post(f"/api/v1/match-proposals/{proposal['id']}/send-to-farmers", headers=coord_headers)

    farmer = farmers[0]
    mine = client.get("/api/v1/match-proposals", headers=farmer["headers"]).json()
    allocation = mine[0]["allocations"][0]
    r = client.post(
        f"/api/v1/match-proposals/allocations/{allocation['id']}/respond",
        json={"accept": False},
        headers=farmer["headers"],
    )
    assert r.json()["status"] == "rejected"

    # availability untouched by a rejected proposal
    listing = client.get(
        f"/api/v1/harvest-listings/{farmer['listing']['id']}", headers=farmer["headers"]
    ).json()
    assert listing["available_quantity"] == "300.00"


def test_regeneration_supersedes_open_proposals(client, admin_headers):
    coord_headers, product, _, _, farmers, buyer_headers, location = _setup(
        client, admin_headers, n_farmers=1
    )
    order = helpers.make_order(client, buyer_headers, location, product)
    first = _generate(client, coord_headers, order)["proposals"][0]
    second = _generate(client, coord_headers, order)["proposals"][0]
    assert first["id"] != second["id"]
    old = client.get(f"/api/v1/match-proposals/{first['id']}", headers=coord_headers).json()
    assert old["status"] == "superseded"


def test_already_allocated_quantity_not_double_booked(client, admin_headers):
    """Competing buyer orders cannot double-book the same listing."""
    coord_headers, product, _, _, farmers, buyer_headers, location = _setup(
        client, admin_headers, n_farmers=1, confirm_qty=300
    )
    buyer2, buyer2_headers, org2 = helpers.make_verified_buyer(client, admin_headers)

    order1 = helpers.make_order(client, buyer_headers, location, product, quantity="300")
    order2 = helpers.make_order(client, buyer2_headers, location, product, quantity="300")
    p1 = _generate(client, coord_headers, order1)["proposals"][0]
    p2 = _generate(client, coord_headers, order2)["proposals"][0]

    def drive_to_buyer(p, farmer):
        client.post(f"/api/v1/match-proposals/{p['id']}/send-to-review", headers=coord_headers)
        client.post(f"/api/v1/match-proposals/{p['id']}/send-to-farmers", headers=coord_headers)
        mine = client.get("/api/v1/match-proposals", headers=farmer["headers"]).json()
        allocation = next(a for prop in mine if prop["id"] == p["id"] for a in prop["allocations"])
        client.post(
            f"/api/v1/match-proposals/allocations/{allocation['id']}/respond",
            json={"accept": True},
            headers=farmer["headers"],
        )

    drive_to_buyer(p1, farmers[0])
    drive_to_buyer(p2, farmers[0])

    r = client.post(f"/api/v1/match-proposals/{p1['id']}/buyer-approve", headers=buyer_headers)
    assert r.status_code == 200

    # second approval must fail: availability is now zero
    r = client.post(f"/api/v1/match-proposals/{p2['id']}/buyer-approve", headers=buyer2_headers)
    assert r.status_code == 409
    assert r.json()["error"]["code"] == "AVAILABILITY_CHANGED"


def test_farmer_cannot_respond_to_others_allocation(client, admin_headers):
    coord_headers, product, _, _, farmers, buyer_headers, location = _setup(
        client, admin_headers, n_farmers=1
    )
    order = helpers.make_order(client, buyer_headers, location, product, quantity="100")
    proposal = _generate(client, coord_headers, order)["proposals"][0]
    client.post(f"/api/v1/match-proposals/{proposal['id']}/send-to-review", headers=coord_headers)
    client.post(f"/api/v1/match-proposals/{proposal['id']}/send-to-farmers", headers=coord_headers)

    intruder = register_user(client, "farmer")
    intruder_headers = auth_headers(client, intruder["email"])
    client.post("/api/v1/farmers/profile", json={"display_name": "Intruder"}, headers=intruder_headers)

    allocation_id = proposal["allocations"][0]["id"]
    r = client.post(
        f"/api/v1/match-proposals/allocations/{allocation_id}/respond",
        json={"accept": True},
        headers=intruder_headers,
    )
    assert r.status_code == 404
