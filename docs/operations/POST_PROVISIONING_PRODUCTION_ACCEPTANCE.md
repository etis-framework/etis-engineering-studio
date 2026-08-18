# Post-Provisioning Production Acceptance

## 1. Purpose

**Post-Provisioning Production Acceptance** is the live-environment acceptance
review performed after Gate 17 has authorized Azure provisioning and after the
production infrastructure/application have been deployed.

Its purpose is to determine whether the deployed ETIS Engineering Studio is
safe and operationally ready for controlled **student access**.

Student access remains disabled until this review reaches an **explicit GO**.

A successful deployment is not itself a go-live decision.

A successful `/ready` response is necessary but not sufficient for student
production authorization.

---

## 2. Relationship to Gate 17

Gate 17 authorizes Azure provisioning.

Post-Provisioning Production Acceptance authorizes student production use.

This review consumes:

- Gate 17 evidence;
- live Azure deployment evidence;
- Gate 16 operational evidence;
- identity/integration validation;
- recovery evidence;
- final Wave 1 acceptance evidence.

No live control may be marked verified merely because corresponding
infrastructure-as-code exists.

---

## 3. Decision outcomes

### GO

GO means all required live production controls pass and controlled student
access may be enabled.

### NO-GO

NO-GO means student access remains disabled until blocking findings are
resolved and revalidated.

A deployment may remain online for controlled operator testing during NO-GO
when doing so is necessary to complete acceptance evidence and does not expose
students or unauthorized users.

---

## 4. Final hostname, DNS, and HTTPS

Verify:

- final production DNS resolves to the intended service;
- the intended hostname matches `ETIS_WEB_ORIGIN`;
- HTTPS is enforced;
- the browser receives a valid certificate;
- insecure HTTP is not accepted where prohibited;
- security headers remain present;
- callback origins match the public hostname.

Result: **PASS / FAIL**

Evidence:

Owner:

---

## 5. Microsoft Entra authentication

Verify live **Microsoft Entra** behavior:

- authorized Loyola identity can authenticate;
- unauthorized/non-enrolled identity does not gain course access;
- redirect/callback URI is exact;
- session creation succeeds only after valid authentication;
- archived/deactivated authority remains revoked;
- role and section authorization remain database-derived.

Result: **PASS / FAIL**

Evidence:

Owner:

---

## 6. GitHub OAuth and GitHub App

Verify live **GitHub OAuth** identity linking and the production **GitHub App**.

At minimum:

- GitHub identity linking succeeds for an authorized user;
- callback URI is exact;
- GitHub App installation is limited to intended repositories;
- an authorized private repository can be read;
- an unauthorized repository cannot be substituted;
- student credentials/PATs are not used for production repository evidence;
- GitHub App access remains scoped and fail closed.

At least one **authorized private repository** must be exercised.

Result: **PASS / FAIL**

Evidence:

Owner:

---

## 7. Secrets and Key Vault

Verify:

- production secrets reside in Azure Key Vault;
- the application retrieves required secrets through the intended managed
  identity boundary;
- no registry password is required;
- secrets are absent from logs and browser configuration;
- secret references survive application restart/revision changes.

Do not record secret values.

Do not place an access token, database password, API key, session cookie,
private key, or OAuth secret in the evidence record.

Result: **PASS / FAIL**

Evidence:

Owner:

---

## 8. Application Insights and Log Analytics

Verify live observability.

### Application Insights

Confirm **Application Insights** receives expected bounded telemetry.

Verify that telemetry does not contain:

- credentials;
- session material;
- unnecessary student content;
- repository secret material;
- raw AI prompts/responses where policy prohibits collection.

### Log Analytics

Confirm **Log Analytics** receives expected operational logging.

Verify logging remains consistent with `docs/SECURITY_AND_PRIVACY.md`.

Result: **PASS / FAIL**

Evidence:

Owner:

---

## 9. Azure Monitor action group and alerts

Verify the production **action group** reaches the intended operator.

Confirm all four Gate 16 alerts exist, are enabled, and target the intended
resource.

Required alerts:

1. Container App `RestartCount`;
2. HTTP `5xx`;
3. PostgreSQL `is_db_alive`;
4. PostgreSQL `storage_percent`.

Where safe, perform a controlled test of alert delivery or otherwise obtain
sufficient live evidence that the alert/action-group path is functional.

Result: **PASS / FAIL**

Evidence:

Owner:

---

## 10. Health and readiness

Verify the deployed endpoints.

### `/health`

Verify:

- HTTP success;
- service identity/version is expected;
- semantic-coaching state accurately reflects production configuration;
- identity/integration readiness indicators are accurate.

### `/ready`

Verify:

- HTTP 200 only when the database is connected;
- Alembic migration is current;
- `database_connected` is true;
- `migration_current` is true.

Also perform a bounded failure test where practicable to confirm readiness fails
closed when a required dependency is unavailable.

Result: **PASS / FAIL**

Evidence:

Owner:

---

## 11. PostgreSQL backup posture

Verify live PostgreSQL **backup** configuration:

- automatic backup is enabled;
- configured retention matches the approved production posture;
- backup/recovery settings are documented;
- expected operational owner is known.

