# DrukAgriLink — Implementation Plan

## 1. Existing repository assessment

The connected repository (`KingaTshering10/KingaTshering10.github.io`) is a personal
academic website built on the **al-folio v1 Jekyll starter**. It is deployed as a static
site via GitHub Pages and has its own CI contracts (prettier, style-contract, visual
regression, Jekyll integration tests).

Consequences for DrukAgriLink:

- **Isolation.** DrukAgriLink lives entirely under `druk-agrilink/` so the Jekyll site,
  its `_config.yml`, its `package.json`, and its CI gates remain untouched.
- **CI separation.** DrukAgriLink workflows are path-scoped to `druk-agrilink/**` and
  named with a `drukagrilink-` prefix. `druk-agrilink/` is added to the root
  `.prettierignore` because the sub-project ships its own formatters.
- **Hosting caveat.** GitHub Pages cannot host the FastAPI/PostgreSQL backend. The repo
  is the system of record for the code; deployment targets a container host (see
  `DEPLOYMENT.md`). This is a documented limitation, not a blocker for the pilot.
- **Branch.** All work is delivered on the session's designated branch
  `claude/drukagrlink-mvp-ei83lu` (serving the role of the feature branch requested as
  `feature/druk-agrilink-mvp`).

## 2. Assumptions

1. No real farmer/buyer/transporter data exists yet; all seed data is fictional.
2. No external credentials (SMS gateway, email provider, routing API, push service) are
   available in this environment — every external integration is built behind an
   adapter with a working mock/local implementation and documented replacement steps.
3. Actual money movement is out of scope; the platform records obligations and
   manually-evidenced payment status only.
4. Dzongkha translations require human verification; the framework ships with clearly
   marked `[DZ REVIEW]` placeholders rather than invented translations.
5. Pilot deployment is a single-region, single-node Docker Compose or small VM/container
   host; horizontal scale is a post-pilot concern.

## 3. Selected architecture

Monorepo under `druk-agrilink/`:

```
druk-agrilink/
├── apps/
│   ├── api/        # FastAPI + SQLAlchemy 2 + Alembic (Python 3.11)
│   └── web/        # Next.js App Router + TypeScript strict + Tailwind (PWA)
├── docs/           # architecture, data model, security, pilot, deployment, API
├── infrastructure/ # docker-compose, DB init (PostGIS), helper scripts
└── .env.example
```

- **API-first.** All business rules (state machines, matching, money math,
  authorization) live server-side. The web app is a typed client.
- **PostgreSQL 16 + PostGIS** in Docker for runtime; SQLite for fast test runs (the
  schema uses portable types; PostGIS-dependent geo queries are isolated behind the
  routing/geo service so tests do not require it).
- **Redis** for rate-limit counters and background queue in deployment; the code uses an
  in-process fallback so local dev and CI work without it.
- **Deterministic, explainable matching engine** as a pure domain service — no
  generative model anywhere in the MVP.

## 4. Technology decisions

| Area | Choice | Rationale |
| --- | --- | --- |
| Backend | FastAPI 0.115 + Pydantic 2 + SQLAlchemy 2 + Alembic | Spec-mandated; typed; OpenAPI for free |
| Auth | JWT access (30 min) + rotating refresh tokens (hashed, revocable, DB-backed) | Stateless API auth with server-side revocation |
| Password hashing | passlib `pbkdf2_sha256` (600k iterations) | Strong, pure-Python, no native-lib pinning issues |
| Money | `Decimal` end-to-end (`Numeric(14,2)` / `Numeric(12,2)`) | Binary floats are forbidden for money |
| Routing | `RoutingService` protocol: `MockRouter` (tests), `LocalApproxRouter` (haversine × mountain-road factor, labelled "approximate"), `ExternalRouterAdapter` stub | No external routing credentials available |
| Route optimisation | Deterministic nearest-neighbour stop sequencing with manual override; OR-Tools documented as the drop-in upgrade behind the same interface | OR-Tools is a heavyweight native dep; the interface keeps it swappable |
| Frontend | Next.js 15, React 19, TanStack Query 5, React Hook Form + Zod, Tailwind 3 | Spec-mandated stack |
| i18n | Locale dictionaries (en complete, dz scaffolded with review placeholders) behind a typed `t()` helper and language switcher | Framework-light, verifiable |
| PWA | Web manifest + hand-written service worker (app-shell + reference-data caching) + IndexedDB draft queue with server `row_version` conflict detection | No silent overwrite |
| Backend QA | ruff (format+lint), mypy, pytest | Fast, standard |
| Frontend QA | prettier, eslint, `tsc --noEmit`, vitest, production build | Standard |
| CI | GitHub Actions: backend, frontend, migration validation vs Postgres+PostGIS service, Docker build, gitleaks secret scan | Path-scoped to `druk-agrilink/**` |

