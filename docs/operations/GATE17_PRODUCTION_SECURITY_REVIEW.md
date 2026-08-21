# Gate 17 Production Security Review

> **Historical status:** Pre-Azure security review completed for Gate 17. Live production security/authorization controls were subsequently accepted on 2026-08-21.


## 1. Review purpose

This document is the formal **Gate 17 Production Security Review** for ETIS
Engineering Studio.

The review is a **pre-Azure** security review. It determines whether the
source-controlled application, CI-validated production architecture, and
operator-configured production boundaries are sufficiently established to
permit a Gate 17 GO decision.

This review does **not** claim live Azure behavior. There is **no live Azure**
production deployment at the time of this review.

Live infrastructure, callback behavior, Key Vault retrieval, telemetry,
alerts, PostgreSQL restore behavior, and deployed authorization remain subject
to Post-Provisioning Production Acceptance.

Review date: **2026-08-19**

Reviewer: **William O'Connell — production/course owner and authorized Gate 17 reviewer**

Review status: **APPROVED**

---

## 2. Evidence classifications

This review uses the Gate 17 evidence classifications:

- **Verified in CI** — enforced by source-controlled implementation and
  automated regression or build evidence.
- **Operator-configured** — configuration was established outside source
  control and must be inspected as part of Gate 17.
- **Requires post-provisioning validation** — cannot honestly be verified
  before Azure resources exist.

A control is not treated as verified merely because it is documented.

---

## 3. Production security review results

### 3.1 Production sessions fail closed

**Result: PASS — Verified in CI**

Production sessions use the hardened database-backed session model rather than
development identity fallback.

Relevant regression coverage includes:

- logout revokes the presented session against replay;
- removal of course authorization invalidates an existing session;
- revoked sessions cannot fall back to developer identity;
- authorization revocation permanently invalidates the session;
- revoked staff assignments invalidate existing staff sessions;
- archived-semester authority is removed while historical evidence remains.

The production security contract therefore treats session validity as current
server-side state rather than possession of a previously issued browser token.

---

### 3.2 Current authorization is database-derived

**Result: PASS — Verified in CI**

Current authorization is database-derived and reevaluated against authoritative
course, section, team, enrollment, staff-assignment, and semester state.

Regression evidence demonstrates that stale staff authority, revoked
enrollment, revoked role authority, cross-team access, unauthorized repository
access, and student impersonation fail closed.

The browser or session token does not become an independent authorization
source.

---

### 3.3 CSRF protection remains enforced

**Result: PASS — Verified in CI**

Cookie-authenticated unsafe requests require the Studio CSRF token.

Regression coverage includes:

- cookie-authenticated mutation requires CSRF;
- an authenticated browser can obtain and use the CSRF token;
- the Studio browser client injects CSRF on same-origin mutations;
- CSRF URL handling uses the document base URI;
- CSRF rejection still receives the normal browser security headers.

---

### 3.4 Secure-cookie behavior is appropriate for production

**Result: PASS — Verified in CI**

The production session-cookie policy is centralized and hardened.

Regression coverage verifies that production cookies use the production
security contract while local HTTP development remains deliberately compatible
with development operation.

Production HTTPS is required independently of local-development behavior.

---

### 3.5 Permitted origins and HTTPS enforcement are correct

**Result: PASS — Verified in CI / Operator-configured**

Production configuration requires an HTTPS `ETIS_WEB_ORIGIN`.

The configured canonical production origin is:

`https://simulator.etisframework.org`

The production deployment workflow derives the authentication callback URIs
from that origin.

Browser security-header and production HSTS behavior are regression tested.

Final DNS resolution, certificate issuance, live HTTPS behavior, and callback
reachability are **Requires post-provisioning validation**.

---

### 3.6 Production repository access uses the GitHub App and not a PAT

**Result: PASS — Verified in CI / Operator-configured**

Private production repository evidence uses a GitHub App installation token.
Personal access tokens are not supported as the production repository
authorization mechanism.

The GitHub App implementation:

- signs short-lived App JWTs;
- locates the App installation for the exact repository;
- mints short-lived installation access tokens;
- caches those tokens only for a conservative bounded lifetime;
- fails when the App is not installed for the repository.

The evidence provider explicitly states that **Personal access tokens are never
used**.

The production GitHub App identity and private key are configured in the
protected GitHub `production` environment.

