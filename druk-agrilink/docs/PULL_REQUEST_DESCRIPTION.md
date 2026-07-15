# feat: implement DrukAgriLink agricultural coordination MVP

## Product summary

**DrukAgriLink** is a Bhutan-focused agricultural aggregation, market coordination,
and shared-transport platform. It converts small, scattered farm harvests into
confirmed institutional orders and coordinated shared transportation, with a
transparent, auditable record of every kilogram and every ngultrum.

## Problem solved

Small Bhutanese farmers produce quantities too small to transport economically,
don't see confirmed demand before harvesting, and lack transparent records of
collections, deductions, and payments. Institutional buyers can't source
consistent quantity/quality from many small farms. DrukAgriLink coordinates the
full cycle: forecast → verified demand → explainable aggregation match →
three-party approval → shared transport → dual-confirmed collection receipts →
delivery acceptance → evidence-based payment tracking → disputes.

## Repository placement

This repository also hosts an unrelated al-folio personal website. DrukAgriLink
is fully contained in **`druk-agrilink/`** plus four path-scoped
**`drukagrilink-*`** GitHub Actions workflows, a Dependabot config, and one new
security issue template. The Jekyll site, its config, and its CI gates are
untouched (the sub-project is excluded from the site's Prettier run because it
ships its own toolchain).

## Major features

- **Auth & authorization** — JWT access + rotating, hashed, family-revocable
  refresh tokens (reuse detection); pbkdf2 password hashing; login throttling;
  centralised object-level policies (cross-tenant reads return 404); separate
  verification gates for publishing.
- **Farmer domain** — profiles, farms, farmer groups, membership approval,
  coordinator scoping (a coordinator can only manage their own groups).
- **Master data** — Bhutan location hierarchy (dzongkhag/gewog/village +
  coordinates + road-access notes), products, varieties, ordered quality grades.
- **Harvest workflow** — draft→forecast→confirmed lifecycle with append-only
  revision history, availability accounting, plausibility checks, and
  optimistic-concurrency conflict detection for offline sync.
- **Procurement** — verified buyer organizations, multi-item orders with price
  ceilings, grade minimums, packaging requirements.
- **Explainable matching** — deterministic 5-stage engine (constraints,
  grouping, allocation, weighted scoring, plain-language explanation); every
  proposal shows its factor breakdown; approval chain is coordinator → each
  farmer → buyer; availability decremented only at final approval with a
  double-booking re-check.
- **Transport** — providers, verified vehicles, capacity + refrigeration
  checks, nearest-neighbour stop sequencing with manual override, labelled
  *approximate* route estimates, trip offer/accept/decline, operational status
  updates with order-lifecycle propagation.
- **Collections & deliveries** — digital receipts (`DAL-YYYY-NNNNNN`) with
  every deduction itemised and exact Decimal math; farmer + coordinator dual
  confirmation; delivery discrepancy flagging (in-transit loss and heavy buyer
  rejection).
- **Payments & disputes** — four obligation types generated at delivery;
  status changes require method + reference + date + authorised recorder;
  partial payments; automatic overdue; order completes when all obligations
  settle; dispute open→assign→resolve.
- **Notifications** — in-app centre + mock email/SMS/push adapters; essential
  templates cannot be disabled.
- **Analytics** — per-role and platform dashboards; estimates (transport
  savings, loss reduction) clearly separated from measured values with their
  assumptions stated.
- **Frontend** — Next.js 15 PWA with role-scoped navigation for all five
  roles, ~25 screens, en/dz i18n (Dzongkha falls back to English rather than
  inventing translations), offline draft queue + conflict-resolution screen,
  accessible forms.
- **AI-ready seams (no generative model in the MVP)** — voice harvest
  extraction, demand forecasting baseline, forecast-realisation dataset,
  advisory price-anomaly check, image quality interface; all values labelled,
  reviewable, overridable.

## Database migrations

One initial Alembic migration (25 tables). CI validates
`upgrade → downgrade → upgrade` **and a full seed run** against
PostgreSQL 16 + PostGIS on every API change.

## Seed data & demo accounts (development only)

