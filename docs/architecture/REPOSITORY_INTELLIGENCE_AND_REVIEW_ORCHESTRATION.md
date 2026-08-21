# Repository Intelligence and Review Orchestration

> **Status:** Current design contract within the production-accepted 2026-08-21 baseline.


## Purpose

The ETIS Engineering Studio does not review an assignment by looking for one seeded file. A review begins from a **frozen repository evidence baseline**, evaluates that baseline against the **current COMP 330 phase contract**, identifies both strengths and material concerns, ranks a small number of high-value engineering conversations, and then lets a senior-reviewer persona coach the student through the judgment.

The design deliberately separates evidence authority from AI conversation.

## Three-layer architecture

### 1. Evidence Intelligence Layer — FACT

This layer answers: **What can the frozen repository state actually prove we observed?**

It collects phase-appropriate evidence from GitHub, including repository files and bounded contents, Issues, Pull Requests, Actions runs, tags, commits, and repository metadata. It records the exact commit SHA used by the review.

The layer classifies repository artifacts as:

- `BASELINE` — byte-identical to the official COMP 330 Fall 2026 starter kit;
- `TEAM_ADAPTED` — a starter-kit path materially changed by the team;
- `TEAM_ADDED` — project evidence not present in the starter baseline;
- `GITHUB` — evidence from GitHub workflow surfaces rather than a repository file.

Artifact quality is separately represented as scaffold, empty, thin, partial, reviewable, too large, or unknown. File existence is therefore never treated as proof that the associated engineering practice occurred.

The official starter-kit SHA-256 manifest is stored in `course-model/starter_baseline.json` and is generated from the actual COMP 330 distribution archive.

### 2. Engineering Judgment Layer — REVIEW

This layer asks: **What is worth discussing at this phase, given the evidence and the learning objective?**

Deterministic review rules identify conditions such as missing evidence, untouched scaffold, workflow gaps, unconfigured starter CI, release-control gaps, and phase-specific operational gaps. When semantic repository review is configured, a bounded model pass may additionally identify meaning that exact-path rules cannot reliably detect, such as:

- weak evidence even though a file exists;
- contradictions among project claims;
- alternate/equivalent evidence in another artifact;
- traceability breaks;
- unsupported readiness or release claims;
- risk blindness;
- ownership ambiguity;
- AI-governance gaps;
- consequential engineering tradeoffs.

Semantic repository findings are always `REVIEW`, never `FACT`. The model may cite only artifact paths supplied from the frozen snapshot. Invalid or invented evidence paths are discarded before the finding enters the review record.

Findings are ranked by engineering consequence, phase relevance, educational value, evidence confidence, and novelty. The board intentionally selects only a small number of high-value conversations. A strong repository receives a decision/tradeoff challenge rather than an empty review.

### 3. Coaching Conversation Layer — APPRENTICESHIP

The selected challenge is given to a senior-reviewer persona. The reviewer receives:

- the phase contract;
- the frozen evidence context;
- the selected finding and provenance;
- previously established reasoning;
- the recent conversation;
- the student's current posture;
- assistance/stall state;
- verified ETIS/LMU guidance.

The reviewer does not become the evidence authority. It interprets student intent semantically and conducts a natural coaching conversation. The assistance ladder is:

`challenge → reframe → nudge → scaffold → teach directly → teach-back/application`

Productive struggle is allowed while the student is progressing. When the student says they do not know, asks for the answer, becomes frustrated, or stalls, the reviewer teaches the concept directly and then checks understanding.

## Phase-aware review surfaces

The evidence inspected and the engineering questions asked depend on the current gate.

- **A1 — Project Launch:** team identity, roles/backups, working agreements, AI governance, initial requirements/planning, repository/workflow readiness.
- **A2 — Planning & Estimation:** scope, requirements-to-work traceability, estimates, risks, dependencies, schedule, commitments, re-estimation triggers.
- **A3 — Architecture & Review:** component responsibilities, interfaces, data/context ownership, ADRs, governance boundaries, review findings, test strategy.
- **A4 — Construction & Integration:** source/tests, issues/branches/commits/PRs, review behavior, CI/CD, AI code review, dependencies, architecture consistency.
- **A5 — Cycle 1 Release:** stable release baseline, tests/CI, defects, known limitations, residual risk, release notes, evidence-backed presentation and Cycle 2 handoff.
- **A6 — Final Maturity:** postmortem-driven improvement, observability, runbook/recovery, security/governance, operational evidence, residual risk, stewardship and final release judgment.

A1 is never penalized merely because A6 operations artifacts are not mature. Later gates are expected to build on earlier evidence rather than restart it.

## Strengths-first review opening

A review should not begin by telling students only what is wrong. The board first identifies specific positive evidence that the frozen snapshot supports, then transitions to one high-value question. For an untouched starter kit, a valid strength is that the official engineering scaffold is well organized; it is not valid to praise the team for having completed the practices represented by that scaffold.

## Starter-kit provenance and artifact theater

The untouched COMP 330 starter kit is an acceptance fixture. A mature review must recognize:

- strong course infrastructure is present;
- unchanged template material is not team evidence;
- a team can adapt the expected path or provide credible equivalent evidence elsewhere;
- a polished folder tree cannot substitute for exercised workflow, decisions, review, tests, or ownership.

The current `working-agreements.md` missing-file scenario is retained only as a regression fixture. Production review selection is repository-driven.

## Evidence disputes

Reviewers can be wrong. A student may challenge a finding and identify repository evidence the board missed. The Studio records both the original finding and the dispute, checks the claimed path against the frozen baseline, and either reopens the finding or explains that the cited evidence is outside the snapshot. A future refresh creates a new frozen baseline rather than silently changing the evidence under an active review.

## Longitudinal engineering memory

Each phase review stores its evidence snapshot. Later reviews can compare current evidence with prior frozen baselines, surface improvements or regressions, and challenge whether commitments made in earlier phases were actually carried forward. The purpose is engineering continuity, not surveillance or activity scoring.

## Turn integrity and responsiveness

Student conversation turns use client-generated turn IDs. The server applies per-session concurrency locks and idempotency checks so retries or double submissions cannot generate duplicate reviewer answers. The UI immediately displays the student's message, disables competing controls while the reviewer is processing, and shows the active reviewer portrait with a visible thinking state.

The conversation-quality critic runs selectively rather than on every ordinary turn, reducing model round trips while preserving a repair path for rescue, frustration, meta-conversation, and high-risk teaching responses. Provider retries are bounded.

## Guidance presentation

Verified ETIS and LMU/COICP references are supplied to the model through an allow-listed guidance catalog. Students see human-friendly **Related Guidance** cards linked to the public Engineering Platform, not internal Markdown paths. Repository paths remain available only for evidence provenance where they are actually relevant.

## Acceptance profiles

The automated test corpus includes:

1. untouched starter-kit baseline;
2. weak/missing-evidence team;
3. average partially adapted team;
4. artifact-theater team;
5. contradictory-readiness team;
6. strong team whose repository is complete enough that judgment, not completeness, should be challenged;
7. phase-progression checks ensuring early gates are not evaluated against later-lifecycle obligations.

The production acceptance standard is not that every profile receives a different sentence. It is that the review identifies materially different evidence conditions, selects an appropriate professional lens, and coaches toward the current phase objective without requiring secret vocabulary.
