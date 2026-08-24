# ETIS Engineering Studio Documentation Library

The **ETIS Engineering Studio Documentation Library** provides the formal, publication-ready documentation set for the ETIS Engineering Studio.

The library is intended for multiple audiences, including:

- students;
- instructors and course owners;
- technical administrators;
- production operators;
- system maintainers; and
- institutional adopters.

The documents are organized as a coordinated set. Start with the **Master Manual & Documentation Index** for the complete system overview and document map, or use the audience and task guidance below to go directly to the manual you need.

---

## Start Here

### 00 — Master Manual & Documentation Index

[Open the Master Manual & Documentation Index](00_ETIS_Engineering_Studio_Master_Manual_and_Documentation_Index.docx)

The authoritative entry point to the documentation library.

Use it to understand:

- the purpose and educational motivation of ETIS Engineering Studio;
- how Studio fits within the broader ETIS ecosystem;
- the relationship among:
  - ETIS Engineering Platform;
  - ETIS Engineering Studio;
  - ETIS Preflight; and
  - ETIS Engineering Review Center;
- student, instructor, administrative, and operational roles;
- the end-to-end engineering-learning workflow;
- production architecture and operating model;
- documentation ownership and governance; and
- which manual to use for a particular task.

---

### 01 — Executive Overview

[Open the Executive Overview](01_ETIS_Engineering_Studio_Executive_Overview.docx)

A concise leadership-level overview of the Studio and its significance.

Recommended for:

- academic leadership;
- faculty evaluating the platform;
- institutional technology leaders;
- program directors;
- external reviewers; and
- organizations considering adoption.

It explains why engineering judgment becomes increasingly important in the AI era and how the Studio develops evidence-based reasoning, accountability, and professional engineering judgment.

---

# Documentation by Audience

## Students

### 05 — Student User Guide

[Open the Student User Guide](05_ETIS_Engineering_Studio_Student_User_Guide.docx)

The complete student-facing guide to using ETIS Engineering Studio.

Covers:

- Loyola SSO sign-in;
- team and repository access;
- GitHub identity linking;
- shared team engineering evidence;
- Engineering Evidence;
- Board Reviews;
- Focused Reviews;
- Review Findings;
- interacting with the controlled specialist reviewers;
- challenging findings;
- engineering recommendations;
- evidence snapshots;
- review history;
- individual versus team state;
- privacy; and
- troubleshooting.

---

### 06 — Team GitHub & Repository Setup Quickstart

[Open the Team GitHub & Repository Setup Quickstart](06_ETIS_Team_GitHub_and_Repository_Setup_Quickstart.docx)

A short, task-focused guide for connecting a team repository to the Studio.

Use this when a team is:

- linking GitHub;
- authorizing the course repository;
- confirming repository access; or
- resolving initial repository setup issues.

---

### 07 — Student Cheat Sheet & Quick Reference

[Open the Student Cheat Sheet & Quick Reference](07_ETIS_Student_Cheat_Sheet_and_Quick_Reference.docx)

A compact reference for students who already understand the basic workflow.

Includes:

- review types;
- evidence concepts;
- recommendations;
- finding responses;
- frozen evidence;
- review history;
- common terminology; and
- quick troubleshooting guidance.

---

## Instructors and Course Owners

### 04 — Instructor & Course Owner Handbook

[Open the Instructor & Course Owner Handbook](04_ETIS_Engineering_Studio_Instructor_and_Course_Owner_Handbook.docx)

The primary instructor-facing guide.

Covers:

- Instructor Command Center;
- sections and teams;
- student visibility;
- team engineering evidence;
- review activity;
- findings;
- persisted review conversations;
- repository administration;
- AI usage and cost;
- Settings & Access;
- coaching versus grading;
- instructor authority boundaries;
- student support; and
- recommended course operating practices.

---

### 10 — Semester Administration & Course Operations Guide

[Open the Semester Administration & Course Operations Guide](10_ETIS_Engineering_Studio_Semester_Administration_and_Course_Operations_Guide.docx)

The operational guide for administering a course term from setup through archive.

Covers:

- term creation;
- sections;
- rosters;
- team assignments;
- repository setup;
- semester activation;
- adds and drops;
- team changes;
- release controls;
- student access;
- operational checkpoints;
- end-of-semester archive; and
- common course-administration scenarios.

