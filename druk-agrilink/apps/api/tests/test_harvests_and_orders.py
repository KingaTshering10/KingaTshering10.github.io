from tests import helpers


def test_unverified_farmer_can_draft_but_not_publish(client, make_user, admin_headers):
    farmer, headers = make_user("farmer")
    client.post("/api/v1/farmers/profile", json={"display_name": "Draft Farmer"}, headers=headers)
    farm = client.post(
        "/api/v1/farms", json={"farm_name": "Field One", "dzongkhag": "Paro"}, headers=headers
    ).json()
    product, _, _ = helpers.make_product(client, admin_headers)

    listing = helpers.make_listing(client, headers, farm, product, save_as_draft=True)
    assert listing["status"] == "draft"

    resp = client.post(f"/api/v1/harvest-listings/{listing['id']}/publish", headers=headers)
    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "VERIFICATION_REQUIRED"


def test_harvest_lifecycle_and_revisions(client, admin_headers):
    coord, coord_headers, group = helpers.make_coordinator_with_group(client)
    farmer, headers, profile, farm = helpers.make_verified_farmer(client, coord_headers, group)
    product, _, _ = helpers.make_product(client, admin_headers)

    listing = helpers.make_listing(client, headers, farm, product, quantity="300", price="30")
    assert listing["status"] == "forecast"
    assert listing["available_quantity"] == "0"

    # update forecast → revision recorded
    resp = client.patch(
        f"/api/v1/harvest-listings/{listing['id']}",
        json={"forecast_quantity": "280"},
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.json()["row_version"] == 2

    confirmed = helpers.confirm_listing(client, headers, listing["id"], 250)
    assert confirmed["status"] == "confirmed"
    assert confirmed["confirmed_quantity"] == "250"
    assert confirmed["available_quantity"] == "250"

    revisions = client.get(f"/api/v1/harvest-listings/{listing['id']}/revisions", headers=headers).json()
    fields = [r["field"] for r in revisions]
    assert "forecast_quantity" in fields and "confirmed_quantity" in fields


def test_invalid_transition_returns_explicit_error(client, admin_headers):
    coord, coord_headers, group = helpers.make_coordinator_with_group(client)
    farmer, headers, profile, farm = helpers.make_verified_farmer(client, coord_headers, group)
    product, _, _ = helpers.make_product(client, admin_headers)
    listing = helpers.make_listing(client, headers, farm, product)

    # forecast → publish (forecast again) is invalid
    resp = client.post(f"/api/v1/harvest-listings/{listing['id']}/publish", headers=headers)
    assert resp.status_code == 409
    body = resp.json()["error"]
    assert body["code"] == "INVALID_STATE_TRANSITION"
    assert body["current"] == "forecast"
    assert "allowed" in body


def test_confirm_rejects_implausible_quantity(client, admin_headers):
    coord, coord_headers, group = helpers.make_coordinator_with_group(client)
    farmer, headers, profile, farm = helpers.make_verified_farmer(client, coord_headers, group)
    product, _, _ = helpers.make_product(client, admin_headers)
    listing = helpers.make_listing(client, headers, farm, product, quantity="100")

    resp = client.post(
        f"/api/v1/harvest-listings/{listing['id']}/confirm",
        json={"confirmed_quantity": "1000"},
        headers=headers,
    )
    assert resp.status_code == 422
    assert resp.json()["error"]["code"] == "HARVEST_QUANTITY_INVALID"


def test_offline_conflict_detection(client, admin_headers):
    """Scenario D: stale row_version → 409 with both versions, no overwrite."""
    coord, coord_headers, group = helpers.make_coordinator_with_group(client)
    farmer, headers, profile, farm = helpers.make_verified_farmer(client, coord_headers, group)
    product, _, _ = helpers.make_product(client, admin_headers)
    listing = helpers.make_listing(client, headers, farm, product, quantity="300")
    version_seen_offline = listing["row_version"]

    # server-side change happens while the client is offline
    client.patch(
        f"/api/v1/harvest-listings/{listing['id']}",
        json={"forecast_quantity": "320"},
        headers=headers,
    )

    # offline client reconnects and replays its edit with the stale version
    resp = client.patch(
        f"/api/v1/harvest-listings/{listing['id']}",
        json={"forecast_quantity": "290", "expected_row_version": version_seen_offline},
        headers=headers,
    )
    assert resp.status_code == 409
    body = resp.json()["error"]
    assert body["code"] == "CONFLICT_STALE_VERSION"
    assert body["server_state"]["forecast_quantity"] == "320"

    # server value was NOT silently overwritten
    current = client.get(f"/api/v1/harvest-listings/{listing['id']}", headers=headers).json()
    assert current["forecast_quantity"] == "320"


def test_farmer_cannot_see_others_listing(client, admin_headers):
    coord, coord_headers, group = helpers.make_coordinator_with_group(client)
    f1, h1, p1, farm1 = helpers.make_verified_farmer(client, coord_headers, group)
    f2, h2, p2, farm2 = helpers.make_verified_farmer(client, coord_headers, group)
    product, _, _ = helpers.make_product(client, admin_headers)
    listing = helpers.make_listing(client, h1, farm1, product)

    resp = client.get(f"/api/v1/harvest-listings/{listing['id']}", headers=h2)
    assert resp.status_code == 404

    # but the group coordinator can see it
    resp = client.get(f"/api/v1/harvest-listings/{listing['id']}", headers=coord_headers)
    assert resp.status_code == 200


def test_buyer_onboarding_and_order_publishing_gate(client, admin_headers, make_user):
    buyer, headers = make_user("buyer")
    org = client.post(
        "/api/v1/buyers/organization",
        json={"name": "Thimphu School Kitchen", "organization_type": "school"},
        headers=headers,
    ).json()
    assert org["verification_status"] == "pending"

    location = helpers.make_location(client, admin_headers, location_type="delivery_point")
    product, _, _ = helpers.make_product(client, admin_headers)

    # drafts allowed before verification
    draft = helpers.make_order(client, headers, location, product, publish=False)
    assert draft["order_status"] == "draft"

    # publishing blocked
    resp = client.post(f"/api/v1/buyer-orders/{draft['id']}/publish", headers=headers)
    assert resp.status_code == 403

    # verify, then publish works
    client.post(
        f"/api/v1/admin/buyer-organizations/{org['id']}/verify",
        json={"approve": True},
        headers=admin_headers,
    )
    resp = client.post(f"/api/v1/buyer-orders/{draft['id']}/publish", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["order_status"] == "published"


def test_buyer_cannot_edit_other_buyers_order(client, admin_headers):
    b1, h1, org1 = helpers.make_verified_buyer(client, admin_headers)
    b2, h2, org2 = helpers.make_verified_buyer(client, admin_headers)
    location = helpers.make_location(client, admin_headers, location_type="delivery_point")
    product, _, _ = helpers.make_product(client, admin_headers)

    order = helpers.make_order(client, h1, location, product)
    resp = client.post(f"/api/v1/buyer-orders/{order['id']}/cancel", headers=h2)
    assert resp.status_code == 404

    resp = client.get(f"/api/v1/buyer-orders/{order['id']}", headers=h2)
    assert resp.status_code == 404


def test_order_item_price_validation(client, admin_headers):
    buyer, headers, org = helpers.make_verified_buyer(client, admin_headers)
    location = helpers.make_location(client, admin_headers, location_type="delivery_point")
    product, _, _ = helpers.make_product(client, admin_headers)

    resp = client.post(
        "/api/v1/buyer-orders",
        json={
            "delivery_location_id": location["id"],
            "required_delivery_date": "2030-01-01",
            "items": [
                {
                    "product_id": product["id"],
                    "required_quantity": "100",
                    "offered_unit_price": "50",
                    "maximum_unit_price": "40",
                }
            ],
        },
        headers=headers,
    )
    assert resp.status_code == 422
