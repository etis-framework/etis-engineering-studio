# ETIS Engineering Studio Database Recovery Runbook

## 1. Purpose

This runbook defines recovery of the ETIS Engineering Studio production
PostgreSQL database when normal database service cannot be trusted or restored.

It applies to conditions such as:

- accidental destructive data change;
- suspected database corruption;
- PostgreSQL service failure requiring recovery;
- an application defect that materially damaged durable state;
- recovery testing;
- disaster-recovery validation.

The objective is to restore a trustworthy database while preserving the
original production server for investigation and rollback until recovery is
validated.

## 2. Recovery principles

Database recovery must follow these principles:

1. preserve the original production database server;
2. restore into a new server;
3. select an explicit restore point;
4. preserve private networking;
5. validate data before application cutover;
6. validate Alembic schema state;
7. verify application `/ready`;
8. update secrets through Key Vault;
9. maintain a rollback path;
10. record recovery evidence;
11. avoid destructive improvisation;
12. distinguish restoration from incident investigation.

Azure Database for PostgreSQL Flexible Server point-in-time restore creates a
new Flexible Server rather than replacing the existing source server.

## 3. Recovery objectives

The initial operational planning targets are:

### RTO

Recovery-time objective (**RTO**) target:

- restore core Engineering Studio service within **4 hours** of a confirmed
  outage requiring database recovery.

### RPO

Recovery-point objective (**RPO**) target:

- no more than **24 hours** of durable database state at risk.

These are engineering planning targets, not an SLA.

The actual observed RTO and RPO must be recorded during the first live Azure
recovery exercise and used to refine these targets.

## 4. When to use point-in-time restore

Use Azure PostgreSQL **point-in-time restore** when the desired trustworthy
state exists within the configured backup retention period and the problem
affects the durable database state.

Examples include:

- accidental deletion;
- destructive application behavior;
- unintended bulk update;
- logical corruption;
- need to inspect the database as it existed before an incident.

Do not perform point-in-time restore merely because the application is
unhealthy. First distinguish:

- application failure;
- migration failure;
- authentication/configuration failure;
- network failure;
- PostgreSQL service availability failure;
- actual durable-data recovery need.

## 5. Preconditions

Before beginning recovery, record:

- incident or recovery identifier;
- current UTC time;
- production resource group;
- source PostgreSQL server name;
- source database name;
- current application Git SHA;
- current Container App revision;
- current Alembic revision if obtainable;
- configured backup retention;
- suspected failure time;
- proposed restore point;
- reason that restore is required;
- operator performing recovery.

If this recovery is part of an incident, preserve incident evidence according
to `INCIDENT_RESPONSE_RUNBOOK.md`.

## 6. Select the restore point

Choose the restore point deliberately.

For accidental destructive changes:

1. identify the earliest confirmed bad event;
2. identify the last known trustworthy point before that event;
3. allow sufficient safety margin to avoid restoring after the destructive
   transaction;
4. record the chosen UTC timestamp and rationale.

For availability recovery where the latest durable state is desired, use the
latest valid restore capability supported by Azure.

The restore point must fall within the server's configured backup retention
window.

Do not guess a restore timestamp when evidence can establish a better one.

## 7. Restore into a new server

Perform Azure PostgreSQL Flexible Server point-in-time restore using a unique
recovery server name.

Example naming pattern:

`etis-studio-prod-pg-recovery-YYYYMMDD-HHMM`

The recovered server must be treated as a candidate, not immediately as the new
production authority.

The existing production source remains preserved during validation.

Record:

- restored server name;
- source server name;
- restore point;
- restore start time;
- restore completion time;
- Azure operation/result identifier where available.

## 8. Preserve private networking

The recovered PostgreSQL server must preserve the intended **private**
production database boundary.

Verify:

- appropriate delegated subnet/VNet integration;
- appropriate private DNS behavior;
- no unnecessary public database exposure;
- Container Apps can resolve and reach the restored host;
- unauthorized Internet clients cannot directly reach the database.

If Azure restore behavior requires networking to be adjusted after creation,
apply only the minimum configuration needed to restore the intended private
architecture.

Do not weaken the network boundary merely to make validation easier.

## 9. Database validation before application cutover

Do not point production traffic at the recovered server until validation is
complete.

Validate at least:

### Connectivity

- PostgreSQL accepts an authorized connection;
- TLS is required;
- the expected database exists.

### Schema

Inspect the `alembic_version` table.

Confirm the recovered database revision is understood relative to the
application revision being restored.

Do not assume that a successfully restored database is automatically compatible
with the currently deployed application.

### Engineering records

Perform bounded integrity checks appropriate to the incident, including as
applicable:

- course terms exist;
- sections exist;
- team memberships exist;
- frozen evidence snapshots exist;
- review sessions exist;
- review turns exist;
- finding state exists;
- archived records remain preserved;
- expected semester lifecycle state remains intact.

Do not mutate records merely to make validation pass.

### Incident-specific validation

Verify that:

- the condition that triggered recovery is absent at the selected restore
  point; and
- required legitimate records expected before that point are present.

Document the validation performed.

