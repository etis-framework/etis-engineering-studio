# ETIS Engineering Studio Incident Response Runbook

## 1. Purpose

This runbook defines how authorized operators respond to security, privacy,
availability, integrity, credential, and production-control incidents affecting
the ETIS Engineering Studio.

The objectives are to:

- protect students and engineering records;
- contain the incident;
- preserve useful evidence;
- restore trustworthy service;
- avoid destructive or speculative remediation;
- maintain fail-closed authorization and identity controls;
- document lessons and required corrective action.

This runbook must be used when normal troubleshooting can no longer establish
that production remains in a known trustworthy state.

## 2. Incident principles

During an incident:

1. protect people and data before convenience;
2. fail closed when authorization or identity state is uncertain;
3. preserve evidence before destructive remediation when practical;
4. prefer reversible containment actions;
5. do not weaken authentication, authorization, CSRF, session, or repository
   controls to restore service;
6. do not fabricate or reconstruct missing engineering evidence;
7. do not delete historical engineering records as an incident shortcut;
8. keep secrets and credentials out of tickets, chat, screenshots, and logs;
9. distinguish confirmed facts from hypotheses;
10. record operator actions and timestamps.

## 3. Incident severity

### Severity 0 — Critical

Examples:

- confirmed or strongly suspected credential compromise with production access;
- unauthorized access to student or instructor data;
- material engineering-record corruption or loss;
- production authorization bypass;
- broad exposure of secrets;
- database integrity failure with uncertain trustworthy state;
- incident requiring immediate production shutdown or access disablement.

Response:

- immediate containment;
- immediate operator escalation;
- preserve evidence;
- suspend affected authority;
- do not restore normal access until trustworthy state is established.

### Severity 1 — High

Examples:

- sustained production outage;
- repeated systemic 5xx failures;
- PostgreSQL unavailable;
- failed deployment leaving uncertain application state;
- repeated application crashes;
- suspected limited-scope unauthorized access;
- confirmed operational control failure with student impact.

Response:

- prompt containment and assessment;
- establish scope;
- preserve evidence;
- recover service only through controlled procedures.

### Severity 2 — Moderate

Examples:

- intermittent 5xx responses;
- repeated but recoverable container restarts;
- storage pressure;
- degraded external-provider behavior;
- isolated operational failure without evidence of compromise.

Response:

- investigate promptly;
- monitor for escalation;
- apply bounded reversible remediation.

### Severity 3 — Low

Examples:

- non-user-impacting operational anomaly;
- warning threshold requiring planned maintenance;
- isolated recoverable event with established cause.

Response:

- document;
- remediate through normal maintenance;
- escalate if scope or impact increases.

Severity may change as facts emerge.

## 4. Incident declaration

Declare an incident when any authorized operator identifies a condition that
could materially affect:

- authentication;
- authorization;
- student privacy;
- engineering-record integrity;
- evidence integrity;
- production credentials;
- database durability;
- production availability;
- deployment trust;
- GitHub repository authority;
- Microsoft Entra identity authority;
- OpenAI provider boundary;
- Azure control-plane integrity.

Record:

- incident start time;
- declaring operator;
- initial severity;
- observed symptoms;
- affected resources;
- known student/instructor impact;
- current production Git SHA if known.

## 5. Immediate assessment

Answer the following before making broad changes:

1. What is known?
2. What is suspected?
3. Which users or systems are affected?
4. Is authentication trustworthy?
5. Is authorization trustworthy?
6. Is PostgreSQL reachable and consistent?
7. Is `/ready` reporting ready?
8. Is the current deployment revision known?
9. Are credentials suspected to be exposed?
10. Is engineering-record integrity uncertain?
11. Is evidence still being generated or overwritten?
12. Is continued service likely to increase harm?

Do not treat absence of an alert as proof that no incident exists.

## 6. Containment

Containment should minimize further impact while preserving evidence.

Possible containment actions include:

- disable or revoke a compromised credential;
- remove or restrict affected GitHub App installation authority;
- disable affected Microsoft Entra application credentials;
- rotate a compromised Key Vault secret;
- prevent further deployment activity;
- scale down or stop an affected workload when continued execution creates risk;
- archive or deactivate course access when normal lifecycle authority applies;
- isolate a compromised integration;
- block an affected external provider path;
- preserve the database and current deployment state before replacement.

Containment must not include:

- enabling development login in production;
- bypassing authentication;
- bypassing current database-derived authorization;
- disabling CSRF or secure-cookie controls;
- granting broad repository access;
- moving production credentials into source control;
- deleting engineering records to simplify recovery.

## 7. Credential incidents

Production credentials may include:

- Azure OIDC application/federated identity authority;
- Azure deployment secrets;
- PostgreSQL administrative credentials;
- ETIS session signing secret;
- Microsoft Entra client secret;
- GitHub App private key;
- GitHub OAuth client secret;
- OpenAI API key.

If a credential is suspected compromised:

1. treat it as compromised until disproven;
2. identify where the credential grants authority;
3. revoke or rotate it at the authoritative provider;
4. update Azure Key Vault as required;
5. redeploy or restart workloads only when needed to consume the new credential;
6. invalidate affected application sessions when relevant;
7. review logs for suspicious use;
8. preserve evidence of the old credential's scope and rotation time without
   recording the secret itself.

Never paste secret values into incident documentation.

## 8. Evidence preservation

