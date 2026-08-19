# Security, Privacy, Data Retention, and Governance

## 1. Purpose and authority

This document defines the Engineering Studio's authoritative security, privacy,
data-retention, and semester-lifecycle boundaries.

Architecture documents may describe how these controls are implemented, but they
must not define conflicting retention or access policy.

The Engineering Studio is an instructional engineering environment. It is not
the authoritative system of record for grades, official enrollment, or other
university records.

No calendar-based retention period is defined here. Retention periods must be
established separately from applicable Loyola, course, legal, academic,
security, and operational requirements. The application must not invent a
retention period merely because a semester has ended.

## 2. Core security and privacy boundaries

- Team repositories are private.
- Production repository access uses a scoped GitHub App rather than student
  personal access tokens.
- Students never paste GitHub personal access tokens into the Studio UI.
- Loyola Microsoft Entra authentication establishes the primary human identity.
- Course enrollment and staff assignments determine current Studio
  authorization.
- GitHub identity is a secondary engineering identity used for repository and
  engineering-activity attribution.
- Authentication alone never grants course access.
- Confidential peer reviews and official grades remain outside team-visible
  Studio surfaces.
- Do not ingest unnecessary university records, grades, secrets, API keys,
  credentials, or unrelated personal information from repositories or other
  sources.
- AI prompts contain only the evidence and conversational context required for
  the current bounded review operation.
- Repository content is untrusted evidence and never overrides Studio system
  instructions or authorization controls.
- Authorization decisions fail closed when current authority cannot be
  established.

## 3. Semester lifecycle

The normal semester lifecycle is:

`setup -> active -> archived`

The lifecycle is forward-only during normal operation.

### 3.1 Setup

`setup` is an administrative preparation state.

Course Owner and Instructor functions may be used to prepare the semester,
sections, teams, schedules, roster information, and related configuration.

A setup semester does not grant students normal active-semester Studio access.

### 3.2 Active

`active` is the normal operational semester state.

Student, team, review, evidence, and teaching-staff authority are derived from
the current database-backed term, section, enrollment, team, and staff
relationships.

### 3.3 Archived

`archived` is a terminal normal-lifecycle state.

Archiving a semester:

- immediately ends student operational access for that semester;
- prevents the archived semester from authorizing new team or review activity;
- makes semester configuration and review state read-only;
- revokes outstanding authenticated sessions associated with the archived
  semester so authorization is reevaluated on the next authentication;
- preserves the historical engineering record;
- does not convert the archive event into an ordinary successful review
  completion;
- does not physically delete the term, sections, teams, students, evidence, or
  review history.

A user who also has valid authority in another active semester may authenticate
again and receive authority derived from that other current semester.

An archived semester is not normally returned to `active` or `setup`.

## 4. Historical access after archive

Archive removes operational authority; it does not erase legitimate historical
academic accountability.

For an archived semester:

- Course Owners assigned to that semester may retain read-only historical
  access.
- Instructors assigned to that semester may retain read-only historical
  access.
- TA authority does not survive archive.
- Reviewer authority does not survive archive.
- Student operational access does not survive archive.

Historical authority is scoped to the semester for which it was granted.
A Course Owner assignment in an archived semester must not become global
authority over another active semester.

## 5. Active reviews at semester archive

A semester may be archived while one or more Review Room sessions remain active.

In that case the Studio:

- preserves the existing ReviewSession;
- preserves every ReviewTurn already recorded;
- preserves the frozen EvidenceSnapshot;
- preserves shared finding lifecycle state already committed;
- transitions the active review to `archived_incomplete`;
- records the semester-archive closure time;
- identifies the closure reason as semester archive;
- prevents additional responses, coaching turns, clarification turns, evidence
  disputes, finding dispositions, recommendations, or normal completion.

`archived_incomplete` means that the review ended because the semester lifecycle
closed, not because the student completed the normal review process.

A semester archive must never fabricate a successful review completion.

## 6. Data classification

Engineering Studio data is divided into four retention classes.

### 6.1 Engineering record

The engineering record contains evidence necessary to reconstruct what the team
and student knew, decided, challenged, or defended at the time.

