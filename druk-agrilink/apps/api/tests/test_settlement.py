from decimal import Decimal

from app.services.settlement import compute_receipt
from tests import helpers
from tests.test_transport import approved_proposal, make_verified_transporter, plan


def test_receipt_math_scenario_b_unit():
    """300 forecast → 250 presented, 20 rejected → 230 accepted at Nu. 30."""
    amounts = compute_receipt(
        accepted_quantity=Decimal("230"),
        unit_price=Decimal("30"),
        transport_deduction=Decimal("150"),
        other_deduction=Decimal("0"),
        platform_fee_percent=Decimal("2.0"),
    )
    assert amounts.gross_amount == Decimal("6900.00")
    assert amounts.platform_fee == Decimal("138.00")
    assert amounts.transport_deduction == Decimal("150.00")
    assert amounts.net_amount_due == Decimal("6612.00")


def test_receipt_rejects_negative_net():
    try:
        compute_receipt(Decimal("1"), Decimal("10"), transport_deduction=Decimal("100"))
        raise AssertionError("expected ValueError")
    except ValueError:
        pass


def drive_to_collection(client, admin_headers, n_farmers=1, quantity="300"):
    ctx = approved_proposal(client, admin_headers, n_farmers=n_farmers, quantity=quantity)
    transporter, t_headers, provider, vehicle = make_verified_transporter(client, admin_headers)
    shipment = plan(client, ctx, vehicle, ctx["coord_headers"]).json()
    coord = ctx["coord_headers"]
    client.post(f"/api/v1/shipments/{shipment['id']}/offer", headers=coord)
    client.post(f"/api/v1/shipments/{shipment['id']}/accept", headers=t_headers)
    client.post(f"/api/v1/shipments/{shipment['id']}/confirm", headers=coord)
    client.post(
        f"/api/v1/shipments/{shipment['id']}/status",
        json={"status": "collection_in_progress"},
        headers=t_headers,
    )
    ctx.update({"shipment": shipment, "t_headers": t_headers, "vehicle": vehicle})
    return ctx


def test_scenario_b_partial_collection_receipt(client, admin_headers):
    """Farmer forecast 300, presents 250, 20 rejected → receipt shows 230 accepted."""
    ctx = drive_to_collection(client, admin_headers, n_farmers=1, quantity="300")
    stop = next(s for s in ctx["shipment"]["stops"] if s["stop_type"] == "pickup")
    farmer = ctx["farmers"][0]

    resp = client.post(
        "/api/v1/collections",
        json={
            "shipment_stop_id": stop["id"],
            "harvest_listing_id": farmer["listing"]["id"],
            "presented_quantity": "250",
            "accepted_quantity": "230",
            "rejected_quantity": "20",
            "unit_price": "35",
            "transport_deduction": "100",
            "rejection_reason": "20 kg below grade due to bruising",
        },
        headers=ctx["coord_headers"],
    )
    assert resp.status_code == 201, resp.text
    receipt = resp.json()

    assert receipt["expected_quantity"] == "300.00"
    assert receipt["presented_quantity"] == "250.00"
    assert receipt["accepted_quantity"] == "230.00"
    assert receipt["rejected_quantity"] == "20.00"
    # gross 230×35 = 8050; platform fee 2% = 161; transport 100 → net 7789
    assert receipt["gross_amount"] == "8050.00"
    assert receipt["platform_fee"] == "161.00"
    assert receipt["transport_deduction"] == "100.00"
    assert receipt["net_amount_due"] == "7789.00"
    assert receipt["receipt_number"].startswith("DAL-")
    assert receipt["coordinator_confirmation"] is True
    assert receipt["farmer_confirmation"] is False

    # farmer sees and confirms their own receipt
    r = client.post(f"/api/v1/collections/{receipt['id']}/farmer-confirm", headers=farmer["headers"])
    assert r.json()["farmer_confirmation"] is True


def test_quantity_identity_enforced(client, admin_headers):
    ctx = drive_to_collection(client, admin_headers)
    stop = next(s for s in ctx["shipment"]["stops"] if s["stop_type"] == "pickup")
    resp = client.post(
        "/api/v1/collections",
        json={
            "shipment_stop_id": stop["id"],
            "harvest_listing_id": ctx["farmers"][0]["listing"]["id"],
            "presented_quantity": "250",
            "accepted_quantity": "240",
            "rejected_quantity": "20",
            "unit_price": "35",
        },
        headers=ctx["coord_headers"],
    )
    assert resp.status_code == 422
    assert resp.json()["error"]["code"] == "QUANTITY_MISMATCH"