---

## Technical Administrators and Maintainers

### 02 — Installation & Administration Guide

[Open the Installation & Administration Guide](02_ETIS_Engineering_Studio_Installation_and_Administration_Guide.docx)

The primary guide for deploying and administering ETIS Engineering Studio.

Covers:

- installation;
- local development;
- Microsoft Entra configuration;
- Loyola SSO integration;
- GitHub OAuth;
- GitHub App configuration;
- Azure resources;
- PostgreSQL;
- Key Vault;
- managed identity;
- DNS and TLS;
- GitHub Actions deployment;
- protected production environments;
- post-deployment acceptance;
- upgrades;
- rollback; and
- decommissioning.

---

### 03 — Architecture & Detailed Design

[Open the Architecture & Detailed Design](03_ETIS_Engineering_Studio_Architecture_and_Detailed_Design.docx)

The technical architecture reference for the system.

Covers:

- logical architecture;
- identity and authorization;
- course, term, section, and team model;
- GitHub integration;
- evidence ingestion;
- frozen evidence snapshots;
- review orchestration;
- student learning history;
- instructor authority;
- persistence;
- PostgreSQL and Alembic;
- concurrency and idempotency;
- fail-closed controls;
- Azure deployment architecture;
- observability;
- security;
- privacy;
- failure behavior; and
- architectural invariants.

---

# Production Operations

## 08 — Azure Operations CLI User Guide

[Open the Azure Operations CLI User Guide](08_ETIS_Engineering_Studio_Azure_Operations_CLI_User_Guide.docx)

The complete operator reference for the ETIS Azure Operations CLI.

Primary entry point:

```bash
./scripts/azure/etis-azure <command> [options]
```

Documents:

- `doctor`
- `status`
- `config`
- `health`
- `replicas`
- `revisions`
- `logs`
- `cost`
- `budget`
- `smoke`
- `drift`
- `acceptance`
- `scale`

Also explains:

- PASS / WARN / FAIL / INFO semantics;
- healthy output;
- common failure conditions;
- command selection;
- production acceptance;
- configuration drift; and
- guarded runtime scaling.

---

## 09 — Production Operations Runbook

[Open the Production Operations Runbook](09_ETIS_Engineering_Studio_Production_Operations_Runbook.docx)

Use this when production is unhealthy, degraded, or behaving unexpectedly.

Includes symptom-driven playbooks for:

- Studio unavailable;
- root page failure;
- `/health` failure;
- `/ready` failure;
- database or migration issues;
- Loyola SSO failures;
- GitHub OAuth issues;
- GitHub repository authorization problems;
- replica restarts;
- HTTP 5xx errors;
- latency;
- OpenAI degradation;
- cost and budget alerts;
- configuration drift;
- wrong production revision;
- failed deployment;
- custom domain and TLS problems;
- Azure alerts; and
- return-to-service validation.

---

## 11 — Backup, Recovery & Disaster Recovery Runbook

[Open the Backup, Recovery & Disaster Recovery Runbook](11_ETIS_Engineering_Studio_Backup_Recovery_and_Disaster_Recovery_Runbook.docx)

Use this for serious recovery events.

Covers:

- recovery decision-making;
- application rollback;
- immutable production images;
- PostgreSQL Point-in-Time Restore;
- temporary restore validation;
- Alembic schema verification;
- data-integrity checks;
- migration recovery;
- Key Vault and secret recovery;
- DNS and TLS recovery;
- Entra and GitHub callback recovery;
- disaster-recovery exercises;
- post-recovery acceptance; and
- recovery evidence preservation.

---

# ETIS Educational Workflow

ETIS Engineering Studio is one part of a coordinated engineering-learning model.

```text
Build real engineering evidence as a team
                │
                ▼
Practice and develop individual engineering judgment
        ETIS Engineering Studio
                │
                ▼
Check team readiness for formal review
             ETIS Preflight
                │
                ▼
Freeze the formal repository evidence boundary
          Required Git tag
                │
                ▼
Conduct instructor-controlled phase-gate review
      ETIS Engineering Review Center
```

The responsibilities are intentionally separated.

