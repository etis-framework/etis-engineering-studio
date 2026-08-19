# Gate 17 Production Cost-Control Plan

## 1. Purpose

This document records the approved **Gate 17 production cost-control plan** for
ETIS Engineering Studio before Azure production resources are provisioned.

The objective is to provide enough production capacity for the initial COMP 330
classroom workload while maintaining explicit cost ownership, early warning,
and the ability to reduce or eliminate recurring infrastructure costs later.

This plan establishes approved configuration and operator intent. Live Azure
budget creation, alert delivery, and actual resource-cost behavior remain part
of **Post-Provisioning Production Acceptance**.

---

## 2. Ownership

Service and cost-control owner:

- `OPERATIONS_ALERT_EMAIL`
- production/course owner

The production notification address configured through
`OPERATIONS_ALERT_EMAIL` is the intended recipient for Azure operational and
cost notifications.

Unexpected or unexplained production spend must be investigated by the service
owner rather than treated as an accepted operating variance.

---

## 3. Azure monthly budget

The approved initial Azure production budget is:

**$75 per month**

The $75 amount is an operating alert threshold and cost-governance boundary. It
is not a target spend and does not authorize unnecessary consumption.

The initial workload is expected to remain materially below the budget under
normal classroom use.

### Notification thresholds

Configure Azure budget notifications for actual spend at:

- **50%**
- **75%**
- **90%**
- **100%**

Configure a **100% forecast** notification where supported by the applicable
Azure budget scope.

These alerts are intended to provide increasingly urgent visibility before or
when the approved monthly budget is reached.

### No automatic shutdown

There is **no automatic shutdown** requirement when a budget threshold is
crossed.

A budget notification triggers operator review and corrective action as
appropriate. Automatic termination is intentionally avoided because abrupt
shutdown could interrupt student work, destroy operational context, or
interfere with controlled recovery and retention obligations.

---

## 4. Approved initial Azure resource posture

The source-controlled infrastructure establishes the following initial
production posture.

### PostgreSQL

- SKU: **Standard_B1ms**
- Tier: Burstable
- Storage: **32 GiB**
- Storage auto-grow: enabled
- Backup retention: **7-day** initial backup retention
- Geo-redundant backup: disabled initially
- High availability: disabled initially
- PostgreSQL major version: 16
- Database networking: private/delegated-subnet design

The PostgreSQL configuration is deliberately small for the initial instructional
load. Capacity must be increased only when production evidence justifies it.

### Container Apps

The production application is initially configured with:

- `minReplicas`: **0**
- `maxReplicas`: **5**
- per-replica CPU: **0.5 vCPU**
- per-replica memory: **1 GiB**

The `minReplicas` value of 0 preserves the intended low-use
scale-to-zero posture.

The `maxReplicas` value of 5 provides a bounded ceiling for the initial
deployment rather than permitting uncontrolled horizontal expansion.

### Container registry

Azure Container Registry uses the Basic SKU.

Administrative registry authentication remains disabled. Runtime pull access is
provided through managed identity and bounded Azure RBAC.

### Logging and telemetry

The initial Log Analytics retention configuration is **30-day** retention.

Application Insights is workspace-backed.

Telemetry collection must remain bounded by the Studio's sensitive-data-safe
logging policy. Increasing telemetry volume or retention requires consideration
of both privacy and cost.

---

## 5. OpenAI cost boundary

OpenAI is **separate** from the Azure $75 monthly budget.

The dedicated ETIS Engineering Studio production OpenAI project has an approved:

**$40 per month hard limit**

This OpenAI **hard limit** provides a separate model-service cost boundary.

Application telemetry records bounded usage information, including token and
estimated-cost information, so unexpected model consumption can be reviewed.

Source-controlled Studio model selection remains:

- student-facing conversation: `gpt-5.6-sol`;
- repository semantic interpretation: `gpt-5.6-luna`;
- selective critic: `gpt-5.6-luna`.

The application must continue to fail closed when required provider capability
is unavailable rather than bypassing cost or provider controls.

---

## 6. Cost escalation posture

Budget and usage notifications are operational signals.

When unexpected cost growth occurs, the owner should determine whether the
cause is:

- expected classroom demand;
- abnormal Container Apps scaling;
- unexpected PostgreSQL growth;
- excessive telemetry ingestion;
- abnormal OpenAI usage;
- repeated failures or retries;
- misconfiguration;
- unauthorized or abusive use;
- an Azure or third-party pricing/configuration change.

Corrective action may include lowering capacity, tightening a usage boundary,
correcting configuration, disabling an unnecessary workload, or escalating for
additional authorization.

The budget itself does not substitute for application security or rate
controls.

---

## 7. Future cost reduction and shutdown

The approved production posture is not permanent.

The Azure budget **may be reduced**, **may be modified**, or **may be
eliminated** when the operational need changes.

Individual Azure resources may likewise be scaled down, stopped where supported,
replaced with a lower-cost archival mechanism, or deleted when they are no
longer required.

The OpenAI project limit may also be reduced or production model access
disabled when the Studio is no longer operating.

These actions must respect applicable **retention obligations**.

Required engineering records, attribution data, audit/recovery evidence, or
other retained information must not be destroyed merely to eliminate
infrastructure cost. Where retention continues after active operation ends,
required records may first need to be moved to an approved lower-cost archival
boundary.

The intended long-term objective is therefore:

> retain only what policy requires, preserve it using an appropriate
> cost-efficient mechanism, and remove unnecessary recurring service costs.

---

## 8. Gate 17 classification

Pre-Azure cost posture:

**Operator-configured — APPROVED**

Approved controls:

- Azure monthly budget: $75;
- actual-spend notifications: 50%, 75%, 90%, 100%;
- forecast notification: 100% where supported;
- notification owner: `OPERATIONS_ALERT_EMAIL`;
- no automatic shutdown;
- bounded PostgreSQL sizing;
- bounded Container Apps scaling;
- bounded telemetry retention;
- separate OpenAI $40 monthly hard limit;
- explicit operator escalation for unexpected spend;
- explicit authority to reduce or eliminate future costs subject to retention
  obligations.

Live Azure budget existence, notification delivery, actual SKU realization,
actual scaling behavior, telemetry cost, and observed spend remain
**Requires post-provisioning validation**.

They must be verified during **Post-Provisioning Production Acceptance** before
student access is authorized.
