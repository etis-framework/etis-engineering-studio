# Product Experience

> **Status:** Current production-accepted student and instructor experience.

## Student: Engineering Studio

The student navigation centers on:

- **Engineering Studio** — Review Room and review launcher;
- **Engineering Evidence** — frozen evidence, strengths, findings, and evidence-driven actions;
- **Review History** — persisted prior review sessions;
- **My Team** — identity/team/project/repository onboarding state;
- **Help & guidance** — bounded product/course guidance.

The product deliberately makes the next student action explicit without turning the experience into a checklist game.

## My Team and repository setup

My Team displays separate readiness states for:

- institutional identity;
- course/team assignment;
- GitHub identity link;
- verified team repository.

Repository nomination accepts an HTTPS GitHub repository URL. The `.git` suffix is optional. Nomination is only a candidate; it is not trusted evidence until verification succeeds.

For a repository that requires GitHub App authorization, the UI presents two explicit steps:

1. GitHub authorization (completed state shows a check/OPENED state);
2. exact repository verification (ACTION REQUIRED until completed).

The GitHub completion page returns the user to Studio without automatically replacing Step 2. Exact verification remains the security boundary.

## Review launcher

Exactly one purpose is selected before a review:

- **Board Review** — board-selected phase-gate question;
- **Focused Review** — student-selected engineering concern;
- **Review Findings** — work directly with existing findings.

The purpose is locked after the session starts.

## Conversation and recommendation

Students can ask questions at any time and may think aloud before deciding.

**Current recommendation** means “this is where I am leaning right now.” It is optional and revisable. The reviewer uses it to challenge the current decision posture.

**State My Recommendation** means the student is prepared to record/defend a more explicit engineering position. It is not required in every review.

The reviewer should:

- recognize what is already defensible;
- explain why the issue matters;
- ask one manageable high-value question;
- provide progressive help when the student is stuck;
- teach directly when productive struggle has ended, followed by teach-back/application;
- accept disagreement and contrary evidence;
- avoid hidden answer-giving or fabricated certainty.

## Engineering Evidence

The evidence workspace distinguishes:

- present/strong evidence;
- starter-kit scaffold;
- weak/incomplete evidence;
- equivalent/project-specific evidence;
- REVIEW findings;
- current phase scope and provenance.

Evidence coverage is not course completion percentage. Starter-kit scaffold does not earn evidence coverage simply because the file exists.

## Instructor workspace

The Instructor Command Center provides:

- shared **SECTION** context across major instructor views;
- aggregate class engineering intelligence;
- teams and attention signals;
- stable team identification;
- team membership/accountability;
- current evidence summary;
- all active student reviews for a team, identified by student;
- persisted review drill-down;
- Engineering Evidence;
- AI Usage & Cost;
- Semester Setup and Settings & Access.

Gold/amber team status means the team currently has an attention signal; green means no current attention signal.

Teaching-staff read visibility does not grant authority to impersonate student review actions.

## Repository recovery

Students cannot directly replace a verified repository. Authorized staff use **Reset repository onboarding**, which clears current repository onboarding state but preserves historical frozen evidence and review records. The team then follows the normal nomination/authorization/verification path.

## Browser behavior

Meaningful Studio navigation participates in browser Back/Forward history while preserving section/team/review context. Minor UI interactions do not create unnecessary history entries.
