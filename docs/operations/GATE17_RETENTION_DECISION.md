# Gate 17 Retention Decision

> **Historical status:** Gate 17 retention decision record. The governing lifecycle/retention policy remains `../SECURITY_AND_PRIVACY.md`; live production acceptance is recorded separately.


## 1. Purpose

This document records the approved production data-retention posture for ETIS
Engineering Studio at Gate 17.

The decision is:

**Deferred with explicit acceptance — PASS**

The Studio may proceed toward controlled Azure provisioning without inventing
calendar-based retention periods that have not yet been established by the
responsible Loyola or institutional authority.

Deferral does not mean retention is uncontrolled. The Studio already defines
what information must be preserved, what information loses active authority,
what operational data is intentionally short-lived, and which destructive
operations remain prohibited.

---

## 2. Governing principle

The initial production posture is:

> preserve the engineering record, remove active authority when it ends,
> minimize operational data, and do not destroy or anonymize retained records
> until an approved institutional retention rule authorizes that action.

Semester archive is therefore an authorization and lifecycle transition, not a
destructive deletion event.

A missing institutional calendar period must not be replaced with an arbitrary
application default.

---

## 3. Engineering records

**Decision: preserve**

Engineering records remain retained when a semester is archived.

This class includes the durable evidence necessary to reconstruct what a team
or student knew, decided, challenged, defended, corrected, accepted, or deferred
at the time of engineering review.

Examples include:

- frozen EvidenceSnapshot records;
- bounded repository evidence retained with the snapshot;
- ReviewSession records;
- ReviewTurn conversation records;
- ReviewFindingState history;
- corrections, confirmations, disputes, resolutions, accepted risks, and
  deferrals;
- engineering recommendations;
- relevant membership-history events;
- instructor notes that form part of the retained engineering record.

Archived engineering records remain immutable or read-only according to their
existing lifecycle contract.

No automatic deletion period is established at Gate 17.

---

## 4. Identity and attribution data

**Decision: preserve only as required to maintain trustworthy attribution**

Identity and attribution information may remain associated with retained
engineering records when necessary to establish who performed, reviewed, or
was responsible for recorded engineering work.

This includes bounded forms of:

- internal user identity;
- institutional identity;
- student identifier used for roster matching;
- institutional email;
- linked GitHub identity;
- section enrollment history;
- staff-assignment history;
- team membership and membership-event history.

Semester archive does not automatically erase this information when doing so
would destroy required attribution or accountability.

No automatic anonymization is authorized by Gate 17.

Any future anonymization or de-identification mechanism requires explicit
policy, review, and regression protection before use.

---

## 5. Archived course administration

**Decision: preserve read-only**

Archived course-administration records remain available as historical context
where required.

An archived semester:

- cannot grant current student authorization;
- cannot grant current team authorization;
- cannot grant current TA or Reviewer authority;
- cannot authorize new reviews or additional review turns;
- cannot authorize roster, team, repository, or schedule mutation;
- cannot be used to regain stale administrative authority.

Authorized historical Course Owner or Instructor access may remain read-only
where the application policy permits it.

Archive is not deletion.

---

## 6. Authentication/session data

**Decision: authorization expires or is revoked according to current security
state; historical cleanup period deferred**

Authentication/session authority is operational security state, not part of
the immutable engineering record.

Sessions must fail closed when:

- the session expires;
- it is explicitly revoked;
- course authorization is removed;
- staff authority is revoked;
- enrollment no longer authorizes access;
- semester lifecycle no longer authorizes the operation.

Outstanding semester-dependent authority is removed when the semester is
archived.

The calendar cleanup period for historical revoked or expired
authentication/session records remains deferred until the approved
institutional and operational retention posture is finalized.

That deferral does not permit an expired or revoked session to retain authority.

---

## 7. Operational telemetry

**Decision: 30 days initially**

Initial production Log Analytics retention is:

**30 days**

Operational telemetry is retained separately from the engineering record.

Telemetry must remain bounded by the sensitive-data-safe logging policy and
must not become a duplicate repository for:

- session credentials;
- bearer tokens;
- OAuth authorization codes;
- cookies;
- passwords;
- API keys;
- complete request bodies;
- complete prompts;
- complete model responses;
- unnecessary student identity data;
- unnecessary repository evidence.

The 30-day operational telemetry period may be adjusted later when justified by
security, operational, institutional, privacy, or cost requirements.

Live Azure telemetry retention must be confirmed during
**Post-Provisioning Production Acceptance**.

---

## 8. PostgreSQL operational backups

