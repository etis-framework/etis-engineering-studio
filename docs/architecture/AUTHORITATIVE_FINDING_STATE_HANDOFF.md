# Authoritative Finding-State and Reviewer Handoff

## Purpose

This revision separates three concepts that must never be conflated:

1. frozen evidence state;
2. finding lifecycle state; and
3. student recommendation / reasoning readiness.

A recommendation may be worth recording while a finding remains open. Inspecting evidence does not change finding lifecycle state. Work performed after the frozen snapshot cannot close the finding in that snapshot.

## Server-owned contract

For an active frozen finding the server exposes:

- `status`: open, under discussion, evidence disputed, confirmed, corrected, resolved, accepted risk, or deferred;
- `closure_state`: open or closed;
- `can_claim_resolved`;
- preferred evidence path and evidence condition;
- explicit invariants that reasoning readiness is not closure and inspection does not change state.

Only authoritative `corrected` or `resolved` lifecycle states support closure language. `accepted_risk`, `deferred`, `confirmed`, and `evidence_disputed` remain non-closure states.

## Reviewer guard

The finding-state contract is appended to the semantic evidence context. If a semantic reply nevertheless makes an explicit positive closure claim while the finding is open, the server appends an authoritative correction before persisting the turn.

## Recommendation handoff

Recording a recommendation preserves a student's current engineering judgment. When a finding is active, the confirmation explicitly states the authoritative finding status and says whether the finding remains open.