Preserve enough evidence to reconstruct what happened without expanding the
privacy impact.

Useful incident evidence may include:

- Azure alert identifiers and timestamps;
- affected resource names;
- deployment Git SHA;
- Container App revision;
- migration-job execution identifier;
- request IDs;
- HTTP route/status/duration metadata;
- bounded error types;
- Azure resource-health information;
- identity-provider audit events where authorized;
- GitHub App installation/activity information where authorized;
- operator actions and timestamps;
- database recovery or migration execution records.

Evidence preservation must follow `docs/SECURITY_AND_PRIVACY.md`.

Do not routinely preserve:

- session cookies;
- bearer tokens;
- passwords;
- API keys;
- OAuth authorization codes;
- full prompt bodies;
- full model responses;
- unnecessary repository evidence;
- unnecessary student personal information.

Evidence preservation does not authorize research or secondary use.

## 9. Student and instructor impact assessment

Determine:

- whether students can authenticate;
- whether unauthorized students can authenticate;
- whether team isolation is intact;
- whether instructor scope is intact;
- whether archived-term authority remains read-only;
- whether current review sessions are durable;
- whether frozen evidence remains immutable;
- whether any student engineering record is missing, altered, or exposed;
- whether normal course work can safely continue.

If access-control correctness is uncertain, fail closed.

Do not restore broad access simply to reduce disruption.

## 10. Communication

Incident communication must be accurate, bounded, and role appropriate.

Internal operational communication should state:

- what is known;
- what remains unknown;
- current severity;
- current containment;
- current user impact;
- next decision point.

Do not speculate about cause or exposure.

When students require course-level notification, use the established
authoritative course communication channel.

Do not disclose:

- credentials;
- exploit details that would increase risk;
- unnecessary student information;
- internal evidence beyond what the audience requires.

Security/privacy notification obligations, if any, must be handled through the
appropriate institutional authority rather than improvised in this runbook.

## 11. Recovery decision

Recovery may begin only when operators understand enough of the incident to
avoid restoring the same unsafe condition.

Before recovery:

1. confirm containment is effective;
2. identify the trusted code revision;
3. identify the trusted configuration boundary;
4. identify whether credentials must be rotated;
5. determine whether database recovery is required;
6. preserve the original database when corruption or data loss is suspected;
7. identify validation criteria;
8. identify a rollback path.

Database recovery must use
`docs/operations/DATABASE_RECOVERY_RUNBOOK.md`.

## 12. Application recovery

For application-only recovery:

1. identify the last trusted Git SHA;
2. confirm that SHA passed the normal release gate;
3. use the controlled GitHub Actions deployment path;
4. do not manually modify a running container;
5. verify migration state;
6. verify `/health`;
7. verify `/ready`;
8. verify one representative authorized workflow;
9. verify monitoring;
10. confirm no new incident indicators appear.

A rollback is a new controlled deployment of a trusted image/configuration, not
an unrecorded production modification.

## 13. Database recovery

Use database recovery when:

- PostgreSQL cannot be restored through normal service recovery;
- durable data corruption is suspected;
- destructive application behavior affected stored records;
- a restore point is required to return to trustworthy data.

Do not overwrite or destroy the source production server while validating a
recovered database.

Use the database recovery runbook and retain the original server until the
recovered environment is validated and an explicit cutover decision is made.

## 14. Recovery validation

Before declaring service recovered:

- `/health` responds as expected;
- `/ready` reports `"status":"ready"`;
- `database_connected=true`;
- `migration_current=true`;
- Microsoft Entra authentication works;
- unauthorized access remains denied;
- authorized team isolation works;
- instructor scope works;
- GitHub repository access remains correctly scoped;
- frozen evidence can still be retrieved;
- historical reviews remain intact;
- no development login is available;
- monitoring and alerts remain configured;
- rotated credentials are active when applicable.

Recovery is not complete merely because the application returns HTTP 200.

## 15. Incident closure

An incident may close when:

- containment is complete;
- trustworthy production state is established;
- affected credentials have been handled;
- service recovery is validated;
- known user impact is documented;
- required communication is complete;
- required follow-up work is assigned.

Record:

- final severity;
- incident duration;
- confirmed cause, if known;
- contributing conditions;
- affected users/resources;
- containment actions;
- recovery actions;
- residual risk;
- required corrective changes.

## 16. Post-incident review

Conduct a post-incident review for Severity 0 and Severity 1 incidents and for
lower-severity incidents that expose meaningful control weaknesses.

The review should address:

- what happened;
- detection method;
- why existing controls did or did not prevent it;
- containment effectiveness;
- recovery effectiveness;
- whether RTO/RPO objectives were met;
- whether logging was sufficient and privacy safe;
- whether alerts were useful;
- whether runbooks were accurate;
- whether architecture, tests, deployment controls, or training should change.

The objective is system improvement, not blame.

Corrective actions should be tracked through normal engineering governance.

## 17. Fail-closed authority

During uncertainty, the Engineering Studio must preserve its fail-closed
security posture.

Specifically:

- authentication failure does not become anonymous access;
- uncertain enrollment does not become student authorization;
- uncertain staff assignment does not become instructor authorization;
- repository-access failure does not become broad GitHub access;
- unavailable evidence does not become fabricated evidence;
- database migration uncertainty does not become application readiness;
- archived semesters do not regain active authority;
- compromised credentials do not remain trusted for convenience.

Operational pressure is not authority to weaken these controls.
