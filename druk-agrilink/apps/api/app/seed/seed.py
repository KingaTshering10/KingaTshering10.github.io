"""Demonstration seed data for DrukAgriLink.

Runs the platform's own API (TestClient) so every seeded record passes the
real business rules — nothing is inserted in an impossible state. All data is
fictional. Demo credentials are development-only: seeding refuses to run when
DRUK_ENVIRONMENT=production or DRUK_SEED_DEMO_ACCOUNTS is false.

Usage:  python -m app.seed          (after `alembic upgrade head`)
"""

import sys
import uuid as uuid_lib
from datetime import date, datetime, timedelta
from decimal import Decimal

from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.core.ratelimit import rate_limiter
from app.core.security import hash_password
from app.db.session import get_sessionmaker
from app.main import app
from app.models import User

DEMO_PASSWORD = "DrukDemo2026!"  # development-only; documented in README
TODAY = date.today()

# Representative (fictional) actors in Paro & Thimphu dzongkhags
DZONGKHAGS = {
    "Paro": ["Wangchang", "Doteng", "Lamgong", "Shaba", "Lungnyi"],
    "Thimphu": ["Chang", "Kawang"],
    "Punakha": ["Guma", "Kabjisa"],
}

FARMER_NAMES = [
    "Tashi Dorji",
    "Pema Choden",
    "Karma Wangchuk",
    "Sonam Dema",
    "Ugyen Tshering",
    "Dechen Wangmo",
    "Kinley Penjor",
    "Tshering Yangzom",
    "Jigme Namgyal",
    "Choki Lhamo",
    "Sangay Khandu",
    "Deki Yangchen",
    "Phurba Tshering",
    "Namgay Zam",
    "Kezang Choden",
    "Dawa Gyeltshen",
    "Tandin Bidha",
    "Chimi Rinzin",
    "Norbu Wangdi",
    "Yeshi Selden",
]

PRODUCTS = [
    {
        "name": "Potato",
        "local_name": "Kewa",
        "category": "vegetable",
        "shelf_life_days": 90,
        "varieties": ["Desiree", "Yusi Maap"],
        "storage_category": "ambient",
    },
    {
        "name": "Chilli",
        "local_name": "Ema",
        "category": "vegetable",
        "shelf_life_days": 10,
        "varieties": ["Sha Ema", "Urka Bangala"],
        "storage_category": "cool_dry",
    },
    {
        "name": "Cabbage",
        "local_name": "Banda Kopi",
        "category": "vegetable",
        "shelf_life_days": 21,
        "varieties": ["Golden Acre"],
        "storage_category": "cool_dry",
    },
    {
        "name": "Apple",
        "local_name": "Apple",
        "category": "fruit",
        "shelf_life_days": 60,
        "varieties": ["Red Delicious", "Royal Gala"],
        "storage_category": "cool_dry",
    },
    {
        "name": "Red Rice",
        "local_name": "Eue Maap",
        "category": "grain",
        "shelf_life_days": 365,
        "varieties": ["Paro Red"],
        "storage_category": "ambient",
    },
]

BUYERS = [
    {"name": "Thimphu Hotel Pemako Kitchen", "organization_type": "hotel"},
    {"name": "Paro Central School Mess", "organization_type": "school"},
    {"name": "JDWNRH Hospital Kitchen (Demo)", "organization_type": "hospital"},
]

TRANSPORTERS = [
    {
        "organization_name": "Paro Valley Logistics",
        "vehicles": [("BP-1-A0001", "light_truck", "1500", False), ("BP-1-A0002", "truck", "4000", False)],
    },
    {
        "organization_name": "Druk Cold Chain Carriers",
        "vehicles": [("BP-2-B0011", "refrigerated_truck", "2500", True)],
    },
    {
        "organization_name": "Wang Chhu Transport",
        "vehicles": [("BP-1-C0021", "pickup", "800", False), ("BP-1-C0022", "light_truck", "1800", False)],
    },
]


