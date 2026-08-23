# ETIS Engineering Studio Azure Operations CLI

This directory contains the operator-facing Azure command-line toolkit for ETIS Engineering Studio production.

The toolkit makes routine production inspection, validation, troubleshooting, and narrowly controlled runtime operations easier without requiring operators to remember raw Azure CLI commands.

It is an operations interface, not an alternative deployment system.

## Quick Start

Check local Azure operations readiness:

    ./scripts/azure/etis-azure doctor

Check current production status:

    ./scripts/azure/etis-azure status

Run the full post-deployment acceptance check:

    ./scripts/azure/etis-azure acceptance

Check for live configuration drift:

    ./scripts/azure/etis-azure drift

Inspect recent production activity:

    ./scripts/azure/etis-azure logs

Show command help:

    ./scripts/azure/etis-azure help

## Operating Model

The toolkit follows these principles:

1. Read-only operations are easy.
2. Production mutation is deliberate and guarded.
3. Repository infrastructure remains authoritative.
4. GitHub Actions remains the production deployment path.
5. Operational output favors clear PASS / WARN / FAIL results over raw Azure data.
6. Routine commands do not display secret values.
7. Informational telemetry does not silently become a production acceptance gate.
8. Live runtime overrides do not replace infrastructure-as-code changes.

## Production Deployment Boundary

This CLI intentionally does not provide a deployment command.

The production deployment path remains:

    branch -> pull request -> CI -> merge to main -> GitHub Deploy Azure workflow -> post-deployment acceptance

Infrastructure under `infra/azure/` remains the production source of truth.

The toolkit is intended to inspect, validate, troubleshoot, and only where explicitly supported make narrowly controlled runtime changes.

## Prerequisites

The operator workstation needs:

- Bash
- Azure CLI (`az`)
- Git
- `curl`
- Python 3
- access to the ETIS Azure subscription
- an authenticated Azure CLI session

Check local readiness with:

    ./scripts/azure/etis-azure doctor

## Command Index

| Command | Purpose | Mutates Azure? |
| --- | --- | --- |
| `doctor` | Check local workstation and Azure operations readiness | No |
| `status` | Show concise production status | No |
| `config` | Show important non-secret production configuration | No |
| `health` | Check health/readiness endpoints and response times | No |
| `replicas` | Inspect configured and running replicas | No |
| `revisions` | Inspect revision history and traffic | No |
| `logs` | Inspect recent or live production logs | No |
| `cost` | Show month-to-date Azure cost telemetry | No |
| `budget` | Show Azure budget and alert configuration | No |
| `smoke` | Run non-destructive external production checks | No |
| `drift` | Compare live production with accepted/source baseline | No |
| `acceptance` | Run the full post-deployment acceptance report | No |
| `scale` | Apply a guarded live runtime scaling override | Yes |
| `help` | Show CLI help | No |

## Command Reference

### `doctor`

Purpose: verify that the local workstation and Azure access are ready for production operations.

Run:

    ./scripts/azure/etis-azure doctor

It checks:

- Azure CLI availability and version
- Git availability
- `curl` availability
- repository detection
- current Git branch and working-tree state
- Azure authentication
- active Azure subscription
- access to the production Container App
- source Bicep replica baseline

A dirty working tree is reported as WARN rather than FAIL.

Use `doctor` first when setting up a new workstation or when Azure commands unexpectedly fail.

### `status`

Purpose: provide a concise snapshot of current production state.

Run:

    ./scripts/azure/etis-azure status

It reports:

- production application and resource group
- Azure region
- public production URL
- Azure Container App FQDN
- subscription
- provisioning state
- latest revision
- revision mode
- current traffic allocation
- configured minimum and maximum replicas
- running replica count

Use `status` for a quick answer to: "Is the Azure production environment in the expected operating state?"

### `config`

Purpose: display important production configuration without exposing secrets.

Run:

    ./scripts/azure/etis-azure config

It reports items such as:

- application and resource group
- public URL and Azure FQDN
- ingress configuration
- target port
- revision mode
- CPU and memory allocation
- runtime min/max replicas
- Bicep min/max replica defaults
- accepted production baseline

Secret values are intentionally not displayed.

### `health`

Purpose: verify the externally reachable application health and readiness endpoints.

Run:

    ./scripts/azure/etis-azure health

The command checks:

- `/health` HTTP status and response time
- `/health` application status and production environment
- `/ready` HTTP status and response time
- readiness state
- database migration-current state
- unauthenticated root-page reachability

Example expected results include HTTP 200 for `/health` and `/ready`, `status=ok`, `environment=production`, and `migration_current=True`.

