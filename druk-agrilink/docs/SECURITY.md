# DrukAgriLink — Security

## 1. Threat model

Actors and threats considered for the pilot:

| Threat | Vector | Mitigation |
| --- | --- | --- |
| Account takeover | Credential stuffing, weak passwords | pbkdf2_sha256 (600k iters), password policy, login throttling per account+IP, security-alert notification on suspicious login patterns |
| Token theft | Stolen refresh token | Rotation on every use; reuse of a rotated token revokes the token family; short-lived access tokens |
| Cross-tenant data access | IDOR on receipts/payments/orders | Centralised object-level policies; 404 for cross-tenant reads; authorization test matrix in CI |
| Financial record tampering | Malicious edits to receipts/payments | Receipts immutable after dual confirmation; payments require method+reference+date+authorized recorder; append-only audit log |
| Privilege escalation | Role manipulation in requests | Role from server-side record only, never from client payloads; admin-only role changes are audited |
| Upload abuse | Malicious files as "photos" | Extension+MIME allow-list (jpeg/png/webp), size cap (5 MB), storage adapter keeps uploads out of the web root, served via authorised endpoints |
| Injection | SQL/command | SQLAlchemy bound parameters; no raw SQL string interpolation; Pydantic validation everywhere |
| Denial of service | Auth endpoint hammering | Rate limiting (in-process fallback, Redis in deployment) |
| Information leakage | Stack traces, verbose errors, logs | Generic 500 body with request_id; structured logs exclude PII/credentials |

## 2. Trust boundaries

1. Browser/PWA ↔ API (HTTPS; the client is untrusted — all validation and
   authorization are server-side).
2. API ↔ database/Redis (private network in deployment).
3. API ↔ external adapters (routing, SMS, email, push, storage) — mock in MVP;
   production adapters must use per-service credentials from the environment.

## 3. Data classification

| Class | Examples | Handling |
| --- | --- | --- |
| Sensitive personal | phone numbers, farmer registration refs, payment references | Access via object-level policy only; excluded from logs; minimum exposure across roles (buyers see aggregate supply, not farmer identity/finances) |
| Financial | receipts, deductions, payment records | Immutable after confirmation; audited; never deleted |
| Credentials | password hashes, refresh-token hashes | Hash-only at rest; never logged; never in audit `before/after` state |
| Operational | listings, orders, shipments | Role-scoped |
| Reference | products, grades, locations | Public within the app; cacheable offline |

## 4. Access control

- Roles: farmer, coordinator, buyer, transporter, admin.
- RBAC via router dependencies; object-level policies in `app/core/policies.py`
  (single module — no scattered role checks).
- Verification is enforced separately: unverified farmers/buyers can draft, not publish.
- Staff (coordinator/admin) sessions use the same short access-token TTL; refresh
  can be revoked centrally (account suspension revokes all token families).

## 5. Session & secret management

- JWT signing key, DB credentials, CORS origins: environment variables only.
  `.env.example` contains placeholders; `.env` is gitignored; gitleaks runs in CI.
- Refresh tokens: 32-byte random values, stored as SHA-256 hashes, single-use,
  14-day TTL, family-revocation on reuse.
- The frontend keeps the access token in memory; the refresh token is confined to the
  auth flow and is never written into the offline draft store or service-worker caches.

## 6. Logging & audit

- Structured JSON logs with request correlation IDs (`X-Request-ID` honoured/echoed).
- No request bodies, passwords, tokens, or personal identifiers in logs.
- AuditLog rows for sensitive actions (verification, suspension, payment recording,
  dispute resolution, configuration changes) written transactionally; sanitiser strips
  secret-like keys from before/after snapshots.

## 7. Upload security

Allow-list content types (`image/jpeg`, `image/png`, `image/webp`), 5 MB cap,
randomised storage names, no execution path, access through authorised endpoints only.
The MVP `LocalFileStorage` adapter documents the S3-compatible production replacement
(with signed URLs).

## 8. Abuse prevention

Rate limiting on register/login/refresh; account suspension (admin, audited);
verification gates before any publish action; dispute channel for contested records;
notification templates for security alerts that users cannot disable.

## 9. Data retention & backups

Pilot policy: financial and audit records retained for the pilot duration + 5 years
(aligning with typical cooperative bookkeeping expectations — confirm with the pilot
institution). Nightly `pg_dump` to encrypted off-host storage; restore procedure in
`DEPLOYMENT.md`. Deactivation requests anonymise contact fields but retain financial
history (documented to users at registration).

## 10. Incident response

1. Triage: identify affected accounts/records via audit log + request IDs.
2. Contain: suspend accounts / revoke token families / rotate `JWT_SECRET`
   (invalidates all sessions).
3. Eradicate & recover: patch, redeploy, restore from backup if integrity is affected.
4. Notify: pilot coordinator and affected users via the security-alert template.
5. Post-mortem recorded in the repository.

## 11. Known limitations (MVP)

- No MFA yet (recommended before scaling beyond the pilot).
- Rate limiter falls back to in-process memory without Redis (single-node only).
- Mock notification channels mean no real out-of-band alerts until gateways are wired.
- No WAF/CDN assumptions; TLS termination is the deployer's responsibility.
- Signed URLs are documented but the local storage adapter serves via app auth instead.
