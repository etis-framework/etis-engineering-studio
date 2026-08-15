# Architecture — ETIS Engineering Studio

## 1. Product posture

The Studio is a **decision-and-defense environment**. Its primary user experience is an Engineering Review Room, not a dashboard.

A student enters with a team, project, lifecycle phase, role context, and a frozen repository evidence snapshot. Bounded reviewer agents challenge claims from professional lenses. The student must make a decision and defend the tradeoff, evidence, uncertainty, consequence, owner, and condition that would change the decision.

The system records learning signals and review history. It does **not** autonomously grade the student or generate the assignment answer.

## 2. Logical architecture

```text
Browser
  |
  v
FastAPI / Web Surface
  |-- Course Model / Phase Contracts (deterministic)
  |-- Access & Course Namespace
  |-- Review Session Service
  |-- Challenge Control Plane (deterministic)
  |      |-- Evidence gap rules
  |      |-- Phase decision defenses
  |      |-- Scenario library
  |      `-- Engineering-move evaluator
  |-- AI Reviewer Adapter (optional, bounded)
  |      `-- OpenAI Responses API
  |-- Evidence Acquisition
  |      |-- GitHub App / GitHub REST (read-only)
  |      `-- Frozen Evidence Snapshot
  `-- Persistence
         `-- PostgreSQL (SQLite local)
```

## 3. Why the deterministic control plane matters

LLMs are used for conversational challenge and synthesis, not for defining course requirements or inventing evaluation rules. The authoritative control plane is the instructor-defined phase contract and repository evidence snapshot.

This prevents five common failures:

1. A generic chatbot giving plausible but course-misaligned advice.
2. The model inventing missing repository evidence.
3. The system rewarding polished language instead of engineering reasoning.
4. An agent silently expanding assignment scope beyond Sakai.
5. A student receiving the answer rather than being forced to defend a choice.

## 4. Evidence model

Evidence has four distinct states that the UI should never collapse:

- **Location coverage** — does assignment-appropriate evidence exist and can it be found?
- **Quality** — is the evidence specific, current, linked, reviewable, honest, and actionable?
- **Workflow traceability** — does GitHub show how intent became controlled, reviewed, verified change?
- **Judgment sufficiency** — can the student/team defend the consequential decision supported by that evidence?

Artifact presence alone is never scored as maturity.

## 5. Review-agent model

Agents are professional lenses, not autonomous authorities. Active lenses vary by phase. The Chief Architect synthesizes; specialist lenses challenge; Red Team attacks the weakest assumption.

Every AI reviewer is bounded by the same rules:

- No browsing beyond explicitly supplied evidence.
- No fabricated evidence.
- No autonomous final grade.
- No hidden change to course requirements.
- No “optimal answer” supplied to the student.
- Ask the minimum useful challenge that forces a professional engineering move.
- Preserve disagreement when professional lenses legitimately differ.

## 6. Authentication and authorization

### Human login

Production recommendation: GitHub OAuth because student engineering identity already maps to GitHub activity and repository access. Login proves identity; **course enrollment still gates access**. An arbitrary GitHub account is not admitted.

### Repository access

Production recommendation: a read-only GitHub App installed on course team repositories. This is superior to student PATs because authority is explicit, scoped, centrally revocable, auditable, and does not require sharing credentials.

### Instructor

The instructor role can view all teams in the active course namespace and aggregate learning/review signals. Students can view only their teams and their own review history unless course policy exposes more.

## 7. Semester isolation

Every durable record is scoped by a course namespace (for example `COMP330-F26`). Semester rollover creates a new namespace. Finalized historical records can be retained without mixing them into the active term.

## 8. Deployment decision

Azure Container Apps is the recommended initial host because it supports containerized web applications without requiring Kubernetes operations. PostgreSQL Flexible Server is the durable relational store. Key Vault holds secrets. Application Insights / Log Analytics provide service telemetry. GitHub Actions uses federated Azure credentials/OIDC where practical rather than long-lived deployment secrets.

For ~30 students, concurrency is modest. The initial production design should optimize for simplicity, security, and recoverability—not premature scale.

## 9. Wave 1 scope boundary

**In:** A1/A2, repository snapshot, evidence rail, guided review, scenarios, student review history foundation, instructor overview, GitHub/AI provider abstractions, Azure deployment starter.

**Deferred:** full A3-A6 conversational depth, full GitHub App installation management UI, roster import UI, instructor annotations workflow, replay/archive UI, advanced analytics, push notifications, research exports, fine-grained rate/cost controls, production SSO alternative.