## 5. Implementation phases

Delivered as incremental conventional commits, pushed per milestone:

1. **Docs & plan** (this commit).
2. **Backend scaffold** — app skeleton, settings, JSON logging + correlation IDs,
   health endpoints, Docker Compose (Postgres/PostGIS, Redis, API, web), `.env.example`.
3. **Auth & authorization** — users, registration, login, refresh rotation, RBAC,
   object-level policies, verification workflow, audit logging, rate limiting, tests.
4. **Master data & farmer domain** — Bhutan locations, products/varieties/grades,
   farmer profiles, farms, groups, membership, tests.
5. **Harvest & procurement** — harvest listings with revision history and availability
   accounting; buyer organizations and orders; state machines; tests.
6. **Matching** — explainable engine, proposals, allocations, three-party approval
   chain, tests for every mismatch case.
7. **Transport** — providers, vehicles, routing abstraction, shipment planning,
   sequenced stops, trip acceptance, tests.
8. **Collection → delivery → payments → disputes** — receipts with itemised
   deductions, discrepancy flags, payment obligations, dispute workflow, tests.
9. **Notifications, analytics, seed data, e2e scenarios A–D.**
10. **Frontend** — all role navigations and required screens, i18n, PWA, offline
    drafts, conflict resolution.
11. **CI + final docs + draft PR.**

## 6. Risks

| Risk | Mitigation |
| --- | --- |
| Repo is a static-site repo; backend cannot deploy from Pages | Documented; Docker Compose + container-host deployment path in `DEPLOYMENT.md` |
| No external routing/SMS/email credentials | Adapter interfaces + working mocks + contract tests + replacement docs |
| Dzongkha content correctness | Placeholder-flagged framework; human review before pilot |
| Low connectivity in gewogs | PWA app-shell caching, offline drafts, sync queue, conflict screen |
| Trust in deductions | Every deduction itemised on the receipt; audit log; farmer + coordinator dual confirmation |
| Scope breadth vs. depth | Core transaction lifecycle is fully functional and tested; peripheral features are honestly classified (pilot-ready / mocked / deferred) in the final report |

## 7. External service abstractions

`RoutingService`, `NotificationChannel` (email/SMS/push), `FileStorage`,
`RateLimiterBackend` — each with a working local/mock implementation, contract tests,
and documented production replacements. No non-functional buttons: UI actions map to
working endpoints; mocked channels record deliveries visibly.

## 8. Testing approach

- Pytest integration tests against the real FastAPI app (TestClient) with a dedicated
  per-run SQLite database and factory fixtures.
- Authorization matrix tests (cross-account access must 403/404).
- State-machine transition tests (invalid transitions must return explicit errors).
- Matching-engine unit tests for all constraint/mismatch cases.
- Money-math tests using exact `Decimal` expectations (scenario B: 300 forecast,
  250 presented, 20 rejected → 230 accepted, exact net due).
- End-to-end scenario tests A (full transaction), B (partial collection),
  C (authorization), D (offline conflict via `row_version` optimistic concurrency).
- Frontend: vitest component/util tests + `tsc` + eslint + production build in CI.

## 9. Security approach

See `SECURITY.md`. Highlights: pbkdf2 hashing, refresh rotation with reuse detection,
central policy module (no scattered role checks), server-side validation, rate limiting
on auth endpoints, secure headers, no PII in logs, no stack traces to clients,
environment-based secrets with `.env.example` placeholders only, gitleaks in CI,
audited admin actions.

## 10. GitHub delivery plan

Incremental conventional commits pushed to `claude/drukagrlink-mvp-ei83lu`; draft PR to
`main` opened once the core is pushed; PR flipped to ready after CI passes; remote SHA
verification before the final report. No force-pushes; the Jekyll site is untouched.

## 11. Pilot limitations

- One dzongkhag, one cooperative, 20–40 farmers, 1–2 crops (see `PILOT_PLAN.md`).
- Payment status is recorded evidence, not money movement.
- Travel estimates are labelled approximate until a road-routing provider is wired in.
- SMS/email/push are mock adapters until gateway credentials exist.
- Dzongkha strings require human verification before farmer-facing use.
