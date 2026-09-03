from decimal import Decimal

from tests.test_settlement import full_delivery


def test_scenario_a_complete_transaction(client, admin_headers):
    """The 10-step complete transaction, ending in a COMPLETED order and a
    COMPLETED shipment, with an auditable trail and notifications."""
    ctx = full_delivery(client, admin_headers)  # steps 1–8 (listing→delivery)

    # step 9: record all payments with evidence
    payments = client.get("/api/v1/payments", headers=ctx["coord_headers"]).json()
    order_payments = [p for p in payments if p["related_order_id"] == ctx["order"]["id"]]
    assert len(order_payments) == 4
    for payment in order_payments:
        r = client.post(
            f"/api/v1/payments/{payment['id']}/record",
            json={
                "amount": payment["amount"],
                "payment_method": "bank_transfer",
                "payment_reference": f"REF-{payment['id'][:8]}",
                "paid_at": "2026-07-12T09:00:00Z",
            },
            headers=ctx["coord_headers"],
        )
        assert r.status_code == 200, r.text

    # step 10: transaction completed
    order = client.get(f"/api/v1/buyer-orders/{ctx['order']['id']}", headers=ctx["buyer_headers"]).json()
    assert order["order_status"] == "completed"

    # transporter closes out the shipment
    deliveries = client.get("/api/v1/deliveries", headers=ctx["coord_headers"]).json()
    delivery = next(d for d in deliveries if d["shipment_id"] == ctx["shipment"]["id"])
    r = client.post(f"/api/v1/deliveries/{delivery['id']}/transporter-confirm", headers=ctx["t_headers"])
    assert r.status_code == 200
    shipment = client.get(f"/api/v1/shipments/{ctx['shipment']['id']}", headers=ctx["t_headers"]).json()
    assert shipment["status"] == "completed"

    # the farmer received in-app notifications along the way
    notifications = client.get("/api/v1/notifications", headers=ctx["farmers"][0]["headers"]).json()
    keys = {n["template_key"] for n in notifications["items"]}
    assert "farmer_response_required" in keys
    assert "match_approved" in keys
    assert "payment_received" in keys

    # audit trail captured the sensitive actions
    logs = client.get("/api/v1/admin/audit-logs?action=payment.recorded", headers=admin_headers).json()
    assert logs["total"] >= 4


def test_notification_centre_read_flow(client, admin_headers, make_user):
    user, headers = make_user("farmer")
    # registration produced an in-app notification
    resp = client.get("/api/v1/notifications", headers=headers)
    assert resp.status_code == 200
    items = resp.json()["items"]
    assert any(n["template_key"] == "registration_received" for n in items)

    unread = client.get("/api/v1/notifications/unread-count", headers=headers).json()["unread"]
    assert unread >= 1
    client.post("/api/v1/notifications/read-all", headers=headers)
    unread = client.get("/api/v1/notifications/unread-count", headers=headers).json()["unread"]
    assert unread == 0

    # a user cannot read another user's notification
    other, other_headers = make_user("farmer")
    other_items = client.get("/api/v1/notifications", headers=other_headers).json()["items"]
    r = client.post(f"/api/v1/notifications/{items[0]['id']}/read", headers=other_headers)
    assert r.status_code == 404
    assert all(n["id"] != items[0]["id"] for n in other_items)


def test_analytics_endpoints(client, admin_headers):
    ctx = full_delivery(client, admin_headers)

    farmer = client.get("/api/v1/analytics/farmer", headers=ctx["farmers"][0]["headers"]).json()
    assert Decimal(farmer["measured"]["quantity_sold"]) == Decimal("300.00")
    assert Decimal(farmer["measured"]["gross_revenue"]) == Decimal("10500.00")

    buyer = client.get("/api/v1/analytics/buyer", headers=ctx["buyer_headers"]).json()
    assert buyer["measured"]["orders_created"] >= 1

    transporter = client.get("/api/v1/analytics/transporter", headers=ctx["t_headers"]).json()
    assert "pending_payment" in transporter["measured"]

    platform = client.get("/api/v1/analytics/platform", headers=admin_headers).json()
    assert "estimated" in platform
    assert "method" in platform["estimated"]["transport_savings_method"] or platform["estimated"]
    # estimates are clearly separated from measured values
    assert "total_produce_sold_kg" in platform["measured"]
    assert "transport_savings_nu" in platform["estimated"]

    # farmers cannot reach platform analytics
    r = client.get("/api/v1/analytics/platform", headers=ctx["farmers"][0]["headers"])
    assert r.status_code == 403
