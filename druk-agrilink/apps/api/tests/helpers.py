"""Scenario builders shared across test modules."""

import uuid
from datetime import date, timedelta

from tests.conftest import auth_headers, create_admin, register_user

TODAY = date.today()


def setup_admin(client):
    admin = create_admin(client)
    return auth_headers(client, admin["email"])


def make_product(client, admin_headers, name=None, **kwargs):
    name = name or f"Potato-{uuid.uuid4().hex[:6]}"
    resp = client.post(
        "/api/v1/products",
        json={"name": name, "category": "vegetable", "shelf_life_days": 60, **kwargs},
        headers=admin_headers,
    )
    assert resp.status_code == 201, resp.text
    product = resp.json()
    grade = client.post(
        f"/api/v1/products/{product['id']}/grades",
        json={"code": "A", "name": "Grade A", "sort_order": 0},
        headers=admin_headers,
    ).json()
    grade_b = client.post(
        f"/api/v1/products/{product['id']}/grades",
        json={"code": "B", "name": "Grade B", "sort_order": 1},
        headers=admin_headers,
    ).json()
    return product, grade, grade_b


def make_location(client, admin_headers, name=None, location_type="collection_point", dzongkhag="Paro"):
    resp = client.post(
        "/api/v1/locations",
        json={
            "name": name or f"CP-{uuid.uuid4().hex[:6]}",
            "location_type": location_type,
            "dzongkhag": dzongkhag,
            "latitude": "27.43",
            "longitude": "89.42",
        },
        headers=admin_headers,
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


def make_coordinator_with_group(client, dzongkhag="Paro"):
    coord = register_user(client, "coordinator")
    headers = auth_headers(client, coord["email"])
    group = client.post(
        "/api/v1/farmer-groups",
        json={"name": f"Group-{uuid.uuid4().hex[:6]}", "dzongkhag": dzongkhag},
        headers=headers,
    ).json()
    return coord, headers, group


def make_verified_farmer(client, coord_headers, group, display_name=None, dzongkhag="Paro"):
    farmer = register_user(client, "farmer")
    headers = auth_headers(client, farmer["email"])
    profile = client.post(
        "/api/v1/farmers/profile",
        json={"display_name": display_name or f"Farmer {uuid.uuid4().hex[:4]}"},
        headers=headers,
    ).json()
    client.post(
        "/api/v1/farmers/membership-request",
        json={"farmer_group_id": group["id"]},
        headers=headers,
    )
    client.post(
        f"/api/v1/farmer-groups/{group['id']}/members/{profile['id']}/approve",
        headers=coord_headers,
    )
    resp = client.post(
        f"/api/v1/farmers/{profile['id']}/verify", json={"approve": True}, headers=coord_headers
    )
    assert resp.status_code == 200, resp.text
    farm = client.post(
        "/api/v1/farms",
        json={
            "farm_name": f"Farm {uuid.uuid4().hex[:4]}",
            "dzongkhag": dzongkhag,
            "latitude": f"27.{40 + len(display_name or '') % 20}",
            "longitude": "89.40",
        },
        headers=headers,
    ).json()
    return farmer, headers, profile, farm


def make_verified_buyer(client, admin_headers, org_type="school"):
    buyer = register_user(client, "buyer")
    headers = auth_headers(client, buyer["email"])
    org = client.post(
        "/api/v1/buyers/organization",
        json={"name": f"Org-{uuid.uuid4().hex[:6]}", "organization_type": org_type},
        headers=headers,
    ).json()
    resp = client.post(
        f"/api/v1/admin/buyer-organizations/{org['id']}/verify",
        json={"approve": True},
        headers=admin_headers,
    )
    assert resp.status_code == 200, resp.text
    return buyer, headers, org


def make_listing(client, farmer_headers, farm, product, quantity="300", price="30", days_out=7, **kwargs):
    resp = client.post(
        "/api/v1/harvest-listings",
        json={
            "farm_id": farm["id"],
            "product_id": product["id"],
            "forecast_quantity": quantity,
            "unit": "kg",
            "harvest_start_date": (TODAY + timedelta(days=days_out)).isoformat(),
            "harvest_end_date": (TODAY + timedelta(days=days_out + 7)).isoformat(),
            "minimum_unit_price": price,
            **kwargs,
        },
        headers=farmer_headers,
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


def confirm_listing(client, headers, listing_id, quantity):
    resp = client.post(
        f"/api/v1/harvest-listings/{listing_id}/confirm",
        json={"confirmed_quantity": str(quantity)},
        headers=headers,
    )
    assert resp.status_code == 200, resp.text
    return resp.json()


def make_order(
    client,
    buyer_headers,
    location,
    product,
    quantity="500",
    price="35",
    days_out=12,
    publish=True,
    **item_kwargs,
):
    resp = client.post(
        "/api/v1/buyer-orders",
        json={
            "delivery_location_id": location["id"],
            "required_delivery_date": (TODAY + timedelta(days=days_out)).isoformat(),
            "save_as_draft": not publish,
            "items": [
                {
                    "product_id": product["id"],
                    "required_quantity": quantity,
                    "unit": "kg",
                    "offered_unit_price": price,
                    **item_kwargs,
                }
            ],
        },
        headers=buyer_headers,
    )
    assert resp.status_code == 201, resp.text
    return resp.json()
