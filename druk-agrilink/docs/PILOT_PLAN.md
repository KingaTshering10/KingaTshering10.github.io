# DrukAgriLink — Bhutan Pilot Plan

## 1. Scope

| Dimension | Pilot choice | Rationale |
| --- | --- | --- |
| Dzongkhag | **Paro** (fallback: Punakha) | Road access, proximity to Thimphu institutional buyers, active vegetable production |
| Farmer group | One existing registered cooperative/group (e.g. a Paro vegetable group under DAMC registration) | Pilot must attach to a real, already-trusted cooperative structure |
| Farmers | 20–40 members of that group | Large enough to test aggregation, small enough to support by hand |
| Crops | **Potato** and **chilli** (one primary + one secondary) | High volume, clear grading conventions, strong institutional demand |
| Buyers | 3–5 verified institutions in Thimphu/Paro (school kitchen, hotel, hospital or wholesaler) | Mix of order sizes and payment terms |
| Transporters | 2–5 providers with Bolero/DCM-class vehicles serving Paro–Thimphu | Realistic shared-transport routes |
| Coordinator | 1 trained human coordinator (cooperative staff or extension officer) | The MVP is coordinator-operated by design |
| Duration | 12 weeks (2 wks setup/training, 8 wks operations, 2 wks evaluation) | One full seasonal cycle segment |

## 2. Roles & staffing

- **Pilot lead** — owns success criteria, buyer relationships, escalation.
- **Coordinator** — daily operation: verifies farmers, confirms supply, reviews match
  proposals, records collections, tracks payments.
- **Technical support** — one developer on call; monitors logs/backups.

## 3. Training

- Half-day coordinator training: full transaction lifecycle on seed data in a staging
  environment (the seed scenarios mirror every situation: partial fulfilment, delays,
  rejections, overdue payments, disputes).
- Two-hour farmer sessions per village: registration, harvest forecasting, reading a
  digital receipt, checking payment status; printed quick-reference card in Dzongkha.
- One-hour buyer/transporter onboarding calls.

## 4. Support process

- Coordinator is first-line support (in person / phone).
- WhatsApp/phone hotline to technical support; issues logged as GitHub issues.
- Weekly review call: pilot lead + coordinator + technical support.
- Disputes handled in-app; unresolved disputes escalate to the pilot lead.

## 5. Data collection plan

Collected automatically by the platform (measured):

- Listings, confirmed vs forecast quantities, allocation rates
- Order fulfilment %, delivery acceptance/rejection rates
- Collection vs delivery discrepancies
- Payment recording lag (due date → paid date)
- Trip capacity utilisation; stops per trip
- Dispute counts and resolution times

Collected manually (estimated / survey):

- Pre-pilot baseline: how farmers currently sell, transport cost per kg, spoilage
- Farmer/buyer/transporter satisfaction (start, mid, end surveys)
- Counterfactual transport cost (what individual trips would have cost)

**Estimated figures (transport savings, loss reduction) are always labelled as
estimates in dashboards and reports — never presented as measured facts.**

## 6. Success indicators

| Indicator | Target |
| --- | --- |
| Farmers completing ≥1 full transaction | ≥ 60% of enrolled |
| Buyer orders fulfilled ≥ 90% of requested quantity | ≥ 70% of orders |
| Collections with dual-confirmed digital receipts | 100% |
| Payments recorded with reference within terms | ≥ 80% |
| Shared trips ≥ 60% vehicle capacity | ≥ 70% of trips |
| Disputes resolved within 7 days | ≥ 80% |
| Coordinator can operate a full cycle unassisted by week 4 | yes/no |

## 7. Feedback process

- In-app dispute + notification trails reviewed weekly.
- Weekly coordinator debrief → triaged GitHub issues.
- Mid-pilot farmer focus group (in Dzongkha) on receipt clarity and trust.
- End-of-pilot report against the success indicators, with measured vs estimated
  figures clearly separated.

## 8. Pilot limitations

- Payment status is **recorded**, not moved — actual payment stays in existing channels
  (bank transfer/cash), evidenced by references in the app.
- Travel estimates are approximate (labelled) until a road-routing provider is added.
- SMS/email are mock adapters until a Bhutanese SMS gateway (e.g. via B-Mobile/
  TashiCell aggregator) is contracted — pilot relies on in-app + coordinator phone calls.
- Dzongkha strings must be human-verified before farmer-facing rollout; English is the
  operational fallback.
- Single-server deployment; a short maintenance window is acceptable to the pilot.
- Prices are negotiated by humans; the platform only checks compatibility and flags
  anomalies advisorily.

## 9. Items requiring institutional consultation before launch

- Cooperative fee rules (platform/coordination fee percentages) — configured, not hardcoded.
- Grading conventions per crop with the buyer institutions.
- Data-sharing consent wording for farmer registration (Dzongkha + English).
- Payment-terms defaults per buyer type (schools/hospitals may have procurement cycles).