### `replicas`

Purpose: inspect production replica capacity and the state of running replicas.

Run:

    ./scripts/azure/etis-azure replicas

It reports:

- configured minimum and maximum replica capacity
- latest revision
- running replica count
- replica name
- revision ownership
- readiness
- restart count
- running state

Use this command when investigating capacity, restart behavior, or whether Azure has a healthy running instance.

### `revisions`

Purpose: inspect Container App revision history and traffic allocation.

Run:

    ./scripts/azure/etis-azure revisions

It reports revision name, active state, traffic percentage, replica count, creation time, and identifies the current revision.

Use this command after deployment or when investigating whether traffic is pointing at the expected revision.

### `logs`

Purpose: inspect recent or live production console activity in an operator-friendly form.

Default view:

    ./scripts/azure/etis-azure logs

The default view suppresses routine `/health` and `/ready` probe traffic from the main table and summarizes it instead, making real application activity easier to see.

Available options:

    ./scripts/azure/etis-azure logs --tail 100
    ./scripts/azure/etis-azure logs --all
    ./scripts/azure/etis-azure logs --raw
    ./scripts/azure/etis-azure logs --follow

Option meanings:

- `--tail N` requests more recent log records. The default is 50.
- `--all` includes routine health and readiness probes in the structured view.
- `--raw` displays raw Azure log output.
- `--follow` or `-f` streams live logs from Azure.

The structured view also summarizes observed requests, health probes, readiness probes, HTTP errors, and application errors.

Use the default view first. Use `--all` when diagnosing probe behavior, `--raw` when the structured parser is hiding needed detail, and `--follow` during a live investigation.

### `cost`

Purpose: display month-to-date Azure cost telemetry for the production environment.

Run:

    ./scripts/azure/etis-azure cost

Cost information is advisory operational telemetry. It is not a production-health or production-acceptance gate.

Azure Cost Management can lag behind live usage and may throttle API requests. If Azure returns HTTP 429 / Too Many Requests, the command reports COST: WARN and exits without treating Studio production as unhealthy.

When throttled, do not repeatedly retry the command. Wait and check again later.

### `budget`

Purpose: verify the configured Azure production budget and alert thresholds.

Run:

    ./scripts/azure/etis-azure budget

The accepted production configuration expects a monthly budget of $100 and enabled actual-cost alert thresholds at 50%, 80%, and 100%.

The command verifies that alert recipients exist but does not print recipient email addresses.

Budget alerts provide visibility into spending. They do not automatically stop or scale down Azure resources.

### `smoke`

Purpose: run non-destructive external checks against the deployed production application.

Run:

    ./scripts/azure/etis-azure smoke

The smoke test checks:

- `/health` returns HTTP 200
- `/ready` returns HTTP 200
- the application reports the production environment
- database migrations are current
- the production root page is reachable
- the Loyola sign-in gate is present
- the Studio application shell has native fail-closed protection
- the Entra sign-in route redirects to the Microsoft identity platform
- external response latency

The fail-closed shell invariant requires the production HTML to contain:

    <div id="appShell" class="shell hidden" hidden>

This protects the authenticated application shell from appearing before authentication state is established.

Use `smoke` after deployment and whenever validating the externally visible authentication/bootstrap path.

### `drift`

Purpose: compare live Azure production state with the repository and accepted production baseline.

Run:

    ./scripts/azure/etis-azure drift

The drift check validates:

- production application and resource-group identity
- Bicep minimum replica baseline
- live minimum replicas versus source
- Bicep maximum replica baseline
- live maximum replicas versus source
- Single revision mode
- external ingress
- target port 8000
- 100% traffic to the latest revision
- native fail-closed application-shell protection in live production

A DRIFT CHECK: FAIL means the checked live production state no longer matches a repository or accepted-production invariant.

Do not automatically change Azure simply because drift is reported. Determine whether the live state is wrong or whether the repository baseline intentionally needs to change.

### `acceptance`

Purpose: run the complete post-deployment production acceptance report.

Run:

    ./scripts/azure/etis-azure acceptance

Required production checks include:

- Production Status
- Application Health
- Replica Capacity
- External Smoke Test
- Runtime Drift
- Budget Controls

Cost Telemetry is informational and does not block production acceptance.

The command should normally be run after the GitHub Deploy Azure workflow completes.

A healthy deployment ends with:

    PRODUCTION ACCEPTANCE: PASS

If a required check fails, acceptance reports the failed area so the operator can investigate with the corresponding detailed command.

### `scale`

Purpose: apply a guarded live runtime scaling override to the Azure Container App.