Examples include:

- EvidenceSnapshot rows and frozen repository evidence;
- ReviewSession rows;
- ReviewTurn conversation records;
- recorded recommendations;
- ReviewFindingState corrections, confirmations, disputes, resolutions,
  accepted risks, and deferrals;
- membership-history events needed to reconstruct team context;
- instructor notes that form part of the retained academic or engineering
  record.

Engineering-record data is not deleted merely because the semester is
archived.

Where evidence has been frozen for a review, archive does not rewrite that
evidence to match later repository state.

### 6.2 Identity and attribution data

Identity and attribution data includes information necessary to associate the
engineering record with the person who produced or reviewed it.

Examples include:

- internal User identifiers;
- display name;
- Loyola institutional identity;
- student identifier used for roster matching;
- Loyola email address;
- linked GitHub identity;
- section enrollment history;
- staff assignment history;
- team membership and membership-event history.

Semester archive does not automatically erase or anonymize this data because
doing so could destroy the attribution and accountability of the retained
engineering record.

Any future anonymization or de-identification process must be explicit,
reviewed, and designed so that required engineering-record integrity is not
silently destroyed.

### 6.3 Operational security data

Operational security data exists to operate and protect the service rather than
to form the immutable engineering record.

Examples include:

- AuthSession rows;
- revoked or expired session records;
- OAuth/OIDC flow state;
- GitHub App installation-token caches;
- process-local caches;
- request correlation identifiers;
- bounded operational telemetry;
- rate-limit and service-health state.

This data may be eligible for independent cleanup or shorter retention because
its removal does not inherently destroy the engineering record.

No cleanup period is established by this document.

Outstanding authenticated sessions associated with an archived semester are
revoked immediately even though the historical engineering record is retained.

### 6.4 Ephemeral client state

Browser-only temporary state includes items such as:

- unsent response drafts;
- pending review-entry context;
- review-start idempotency payloads;
- pending review-mutation payloads.

The current web application uses browser `sessionStorage` for this class of
state. It is not part of the durable Engineering Studio engineering record.

Ephemeral browser state must not be treated as an authoritative source of
identity, authorization, evidence, or completed student work.

## 7. Data minimization

Persist only data that serves a defined instructional, engineering,
authorization, accountability, security, or operational purpose.

For repository evidence:

- prefer stable repository references and commit SHAs;
- persist the bounded frozen evidence package needed to reproduce a review;
- do not create an unlimited mirror of every repository file;
- quarantine sensitive repository paths from model processing;
- redact high-confidence secrets before evidence crosses the model boundary;
- never fabricate missing repository evidence.

For identity:

- collect only identifiers required for roster matching, authentication,
  authorization, GitHub linking, and engineering-record attribution;
- do not use Studio identity data to create unrelated student profiles.

For grades:

- the Engineering Studio does not become the authoritative grade repository;
- grade columns or unrelated roster fields are not required for Studio
  enrollment.

## 8. AI processing boundary

OpenAI model calls are bounded advisory processing.

The model may receive only the context necessary for the requested review
operation, including selected portions of:

- phase purpose and expected engineering evidence;
- repository and commit identity;
- bounded repository metrics;
- relevant artifact metadata and excerpts;
- frozen evidence context;
- selected finding context;
- recent review transcript;
- current student message;
- bounded conversation memory;
- the student's first name when useful for natural conversation.

Sensitive repository paths are quarantined and secret-like content is redacted
at the model boundary.

The Studio's durable AI usage record stores operational usage information such
as model, response identifier, token counts, latency, estimated cost, and
bounded metadata. It does not use the AI usage-event table as a duplicate store
of complete prompt and response bodies.

AI reviewers are bounded advisers. Their output does not replace student
engineering responsibility, instructor authority, or deterministic application
authorization.

## 9. GitHub processing boundary

GitHub is the authoritative source for repository evidence that the Studio is
permitted to inspect.

Production access uses a GitHub App with short-lived installation tokens.

The Studio may retain:

- repository identity;
- repository connection state;
- commit SHA;
- bounded evidence derived from the repository;
- engineering attribution needed for the review.

