def _create_product(client, admin_headers, name="Potato"):
    resp = client.post(
        "/api/v1/products",
        json={"name": name, "category": "vegetable", "shelf_life_days": 60},
        headers=admin_headers,
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


def test_master_data_admin_only_writes(client, admin_headers, make_user):
    _, farmer_headers = make_user("farmer")
    resp = client.post(
        "/api/v1/products",
        json={"name": "IllegalProduct", "category": "vegetable"},
        headers=farmer_headers,
    )
    assert resp.status_code == 403

    product = _create_product(client, admin_headers, name="Chilli")
    resp = client.post(
        f"/api/v1/products/{product['id']}/grades",
        json={"code": "A", "name": "Grade A", "sort_order": 0},
        headers=admin_headers,
    )
    assert resp.status_code == 201

    # any authenticated user can read
    resp = client.get("/api/v1/products", headers=farmer_headers)
    assert resp.status_code == 200
    assert any(p["name"] == "Chilli" for p in resp.json()["items"])


def test_location_hierarchy(client, admin_headers):
    resp = client.post(
        "/api/v1/locations",
        json={
            "name": "Paro Central Collection Point",
            "location_type": "collection_point",
            "dzongkhag": "Paro",
            "gewog": "Wangchang",
            "village": "Bondey",
            "latitude": "27.383",
            "longitude": "89.417",
            "road_access_notes": "Paved access; trucks up to 8t.",
        },
        headers=admin_headers,
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["country"] == "Bhutan"
    resp = client.get("/api/v1/locations?dzongkhag=Paro", headers=admin_headers)
    assert resp.json()["total"] >= 1


def test_farmer_onboarding_flow(client, make_user, admin_headers):
    farmer, headers = make_user("farmer")

    # profile required before farm creation
    resp = client.post("/api/v1/farms", json={"farm_name": "Orchard", "dzongkhag": "Paro"}, headers=headers)
    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "PROFILE_MISSING"

    resp = client.post(
        "/api/v1/farmers/profile",
        json={"display_name": "Tashi Farmer", "primary_phone": "+97517000001"},
        headers=headers,
    )
    assert resp.status_code == 201
    assert resp.json()["verification_status"] == "pending"

    resp = client.post(
        "/api/v1/farms",
        json={"farm_name": "Upper Field", "dzongkhag": "Paro", "gewog": "Doteng"},
        headers=headers,
    )
    assert resp.status_code == 201

    resp = client.get("/api/v1/farms", headers=headers)
    assert len(resp.json()) == 1


def test_group_membership_and_coordinator_scoping(client, make_user):
    coord_a, headers_a = make_user("coordinator")
    coord_b, headers_b = make_user("coordinator")

    group_a = client.post(
        "/api/v1/farmer-groups",
        json={"name": f"Paro Veg Group {coord_a['id'][:6]}", "dzongkhag": "Paro"},
        headers=headers_a,
    ).json()

    farmer, farmer_headers = make_user("farmer")
    client.post("/api/v1/farmers/profile", json={"display_name": "Pema"}, headers=farmer_headers)
    resp = client.post(
        "/api/v1/farmers/membership-request",
        json={"farmer_group_id": group_a["id"]},
        headers=farmer_headers,
    )
    assert resp.json()["membership_status"] == "requested"
    profile_id = resp.json()["id"]

    # Coordinator B must not manage group A (404, existence not leaked)
    resp = client.post(
        f"/api/v1/farmer-groups/{group_a['id']}/members/{profile_id}/approve", headers=headers_b
    )
    assert resp.status_code == 404
    resp = client.get(f"/api/v1/farmer-groups/{group_a['id']}/members", headers=headers_b)
    assert resp.status_code == 404

    # Coordinator A approves
    resp = client.post(
        f"/api/v1/farmer-groups/{group_a['id']}/members/{profile_id}/approve", headers=headers_a
    )
    assert resp.status_code == 200
    assert resp.json()["membership_status"] == "member"

    # Coordinator A verifies the farmer
    resp = client.post(
        f"/api/v1/farmers/{profile_id}/verify",
        json={"approve": True},
        headers=headers_a,
    )
    assert resp.status_code == 200
    assert resp.json()["verification_status"] == "verified"

    # Coordinator B cannot verify farmers of group A
    resp = client.post(
        f"/api/v1/farmers/{profile_id}/verify",
        json={"approve": False},
        headers=headers_b,
    )
    assert resp.status_code == 404


def test_farmer_cannot_view_other_farmer_profile(client, make_user):
    f1, h1 = make_user("farmer")
    f2, h2 = make_user("farmer")
    p1 = client.post("/api/v1/farmers/profile", json={"display_name": "Farmer One"}, headers=h1).json()
    client.post("/api/v1/farmers/profile", json={"display_name": "Farmer Two"}, headers=h2)

    resp = client.get(f"/api/v1/farmers/{p1['id']}", headers=h2)
    assert resp.status_code == 404  # existence not leaked

    resp = client.get(f"/api/v1/farmers/{p1['id']}", headers=h1)
    assert resp.status_code == 200


def test_admin_verification_queue_and_audit(client, admin_headers, make_user):
    farmer, headers = make_user("farmer")
    client.post("/api/v1/farmers/profile", json={"display_name": "Queue Farmer"}, headers=headers)

    resp = client.get("/api/v1/admin/verification-queue", headers=admin_headers)
    assert resp.status_code == 200
    assert any(f["display_name"] == "Queue Farmer" for f in resp.json()["farmers"])

    # non-admin blocked
    resp = client.get("/api/v1/admin/verification-queue", headers=headers)
    assert resp.status_code == 403

    # audit log captured registration events and is admin-only
    resp = client.get("/api/v1/admin/audit-logs?action=user.register", headers=admin_headers)
    assert resp.status_code == 200
    assert resp.json()["total"] >= 1
    resp = client.get("/api/v1/admin/audit-logs", headers=headers)
    assert resp.status_code == 403


def test_suspended_user_cannot_authenticate(client, admin_headers, make_user):
    farmer, headers = make_user("farmer")
    resp = client.get("/api/v1/users/me", headers=headers)
    user_id = resp.json()["id"]

    resp = client.post(
        f"/api/v1/admin/users/{user_id}/suspend",
        json={"reason": "suspicious activity"},
        headers=admin_headers,
    )
    assert resp.status_code == 200

    # existing access token no longer works
    resp = client.get("/api/v1/users/me", headers=headers)
    assert resp.status_code == 401
    # login blocked
    resp = client.post("/api/v1/auth/login", json={"email": farmer["email"], "password": "Str0ngPassw0rd"})
    assert resp.status_code == 401
    assert resp.json()["error"]["code"] == "ACCOUNT_SUSPENDED"