This is the only current command in the toolkit that mutates live Azure configuration.

Syntax:

    ./scripts/azure/etis-azure scale <min-replicas> <max-replicas>

Example using the accepted production baseline:

    ./scripts/azure/etis-azure scale 1 5

Example of an intentional scale-to-zero-capable configuration:

    ./scripts/azure/etis-azure scale 0 5

When a change is required, the command:

1. reads the current live scaling configuration;
2. displays the current and requested values;
3. warns that the change affects live production;
4. reminds the operator that Bicep remains authoritative;
5. requires the operator to type exactly `PROD`;
6. applies the Azure runtime change;
7. reads the configuration back from Azure;
8. verifies that Azure accepted the requested values.

If the requested values already match live production, no Azure mutation occurs and no confirmation is required.

The command rejects invalid ranges, including a minimum greater than the maximum. A requested maximum above 10 replicas is outside the accepted operational safety boundary and is rejected.

Setting minimum replicas to `0` is permitted as an explicit override, but the command warns that scale-from-zero can reintroduce cold-start latency.

Important: `scale` changes live runtime state only. It does not modify `infra/azure/app.bicep`.

A later infrastructure deployment can overwrite a runtime-only scale override. Permanent scaling changes must therefore be made through the repository, reviewed through a pull request, and deployed through the normal GitHub workflow.

## Accepted Production Baseline

The current accepted runtime baseline is:

| Setting | Accepted value |
| --- | --- |
| Minimum replicas | `1` |
| Maximum replicas | `5` |
| Revision mode | `Single` |
| Target port | `8000` |
| External ingress | Enabled |
| Public URL | `https://simulator.etisframework.org` |

These values are checked by the toolkit where appropriate. Repository infrastructure remains authoritative for persistent production configuration.

## Output Semantics

The toolkit uses four operator-facing result labels:

- `PASS` — the expected condition was confirmed.
- `WARN` — attention is warranted, but the condition does not necessarily make production unacceptable.
- `FAIL` — a required invariant or operation failed.
- `INFO` — neutral operational information.

Color may be used when output is attached to a terminal, but meaning never depends on color alone. ANSI color is suppressed when output is redirected or when `NO_COLOR` is set.

## Normal Post-Deployment Workflow

After the GitHub Deploy Azure workflow succeeds, run:

    ./scripts/azure/etis-azure acceptance

If acceptance passes, the checked production baseline is accepted.

If acceptance fails, investigate the reported area rather than immediately changing Azure.

Useful follow-up commands include:

    ./scripts/azure/etis-azure status
    ./scripts/azure/etis-azure health
    ./scripts/azure/etis-azure replicas
    ./scripts/azure/etis-azure revisions
    ./scripts/azure/etis-azure smoke
    ./scripts/azure/etis-azure drift
    ./scripts/azure/etis-azure logs

## Common Operational Workflows

Check whether production is generally healthy:

    ./scripts/azure/etis-azure status
    ./scripts/azure/etis-azure health

Investigate a suspected deployment problem:

    ./scripts/azure/etis-azure revisions
    ./scripts/azure/etis-azure replicas
    ./scripts/azure/etis-azure smoke
    ./scripts/azure/etis-azure logs

Check whether Azure has drifted from the accepted configuration:

    ./scripts/azure/etis-azure drift

Review cost controls:

    ./scripts/azure/etis-azure cost
    ./scripts/azure/etis-azure budget

Perform the final verification after a deployment:

    ./scripts/azure/etis-azure acceptance

## Safety and Secret Handling

Routine toolkit commands are designed not to expose application secrets, Key Vault secret values, credentials, or authentication tokens.

The toolkit must not be used to bypass the repository-controlled production deployment process.

The only current live mutating command is `scale`, and it requires explicit production confirmation before making a change.

## Troubleshooting Sequence

When the cause of a problem is unclear, use this order:

1. Run `doctor` to verify the local workstation and Azure access.
2. Run `status` to inspect the overall production state.
3. Run `health` to verify application health and readiness.
4. Run `smoke` to test the externally visible production path.
5. Run `replicas` and `revisions` to inspect the Azure runtime.
6. Run `drift` to compare live state with the accepted baseline.
7. Run `logs` to investigate application or request activity.
8. Run `acceptance` again after the underlying issue has been resolved.

## Design Boundary

The Azure Operations CLI is an operator interface, not an alternative control plane.

The authoritative production model remains:

    Git repository -> review -> CI -> merge -> GitHub deployment workflow -> Azure -> post-deployment acceptance

The toolkit exists to make that model easier to inspect, validate, and safely operate without bypassing it.
