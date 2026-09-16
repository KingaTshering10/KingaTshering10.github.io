# DrukAgriLink — Deployment

## Environments

| Environment | Purpose | How |
| --- | --- | --- |
| Development | Local work | venv + `uvicorn --reload`, `npm run dev`, local Postgres or SQLite |
| Staging | Pilot training & UAT | Docker Compose on a small VM, seeded demo data |
| Production (pilot) | Live pilot | Docker Compose on a hardened VM/container host, TLS reverse proxy in front |

GitHub Pages in this repository serves only the unrelated Jekyll site;
DrukAgriLink requires a container host (any VPS, or a managed container
service reachable from Bhutan with acceptable latency).

## Production checklist

1. `cp .env.example .env`; set a strong `POSTGRES_PASSWORD`, a random
   `DRUK_JWT_SECRET` (`openssl rand -hex 32`), `DRUK_ENVIRONMENT=production`,
   `DRUK_SEED_DEMO_ACCOUNTS=false`, and the real `DRUK_CORS_ORIGINS` /
   `NEXT_PUBLIC_API_BASE_URL`. The API **refuses to boot** in production with
   the default JWT secret or demo seeding enabled.
2. `docker compose up -d` — the API container runs `alembic upgrade head`
   before serving.
3. Put a TLS-terminating reverse proxy (Caddy/nginx) in front of :3000 and
   :8000; the compose file binds both to 127.0.0.1 only.
4. Create the first admin directly in the database (there is deliberately no
   self-service admin registration):
   ```bash
   docker compose exec api python -c "
   from app.db.session import get_sessionmaker
   from app.core.security import hash_password
   from app.models import User
   import getpass
   with get_sessionmaker()() as db:
       db.add(User(email='admin@your-domain', password_hash=hash_password(getpass.getpass()), role='admin', is_verified=True)); db.commit()"
   ```

## Migrations

- Apply: `docker compose exec api alembic upgrade head`
- New migration (dev): `alembic revision --autogenerate -m "…"` then review the
  generated file (custom `SafeNumeric` columns import `app.db.base`).
- CI validates `upgrade → downgrade → upgrade` plus a full seed run against
  PostgreSQL + PostGIS on every API change.

## Rollback

1. `docker compose exec api alembic downgrade -1` (schema) — only if the
   release's migration is reversible; otherwise restore from backup.
2. Redeploy the previous image tag (`docker compose up -d api web`).
3. Confirm `/health/ready` and run a smoke transaction on staging first.

## Backups

Nightly dump, encrypted, shipped off the host:

```bash
docker compose exec -T db pg_dump -U druk drukagrilink | gzip \
  | age -r <recipient> > backups/drukagrilink-$(date +%F).sql.gz
```

Restore: `gunzip -c … | docker compose exec -T db psql -U druk drukagrilink`.
Test a restore before the pilot starts and monthly thereafter. Retain per the
pilot data policy (docs/SECURITY.md §9).

## Monitoring, logging, health

- `GET /health` (liveness) and `GET /health/ready` (DB connectivity) —
  compose healthchecks already poll these; point uptime monitoring at them.
- Logs are structured JSON on stdout with request IDs
  (`docker compose logs -f api`); ship to your aggregator of choice.
  No PII or credentials appear in logs.
- Watch: 5xx rate, auth 429s (attack signal), `INVALID_STATE_TRANSITION`
  spikes (client bugs), DB disk, backup job success.

## Secret management

Secrets live only in the host's `.env` (never committed; gitleaks runs in CI).
Rotating `DRUK_JWT_SECRET` invalidates all sessions — do it during a
maintenance window. Rotate `POSTGRES_PASSWORD` by updating both the DB user
and `.env` together.

## Replacing the mock adapters

| Adapter | MVP implementation | Production replacement |
| --- | --- | --- |
| SMS (`MockSmsChannel`) | in-memory outbox | implement `ChannelAdapter.send` against a Bhutan SMS aggregator (B-Mobile/TashiCell); register in `app/services/notifications._ADAPTERS` |
| Email (`MockEmailChannel`) | in-memory outbox | SMTP/SES adapter, same seam |
| Push (`MockPushChannel`) | in-memory outbox | FCM/WebPush adapter, same seam |
| Routing (`LocalApproxRouter`) | haversine × circuity factor, labelled approximate | self-hosted OSRM/Valhalla with Bhutan OSM extract; implement `RoutingService.estimate_route`, call `set_router()`; estimates then stop being labelled approximate |
| Stop sequencing | nearest-neighbour heuristic | OR-Tools VRP behind `sequence_stops_nearest_neighbour`'s signature |
| Rate limiter | in-process (single node) | Redis-backed `RateLimiterBackend` using the compose `redis` service |
| File storage | deferred (URL references) | S3-compatible adapter with signed URLs |

Each mock is functional (visible in dev tooling and tests) — no dead buttons.
