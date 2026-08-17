# ETIS Engineering Studio v0.11.0 Overlay Notes

## Theme

**Identity, Semester Operations, Team Onboarding & Phase-Gated Reviews**

This release converts the Studio from a course-aware local product into a semester-operable architecture. The major product rule is now explicit: institutional identity authenticates the person, the instructor-controlled roster/team model authorizes course access, GitHub identity maps engineering activity, and a team-level GitHub App connection supplies repository evidence.

## Student experience

- Sign in with Loyola; no Studio password.
- Team assignment comes from the instructor, not from GitHub collaborators.
- Link GitHub identity once.
- Only the first teammate needs to connect the team repository; later teammates inherit it.
- Team/project/repository context becomes persistent and read-only in the Review Room.
- Current/released earlier phases are available; future phases are locked until the section calendar releases them.
- Choose Board Review, Focused Review, or Explore a Finding. Board Review is the default novice experience.
- Team evidence is shared; coaching conversations and learning history are individual.

## Instructor experience

- Multi-term and multi-section course model.
- Gradebook CSV roster import ignoring all grade columns.
- Add/reactivate/deactivate students and move them between teams without rewriting history.
- Create terms, sections, teams, staff roles, and section-specific phase calendars.
- Automatic phase release from availability dates plus manual release/lock override.
- Section-aware Command Center, roster, team, and AI-usage views.
- Archive terms without deleting historical evidence/reviews.

## Security / integration

- Entra OIDC foundation with signed ID-token validation.
- Section staff authorization model.
- GitHub App short-lived installation tokens for team repository access.
- GitHub user OAuth is identity linking, not the repository authorization mechanism.
- Review routes require authentication in production and bind student review access to the student's own identity/team.

## Files in hidden directories

None. This overlay intentionally does not contain files inside hidden directories. A root-level `.env.example` replacement is also omitted from the tar; use `ENV_EXAMPLE_v0.11.0.txt` to merge the new configuration variables into your local `.env` and `.env.example` manually.

## Authorization refinement

- Course Owners control term creation/archive and elevated Course Owner/Instructor grants.
- Instructors manage roster, teams, phase release/calendar, and bounded TA/Reviewer grants only for assigned sections.
- TAs and Reviewers receive section-scoped read/review access and do not receive administrative mutation controls.
- OAuth/OIDC flow state is signed/stateless so a callback does not depend on returning to the same server process.
- The first student who connects a team repository must link their GitHub identity first; repository access remains a one-time team-level GitHub App connection.
- Proposed phase dates are generated in the term timezone rather than UTC.

## Configuration overlay note

This archive intentionally contains **no dot-prefixed files or hidden directories**. Merge `ENV_EXAMPLE_v0.11.0.txt` into your existing `.env` and, if desired, update `.env.example` manually. Never copy secrets into `.env.example`.
