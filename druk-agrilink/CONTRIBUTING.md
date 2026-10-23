# Contributing to DrukAgriLink

This sub-project lives in `druk-agrilink/` inside a repository that also hosts an
unrelated al-folio website. Keep changes for the two projects in separate PRs.

## Branching

- Branch from `main`: `feature/<topic>`, `fix/<topic>`, or `docs/<topic>`.
- Never commit directly to `main`; all changes go through a pull request.
- Rebase or merge `main` before requesting review; do not force-push shared branches.

## Commit conventions

Conventional commits, scoped where useful:

```
feat(matching): add packaging compatibility constraint
fix(payments): block overpayment beyond outstanding balance
docs: describe routing adapter replacement
test: cover shipment stop reordering
ci: pin postgis service image
```

## Pull-request expectations

- Fill in the PR template: summary, changes, tests, database changes, security
  considerations, deployment notes.
- All `drukagrilink-*` CI checks must pass (API, Web, Docker, Security).
- Schema changes require an Alembic migration that survives
  `upgrade → downgrade → upgrade` (CI enforces this).
- New behaviour requires tests; authorization changes require negative tests
  (cross-account access must 404/403).

## Code style

- **Python**: ruff (format + lint) and mypy must be clean.
  Money and quantities are `Decimal` via `SafeNumeric` — never floats.
  Status changes go through `app/domain/state_machine.py`.
  Ownership checks live in `app/core/policies.py` — no scattered role checks.
- **TypeScript**: prettier + eslint + `tsc --noEmit` must be clean; strict mode
  stays on. UI strings go through the i18n dictionaries; do not hardcode
  user-facing English in components. Dzongkha entries must be human-verified —
  never machine-translate into `src/i18n/dz.ts`.

## Test expectations

```bash
cd druk-agrilink/apps/api && .venv/bin/pytest -q       # backend
cd druk-agrilink/apps/web && npm test && npm run build # frontend
```

End-to-end scenarios A–D (complete transaction, partial collection,
authorization matrix, offline conflict) must stay green.

## Reporting security issues

Use the "🔒 Security concern" issue template **without** exploit details,
credentials, or personal data, and note that details can be shared privately
with the maintainer. See `docs/SECURITY.md` for the threat model and incident
response process.
