# Gate 17 Production Cost-Control Plan

> **Historical decision record with production closeout.** This document keeps
> the approved Gate 17 pre-provisioning plan intact while separately recording
> the live configuration accepted on 2026-08-21. Historical planned values are
> not the same thing as current production values.

## 1. Purpose

This document records the approved **Gate 17 production cost-control plan** for
ETIS Engineering Studio before Azure production resources were provisioned and
then records the production closeout established during **Post-Provisioning
Production Acceptance**.

The objective is to provide enough production capacity for the classroom
workload while maintaining explicit cost ownership, early warning, and the
ability to reduce or eliminate recurring infrastructure costs later.

## 2. Ownership

Service and cost-control owner configuration:

- `OPERATIONS_ALERT_EMAIL`
- production/course owner

The production notification address configured through
`OPERATIONS_ALERT_EMAIL` is the intended recipient for Azure operational and
cost notifications. Institution adopters must provide their own operations
recipient rather than reuse the ETIS reference deployment's operator identity.

## 3. Historical Gate 17 approved Azure budget

Before Azure provisioning, Gate 17 approved an initial Azure production budget
of **$75 per month**.

The $75 amount was an operating alert threshold and cost-governance boundary,
not a target spend or authorization to consume the full amount.

The approved actual-spend notification thresholds were:

- **50%**
- **75%**
- **90%**
- **100%**

The plan also called for a **100% forecast** notification where supported.

There was **no automatic shutdown** requirement when a budget threshold was
crossed. Budget notification was designed to trigger operator review rather
than abruptly interrupt student work, recovery activity, or applicable
retention obligations.

## 4. Historical Gate 17 approved resource posture

The pre-provisioning plan approved the following initial posture.

### PostgreSQL

- SKU: **Standard_B1ms**
- Tier: Burstable
- Storage: **32 GiB**
- Backup retention: **7-day** initial retention
- Geo-redundant backup: disabled initially
- High availability: disabled initially
- PostgreSQL major version: 16
- private/delegated-subnet network design

### Container Apps

The historical Gate 17 plan recorded:

- `minReplicas`: **0**
- `maxReplicas`: **5**
- per-replica CPU: **0.5 vCPU**
- per-replica memory: **1 GiB**

The original `minReplicas=0` value was the pre-provisioning scale-to-zero cost
assumption. Production acceptance later changed the live minimum to 1; see
Section 7.

### Logging and telemetry

The approved initial Log Analytics posture was **30-day** retention with
workspace-backed Application Insights and bounded sensitive-data-safe
telemetry.

## 5. Historical OpenAI cost boundary

OpenAI was deliberately **separate** from the Azure $75 monthly budget.

The dedicated production OpenAI project had an approved **$40 per month hard
limit**. This OpenAI **hard limit** was a separate model-service cost boundary,
with application telemetry used to identify abnormal usage.

The budget itself does not substitute for application security, rate controls,
or fail-closed provider behavior.

## 6. Historical cost reduction authority

The Gate 17 plan was intentionally non-permanent. As operational need changes:

- the Azure budget **may be reduced**;
- the Azure budget **may be modified**;
- the Azure budget **may be eliminated**;
- individual resources may be scaled down or removed when no longer required;
- OpenAI limits may also be reduced or model access disabled.

Any such action must respect applicable **retention obligations**. Required
engineering records, attribution data, audit/recovery evidence, or other
retained information must not be destroyed merely to reduce infrastructure
cost.

## 7. Production closeout — accepted live controls

Post-Provisioning Production Acceptance on 2026-08-21 established the live
production configuration actually in use after deployment:

- production resource-group budget: **$100/month**;
- actual-cost notifications: **50%**, **80%**, and **100%**;
- no automatic shutdown at a budget threshold;
- PostgreSQL: `Standard_B1ms`, 32 GB, 7-day backup retention;
- Container Apps: accepted live `minReplicas=1`, `maxReplicas=5`;
- ACR Basic;
- Log Analytics retention: 30 days;
- bounded OpenAI usage telemetry and application warning thresholds.

The $100 budget is the accepted live alert/governance threshold. It supersedes
the historical $75 pre-provisioning budget for the current ETIS reference
production deployment; the historical value remains above because it is part
of the Gate 17 decision record and CI/documentation contract.

The minimum replica count also changed from the historical plan's
`minReplicas=0` to accepted live `minReplicas=1` to avoid scale-to-zero cold
starts during the semester.

**Known IaC drift:** `infra/azure/app.bicep` still defaults `minReplicas` to `0`.
That source-controlled default should be reconciled separately before a future
production deployment is expected to preserve the accepted live value of 1.

## 8. Current budget response

At 50% of the accepted live monthly threshold:

- confirm spend is attributable to expected course activity;
- check for duplicate resources, abnormal retries, or unusually high model use.

At 80%:

- review current-month forecast and utilization;
- identify safe reductions that do not disrupt active student work or retention
  obligations.

At 100%:

- treat the condition as an operational escalation;
- determine whether the increased spend is expected and approved;
- freeze discretionary scale/features until the cause is understood.

There is no automatic resource shutdown solely because a budget threshold is
crossed.

## 9. Closeout

Gate 17 cost posture is **CLOSED / ACCEPTED**. The historical plan is preserved
above, and the live Azure budget configuration/resource posture were verified
during 2026-08-21 Post-Provisioning Production Acceptance.