Live access to an authorized private team repository is
**Requires post-provisioning validation**.

---

### 3.7 GitHub App permissions remain least-privilege and read-only where intended

**Result: PASS — Operator-configured**

The registered ETIS Engineering Studio GitHub App is restricted to the
`etis-framework` account.

Repository permissions are limited to the read-only capabilities required by
the source-controlled GitHub API endpoint inventory:

- Actions — Read-only;
- Contents — Read-only;
- Issues — Read-only;
- Pull requests — Read-only;
- Metadata — Read-only.

Organization permissions are not granted.

Webhooks are disabled because the Studio does not implement a webhook
receiver.

The App is therefore configured as a bounded evidence-reader rather than a
repository administration or mutation mechanism.

---

### 3.8 Secrets are excluded from repository source and browser-delivered configuration

**Result: PASS — Verified in CI / Operator-configured**

Production credentials are supplied through the protected GitHub `production`
environment and provisioned to the intended Azure secret boundary.

Sensitive production values include:

- PostgreSQL administrator password;
- ETIS session secret;
- Microsoft Entra client secret;
- GitHub App private key;
- GitHub OAuth client secret;
- OpenAI API key.

The GitHub Actions environment uses `ETIS_GITHUB_*` operator-facing names where
necessary to avoid GitHub's reserved `GITHUB_` prefix while preserving the
application's established runtime configuration.

Secret values are not to be committed to source, copied into Gate 17 evidence,
returned through browser-delivered configuration, written to application logs,
or included in evidence snapshots.

A GitHub App private key accidentally exposed during setup was revoked and
replaced before the production secret was stored.

---

### 3.9 Key Vault is the intended runtime secret boundary

**Result: PASS — Verified in CI for architecture**

The Azure IaC defines Key Vault with RBAC authorization and managed-identity
secret access.

The application and migration workload reference Key Vault-backed Container
Apps secrets for runtime credentials.

Azure Container Registry administrative authentication is disabled.

Live Key Vault provisioning, managed-identity retrieval, and runtime secret
resolution are **Requires post-provisioning validation**.

---

### 3.10 AI/provider failures do not become fabricated evidence or fabricated reviewer conversation

**Result: PASS — Verified in CI**

AI processing is advisory and bounded.

The security and privacy policy requires:

- sensitive repository paths to be quarantined;
- high-confidence secrets to be redacted before model processing;
- missing repository evidence never to be fabricated;
- AI reviewers not to replace deterministic application authorization or
  student engineering responsibility.

Production OpenAI regression coverage includes provider errors, rate-limit
errors, bounded output handling, malformed/failed responses, timeouts, and
fail-closed behavior.

A provider failure therefore does not authorize fabricated evidence or
fabricated reviewer conversation.

---

### 3.11 Application and AI rate/cost controls remain bounded

**Result: PASS — Verified in CI / Operator-configured**

The application has a bounded AI-provider timeout and records model usage,
token counts, latency, and estimated cost.

Production defaults are:

- student-facing conversation: `gpt-5.6-sol`;
- repository semantic interpretation: `gpt-5.6-luna`;
- selective conversation-quality critic: `gpt-5.6-luna`.

The production OpenAI project is separate from development and has a
**$40 monthly hard spend limit**.

The application fails closed when required AI configuration is unavailable.

The OpenAI project model allow/block list is intentionally not restricted at
Gate 17 because source-controlled model selection already bounds Studio use and
other ETIS tools may use separately managed OpenAI projects.

---

### 3.12 Logging remains sensitive-data-safe

**Result: PASS — Verified in CI**

Application logging is deliberately narrow.

Permitted operational fields are bounded items such as request identifier,
HTTP method, route template, status, duration, and bounded error type.

The security policy prohibits normal logs from containing:

- session credentials;
- bearer tokens;
- OAuth authorization codes;
- cookies;
- passwords;
- API keys;
- request bodies;
- complete prompts;
- complete model responses;
- unnecessary student email addresses;
- unnecessary repository evidence.

Observability hardening regression tests exercise sensitive-data redaction and
bounded request identifiers.

Live Application Insights and Log Analytics ingestion are
**Requires post-provisioning validation**.

---

### 3.13 Backup and recovery procedures are defined

**Result: PASS — Verified in CI for procedure and logical restore**