def test_farmer_cannot_view_others_receipt(client, admin_headers):
    """Scenario C: Farmer A cannot access Farmer B's receipt."""
    ctx = drive_to_collection(client, admin_headers, n_farmers=2, quantity="600")
    stops = [s for s in ctx["shipment"]["stops"] if s["stop_type"] == "pickup"]
    farmer_a, farmer_b = ctx["farmers"]

    receipt = None
    for stop in stops:
        r = client.post(
            "/api/v1/collections",
            json={
                "shipment_stop_id": stop["id"],
                "harvest_listing_id": farmer_a["listing"]["id"],
                "presented_quantity": "300",
                "accepted_quantity": "300",
                "rejected_quantity": "0",
                "unit_price": "35",
            },
            headers=ctx["coord_headers"],
        )
        if r.status_code == 201:
            receipt = r.json()
            break
    assert receipt is not None

    r = client.get(f"/api/v1/collections/{receipt['id']}", headers=farmer_b["headers"])
    assert r.status_code == 404
    r = client.get(f"/api/v1/collections/{receipt['id']}", headers=farmer_a["headers"])
    assert r.status_code == 200


def full_delivery(client, admin_headers, reject="0"):
    ctx = drive_to_collection(client, admin_headers, n_farmers=1, quantity="300")
    stop = next(s for s in ctx["shipment"]["stops"] if s["stop_type"] == "pickup")
    receipt = client.post(
        "/api/v1/collections",
        json={
            "shipment_stop_id": stop["id"],
            "harvest_listing_id": ctx["farmers"][0]["listing"]["id"],
            "presented_quantity": "300",
            "accepted_quantity": "300",
            "rejected_quantity": "0",
            "unit_price": "35",
        },
        headers=ctx["coord_headers"],
    ).json()
    for status in ("in_transit", "arrived"):
        client.post(
            f"/api/v1/shipments/{ctx['shipment']['id']}/status",
            json={"status": status},
            headers=ctx["t_headers"],
        )
    accepted = str(Decimal("300") - Decimal(reject))
    delivery = client.post(
        "/api/v1/deliveries",
        json={
            "shipment_id": ctx["shipment"]["id"],
            "delivered_quantity": "300",
            "accepted_quantity": accepted,
            "rejected_quantity": reject,
            "arrival_condition": "good",
            "rejection_reason": "bruising on arrival" if reject != "0" else None,
        },
        headers=ctx["buyer_headers"],
    )
    assert delivery.status_code == 201, delivery.text
    ctx.update({"receipt": receipt, "delivery": delivery.json()})
    return ctx


def test_delivery_generates_payment_obligations(client, admin_headers):
    ctx = full_delivery(client, admin_headers)
    assert ctx["delivery"]["buyer_confirmation"] is True
    assert ctx["delivery"]["discrepancy_flag"] is False

    order = client.get(f"/api/v1/buyer-orders/{ctx['order']['id']}", headers=ctx["buyer_headers"]).json()
    assert order["order_status"] == "payment_pending"

    # buyer sees their payables: produce + transport
    buyer_payments = client.get("/api/v1/payments", headers=ctx["buyer_headers"]).json()
    payer_types = sorted(p["recipient_type"] for p in buyer_payments)
    assert payer_types == ["farmer_group", "transport_provider"]
    produce = next(p for p in buyer_payments if p["recipient_type"] == "farmer_group")
    assert produce["amount"] == "10500.00"  # 300 × 35

    # farmer sees the net receivable (gross − 2% fee)
    farmer_payments = client.get("/api/v1/payments", headers=ctx["farmers"][0]["headers"]).json()
    assert len(farmer_payments) == 1
    assert farmer_payments[0]["amount"] == "10290.00"
    assert farmer_payments[0]["status"] == "pending"


def test_partial_buyer_rejection_flags_and_prorates(client, admin_headers):
    ctx = full_delivery(client, admin_headers, reject="30")
    assert ctx["delivery"]["discrepancy_flag"] is True  # 270 vs 300 collected > 2%

    buyer_payments = client.get("/api/v1/payments", headers=ctx["buyer_headers"]).json()
    produce = next(p for p in buyer_payments if p["recipient_type"] == "farmer_group")
    assert produce["amount"] == "9450.00"  # 270 × 35 pro-rated