`python -m app.seed` builds the demo world **through the real API** (so every
record obeys business rules): 20 farmers, 2 groups, 10+ farms with coordinates,
5 products with grades/varieties, 3 buyers, 3 transport providers, 5 vehicles,
and lifecycle scenarios (full fulfilment, partial presentation + rejection,
transport delay, partial buyer rejection, partial/overdue payments, disputes
open + resolved, buyer cancellation, price/date mismatches, harvest above/below
forecast). Demo password `DrukDemo2026!`; seeding refuses to run in production.

## How to run

```bash
cd druk-agrilink
cp .env.example .env    # set POSTGRES_PASSWORD, DRUK_JWT_SECRET
docker compose up -d
docker compose exec api python -m app.seed
# web http://localhost:3000 · api docs http://localhost:8000/api/docs
```

Local (no Docker): see `druk-agrilink/README.md`.

## Tests & validation (all passing locally)

- **Backend**: 59 pytest integration tests — auth (rotation/reuse/ratelimit),
  authorization matrix (scenario C), state machines, matching (aggregation,
  partial fulfilment, price/date/grade mismatch, double-booking, supersede),
  transport (capacity, refrigeration, reorder), exact receipt money math
  (scenario B: 300 forecast → 250 presented → 20 rejected → 230 accepted),
  payments, disputes, offline conflict (scenario D), and the complete
  10-step transaction (scenario A). ruff + mypy clean.
- **Frontend**: 11 vitest tests (i18n fallback + no-placeholder-leak, financial
  display, accessibility of form fields/dialogs/status badges), eslint,
  prettier, `tsc --noEmit`, production build — all clean.
- **Migrations**: validated up/down/up against PostgreSQL 16 locally and in CI.

## GitHub Actions

`drukagrilink-api` (quality + migration validation with a PostGIS service),
`drukagrilink-web` (format/lint/types/tests/build), `drukagrilink-docker`
(builds both production images and smoke-tests the API container), and
`drukagrilink-security` (gitleaks + pip-audit/npm-audit). All path-scoped so
the website's CI is unaffected.

## Security

Threat model in `docs/SECURITY.md`. Highlights: refresh-token family
revocation, rate limiting, server-side validation everywhere, secure headers,
no stack traces to clients, structured logs without PII, sanitised audit
trail on all sensitive actions, environment-based secrets with placeholders
only in `.env.example`, production boot-guards against default secrets/demo
seeding, gitleaks in CI. No secrets in this diff.

## Offline support & localisation

PWA (manifest + service worker caching the shell and reference data only —
never financial data), IndexedDB draft queue with automatic replay, and a
409-driven conflict screen showing both versions (no silent overwrite).
English is complete; Dzongkha infrastructure is in place with a handful of
verified strings and enforced English fallback pending human translation.

## Mock integrations (documented replacements in docs/DEPLOYMENT.md)

SMS / email / push channels, routing (local approximate, labelled), stop
sequencing (heuristic; OR-Tools upgrade path), rate-limiter backend, file
storage (deferred).

## Known limitations

Listed in `druk-agrilink/README.md` — notably: no real out-of-band
notifications until a gateway is contracted, approximate travel estimates,
Dzongkha review outstanding, photo upload deferred, payment recording is
evidence-tracking (no money movement, by design), and this repo's GitHub Pages
cannot host the server stack.

## Recommended next phase

1. Contract a Bhutanese SMS gateway and implement the SMS adapter.
2. Self-host OSRM with the Bhutan OSM extract for real road routing.
3. Human-verified Dzongkha translation pass.
4. Photo upload (S3-compatible storage adapter with signed URLs).
5. Pilot per `docs/PILOT_PLAN.md` (Paro, one cooperative, potato + chilli).

## Manual review checklist

- [ ] `docker compose up -d` from `druk-agrilink/` starts db/redis/api/web
- [ ] `docker compose exec api python -m app.seed` loads demo data
- [ ] Log in as coordinator → generate proposals on the open chilli order
- [ ] Approve chain: farmer accept → buyer approve → plan shipment → trip accept
- [ ] Record a collection → receipt shows itemised deductions and exact net
- [ ] Confirm delivery as buyer → four payment obligations appear
- [ ] Record payment with reference → order completes; audit log shows it
- [ ] Farmer A cannot open Farmer B's receipt (404)
- [ ] Language switcher: Dzongkha shows verified strings, English elsewhere
- [ ] No `.env` or secrets anywhere in the diff