class Seeder:
    def __init__(self) -> None:
        self.client = TestClient(app)
        self.tokens: dict[str, str] = {}

    # ---------- helpers ----------

    def h(self, email: str) -> dict:
        return {"Authorization": f"Bearer {self.tokens[email]}"}

    def login(self, email: str) -> None:
        rate_limiter.reset()  # seeding is a dev-only bulk operation
        resp = self.client.post("/api/v1/auth/login", json={"email": email, "password": DEMO_PASSWORD})
        resp.raise_for_status()
        self.tokens[email] = resp.json()["access_token"]

    def register(self, email: str, role: str, language: str = "en") -> None:
        resp = self.client.post(
            "/api/v1/auth/register",
            json={"email": email, "password": DEMO_PASSWORD, "role": role, "preferred_language": language},
        )
        if resp.status_code == 409:
            print(f"  seed already present ({email}); aborting to avoid duplicates.")
            sys.exit(0)
        resp.raise_for_status()
        self.login(email)

    def post(self, email: str, path: str, json: dict, expect: int = 201) -> dict:
        resp = self.client.post(f"/api/v1{path}", json=json, headers=self.h(email))
        if resp.status_code not in (expect, 200):
            raise RuntimeError(f"{path} -> {resp.status_code}: {resp.text[:300]}")
        return resp.json()

    # ---------- steps ----------

    def create_admin(self) -> str:
        email = "admin@demo.drukagrilink.bt"
        with get_sessionmaker()() as db:
            db.add(
                User(
                    email=email,
                    password_hash=hash_password(DEMO_PASSWORD),
                    role="admin",
                    is_verified=True,
                )
            )
            db.commit()
        self.login(email)
        return email

    def run(self) -> None:
        settings = get_settings()
        if settings.is_production or not settings.seed_demo_accounts:
            raise SystemExit("Seeding demo accounts is disabled in this environment.")

        print("Seeding DrukAgriLink demo data (all records fictional)…")
        admin = self.create_admin()

        # master data
        products: dict[str, dict] = {}
        for spec in PRODUCTS:
            product = self.post(
                admin,
                "/products",
                {
                    "name": spec["name"],
                    "local_name": spec["local_name"],
                    "category": spec["category"],
                    "shelf_life_days": spec["shelf_life_days"],
                    "storage_category": spec["storage_category"],
                },
            )
            for grade_code, grade_name, order in (
                ("A", "Grade A", 0),
                ("B", "Grade B", 1),
                ("C", "Grade C", 2),
            ):
                self.post(
                    admin,
                    f"/products/{product['id']}/grades",
                    {"code": grade_code, "name": grade_name, "sort_order": order},
                )
            for variety in spec["varieties"]:
                self.post(admin, f"/products/{product['id']}/varieties", {"name": variety})
            products[spec["name"]] = product

        locations = {}
        for dzongkhag, gewogs in DZONGKHAGS.items():
            for i, gewog in enumerate(gewogs[:2]):
                loc = self.post(
                    admin,
                    "/locations",
                    {
                        "name": f"{gewog} Collection Point",
                        "location_type": "collection_point",
                        "dzongkhag": dzongkhag,
                        "gewog": gewog,
                        "latitude": str(Decimal("27.30") + Decimal(i) / 10),
                        "longitude": str(Decimal("89.35") + Decimal(i) / 10),
                        "road_access_notes": "Feeder road, passable year-round.",
                    },
                )
                locations[f"{dzongkhag}/{gewog}"] = loc
        delivery_thimphu = self.post(
            admin,
            "/locations",
            {
                "name": "Centenary Farmers Market Bay 4",
                "location_type": "delivery_point",
                "dzongkhag": "Thimphu",
                "gewog": "Chang",
                "latitude": "27.4712",
                "longitude": "89.6339",
            },
        )

        # coordinators + groups
        coord1 = "coordinator@demo.drukagrilink.bt"
        self.register(coord1, "coordinator")
        group1 = self.post(
            coord1,
            "/farmer-groups",
            {
                "name": "Paro Organic Vegetable Group",
                "dzongkhag": "Paro",
                "gewog": "Wangchang",
                "registration_reference": "DAMC-PARO-042",
            },
        )
        coord2 = "coordinator2@demo.drukagrilink.bt"
        self.register(coord2, "coordinator")
        group2 = self.post(
            coord2,
            "/farmer-groups",
            {
                "name": "Punakha Red Rice Cooperative",
                "dzongkhag": "Punakha",
                "gewog": "Guma",
            },
        )
        self.post(admin, f"/admin/farmer-groups/{group1['id']}/verify", {"approve": True}, expect=200)
        self.post(admin, f"/admin/farmer-groups/{group2['id']}/verify", {"approve": True}, expect=200)

        # farmers (20), farms (>=10 with coordinates)
        farmers = []
        for index, name in enumerate(FARMER_NAMES):
            email = f"farmer{index + 1}@demo.drukagrilink.bt"
            self.register(email, "farmer", language="dz" if index % 3 == 0 else "en")
            profile = self.post(
                email,
                "/farmers/profile",
                {
                    "display_name": name,
                    "primary_phone": f"+97517{600000 + index}",
                    "farmer_registration_reference": f"FR-PARO-{1000 + index}",
                },
            )
            group = group1 if index < 14 else group2
            coord = coord1 if index < 14 else coord2
            dzongkhag = "Paro" if index < 14 else "Punakha"
            gewogs = DZONGKHAGS[dzongkhag]
            self.post(email, "/farmers/membership-request", {"farmer_group_id": group["id"]}, expect=200)
            self.post(coord, f"/farmer-groups/{group['id']}/members/{profile['id']}/approve", {}, expect=200)
            self.post(coord, f"/farmers/{profile['id']}/verify", {"approve": True}, expect=200)
            farm = self.post(
                email,
                "/farms",
                {
                    "farm_name": f"{name.split()[0]}'s Farm",
                    "dzongkhag": dzongkhag,
                    "gewog": gewogs[index % len(gewogs)],
                    "village": f"Village {index % 5 + 1}",
                    "latitude": str(Decimal("27.35") + Decimal(index % 10) / 100),
                    "longitude": str(Decimal("89.40") + Decimal(index % 7) / 100),
                    "road_access_notes": "Farm road; light truck accessible."
                    if index % 4
                    else "Footpath last 300 m; carry to road head.",
                },
            )
            farmers.append({"email": email, "profile": profile, "farm": farm, "coord": coord})

        # buyers
        buyer_emails = []
        for index, spec in enumerate(BUYERS):
            email = f"buyer{index + 1}@demo.drukagrilink.bt"
            self.register(email, "buyer")
            org = self.post(
                email,
                "/buyers/organization",
                {
                    "name": spec["name"],
                    "organization_type": spec["organization_type"],
                    "payment_terms_days": 30,
                },
            )
            self.post(admin, f"/admin/buyer-organizations/{org['id']}/verify", {"approve": True}, expect=200)
            buyer_emails.append(email)

        # transporters + vehicles
        transporter_emails = []
        vehicles = []
        for index, spec in enumerate(TRANSPORTERS):
            email = f"transporter{index + 1}@demo.drukagrilink.bt"
            self.register(email, "transporter")
            provider = self.post(
                email,
                "/transport-providers",
                {
                    "organization_name": spec["organization_name"],
                    "service_dzongkhags": ["Paro", "Thimphu", "Punakha"],
                    "phone": f"+97577{500000 + index}",
                },
            )
            self.post(
                admin, f"/admin/transport-providers/{provider['id']}/verify", {"approve": True}, expect=200
            )
            for reg, vtype, cap, refrigerated in spec["vehicles"]:
                vehicle = self.post(
                    email,
                    "/vehicles",
                    {
                        "registration_number": reg,
                        "vehicle_type": vtype,
                        "capacity_kg": cap,
                        "has_refrigeration": refrigerated,
                    },
                )
                self.post(admin, f"/admin/vehicles/{vehicle['id']}/verify", {"approve": True}, expect=200)
                vehicles.append({"email": email, "vehicle": vehicle})
            transporter_emails.append(email)

        # harvest listings across scenarios
        def listing(farmer, product, qty, price, days_out=7, confirm=None, **kw):
            body = {
                "farm_id": farmer["farm"]["id"],
                "product_id": products[product]["id"],
                "forecast_quantity": qty,
                "unit": "kg",
                "harvest_start_date": (TODAY + timedelta(days=days_out)).isoformat(),
                "harvest_end_date": (TODAY + timedelta(days=days_out + 10)).isoformat(),
                "minimum_unit_price": price,
                **kw,
            }
            created = self.post(farmer["email"], "/harvest-listings", body)
            if confirm is not None:
                created = self.post(
                    farmer["email"],
                    f"/harvest-listings/{created['id']}/confirm",
                    {"confirmed_quantity": str(confirm)},
                    expect=200,
                )
            return created

        listings = []
        for index, farmer in enumerate(farmers[:12]):
            product = ["Potato", "Chilli", "Cabbage", "Apple"][index % 4]
            qty = str(150 + index * 25)
            confirm = 150 + index * 25 if index % 5 != 4 else None  # some stay forecast-only
            listings.append(listing(farmer, product, qty, str(28 + index % 6), confirm=confirm))
        # scenario: harvest below forecast (forecast 400, confirms 300)
        listing(farmers[12], "Potato", "400", "30", confirm=300)
        # scenario: harvest above forecast within plausibility (forecast 200, confirms 260)
        listing(farmers[13], "Potato", "200", "30", confirm=260)
        # price mismatch listing: minimum far above typical offers
        listing(farmers[14], "Chilli", "180", "95", confirm=180)
        # date mismatch listing: harvest far in the future
        listing(farmers[15], "Cabbage", "220", "25", days_out=60, confirm=220)
        # draft-only listing
        self.post(
            farmers[16]["email"],
            "/harvest-listings",
            {
                "farm_id": farmers[16]["farm"]["id"],
                "product_id": products["Apple"]["id"],
                "forecast_quantity": "90",
                "unit": "kg",
                "harvest_start_date": (TODAY + timedelta(days=14)).isoformat(),
                "harvest_end_date": (TODAY + timedelta(days=21)).isoformat(),
                "minimum_unit_price": "55",
                "save_as_draft": True,
            },
        )

        # a published buyer order awaiting matching (open demand)
        self.post(
            buyer_emails[0],
            "/buyer-orders",
            {
                "delivery_location_id": delivery_thimphu["id"],
                "required_delivery_date": (TODAY + timedelta(days=15)).isoformat(),
                "save_as_draft": False,
                "items": [
                    {
                        "product_id": products["Chilli"]["id"],
                        "required_quantity": "250",
                        "unit": "kg",
                        "offered_unit_price": "40",
                        "maximum_unit_price": "48",
                    }
                ],
            },
        )
        # a cancelled order (buyer cancellation scenario)
        cancelled = self.post(
            buyer_emails[1],
            "/buyer-orders",
            {
                "delivery_location_id": delivery_thimphu["id"],
                "required_delivery_date": (TODAY + timedelta(days=20)).isoformat(),
                "save_as_draft": False,
                "items": [
                    {
                        "product_id": products["Cabbage"]["id"],
                        "required_quantity": "300",
                        "unit": "kg",
                        "offered_unit_price": "26",
                    }
                ],
            },
        )
        self.post(buyer_emails[1], f"/buyer-orders/{cancelled['id']}/cancel", {}, expect=200)

        # full successful transaction: order → match → approvals → shipment →
        # collection (partial presentation + rejection) → delivery → payments
        order = self.post(
            buyer_emails[0],
            "/buyer-orders",
            {
                "delivery_location_id": delivery_thimphu["id"],
                "required_delivery_date": (TODAY + timedelta(days=18)).isoformat(),
                "save_as_draft": False,
                "payment_terms": "Net 30 on delivery acceptance",
                "items": [
                    {
                        "product_id": products["Potato"]["id"],
                        "required_quantity": "500",
                        "unit": "kg",
                        "offered_unit_price": "34",
                        "maximum_unit_price": "40",
                    }
                ],
            },
        )
        proposals = self.post(
            coord1, "/match-proposals/generate", {"buyer_order_item_id": order["items"][0]["id"]}
        )
        proposal = proposals["proposals"][0]
        self.post(coord1, f"/match-proposals/{proposal['id']}/send-to-review", {}, expect=200)
        self.post(coord1, f"/match-proposals/{proposal['id']}/send-to-farmers", {}, expect=200)
        for allocation in proposal["allocations"]:
            with get_sessionmaker()() as db:
                from app.models import FarmerProfile, HarvestListing

                hl = db.get(HarvestListing, uuid_lib.UUID(allocation["harvest_listing_id"]))
                fp = db.get(FarmerProfile, hl.farmer_id)
                farmer_user = db.get(User, fp.user_id)
                farmer_email = farmer_user.email
            self.post(
                farmer_email,
                f"/match-proposals/allocations/{allocation['id']}/respond",
                {"accept": True},
                expect=200,
            )
        self.post(buyer_emails[0], f"/match-proposals/{proposal['id']}/buyer-approve", {}, expect=200)

        chosen = vehicles[0]
        shipment = self.post(
            coord1,
            "/shipments/plan",
            {
                "match_proposal_id": proposal["id"],
                "vehicle_id": chosen["vehicle"]["id"],
                "planned_pickup_at": (datetime.now() + timedelta(days=16)).isoformat(),
                "planned_delivery_at": (datetime.now() + timedelta(days=17)).isoformat(),
                "driver_name": "Karma Driver",
                "driver_phone": "+97577880001",
            },
        )
        self.post(coord1, f"/shipments/{shipment['id']}/offer", {}, expect=200)
        self.post(chosen["email"], f"/shipments/{shipment['id']}/accept", {}, expect=200)
        self.post(coord1, f"/shipments/{shipment['id']}/confirm", {}, expect=200)
        # transport delay scenario, then recovery
        self.post(
            chosen["email"],
            f"/shipments/{shipment['id']}/status",
            {"status": "collection_in_progress"},
            expect=200,
        )
        # collections with a partial presentation and a rejection
        pickups = [s for s in shipment["stops"] if s["stop_type"] == "pickup"]
        with get_sessionmaker()() as db:
            from app.models import FarmerProfile, HarvestListing, MatchAllocation

            allocation_rows = db.scalars(
                __import__("sqlalchemy")
                .select(MatchAllocation)
                .where(MatchAllocation.match_proposal_id == uuid_lib.UUID(proposal["id"]))
            ).all()
            listing_by_farmer = {}
            for row in allocation_rows:
                hl = db.get(HarvestListing, row.harvest_listing_id)
                listing_by_farmer[str(hl.farmer_id)] = (str(hl.id), str(row.allocated_quantity))
        for stop_index, stop in enumerate(pickups):
            with get_sessionmaker()() as db:
                from app.models import ShipmentStop

                stop_row = db.get(ShipmentStop, uuid_lib.UUID(stop["id"]))
                farmer_id = str(stop_row.farmer_id)
            listing_id, allocated = listing_by_farmer[farmer_id]
            allocated_dec = Decimal(allocated)
            if stop_index == 0:
                presented = allocated_dec - Decimal("50")
                rejected = Decimal("20")
                reason = "20 kg undersized tubers rejected at grading"
            else:
                presented = allocated_dec
                rejected = Decimal("0")
                reason = None
            accepted = presented - rejected
            self.post(
                coord1,
                "/collections",
                {
                    "shipment_stop_id": stop["id"],
                    "harvest_listing_id": listing_id,
                    "presented_quantity": str(presented),
                    "accepted_quantity": str(accepted),
                    "rejected_quantity": str(rejected),
                    "unit_price": "34",
                    "transport_deduction": "120",
                    "rejection_reason": reason,
                },
            )

        # transport delay scenario, then recovery and transit
        self.post(
            chosen["email"],
            f"/shipments/{shipment['id']}/status",
            {"status": "delayed", "note": "Landslide clearance at Chuzom; 3 h delay."},
            expect=200,
        )
        self.post(
            chosen["email"], f"/shipments/{shipment['id']}/status", {"status": "in_transit"}, expect=200
        )
        self.post(chosen["email"], f"/shipments/{shipment['id']}/status", {"status": "arrived"}, expect=200)
        with get_sessionmaker()() as db:
            from app.models import CollectionRecord, ShipmentStop

            stop_ids = [s["id"] for s in pickups]
            total_collected = sum(
                (
                    c.accepted_quantity
                    for c in db.scalars(
                        __import__("sqlalchemy")
                        .select(CollectionRecord)
                        .where(
                            CollectionRecord.shipment_stop_id.in_([uuid_lib.UUID(sid) for sid in stop_ids])
                        )
                    )
                ),
                Decimal("0"),
            )
        buyer_rejected = Decimal("15")  # partial buyer rejection scenario
        delivery = self.post(
            buyer_emails[0],
            "/deliveries",
            {
                "shipment_id": shipment["id"],
                "delivered_quantity": str(total_collected),
                "accepted_quantity": str(total_collected - buyer_rejected),
                "rejected_quantity": str(buyer_rejected),
                "arrival_condition": "Good; two crates with minor bruising",
                "rejection_reason": "15 kg bruised in transit",
            },
        )
        self.post(chosen["email"], f"/deliveries/{delivery['id']}/transporter-confirm", {}, expect=200)

        # record some payments (one fully paid, one partial, leave others pending/overdue)
        payments = self.client.get("/api/v1/payments", headers=self.h(coord1)).json()
        order_payments = [p for p in payments if p["related_order_id"] == order["id"]]
        if order_payments:
            first = order_payments[0]
            self.post(
                coord1,
                f"/payments/{first['id']}/record",
                {
                    "amount": first["amount"],
                    "payment_method": "bank_transfer",
                    "payment_reference": "BNB-2026-000188",
                    "paid_at": datetime.now().isoformat(),
                },
                expect=200,
            )
        if len(order_payments) > 1:
            second = order_payments[1]
            half = str(Decimal(second["amount"]) / 2)
            self.post(
                coord1,
                f"/payments/{second['id']}/record",
                {
                    "amount": half,
                    "payment_method": "cash",
                    "payment_reference": "CASH-BOOK-77",
                    "paid_at": datetime.now().isoformat(),
                },
                expect=200,
            )

        # disputes: one resolved, one open (overdue payment)
        farmer_email = farmers[0]["email"]
        my_payments = self.client.get("/api/v1/payments", headers=self.h(farmer_email)).json()
        if my_payments:
            dispute = self.post(
                farmer_email,
                "/disputes",
                {
                    "related_entity_type": "payment_record",
                    "related_entity_id": my_payments[0]["id"],
                    "category": "overdue_payment",
                    "description": "The cooperative payment shown as pending has not reached my account.",
                },
            )
            self.post(coord1, f"/disputes/{dispute['id']}/assign", {}, expect=200)
            self.post(
                coord1,
                f"/disputes/{dispute['id']}/resolve",
                {
                    "resolution": "Bank reference shared with the farmer; payment confirmed received.",
                },
                expect=200,
            )
        self.post(
            farmers[1]["email"],
            "/disputes",
            {
                "related_entity_type": "collection_record",
                "related_entity_id": listings[1]["id"],
                "category": "unexplained_deduction",
                "description": "The transport deduction on my receipt looks higher than agreed.",
            },
        )

        print("Seed complete.")
        print(f"  Demo password (all accounts): {DEMO_PASSWORD}")
        print("  admin@demo.drukagrilink.bt · coordinator@demo.drukagrilink.bt")
        print("  farmer1..20@ · buyer1..3@ · transporter1..3@ demo.drukagrilink.bt")


def main() -> None:
    Seeder().run()


if __name__ == "__main__":
    main()
