# Identity, Course Administration, and Team Onboarding

## Governing model

Engineering Studio deliberately separates four identities/authorizations that are often conflated:

1. **Loyola Microsoft SSO** authenticates the human being.
2. **Term/section roster and staff assignments** authorize course access and privileges.
3. **GitHub identity linking** maps the authenticated person to their engineering identity once.
4. **GitHub App installation** authorizes the Studio to read the team's selected private repository using short-lived installation tokens.

The Studio never stores a separate student, TA, reviewer, or instructor password.

OAuth/OIDC flow state is signed and self-contained rather than kept only in process memory so authentication can survive production deployments with more than one application replica.

## Data hierarchy

`Course Template -> Term -> Section -> Team -> Student`

A term may contain multiple parallel COMP 330 sections. Sections inherit the same A1-A6 course model but can diverge in dates, release state, roster, teams, and teaching staff.

## Teaching-staff authorization

- **Course Owner**: term-scoped elevated authority. May create and prepare terms, create sections, grant elevated staff roles, activate/archive semesters, and manage permitted setup/active-semester administration. An archived-term assignment provides only the historical authority permitted for that archived term; it is not application-global authority over another semester.
- **Instructor**: manages assigned setup/active section rosters, teams, schedules, students, and may add bounded TA/Reviewer access. An Instructor assigned to an archived semester may retain read-only historical access.
- **TA**: bounded section-scoped review/read authority while the semester lifecycle permits it; does not alter roster, schedule, term lifecycle, or elevated privileges, and does not retain archived-semester authority.
- **Reviewer**: bounded section-scoped review/read authority while the semester lifecycle permits it; does not alter course administration and does not retain archived-semester authority.
- **Student**: only current active section/team context, shared team evidence, and review activity authorized by the active semester. Semester archive ends student operational access without deleting the historical engineering record.

Authentication answers *who are you?* Authorization answers *what are you allowed to do here?*

## Student onboarding

The normal first-login path is intentionally short:

`Loyola sign-in -> roster check -> team assignment -> GitHub identity link -> enter Studio`

If the team repository is not yet connected, the first team member who reaches that state and has linked GitHub may paste the required HTTPS `.git` URL. The Studio verifies the repository and guides the student to install/authorize the ETIS GitHub App when necessary. The repository is a **team-level connection**; later teammates are never asked to provide the URL again.

A transactional team-row lock protects the authoritative repository binding when two teammates onboard at nearly the same time.

## Shared versus individual state

**Shared team state:** project identity, team membership, repository connection, frozen evidence snapshots, findings, strengths, repository history.

**Individual student state:** conversations, assistance progression, demonstrated concepts, recorded recommendations, review history.

A repository refresh never mutates evidence underneath an active review. The active conversation remains pinned to its original snapshot.

## Enrollment changes

Roster imports are repeatable and use only `Student ID` and `Name`. Grade columns are ignored. Missing students are not deactivated unless the instructor explicitly chooses that option. Drops preserve historical reviews. Moving a student records a membership event; earlier reviews remain associated with the earlier team context.

## Semester lifecycle and archive

The normal term lifecycle is forward-only:

`setup -> active -> archived`

`setup` is administrative preparation. Course Owner and Instructor authority may be used to prepare the semester, but setup status does not provide normal student semester access.

`active` is the operational teaching state. Student access, team authority, review access, and staff privileges are resolved from the current database-backed term, section, enrollment, membership, and staff relationships.

`archived` is the normal terminal state. Archive:

- ends student operational access for that semester;
- makes semester administration and review state read-only;
- revokes outstanding sessions associated with the archived semester so authorization is reevaluated;
- preserves enrollment and membership history;
- preserves frozen evidence and review transcripts;
- preserves finding corrections, disputes, resolutions, accepted risks, and deferrals;
- preserves identity attribution required to interpret the engineering record;
- closes still-active reviews as `archived_incomplete` rather than ordinary successful completions.

Course Owners and Instructors assigned to the archived semester may retain read-only historical access. TA and Reviewer authority ends at archive.

Archive is not deletion. There is no normal Delete Term lifecycle operation, and an archived semester is not normally reactivated.

Retention, deletion, anonymization, external-processing, and data-classification rules are governed by [`../SECURITY_AND_PRIVACY.md`](../SECURITY_AND_PRIVACY.md). No calendar-based retention period is implied merely because a semester has ended.

## Semester and section calendar

Each section receives a proposed A1-A6 calendar from the COMP 330 cadence template. Proposed times are created in the term's configured timezone (default `America/Chicago`): review availability begins at 12:05 AM local time and deadline-style fields default to 11:55 PM local time. Instructors may change the dates independently for each section.

Each phase stores `available_at`, `due_at`, `accept_until`, and `release_override`:

- `auto`: release automatically at the section availability date/time;
- `released`: instructor releases early;
- `locked`: instructor temporarily prevents formal review.

Students may revisit released earlier phases. A locked future phase cannot be used for a formal phase review, although a reviewer may still explain a future concept when useful.

Sakai remains authoritative for official course submission requirements and deadlines. The Studio calendar governs Studio review availability and phase context.

## Review entry points

Students have three phase-aware ways to work with the board:

1. **Board Review** - recommended/default; the board chooses the highest-value current challenge.
2. **Focused Review** - the student asks for review of a specific artifact, decision, PR, risk, or engineering area.
3. **Explore a Finding** - the student questions, challenges, or works through a finding already derived from the frozen snapshot.

All three operate against the same frozen evidence semantics and the same section release controls.