### ETIS Engineering Studio

**Developmental engineering coaching**

- shared team repository evidence;
- individual engineering reasoning;
- controlled specialist reviewers acting as mentors;
- repeated use throughout a phase;
- safe space to challenge, reconsider, and improve.

### ETIS Preflight

**Readiness assessment**

Answers:

> Are we ready for formal phase-gate review?

Preflight identifies missing or weak repository evidence before formal submission.

### ETIS Engineering Review Center

**Formal instructor-controlled phase-gate review**

- uses a deliberately frozen Git-tagged evidence boundary;
- applies the same controlled engineering perspectives in a formal review role;
- supports instructor judgment;
- does not replace academic authority.

Developmental Studio conversations do not silently become formal assessment evidence.

---

# Which Document Should I Use?

| I need to... | Start with |
|---|---|
| Understand what ETIS Engineering Studio is | **00 — Master Manual & Documentation Index** |
| Explain the system to leadership | **01 — Executive Overview** |
| Learn how to use Studio as a student | **05 — Student User Guide** |
| Connect a team GitHub repository | **06 — Team GitHub & Repository Setup Quickstart** |
| Get a fast student reference | **07 — Student Cheat Sheet** |
| Operate Studio as an instructor | **04 — Instructor & Course Owner Handbook** |
| Configure a semester, roster, or teams | **10 — Semester Administration & Course Operations Guide** |
| Install or configure the platform | **02 — Installation & Administration Guide** |
| Understand the system architecture | **03 — Architecture & Detailed Design** |
| Use the production CLI | **08 — Azure Operations CLI User Guide** |
| Diagnose a production problem | **09 — Production Operations Runbook** |
| Recover from a serious failure | **11 — Backup, Recovery & Disaster Recovery Runbook** |

---

# Documentation Set

The formal documentation library consists of:

```text
docs/manuals/
├── README.md
├── 00_ETIS_Engineering_Studio_Master_Manual_and_Documentation_Index.docx
├── 01_ETIS_Engineering_Studio_Executive_Overview.docx
├── 02_ETIS_Engineering_Studio_Installation_and_Administration_Guide.docx
├── 03_ETIS_Engineering_Studio_Architecture_and_Detailed_Design.docx
├── 04_ETIS_Engineering_Studio_Instructor_and_Course_Owner_Handbook.docx
├── 05_ETIS_Engineering_Studio_Student_User_Guide.docx
├── 06_ETIS_Team_GitHub_and_Repository_Setup_Quickstart.docx
├── 07_ETIS_Student_Cheat_Sheet_and_Quick_Reference.docx
├── 08_ETIS_Engineering_Studio_Azure_Operations_CLI_User_Guide.docx
├── 09_ETIS_Engineering_Studio_Production_Operations_Runbook.docx
├── 10_ETIS_Engineering_Studio_Semester_Administration_and_Course_Operations_Guide.docx
└── 11_ETIS_Engineering_Studio_Backup_Recovery_and_Disaster_Recovery_Runbook.docx
```

---

# Documentation Principles

The ETIS Engineering Studio documentation follows the same principles as the platform itself:

- **evidence over assumption**;
- **human engineering judgment remains authoritative**;
- **student coaching is distinct from formal assessment**;
- **shared team evidence does not eliminate individual accountability**;
- **authorization fails closed where authority matters**;
- **production operation must be observable and recoverable**;
- **historical evidence must not be silently rewritten**; and
- **critical operational knowledge should not depend on tribal knowledge**.

---

# Current Reference Implementation

The current production implementation is the ETIS Engineering Studio deployment supporting Loyola University Chicago software engineering instruction.

The course implementation uses:

- team-based GitHub repositories;
- phase-aware engineering evidence;
- developmental Studio reviews;
- ETIS Preflight readiness checks;
- formal phase-gate reviews through the ETIS Engineering Review Center; and
- instructor-controlled course operations.

Course-specific implementation details are documented where appropriate, while the architecture, installation, production-operations, and disaster-recovery manuals are intended to serve as broader ETIS technical references.

---

## Repository

For source code, project documentation, release history, and supporting material, return to the repository root.

[← Back to the ETIS Engineering Studio repository](../../README.md)