def test_payment_recording_requires_evidence_and_completes_order(client, admin_headers):
    ctx = full_delivery(client, admin_headers)

    payments = client.get("/api/v1/payments", headers=ctx["coord_headers"]).json()
    order_payments = [p for p in payments if p["related_order_id"] == ctx["order"]["id"]]
    assert len(order_payments) == 4  # buyer→coop, coop→farmer, buyer→transporter, coop→platform

    # missing reference rejected by validation
    r = client.post(
        f"/api/v1/payments/{order_payments[0]['id']}/record",
        json={"amount": order_payments[0]["amount"], "payment_method": "bank_transfer"},
        headers=ctx["coord_headers"],
    )
    assert r.status_code == 422

    # record all four with full evidence
    for payment in order_payments:
        r = client.post(
            f"/api/v1/payments/{payment['id']}/record",
            json={
                "amount": payment["amount"],
                "payment_method": "bank_transfer",
                "payment_reference": f"BNB-{payment['id'][:8]}",
                "paid_at": "2026-07-10T10:00:00Z",
            },
            headers=ctx["coord_headers"],
        )
        assert r.status_code == 200, r.text
        assert r.json()["status"] == "paid"

    order = client.get(f"/api/v1/buyer-orders/{ctx['order']['id']}", headers=ctx["buyer_headers"]).json()
    assert order["order_status"] == "completed"


def test_partial_payment_status(client, admin_headers):
    ctx = full_delivery(client, admin_headers)
    payments = client.get("/api/v1/payments", headers=ctx["farmers"][0]["headers"]).json()
    payment = payments[0]
    half = str(Decimal(payment["amount"]) / 2)
    r = client.post(
        f"/api/v1/payments/{payment['id']}/record",
        json={
            "amount": half,
            "payment_method": "cash",
            "payment_reference": "CASH-001",
            "paid_at": "2026-07-10T10:00:00Z",
        },
        headers=ctx["coord_headers"],
    )
    assert r.json()["status"] == "partially_paid"
    # overpayment rejected
    r = client.post(
        f"/api/v1/payments/{payment['id']}/record",
        json={
            "amount": payment["amount"],
            "payment_method": "cash",
            "payment_reference": "CASH-002",
            "paid_at": "2026-07-10T11:00:00Z",
        },
        headers=ctx["coord_headers"],
    )
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "AMOUNT_EXCEEDS_BALANCE"


def test_transporter_cannot_see_farmer_payments(client, admin_headers):
    """Scenario C: transporter access is limited to their own receivables."""
    ctx = full_delivery(client, admin_headers)
    t_payments = client.get("/api/v1/payments", headers=ctx["t_headers"]).json()
    assert all(p["recipient_type"] == "transport_provider" for p in t_payments)

    farmer_payment = client.get("/api/v1/payments", headers=ctx["farmers"][0]["headers"]).json()[0]
    r = client.get(f"/api/v1/payments/{farmer_payment['id']}", headers=ctx["t_headers"])
    assert r.status_code == 404


def test_dispute_workflow(client, admin_headers):
    ctx = full_delivery(client, admin_headers)
    farmer_headers = ctx["farmers"][0]["headers"]
    payment = client.get("/api/v1/payments", headers=farmer_headers).json()[0]

    dispute = client.post(
        "/api/v1/disputes",
        json={
            "related_entity_type": "payment_record",
            "related_entity_id": payment["id"],
            "category": "overdue_payment",
            "description": "Payment has not arrived although the due date passed.",
        },
        headers=farmer_headers,
    ).json()
    assert dispute["status"] == "open"

    # another farmer cannot see it
    coord, coord_h, group = helpers.make_coordinator_with_group(client)
    _, other_headers, _, _ = helpers.make_verified_farmer(client, coord_h, group)
    r = client.get(f"/api/v1/disputes/{dispute['id']}", headers=other_headers)
    assert r.status_code == 404

    r = client.post(f"/api/v1/disputes/{dispute['id']}/assign", headers=ctx["coord_headers"])
    assert r.json()["status"] == "under_review"
    r = client.post(
        f"/api/v1/disputes/{dispute['id']}/resolve",
        json={"resolution": "Payment reference verified with the bank and shared with the farmer."},
        headers=ctx["coord_headers"],
    )
    assert r.json()["status"] == "resolved"
    assert r.json()["resolved_at"] is not None
