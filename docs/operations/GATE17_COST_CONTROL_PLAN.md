# Gate 17 Production Cost-Control Plan

> **Historical decision record with production closeout.** Gate 17 approved the initial cost posture before Azure provisioning. Post-Provisioning Production Acceptance subsequently established the live controls below.

## 1. Purpose

The cost-control objective is to keep the small COMP 330 production environment predictable and visible without automatically shutting down a service students may be actively using.

## 2. Current production cost controls

Accepted live configuration as of 2026-08-21:

- production resource-group budget: **$100/month**;
- actual-cost notifications at **50%**, **80%**, and **100%**;
- notifications delivered to the configured production operations recipient;
- no automatic shutdown at a budget threshold;
- PostgreSQL `Standard_B1ms`, 32 GB, 7-day backup retention;
- Container Apps maximum replicas: **5**;
- accepted live Container Apps minimum replicas: **1**;
- ACR Basic;
- Log Analytics retention: 30 days;
- bounded OpenAI usage telemetry and course/team warning thresholds in application configuration.

The $100 budget is an alert/governance threshold, not a target spend or authorization to consume the full amount.

## 3. Budget response

At 50%:

- confirm spend is attributable to expected course activity;
- check for accidental duplicate resources or unusually high model usage.

At 80%:

- review current-month forecast and resource utilization;
- identify safe cost reductions that do not disrupt active student work or retention obligations.

At 100%:

- treat as an operational escalation;
- determine whether increased spend is expected/approved;
- freeze discretionary scale/features until the cause is understood.

There is no automatic resource shutdown solely because a budget threshold is crossed.

## 4. Accepted resource posture

### PostgreSQL

- PostgreSQL 16;
- Burstable `Standard_B1ms`;
- 32 GB storage;
- 7-day PITR retention;
- geo-redundant backup disabled;
- HA disabled;
- private VNet integration.

### Container Apps

Accepted live runtime:

- minimum replicas: **1**;
- maximum replicas: **5**;
- current design target remains small-course use rather than unconstrained scale.

**Known IaC drift:** `infra/azure/app.bicep` still defaults `minReplicas` to `0`. This document records the accepted live value of `1`; reconcile source control separately before a future deployment is expected to preserve that value automatically.

### Telemetry

- workspace-backed Application Insights;
- 30-day Log Analytics retention;
- alerts for 5xx, restarts, PostgreSQL availability, and PostgreSQL storage.

## 5. OpenAI cost boundary

Application AI usage records token counts, cached input, output, latency, model purpose, and estimated cost. Instructor AI economics views provide team/course visibility.

Cost pressure must not silently terminate an active student learning conversation. Operational review and future configuration changes are preferred to surprise mid-session failure.

## 6. Closeout

Gate 17 cost posture is **CLOSED / ACCEPTED**. Live Azure budget configuration and resource posture were verified during 2026-08-21 Post-Provisioning Production Acceptance.