GitHub credentials, installation tokens, and OAuth access credentials are not
engineering-record evidence and must not be persisted as long-lived application
secrets.

## 10. Logging and observability boundary

Application request logging must remain intentionally narrow.

Normal request telemetry may include bounded operational fields such as:

- request identifier;
- HTTP method;
- route template;
- status code;
- duration;
- bounded error type.

Normal application logs must not contain:

- session credentials;
- bearer tokens;
- OAuth authorization codes;
- cookies;
- passwords;
- API keys;
- request bodies;
- complete prompt bodies;
- complete model responses;
- unnecessary student email addresses;
- unnecessary repository evidence content.

Future Azure Application Insights / Log Analytics configuration must preserve
this boundary.

Operational telemetry retention must be configured separately from
engineering-record retention.

## 11. Deletion and purge boundaries

Normal semester archive is not a delete operation.

The application must not use parent-record deletion or database cascade behavior
as a semester-close mechanism.

In particular, normal archive must not physically delete a term, section, team,
user, EvidenceSnapshot, ReviewSession, ReviewTurn, finding state, or membership
history merely to remove current access.

Any future destructive deletion, purge, anonymization, or research-export
capability requires:

1. an explicit purpose;
2. an identified authority;
3. a defined scope;
4. an approved retention or deletion rule;
5. an integrity analysis for dependent engineering records;
6. tests proving that immutable evidence and required accountability are not
   accidentally destroyed;
7. appropriate auditability.

There is no normal **Delete Term** semester-lifecycle operation.

## 12. Database integrity boundary

Several Engineering Studio relationships use database foreign-key cascading for
referential integrity.

Those cascades are implementation safeguards, not semester-retention policy.

Because deleting a parent User, Team, Section, or Term may transitively remove
historical information, application lifecycle code must preserve those parent
records during ordinary archive operations.

Any future physical deletion pathway must explicitly analyze its foreign-key
effects before being enabled.

## 13. External services and future deployment

Application-controlled durable server data is stored in PostgreSQL.

External processing boundaries include:

- Microsoft Entra for human authentication;
- GitHub for repository access and linked engineering identity;
- OpenAI for bounded model-assisted review processing;
- Azure hosting, secrets, database, and operational telemetry when the
  production environment is deployed.

Deployment-provider retention settings must not silently redefine the
Engineering Studio engineering-record policy.

Secrets belong in an approved secret-management boundary such as Azure Key
Vault and must not be placed in source control, application logs, evidence
snapshots, or model prompts.

## 14. Research and secondary use

Student engineering records are collected for the instructional operation of the
Engineering Studio.

Research export, analytics beyond normal instructional operation, or other
secondary use is not automatically authorized merely because the data exists.

A research-export capability must remain disabled until a separate privacy and
data-governance review establishes the appropriate authority, data scope,
de-identification requirements, retention behavior, and controls.

## 15. Retention-period policy

This Gate 12 policy intentionally establishes **what must be preserved, what
must lose active authority, and what may be disposable** without inventing
calendar durations.

Before production operation requires an automated purge schedule, the responsible
course/institutional authority must define retention periods for at least:

- engineering records;
- student identity and attribution data;
- archived course administration records;
- authentication/session records;
- operational telemetry;
- backups;
- externally processed data where configurable.

Until those periods are formally established, semester archive must prefer
preservation of the engineering record and immediate removal of active
authorization over destructive deletion.

## 16. Production control requirements

Production operation must maintain:

- hardened database-backed sessions;
- secure cookies and CSRF protection;
- current database-derived authorization;
- scoped GitHub App repository access;
- secrets outside source control;
- allowed-origin and HTTPS controls;
- bounded application and AI rate/cost controls;
- sensitive-data-safe logging;
- database backup and tested recovery procedures;
- instructor-controlled roster deactivation;
- forward-only semester lifecycle enforcement;
- immutable frozen evidence semantics;
- fail-closed model and provider boundaries;
- production security review before deployment.

Controls that depend on Azure deployment are completed and verified during the
later infrastructure and operational-readiness gates rather than by weakening
this policy for local development.