**Decision: 7 days initially**

The production PostgreSQL infrastructure is initially configured with:

**7 days** of managed backup retention.

This is an operational **recovery window**.

It is not the retention period for the Engineering Studio engineering record.

The application must not interpret expiry of an Azure backup as authorization
to delete retained engineering records from the active or archival data store.

Live PostgreSQL backup configuration and point-in-time recovery behavior must be
verified during Post-Provisioning Production Acceptance.

---

## 9. Ephemeral browser state

**Decision: session-only and non-authoritative**

Ephemeral browser state is **session-only** and is not part of the durable
engineering record.

Examples include:

- unsent response drafts;
- pending review-entry context;
- review-start idempotency payloads;
- pending review-mutation payloads.

Browser state must never become an authoritative source of:

- identity;
- authorization;
- frozen evidence;
- completed student work;
- review completion.

---

## 10. OpenAI external processing

**Decision: minimize provider-side application-state retention**

Production Responses API requests explicitly set:

`store: false`

The Studio therefore does not intentionally request provider-side retention of
Responses API application state for later retrieval.

The Studio retains only its own bounded engineering and operational records
required by the application.

Provider-side security, abuse-monitoring, or legally required processing that
is outside application control does not become part of the Studio's engineering
record.

The Studio must not use an external provider as an uncontrolled duplicate
archive of student work or engineering evidence.

---

## 11. GitHub and Microsoft Entra external boundaries

GitHub and Microsoft Entra remain external authoritative or identity providers
for their bounded purposes.

The Studio retains only the provider identifiers, linkage state, repository
identity, attribution, and other bounded integration data required for:

- authentication;
- authorization;
- roster matching;
- repository access;
- engineering attribution;
- reproducibility of retained evidence.

The Studio must not create unnecessary provider-data mirrors.

Provider retention settings must not silently redefine the Studio engineering
record retention policy.

---

## 12. Destructive operations

Gate 17 authorizes:

**no destructive purge**

of retained production engineering records merely because a semester ends.

Gate 17 also authorizes:

- no automatic anonymization;
- no automatic destructive semester cleanup;
- no use of database cascade behavior as retention policy;
- no research export merely because the data exists.

A research export remains disabled until separately authorized through an
appropriate privacy and data-governance process.

Any future destructive deletion, purge, anonymization, or equivalent lifecycle
feature must have:

1. an approved institutional retention rule;
2. an identified authority and owner;
3. documented scope;
4. explicit treatment of engineering-record integrity and attribution;
5. implementation safeguards;
6. regression tests;
7. an auditable execution path.

---

## 13. Deferred institutional retention decision

The remaining calendar-based institutional retention periods are explicitly
deferred.

The responsible **course/institutional owner** must confirm the authoritative
institutional retention requirements for at least:

- engineering records;
- student identity and attribution;
- archived course-administration records;
- historical authentication/session records;
- operational telemetry where institutional policy overrides the initial
  operational period;
- backups where institutional policy requires a different period;
- externally processed data where configurable.

This confirmation must occur:

**before the first production semester is archived**

or

**before any destructive purge**, anonymization, or deletion capability is
enabled or executed,

**whichever occurs first**.

If authoritative policy is still unresolved at that completion point, the safe
default remains preservation rather than destructive deletion.

---

## 14. Ownership

Retention decision owner:

**Course/institutional owner**

The production/course owner is responsible for ensuring that the appropriate
Loyola or institutional records, privacy, academic, or data-governance authority
is consulted where authoritative retention periods are required.

Application developers must not substitute a technical convenience for that
institutional decision.

---

## 15. Post-provisioning obligations

Post-Provisioning Production Acceptance must verify that the deployed
environment matches this approved posture, including:

- PostgreSQL backup retention;
- Log Analytics retention;
- archived-semester authorization behavior;
- runtime secret and logging boundaries;
- absence of unintended destructive lifecycle behavior;
- OpenAI production configuration consistent with the approved external
  processing boundary.

Student production access remains prohibited until Post-Provisioning Production
Acceptance is explicitly GO.

---

## 16. Gate 17 result

Retention classification:

**Deferred with explicit acceptance — PASS**

There is no identified retention ambiguity that requires destructive deletion,
causes uncontrolled exposure, or requires excessive collection before Azure
provisioning.

The unresolved institutional calendar periods remain explicitly owned and
bounded by the completion point defined above.

This decision therefore satisfies the Gate 17 retention-policy requirement
without falsely asserting institutional retention authority that has not yet
been established.
