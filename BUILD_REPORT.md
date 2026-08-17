# ETIS Engineering Studio — v0.15.0 Build Report

## Release objective

v0.15 is the pre-Azure **Interaction Integrity & Product Hardening** release. It is intentionally focused on end-to-end product behavior rather than adding another major feature family.

## Problems addressed

- Contextual actions from Engineering Evidence or Review Findings could previously arrive in the Review Room as a generic review and drift to an unrelated challenge.
- Evidence `Open` controls could use guessed URLs and produce 404s.
- Contextual navigation could land at inconsistent scroll positions.
- Completed/prior sessions lacked a sufficiently obvious clean path back to a new review.
- Front-end state could carry hidden controls into a subsequent review session.
- Failure/retry behavior on several teaching-staff surfaces was not consistently explicit.
- Automated validation had strong API/semantic coverage but insufficient browser-level product-journey coverage.

## Product hardening implemented

- Stable finding/evidence/intent/source-view context from click through API, orchestration, semantic reviewer context, and evidence dispute.
- Exact Finding Review challenge construction for selected findings.
- Local frozen-artifact viewer and immutable external source links only when a real frozen artifact exists.
- Deterministic top-of-view navigation for contextual handoffs.
- Completed-session `Start New Review` path and clear read-only history state.
- Session-storage draft recovery and failed-turn restoration.
- Duplicate-send protection while semantic reviewers are working.
- Expanded multilingual/non-native-English, cultural phrasing, accidental-input, adversarial, and meta-conversation policy/corpora.
- Retryable staff views and pending-action controls for administrative mutations.
- Browser-level interaction war games that mock conversation output to avoid OpenAI charges while exercising the actual local API for review/session/evidence operations.

## Validation completed

- **74 automated API/unit/contract tests passed.**
- Course model validator passed.
- Python compilation passed.
- JavaScript syntax validation passed.
- FastAPI health endpoint reports `0.15.0`.
- **16 browser-level product journeys passed**, including:
  - all student navigation destinations;
  - Board Review start, Enter-to-send, and Nudge;
  - completed-session recovery / new-review home;
  - single-select review modes;
  - exact `estimates.md` Engineering Evidence -> Finding Review remediation handoff;
  - Evidence Rail Ask / Reference / Open behavior;
  - exact Finding Discuss / Challenge handoffs;
  - slow-response duplicate-send protection;
  - Engineering Evidence inventory -> Focused Review;
  - Engineering Evidence professional lenses;
  - Review History -> prior session -> new review home;
  - all Course Owner/Instructor navigation destinations;
  - team drilldown;
  - semester schedule save;
  - role-aware teaching-staff Help;
  - no browser/page errors in exercised journeys.
- Scenario corpora contain:
  - **143 student behavior cases**;
  - **41 teaching-staff cases**;
  - **53 UI interaction contracts**.

## Deliberately not claimed complete

The application still requires production integration/configuration before Azure rollout:

- Microsoft Entra application registration and real Loyola tenant consent testing;
- GitHub App registration/installation and private-team repository testing;
- production PostgreSQL/Key Vault/Container Apps provisioning;
- production OpenAI secrets/model configuration and live semantic evaluation;
- production DNS/TLS and operational monitoring.

Those are the next deployment/integration steps; they are not hidden behind local demo behavior.