The CI logical backup/restore drill remains supporting evidence but does not
replace this live verification.

Result: **PASS / FAIL**

Evidence:

Owner:

---

## 12. Live point-in-time recovery exercise

Perform an Azure PostgreSQL **point-in-time restore**.

The exercise must:

1. choose a documented safe restore point;
2. restore to a **separate recovery server**;
3. preserve the original source server;
4. preserve required **private networking**;
5. validate restored database content;
6. validate Alembic state;
7. validate application compatibility;
8. demonstrate the controlled Key Vault connection-switch procedure;
9. verify `/health`;
10. verify `/ready`;
11. verify representative durable engineering records;
12. measure actual recovery duration;
13. retain a rollback option.

Do not overwrite or destructively repurpose the source server during the
exercise.

Result: **PASS / FAIL**

Evidence:

Owner:

---

## 13. Alembic and data integrity

Against the recovery candidate verify:

- expected Alembic revision;
- migration compatibility;
- required schema exists;
- representative durable records are intact;
- evidence snapshots remain immutable;
- review history remains available;
- no known-bad state is silently accepted.

If migration is required, use the normal Alembic migration process. Do not
manually falsify the Alembic version table.

Result: **PASS / FAIL**

Evidence:

Owner:

---

## 14. Authentication and authorization validation

Perform live production **authentication** and **authorization** tests using
controlled accounts.

Verify:

- enrolled student access;
- non-enrolled denial;
- team isolation;
- instructor section scope;
- course-owner authority;
- archived/deactivated access revocation;
- stale-session authority fails closed;
- private repository authorization;
- no unauthorized student/instructor data crossover.

Result: **PASS / FAIL**

Evidence:

Owner:

---

## 15. Wave 1 controlled-use acceptance

Reconfirm the complete Wave 1 acceptance criteria against the deployed system.

The live environment must demonstrate or retain evidence for:

- A1 and A2 phase contracts;
- authentication and enrollment denial;
- authorized-team isolation;
- frozen evidence at a known commit;
- consequence-oriented missing-evidence handling;
- Socratic reviewer conversation;
- A1/A2 scenarios;
- AI-disabled deterministic core behavior;
- non-fabricated evidence and provenance;
- instructor review visibility;
- peer/privacy boundaries;
- automated tests and health checks;
- Azure **budget**;
- Azure **alerts**;
- Key Vault **secrets**;
- **HTTPS**;
- production **logging**;
- PostgreSQL **backups**;
- production **access controls**;
- strong/mixed/weak representative repositories against A1 and A2.

Result: **PASS / FAIL**

Evidence:

Owner:

---

## 16. Budget and cost controls

Verify the live Azure and OpenAI cost-control posture.

Confirm:

- Azure budget exists as approved;
- cost notifications reach intended recipients;
- PostgreSQL SKU is as expected;
- Container Apps scaling is as expected;
- telemetry ingestion posture is understood;
- OpenAI usage controls and monitoring are active;
- unexpected spend has an identified escalation owner.

Result: **PASS / FAIL**

Evidence:

Owner:

---

## 17. RTO and RPO evidence

Record actual recovery evidence.

The initial planning targets remain:

- **RTO:** 4 hours;
- **RPO:** 24 hours.

These are engineering planning targets and are not an SLA.

Record:

- actual **RTO** observed during the recovery exercise;
- actual **RPO** demonstrated by the selected restore point;
- deviations;
- operational implications;
- any required follow-up.

Result: **PASS / FAIL**

Evidence:

Owner:

---

## 18. Rollback and cutover

Verify the production **rollback** and cutover procedure.

Confirm:

- original database/source state is preserved until recovery acceptance;
- previous known-good application revision is identifiable;
- Key Vault connection changes are controlled;
- rollback authority is known;
- failed acceptance does not force continued use of an untrusted candidate;
- student access can remain disabled independently of infrastructure state.

Result: **PASS / FAIL**

Evidence:

Owner:

---

## 19. Retention and privacy

Before student access, verify the approved retention posture for:

- engineering records;
- identity/attribution information;
- archived course administration;
- authentication/session records;
- telemetry;
- backups;
- externally processed data where configurable.

Confirm operational telemetry and evidence collection remain bounded by
`docs/SECURITY_AND_PRIVACY.md`.

Result: **PASS / FAIL**

Evidence:

Owner:

---

## 20. Acceptance evidence record

For each live verification record:

- date/time;
- operator;
- resource;
- Git SHA;
- control;
- expected result;
- actual result;
- evidence reference;
- PASS/FAIL;
- follow-up;
- owner.

Do not record secret values.

Never record an access token, database password, API key, session cookie,
private key, or OAuth secret.

---

## 21. Final decision

Production Acceptance must end with an explicit decision:

### GO

All blocking production controls pass.

Controlled student production access may be enabled.

### NO-GO

One or more blocking production controls have failed, are unresolved, or lack
sufficient evidence.

Student access remains disabled.

The decision record must identify:

- decision;
- date/time;
- decision owner;
- supporting evidence;
- unresolved issues;
- accepted deferrals, if any;
- required follow-up.

A successful deployment is not itself a go-live decision.

A successful `/ready` response is necessary but not sufficient for student
production authorization.