## 10. Application/schema compatibility

The target application image and recovered database must have compatible
Alembic state.

If the recovered database is behind the Alembic head required by the trusted
application image:

1. identify the trusted application Git SHA;
2. verify its migration chain;
3. use the normal migration mechanism;
4. run `alembic upgrade head`;
5. require migration success before application readiness.

Do not manually modify the `alembic_version` table to bypass migration logic.

If migration fails, stop the recovery cutover and investigate.

## 11. Connection-secret preparation

The application's production database connection is stored in Azure Key Vault.

Prepare a database URL for the recovered server that preserves:

- the expected PostgreSQL driver;
- authorized credentials;
- recovered host name;
- database name;
- TLS requirement.

Update the appropriate **Key Vault** secret only as part of an authorized
cutover decision.

Do not commit the recovered database URL or password to source control.

Do not paste credentials into the recovery record.

## 12. Controlled cutover

After the recovered database passes validation:

1. confirm the selected application Git SHA;
2. confirm the recovered database Alembic state;
3. confirm private network reachability;
4. record the current production database secret version;
5. update the Key Vault database connection secret to the recovered server;
6. redeploy/restart through the controlled production path as necessary;
7. verify application startup;
8. verify `/health`;
9. verify `/ready`;
10. require:
    - `"status":"ready"`;
    - `"database_connected":true`;
    - `"migration_current":true`;
11. test Microsoft Entra authentication;
12. test an authorized student/team boundary;
13. test instructor authorization;
14. verify a representative frozen evidence snapshot;
15. verify representative review history;
16. confirm Azure Monitor telemetry;
17. monitor for new errors.

The cutover is complete only after trustworthy application behavior is
established.

## 13. Rollback

Maintain a **rollback** path until the recovery decision is accepted.

Possible rollback paths include:

- return the application database secret to the prior source server if that
  server is determined trustworthy;
- select a different point-in-time recovery candidate;
- deploy a previously trusted application image;
- abandon the candidate recovery server and repeat restoration.

Before rollback, determine whether the prior source still represents a
trustworthy state.

Do not return to a known-corrupted source merely because it is familiar.

Record any Key Vault secret version change associated with rollback.

## 14. Failed recovery validation

If the recovered server does not validate:

1. do not expose it to normal student traffic;
2. preserve relevant recovery evidence;
3. determine whether the restore point was incorrect;
4. determine whether schema/application mismatch exists;
5. determine whether the incident predates the chosen restore point;
6. determine whether another restore point is required;
7. escalate according to the incident runbook when trustworthy state remains
   uncertain.

A completed Azure restore operation is not evidence that recovery succeeded.

## 15. Source-server disposition

The original production server remains preserved until:

- the recovered system has been validated;
- required incident/recovery evidence has been collected;
- the recovery decision has been accepted;
- rollback need has passed;
- any required data comparison is complete.

Deletion or decommissioning of the former source is a separate controlled
decision.

Normal recovery does not authorize deletion of engineering records or evidence.

## 16. Recovery evidence

Record:

- incident/recovery identifier;
- operator;
- source server;
- recovery server;
- restore point;
- recovery start;
- restore completion;
- cutover time;
- application Git SHA;
- application revision;
- Alembic revision before and after migration;
- validation checks performed;
- `/health` result;
- `/ready` result;
- authentication/authorization validation;
- Key Vault secret version change;
- alerts observed;
- actual RTO;
- actual RPO;
- rollback decision;
- residual concerns.

Do not record secret values.

## 17. Live recovery exercise

The first live Azure point-in-time restore exercise must be performed after the
production Azure infrastructure exists and before student production access is
approved.

The exercise should:

1. identify a safe restore point;
2. restore to a new server;
3. validate private networking;
4. validate database contents;
5. validate Alembic state;
6. validate application compatibility;
7. demonstrate the Key Vault connection-switch procedure without exposing
   credentials;
8. verify `/ready`;
9. measure actual recovery time;
10. record evidence.

The exercise may use production-like test data where appropriate to avoid
unnecessary risk to active student records.

## 18. Recovery success criteria

Database recovery succeeds only when:

- the restored PostgreSQL server is trusted;
- the selected restore point is documented;
- expected durable records are present;
- known bad state is absent where applicable;
- Alembic state is valid;
- private networking is preserved;
- Key Vault contains the intended active connection secret;
- the application reports `/ready`;
- authentication and authorization remain fail closed;
- representative historical engineering records remain intact;
- monitoring is functioning;
- rollback remains understood;
- actual RTO and RPO are recorded.

## 19. Gate 16 evidence boundary

Before Azure provisioning, Gate 16 can prove:

- recovery procedure completeness;
- PostgreSQL logical backup/restore correctness in CI;
- migration compatibility checking;
- operational alert definitions;
- recovery safety rules.

After Azure provisioning, Gate 16 evidence must additionally prove:

- actual point-in-time restore;
- actual restored-server networking;
- actual Azure recovery duration;
- actual alert delivery;
- actual production readiness after restoration.

Those live results become evidence for the final Gate 17 production go/no-go
decision.
