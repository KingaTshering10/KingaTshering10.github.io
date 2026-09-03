# DrukAgriLink

**Bhutan-focused agricultural aggregation, market coordination, and shared-transport
platform.** DrukAgriLink converts small, scattered farm harvests into confirmed
institutional orders and coordinated shared transportation — with a transparent,
auditable record of every kilogram and every ngultrum.

> This sub-project lives inside a repository that also hosts an unrelated
> al-folio personal website. Everything DrukAgriLink is contained in
> `druk-agrilink/` plus the `drukagrilink-*` GitHub Actions workflows.

## The problem

Small farmers in Bhutan often produce quantities too small to justify independent
transport, don't know confirmed buyer demand before harvesting, and receive no
transparent record of collected quantities, deductions, and payments. Institutional
buyers struggle to source consistent quantity and quality from many small farms.

## What the MVP does

- **Harvest forecasting** — farmers publish forecast → confirmed quantities with
  revision history and availability accounting.
- **Verified procurement** — institutional buyers publish demand once verified.
- **Explainable matching** — a deterministic engine aggregates compatible listings,
  scores each proposal on six visible factors, and explains itself in plain
  sentences. Nothing auto-approves: coordinator → farmers → buyer all confirm.
- **Shared transport** — capacity/refrigeration-checked vehicle assignment,
  nearest-neighbour sequenced pickup stops (manual override always available),
  labelled *approximate* route estimates.
- **Collection receipts** — dual-confirmed digital receipts with every deduction
  itemised (`DAL-YYYY-NNNNNN`), exact `Decimal` money math.
- **Delivery & discrepancy** — buyer acceptance/rejection with automatic flagging
  of in-transit loss or heavy rejection.
- **Payment obligations** — buyer→cooperative, cooperative→farmer, buyer→
  transporter, and the platform fee, each tracked with evidence-required status
  changes (method, reference, date, authorised recorder). **No money moves in the
  MVP** — the platform records obligations and manually evidenced status only.
- **Disputes, notifications, audit log, role dashboards, analytics** (measured vs
  clearly labelled estimates), **English + Dzongkha-ready i18n**, **PWA offline
  drafts with conflict resolution** (no silent overwrites).

## Architecture & stack

| Layer | Technology |
| --- | --- |
| API | Python 3.11, FastAPI, Pydantic v2, SQLAlchemy 2, Alembic |
| Database | PostgreSQL 16 + PostGIS (SQLite for tests) |
| Frontend | Next.js 15 (App Router), TypeScript strict, Tailwind, TanStack Query, RHF+Zod |
| Auth | JWT access + rotating hashed refresh tokens with family revocation |
| Offline | PWA manifest + service worker, IndexedDB draft queue, row_version conflicts |
| CI | GitHub Actions (`drukagrilink-*` workflows), gitleaks, pip/npm audit |

See `docs/ARCHITECTURE.md`, `docs/DATA_MODEL.md`, `docs/SECURITY.md`,
`docs/API.md`, `docs/PILOT_PLAN.md`, `docs/DEPLOYMENT.md`.

## Repository structure

```
druk-agrilink/
├── apps/api/        FastAPI backend (app/, alembic/, tests/)
├── apps/web/        Next.js frontend (src/app, src/lib, src/i18n)
├── infrastructure/  DB init (PostGIS)
├── docs/            architecture, data model, security, pilot, API, deployment
├── docker-compose.yml
└── .env.example     placeholders only — never commit real secrets
```

## Prerequisites

- Python 3.11+, Node 22+, Docker + Compose (for the containerised path)
- PostgreSQL 16 for a production-like local run (SQLite works for a quick start)

## Quick start (Docker)

```bash
cd druk-agrilink
cp .env.example .env          # set POSTGRES_PASSWORD and DRUK_JWT_SECRET
docker compose up -d          # postgis + redis + api (migrations run on start) + web
docker compose exec api python -m app.seed   # demo data (dev only)
# web: http://localhost:3000 · api docs: http://localhost:8000/api/docs
```

## Local development

Backend:

```bash
cd druk-agrilink/apps/api
python3 -m venv .venv && .venv/bin/pip install -e ".[dev]"
export DRUK_DATABASE_URL=postgresql+psycopg://druk:druk_dev_only@localhost:5432/drukagrilink
.venv/bin/alembic upgrade head
.venv/bin/python -m app.seed                   # demo data (refuses in production)
.venv/bin/uvicorn app.main:app --reload        # http://localhost:8000/api/docs
```

Frontend:

```bash
cd druk-agrilink/apps/web
npm install
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000 npm run dev   # http://localhost:3000
```

## Testing, linting, building

```bash
# backend (59 tests: auth, authz matrix, state machines, matching, money math, e2e A–D)
cd druk-agrilink/apps/api
.venv/bin/ruff format --check app tests && .venv/bin/ruff check app tests
.venv/bin/mypy app
.venv/bin/pytest -q

# frontend
cd druk-agrilink/apps/web
npm run format:check && npm run lint && npm run typecheck && npm test && npm run build
```

## Demo accounts (development only)

Seeding is blocked when `DRUK_ENVIRONMENT=production` or
`DRUK_SEED_DEMO_ACCOUNTS=false`. Password for every demo account: `DrukDemo2026!`

| Account | Role |
| --- | --- |
| `admin@demo.drukagrilink.bt` | Platform administrator |
| `coordinator@demo.drukagrilink.bt` | Paro Organic Vegetable Group coordinator |
| `coordinator2@demo.drukagrilink.bt` | Punakha Red Rice Cooperative coordinator |
| `farmer1..20@demo.drukagrilink.bt` | Farmers (verified, with farms + listings) |
| `buyer1..3@demo.drukagrilink.bt` | Hotel / school / hospital buyers (verified) |
| `transporter1..3@demo.drukagrilink.bt` | Transport providers with 5 vehicles |

Seeded scenarios include: a full completed transaction, partial presentation with
rejection, transport delay, partial buyer rejection, partial payment, an open and a
resolved dispute, buyer cancellation, price/date-mismatch listings, and harvests
above/below forecast.

## Environment variables

See `.env.example`. Key values: `DRUK_DATABASE_URL`, `DRUK_JWT_SECRET`
(**required in production**), `DRUK_CORS_ORIGINS`, `DRUK_PLATFORM_FEE_PERCENT`,
`DRUK_ROAD_CIRCUITY_FACTOR`, `DRUK_SEED_DEMO_ACCOUNTS` (**must be false in
production**), `NEXT_PUBLIC_API_BASE_URL`.

## Known limitations

- SMS/email/push are **mock adapters** (in-app notifications are real); a Bhutanese
  SMS gateway must be contracted for the pilot's out-of-band alerts.
- Route estimates are **approximate** (haversine × mountain-road factor, labelled
  as such) until an OSRM/Valhalla adapter is wired in; OR-Tools VRP is the
  documented upgrade for stop sequencing.
- Dzongkha strings beyond a handful of verified terms fall back to English until a
  human translator reviews them (the framework enforces this rather than inventing
  translations).
- File/photo upload endpoints are deferred; receipt `photo_urls` accept references.
- Payment status is **recorded evidence**, not money movement — by design.
- GitHub Pages hosts only the unrelated Jekyll site in this repo; DrukAgriLink
  deploys to a container host (see `docs/DEPLOYMENT.md`).
