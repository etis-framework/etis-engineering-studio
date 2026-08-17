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

- **Course Owner**: creates/archives terms, creates sections, grants elevated staff roles, and has full course authority.
- **Instructor**: manages assigned section rosters, teams, schedules, students, and may add bounded TA/Reviewer access.
- **TA**: section-scoped review/read access; does not alter roster, schedule, term lifecycle, or elevated privileges.
- **Reviewer**: section-scoped review/read access; does not alter course administration.
- **Student**: only their active section/team context, shared team evidence, and their own review conversations/history.

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
