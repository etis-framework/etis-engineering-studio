# Identity, Course Administration, and Team Onboarding

> **Status:** Current design contract within the production-accepted 2026-08-21 baseline.

## Governing model

Engineering Studio deliberately separates four concerns that are often conflated:

1. **Microsoft Entra** authenticates the human being.
2. **Term/section roster and staff assignments** authorize current course access and privileges.
3. **GitHub identity linking** maps the authenticated person to an immutable GitHub account identity.
4. **GitHub App repository authorization** allows ETIS to read only the verified team repository using short-lived installation tokens.

The Studio never stores a separate student, TA, reviewer, or instructor password.

## Data hierarchy

`Course Template → Term → Section → Team → Student`

A term may contain multiple parallel sections. Sections inherit the course model but may diverge in dates, release state, roster, teams, and teaching staff.

## Teaching-staff authorization

- **Course Owner** — term-scoped elevated authority for term lifecycle and permitted administration.
- **Instructor** — manages assigned setup/active section rosters, teams, schedules, students, and bounded staff access.
- **TA** — bounded current-section read/review authority; no roster/schedule/term-lifecycle/elevated privilege mutation.
- **Reviewer** — bounded current-section read/review authority; no course-administration mutation.
- **Student** — only current active section/team context and student-originated review actions.

Generic team visibility is not mutation authority. Teaching staff who can read a student's persisted Review Room conversation cannot silently start/respond/clarify/coach/commit/complete as that student.

Authentication answers *who are you?* Authorization answers *what are you allowed to do here now?*

## Semester lifecycle

The normal lifecycle is forward-only:

`setup → active → archived`

- `setup` — administrative preparation; no normal student operational access.
- `active` — normal semester operation.
- `archived` — historical/read-only; cannot grant current student/team/reviewer authority.

Archive preserves enrollment, membership history, frozen evidence, review sessions/turns, finding corrections/dispositions, membership events, and AI usage records. Active reviews become `archived_incomplete` rather than successful completions.

An archived Course Owner/Instructor assignment is not application-global authority over another term.

## Student onboarding

Normal first-login path:

`Loyola sign-in → current roster/team authorization → GitHub identity link (if needed) → repository readiness → Engineering Studio`

The bounded production-test student is an exact configured exception used only for controlled acceptance testing; it does not authorize Gmail generally.

## GitHub identity linking

GitHub OAuth links the current Studio user to a GitHub account. The immutable GitHub account ID is authoritative; username renames do not break identity ownership.

OAuth callback mutation requires:

- valid signed state;
- the still-valid/revocation-aware Studio session that initiated linking;
- matching user/session identity.

GitHub OAuth access tokens are not retained.

Legacy GitHub identity rows that lack immutable GitHub account ID are incomplete and must follow the relink path rather than being treated as fully linked.

## Team repository onboarding

Repository trust is team-level and follows this state model:

```text
No repository
  → Candidate repository
  → Owner authorization required
  → Verified team repository
```

A student pastes the HTTPS GitHub repository URL for the team's actual working repository. The `.git` suffix is optional. Browser validation is convenience only; the server validates/canonicalizes the repository URL.

Nomination alone does not make the repository trusted evidence and does not mutate the authoritative team's verified repository field.

### Personal repositories

- ownership is resolved from the repository owner's immutable GitHub account ID;
- only the actual owner may perform the owner authorization step;
- non-owning teammates wait for the owner;
- successful exact verification becomes team-wide;
- username changes do not change ownership authority.

### Organization repositories

- repository owner is the GitHub organization;
- students use GitHub's native GitHub App installation/request flow;
- organization owners/admins may need to approve repository access;
- ETIS must not claim an instructor is the approver unless that instructor actually has organization authority;
- after GitHub grants access, ETIS still verifies the exact nominated repository.

### GitHub App security

- App installation must use **Only select repositories**;
- `all repositories` fails closed;
- installation token is requested for the exact repository only;
- PATs are not supported;
- authorization navigation is side-effect free until an explicit state transition is posted;
- verification re-reads/locks candidate state after external GitHub checks to prevent candidate-change races.

### Verified repository recovery

Students cannot directly replace a verified repository. Course Owner/Instructor may use the bounded **Reset repository onboarding** action. Reset clears the current team repository binding/onboarding state and then requires the normal nomination/authorization/verification path. Historical frozen evidence and review snapshots remain immutable.

## Shared versus individual state

**Shared team state:** project identity, team membership, verified repository, frozen evidence snapshots, strengths/findings, repository history.

**Individual state:** student conversations, assistance progression, demonstrated concepts, current recommendation, recorded recommendations, review history.

A repository refresh never mutates evidence underneath an active review. Active review conversation remains pinned to its original frozen snapshot.

## Enrollment changes

Roster imports are repeatable and use only required identity fields. Grade columns are ignored. Drops preserve history. Team moves record membership events; earlier reviews remain associated with their original team context.

## Section calendar

Each section has instructor-controlled phase availability/release state. Sakai remains authoritative for official course submission requirements and deadlines. The Studio calendar governs Studio review availability and phase context.

## Review entry points

Students have three phase-aware ways to work with the board:

1. **Board Review** — normal/default phase-gate review; the board chooses the highest-value current challenge.
2. **Focused Review** — the student selects a specific artifact, decision, PR, risk, architecture choice, AI-use question, or other engineering area.
3. **Review Findings** — the student works with one or a small coherent set of existing findings to understand, challenge, resolve, accept, defer, or provide contrary evidence.

Exactly one purpose is active per session and is locked after the review starts.
