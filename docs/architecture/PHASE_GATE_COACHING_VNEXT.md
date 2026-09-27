# Phase-Gate Coaching vNext

## Purpose

Studio is a continuous coaching environment used while a team prepares for A1-A6. Workbench is the instructor assessment of the submitted phase-gate baseline. Studio must therefore surface the kinds of evidence gaps and professional review challenges that could later matter without predicting a grade or becoming a checklist for gaming assessment.

## Board Review contract

Every A1-A6 Board Review is an industry-level expert engineering review used for coaching. On entry, Studio provides a phase-specific executive assessment, a non-numeric readiness map, strengths, and a prioritized Board Agenda. The board chooses the most consequential issue and begins probing it.

The board leads, but the student can steer naturally at any time by asking about another issue, challenging an interpretation, citing evidence, or making an engineering assertion. Topic changes within the same phase and frozen evidence snapshot do not require a new review. A new review is required when the phase/evidence contract changes.

## Coaching progression

The objective is to get the student to a correct, defensible engineering answer efficiently:

1. Challenge/probe.
2. Reframe.
3. Nudge.
4. Scaffold.
5. Teach directly: give the professional answer and explain why.
6. Teach-back/application: have the student apply the concept to the repository.

Direct teaching is a successful coaching outcome. Later phases raise the engineering standard; they do not make help harder to obtain.

## Readiness model

The executive assessment uses `Major`, `Issue`, and `Observation`. It does not emit a predicted grade or a binary Ready/Not Ready verdict. Readiness dimensions are phase-specific. The readout is explicitly a coaching signal, not an autonomous course grade.

## Reasoning model

Studio should reason across evidence using these concepts:

- claim -> evidence -> contradiction;
- assumptions and uncertainty;
- authoritative source of truth / supersession when artifacts conflict;
- control maturity: Defined -> Demonstrated -> Consistently Applied -> Effective;
- claim-strength calibration: claims must not outrun evidence;
- mechanism vs demonstrated outcome (backup != restore proof, logging != demonstrated observability, CI presence != meaningful verification);
- course-readiness concern vs broader professional challenge.

## Submission baseline / tags

Studio is used before submission, so absence of a phase-gate tag during ordinary preparation is not a defect. When the team is ready for final instructor review, all intended work should be merged and the required phase-gate tag should identify that exact point-in-time commit. Existing tags are context, not automatically the intended submission baseline.

## Continuity and closure

A repeated review compares the current frozen snapshot with prior evidence and identifies continuing, new, and no-longer-detected findings. No-longer-detected is not synonymous with formally resolved; closure remains evidence-backed. Existing finding dispositions continue to support corrected/resolved/confirmed/accepted-risk/deferred/evidence-disputed states.

## A2-A6 synthetic war-game coverage

The acceptance suite includes these representative failures:

- A2: estimates depend on unresolved scope/assumptions or uncontrolled external dependencies.
- A3: ADR, interface contract, diagram, or data-boundary evidence conflicts and authority is unclear.
- A4: a review control is documented but not consistently operated/effective; implementation violates architecture boundaries.
- A5: release claims exceed acceptance/negative/regression verification evidence.
- A6: operational mechanisms exist but outcomes such as restore/recovery/diagnosis are not demonstrated.

These scenarios are intended to prevent polished artifact presence from masking weak engineering evidence.