Production operations and database-recovery runbooks define:

- backup/recovery decision criteria;
- point-in-time restore into a separate recovery server;
- explicit restore-point selection;
- private-networking requirements;
- Alembic compatibility checks;
- validation before cutover;
- rollback preservation;
- recovery evidence requirements;
- initial RTO target of 4 hours;
- initial RPO target of 24 hours.

CI executes a real PostgreSQL logical backup/restore drill using `pg_dump` and
`pg_restore`, validates the restored Alembic revision, and verifies sentinel
data.

Actual Azure PostgreSQL backup settings, point-in-time restore, private recovery
networking, and measured RTO/RPO are **Requires post-provisioning validation**.

---

### 3.14 Production authentication and authorization boundaries remain fail closed

**Result: PASS — Verified in CI / Operator-configured**

Microsoft Entra is the primary human-authentication boundary.

Normal Loyola identities must satisfy the configured institutional-domain and
course authorization rules.

The designated production-acceptance test student is not admitted by email
domain. It is bounded by:

- exact tenant-scoped Entra Object ID;
- canonical configured test identity;
- designated production-test section;
- designated production-test team;
- normal active enrollment and team authorization;
- ordinary student authority only.

The exception does not allow `gmail.com` generally.

GitHub identity linking is separate from institutional authorization.

The production Microsoft Entra application, exact callback URI, GitHub OAuth
application, GitHub App, protected GitHub environment, and production secrets
have been operator-configured.

Live Entra login, GitHub OAuth callback behavior, and deployed authorization
remain **Requires post-provisioning validation**.

---

## 4. Review findings

### Resolved findings

The Gate 17 security review identified two source-controlled issues before
reviewer sign-off.

#### Entra identity rebinding

The Microsoft Entra callback previously permitted an existing institutional
identity located through roster email or student ID to have its
`provider_subject` replaced by a newly presented Entra Object ID.

This could have weakened the intended rule that the verified tenant-scoped
Entra Object ID becomes the authoritative external identity binding.

The callback now:

- prefers an exact existing Entra Object ID binding;
- rejects duplicate Object ID bindings;
- rejects ambiguous roster matches;
- rejects an attempted roster match when the identity is already bound to a
  different Entra Object ID.

Regression coverage verifies that silent Entra Object ID rebinding fails closed.

**Finding result: RESOLVED — Verified in CI**

#### OpenAI Responses application-state storage

The OpenAI Responses request did not previously state the Studio's intended
provider-side application-state retention posture explicitly.

Production Responses API requests now set:

`store: false`

Regression coverage verifies that the production request payload disables
provider-side Responses application-state storage.

This change does not claim that all external provider security, abuse-monitoring,
or legally required retention is under Studio control.

**Finding result: RESOLVED — Verified in CI**

### Blocking findings

**No unresolved blocking production-security findings remain.**

This statement does not itself authorize Azure deployment. Gate 17 remains
subject to completion of all other blocking and operator-configured decision
rows and explicit reviewer sign-off.

### Post-provisioning security validations

The following remain intentionally open because they require live Azure:

- DNS resolution and certificate behavior;
- live HTTPS/HSTS behavior;
- live Microsoft Entra callback;
- live GitHub OAuth callback;
- GitHub App access to an authorized private team repository;
- Key Vault managed-identity retrieval;
- Application Insights and Log Analytics ingestion;
- production alert delivery;
- live `/health` and `/ready`;
- Azure PostgreSQL backup configuration;
- point-in-time restore and recovery-server networking;
- measured RTO/RPO;
- production authentication and authorization against the deployed system.

These are classified **Requires post-provisioning validation** and must block
student access until Post-Provisioning Production Acceptance is explicitly GO.

---

## 5. Security review conclusion

The Gate 17 production security architecture is suitable to proceed to final
Gate 17 decision review.

The reviewed source-controlled controls are **Verified in CI** where applicable.

The reviewed external production configuration is **Operator-configured** where
applicable.

No control in this review is represented as live-Azure verified.

The review does not weaken any requirement that is classified
**Requires post-provisioning validation**.

**Technical review result: PASS**

Reviewer sign-off: **APPROVED**

Reviewer approval confirms that this record accurately reflects the reviewed
production security posture and accepts the listed post-provisioning validation
obligations. Reviewer approval does not itself constitute Gate 17 GO.
