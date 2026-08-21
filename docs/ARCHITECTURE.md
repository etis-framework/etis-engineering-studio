# Architecture — ETIS Engineering Studio

> **Status:** Current production architecture. Production Post-Provisioning Acceptance reached **GO** on 2026-08-21. See `PRODUCTION_BASELINE.md` for the accepted live topology and configuration.

## 1. Product posture

ETIS Engineering Studio is an engineering apprenticeship system, not an autonomous engineering authority. Its architecture is built around a deterministic control plane that owns authorization, evidence boundaries, review purpose, persistence, and lifecycle rules, with bounded AI services used for semantic interpretation, coaching, critique, and synthesis.

The system must remain useful when students are uncertain, disagree with the reviewer, use non-expert language, or supply contrary evidence. The reviewer is fallible; repository evidence and governed system state are authoritative where appropriate.

## 2. Logical architecture

```text
Browser
  ├─ Student Engineering Studio
  └─ Instructor Workspace
          │
          ▼
FastAPI application
  ├─ Authentication / session boundary
  ├─ Course / term / section / team authorization
  ├─ GitHub identity + repository onboarding
  ├─ Evidence acquisition / snapshot service
  ├─ Review orchestrator / challenge engine
  ├─ Semantic coaching / critic adapters
  ├─ Instructor administration / recovery
  └─ Health / readiness / telemetry
          │
          ├─────────────► GitHub OAuth + GitHub App
          ├─────────────► Microsoft Entra
          ├─────────────► OpenAI API
          │
          ▼
PostgreSQL
  ├─ identity/course authority
  ├─ repository onboarding state
  ├─ frozen evidence + findings
  ├─ reviews/turns/learning state
  └─ AI usage / audit-relevant records
```

Production infrastructure places the application in Azure Container Apps and PostgreSQL Flexible Server behind private VNet integration. Runtime secrets are Key Vault-backed and read through managed identity.

## 3. Deterministic control plane

AI output never defines authority. Deterministic application logic controls:

- current user/session identity;
- current term/section/team/role authority;
- review purpose and allowed mutations;
- which repository is verified;
- which frozen snapshot is in scope;
- finding lifecycle and correction state;
- persistence and idempotency;
- production configuration readiness.

This separation is the primary fail-closed boundary when model output, GitHub state, or external services are uncertain.

## 4. Identity and course authority

```text
Microsoft Entra → authenticated Studio user
Course/Term/Section → current course authority
TeamMembership → current team authority
StaffAssignment → current role-scoped staff authority
```

`CourseTerm.status` is authoritative:

- `setup` — administrative preparation;
- `active` — normal semester operation;
- `archived` — historical/read-only; cannot grant current authority.

Archived-term authority must never become application-global authority.

## 5. GitHub identity and repository authority

GitHub identity is individual. Repository trust is team-level.

```text
GitHub OAuth identity link
        │
        └─ immutable GitHub account ID

Candidate repository
        │
        ├─ resolve personal or organization owner
        ├─ authorize GitHub App for correct owner
        ├─ require Only select repositories
        └─ verify exact nominated repository
                    │
                    ▼
           Verified team repository
```

Important invariants:

- a typed URL is never authoritative evidence;
- personal owner authority is based on immutable GitHub account ID, not mutable username;
- organization owners/admins may need to approve GitHub App access;
- staff who can read a team do not automatically gain repository mutation authority;
- GitHub App tokens are exact-repository scoped;
- `all repositories` installation scope fails closed;
- OAuth callback is bound to the initiating Studio session;
- GET navigation does not persist authorization transitions;
- verification locks/re-reads candidate state after external GitHub checks to prevent race promotion.

## 6. Evidence architecture

Evidence has two layers:

### FACT

Deterministic facts about the frozen repository baseline: commit identity, paths, selected contents, workflow signals, provenance, phase scope, and other directly observed repository state.

### REVIEW

Bounded interpretation of FACT: strengths, weaknesses, contradictions, traceability gaps, judgment concerns, equivalent evidence, and review findings.

Frozen FACT evidence is immutable. REVIEW interpretation can be corrected when contrary evidence proves the interpretation wrong. A correction must persist so the same false finding is not rediscovered against the same snapshot.

## 7. Review architecture

Exactly one review purpose is active per session:

- **Board Review** — phase-gate apprenticeship review selected/ranked by the board;
- **Focused Review** — student-selected engineering subject;
- **Review Findings** — work directly with one or a small related set of existing REVIEW findings.

The selected purpose is locked during the session. Students may ask questions in any mode.

Review orchestration combines:

- frozen evidence;
- current phase contract;
- prior corrected findings;
- current review purpose;
- cumulative student reasoning/learning state;
- senior-reviewer lens selection;
- bounded semantic coaching.

## 8. Student responsibility and recommendation model

Students can think aloud before deciding. **Current recommendation** is a revisable decision posture used by the reviewer to challenge the student's current thinking. **State My Recommendation** is the later explicit action indicating that the student is prepared to defend the position.

Not every review requires a recommendation. Review Findings may be purely explanatory/corrective, and Focused Review may be exploratory.

## 9. Teaching-staff boundary

Authorized teaching staff may inspect persisted student/team evidence and review conversations within their current authority. Read authority does not permit staff to impersonate student actions.

Administrative mutations such as roster, term, section, repository reset, or staff assignment remain role-bounded.

Unsent browser drafts remain private to the student browser and are not instructor-visible.

## 10. AI architecture

The AI layer is divided by purpose:

- reviewer conversation — `gpt-5.6-sol` in the accepted configuration;
- repository interpretation — `gpt-5.6-luna`;
- selective critic — `gpt-5.6-luna`.

The provider boundary tracks token usage, cached input, output tokens, latency, response IDs, and estimated cost. Cost warnings are advisory and must not silently interrupt an active learning conversation.

## 11. Production Azure topology

```text
Internet / HTTPS
      │
      ▼
simulator.etisframework.org
      │
Azure Container App (public ingress)
      │  user-assigned managed identity
      ├────────► Key Vault
      ├────────► ACR
      │
      ▼
Container Apps managed environment / VNet
      │
      ▼
Private PostgreSQL Flexible Server

Telemetry → Application Insights → Log Analytics → Azure Monitor alerts
```

See `AZURE_DEPLOYMENT.md` and `infra/azure/README.md`.

## 12. Availability and recovery posture

Accepted production runtime keeps one minimum replica warm and allows up to five replicas.

Database durability uses Azure PostgreSQL automatic backups with 7-day PITR. A real restore drill passed during acceptance. Application rollback uses immutable ACR commit-SHA images in Single revision mode.

## 13. Design invariants

The following must not regress:

- no fabricated evidence;
- no hidden autonomous grading;
- no authority inferred from generic visibility;
- no archived-term current authority;
- no direct student replacement of a verified repository;
- no broad GitHub App installation scope;
- no PAT repository path;
- no retained GitHub OAuth access token;
- no production SQLite;
- no application-startup schema mutation;
- no mutation of frozen evidence snapshots;
- no exposure of unsent drafts to staff;
- no silent fallback that pretends deterministic text is equivalent to configured semantic coaching.
