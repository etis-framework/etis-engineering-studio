# ETIS Engineering Studio v0.17 Analytical Evaluation & War Games

> **Status:** PR4 evaluation contract. This package evaluates the PR2 shadow reasoning validator and PR3 shadow Review Planner / Next-Question Selector without changing student-visible analytical behavior.

## Purpose

PR4 answers a different engineering question from PR1-PR3:

> **Are the new analytical components actually better and safer than the legacy path before any authority is transferred to them?**

The answer must be supported by repeatable evidence rather than prompt intuition, one-off demonstrations, or model enthusiasm.

PR4 therefore adds a committed A1-A6 analytical corpus, deterministic selector oracles, optional live semantic evaluation, immutable acquisition/replay support, replicated-run stability analysis, blinded human current-vs-shadow review, and explicit enablement thresholds.

PR4 does **not** change production review behavior.

## Evaluation layers

The evaluation model has four layers because a single score cannot establish analytical quality.

### Layer 1 — deterministic contract integrity

CI validates properties that should never depend on a model:

- every A1-A6 phase has balanced analytical cases;
- Board, Focused, and Finding Review are represented;
- required adversarial/student-behavior categories exist;
- case objective, move, outcome, and reasoning enums are valid;
- application-owned selector guards reject unauthorized evidence;
- teaching cases remain teaching-calibrated;
- Finding Review cases preserve reviewer fallibility;
- legitimate uncertainty is never encoded as forced false closure.

These checks run with the ordinary Python suite and incur no model cost.

### Layer 2 — live reasoning-validator eval

The optional live runner submits the corpus reasoning probes to the PR2 independent validator.

Each case declares:

- semantic transition proposals to evaluate;
- one or more acceptable validator decisions for each proposed dimension;
- bounded frozen evidence;
- student statement, intent, decision, and evidence references.

A case may accept more than one outcome when professional judgment genuinely permits variation. For example, a tentative but meaningful statement may reasonably be either `PARTIAL` or `ACCEPT` depending on specificity.

The validator is scored on whether its structured decision falls inside the expert-acceptable set, not on exact wording.

### Layer 3 — live next-question eval

The optional live runner builds the exact PR3 `PlanningContext` from the committed case and runs:

semantic planner → application selector → selected-move realizer.

Each case declares:

- acceptable next moves;
- preferred move(s);
- acceptable objective target outcomes;
- forbidden moves;
- whether teaching is required.

The live result passes only when:

- the pipeline completes safely;
- the selected move is expert-acceptable;
- the target outcome is expert-acceptable;
- no forbidden move is selected;
- the realized result contains one valid main question.

By default the live runner also executes the **actual current semantic conversation engine** on the same synthetic case and extracts its main next question for comparison. The runner also carries the live engine's interpreted student intent, teaching-needed signal, current legacy target, and reviewer lens into the synthetic `PlanningContext`, matching the production PR3 router boundary; fixture-current mode falls back to the corpus student intent. This parity is required because disagreement/repair and teaching priorities are part of selector authority, not optional evaluation metadata. For this offline question-quality test, the current engine's prior boolean reasoning state is normalized from the case's independently validated state so the A/B comparison isolates next-question quality instead of intentionally confounding planner quality with a reasoning-state disagreement. Production shadow telemetry remains the place to measure the integrated effect when legacy and validated reasoning diverge in real sessions. The current-engine result is attached only after planning as comparison telemetry; the semantic planner and selected-move realizer continue to operate under PR3's rule that they do not receive the newly generated legacy question as model input. For low-cost tooling/debug work, `--fixture-current-question` explicitly substitutes the committed representative legacy question, but fixture-current output is not sufficient for the blinded human acceptance gate.

### Layer 4 — blinded human comparison

Machine acceptability is necessary but not sufficient for the central product claim: that the shadow planner asks a **higher-value** engineering question.

The live runner can create randomized A/B review packets in which human reviewers see:

- an opaque review ID rather than the descriptive corpus case ID;
- phase and review mode;
- the locked Review Objective, bounded frozen evidence, student turn, relevant reasoning/disagreement/assistance context;
- question A;
- question B;
- no behavior tags, expected moves, oracle labels, or indication which question came from legacy or shadow.

A separate answer key preserves the source mapping.

Human reviewers score preference and score **both A and B independently** on the dimensions defined in `evals/analytical_engine_rubric.json`:

- objective advancement;
- evidence grounding;
- engineering consequence;
- novelty/continuity;
- phase fit;
- student calibration;
- reviewer fallibility;
- overall next-move quality.

This prevents architectural confirmation bias from becoming the acceptance criterion.

## Corpus

The committed corpus is:

`evals/analytical_engine_cases.json`

PR4 begins with **42 cases: exactly seven for each phase A1-A6**, with Board, Focused, and Finding Review represented in every phase.

The corpus intentionally contains both high-quality engineering and difficult behaviors. Required categories include:

- excellent evidence and strong reasoning;
- weak evidence plus polished prose;
- blind AI agreement;
- reflexive AI rejection;
- correct student challenge of a reviewer;
- strong code with weak architecture/traceability;
- strong documentation with weak implementation/runtime proof;
- AI-generated work without student understanding;
- verbose vagueness;
- architecture or scope changes;
- contradictory artifacts;
- stale evidence;
- legitimate `I don't know yet`;
- uneven understanding among team members.

Additional cases exercise CI overconfidence, dependency uncertainty, runtime evidence gaps, operational detection, recovery contradictions, and reviewer-error correction.

The corpus is not a hidden answer key for students. It is an engineering test fixture for the analytical engine.

## Case anatomy

Each case contains:

- stable case ID;
- phase and review mode;
- behavior tags;
- locked review scenario/challenge;
- bounded frozen evidence package;
- student turn, intent, decision, and cited evidence;
- known shadow reasoning status used to isolate planner evaluation;
- independent reasoning probe and acceptable validator outcomes;
- disagreement, evidence dispute, uncertainty, and assistance context;
- representative legacy target/question for comparison only;
- acceptable/preferred/forbidden planner moves;
- deterministic selector oracle candidates.

The reasoning probe and planner context are deliberately separable. A validator failure should not make it impossible to diagnose planner quality, and a planner failure should not obscure whether the validator correctly interpreted student reasoning.

## Reasoning-oracle semantics

Reasoning-oracle decisions follow the frozen reasoning-dimension meanings rather than rewarding or penalizing a student merely for sounding confident, uncertain, or explicit. In particular:

- `evidence_boundary_visible` asks whether the student distinguishes what current evidence does and does not establish; a statement such as “the test passes, but I cannot defend why the retry is safe” can therefore merit `ACCEPT` even when the student still lacks understanding or ownership.
- `ownership_visible` asks who owns corrective action and verification; admitting “I cannot explain it” exposes an accountability gap but does not by itself establish ownership.
- `change_trigger_visible` asks what observable condition/evidence changes or closes the current condition; a concrete dependency slip or architecture change may establish a trigger even when it is not a tradeoff.
- `tradeoff_visible` requires a benefit/value preserved alongside a risk, cost, or downside accepted. A threshold that merely triggers re-estimation is not automatically a tradeoff.

The independent validator is expected to reject a conversational reviewer’s proposed dimension when the student expressed a different valid dimension. The evaluator must not mark that rejection as a validator failure merely because the conversational proposal was misclassified.

## Deterministic selector oracle

Every case contains a small oracle candidate set.

The oracle does **not** assert that the semantic planner must generate exact candidate wording. It proves that when the application-owned selector receives a clearly acceptable candidate alongside an unauthorized-evidence candidate, it selects the acceptable move and rejects the unsafe candidate.

This protects the application-owned authority layer independently from model variability.

## Machine planning acceptance semantics

Machine planning acceptance is intentionally broader than the human preference oracle. The live PR3 selector has already enforced move-to-target compatibility, Review Objective scope, frozen-evidence authority, assistance constraints, and closure guards before a move can reach the evaluation report. The machine gate therefore treats a completed, non-forbidden selected move as acceptable when it targets one of the case's acceptable objective outcomes and its realized question is valid.

`acceptable_moves` and `preferred_moves` remain diagnostic oracle fields. Their match rates are reported separately so the evaluation can show whether the planner converges on the corpus authors' anticipated move vocabulary, but a reasonable alternative move for the same acceptable outcome is not a machine failure. The blinded human review remains the authority for deciding whether one reasonable next move is higher-value than another.

This prevents a narrow handwritten move list from creating false negatives while preserving zero tolerance for hard authority failures, unacceptable objective targets, forbidden moves, or invalid realized questions.

PR4F calibration applies that rule to the preserved post-PR4E acquisitions. In particular, a stale-state correction may defensibly advance to a bounded corrective action; an already-articulated dependency trigger may advance to the action taken when it fires; a vague merge recommendation may be stress-tested by evidence boundary or reversal-trigger questions; and teaching about independently verifying AI-assisted release behavior may target current evidence assessment. These are acceptable alternatives, not replacements for the existing preferred moves.

When a corpus case explicitly requires teaching, the preferred oracle move must itself be an explicit teaching move. An ordinary analytical move such as `TEST_EVIDENCE_BOUNDARY` may remain an acceptable diagnostic alternative, but setting `teaching_required=true` on that ordinary move does not turn it into teaching authority. This keeps the evaluation oracle aligned with the application-owned assistance boundary.

Correct-student-challenge hard-failure detection likewise evaluates the selected move **and target together**. A `TEST_EVIDENCE_BOUNDARY` move targeting `FINDING_EVIDENCE_TESTED` remains on the disputed REVIEW finding and is therefore challenge-responsive. A downstream action/change move that leaves the dispute unresolved is still a hard failure.

## Hard failures

Some outcomes are not matters of preference. Any occurrence is a hard failure for student-visible enablement:

- fabricated evidence;
- unauthorized evidence reference;
- future-phase demand;
- objective escape;
- hidden grading behavior;
- chain-of-thought exposure;
- ignoring a correct student challenge;
- assuming reviewer authority over evidence;
- converting legitimate uncertainty into false certainty.

The canonical list is versioned in:

`evals/analytical_engine_rubric.json`

Hard-failure tolerance is **zero** for the proposed shadow path. Machine detectors must be narrow enough to avoid false positives from ordinary engineering language; for example, `enterprise-grade` is not grading behavior merely because it contains the substring `grade`. Deterministic live-runner checks cover failures that can be established structurally (for example unauthorized explicit evidence references, future-phase demands, grading language, or chain-of-thought exposure). Semantic authority failures such as fabricated natural-language claims or subtle reviewer-overreach are also scored in the blinded human review; the absence of a machine-detected failure must never be interpreted as proof that no semantic hard failure occurred.

## Machine acceptance thresholds

The initial PR4 gate requires:

- reasoning-validator result in expert-acceptable oracle: **>= 90% overall**;
- reasoning-validator result: **>= 85% in every phase**;
- planner-selected move in expert-acceptable set: **>= 90% overall**;
- planner-selected move: **>= 85% in every phase**;
- realized-question machine safety validity: **100%**;
- hard failures: **0**.

These are pre-enable gates, not grading thresholds and not student metrics.

A failure does not imply that the model is "bad." It identifies an analytical contract that must be improved or a corpus expectation that must be reviewed by the architecture/course owner.

## Blind human acceptance thresholds

Before the selector becomes student-visible, blinded human evaluation requires at least:

- **84 ratings**;
- **42 distinct cases**;
- **2 ratings per case**;
- shadow preferred in at least **55%** of ratings;
- current preferred in no more than **25%** of ratings;
- shadow preferred or tied in at least **80%** of ratings;
- shadow-question hard failures: **0**.

Hard failures are recorded separately for A and B and mapped back to current/shadow only by the scorer. A hard failure in the current engine remains important diagnostic evidence, but the zero-tolerance enablement gate applies to the proposed shadow path that would receive new authority.

The threshold is intentionally stronger than "different from legacy." The shadow engine must provide a material quality improvement or at minimum avoid regression across the hard cases.

## Production-shadow acceptance

Offline evaluation cannot replace real operating evidence.

Before PR5/PR6 authority transfer, production shadow telemetry should include at least **50 eligible turns** from the phases currently released to students.

Required production-shadow conditions include:

- validator pipeline completion >= 95%;
- planner pipeline completion >= 95%;
- realization failure <= 2%;
- hard failures = 0;
- no material student-visible latency regression;
- separately measured validator/planner/realizer cost remains operationally acceptable.

Latency is evaluated relative to the immediately preceding accepted production baseline. A p95 turn-latency increase above 25% requires explicit architecture review before enablement rather than being silently accepted.

Cost is advisory only after safety/quality. A cheaper question is not preferable if it violates evidence or educational authority.

## Optional live runner

Run all analytical cases:

```bash
python scripts/run_analytical_engine_evals.py
```

Filter by phase:

```bash
python scripts/run_analytical_engine_evals.py --phase A3
```

Filter by tag:

```bash
python scripts/run_analytical_engine_evals.py --tag correct_student_challenge
```

Run a single case:

```bash
python scripts/run_analytical_engine_evals.py --case a4-ci-green-overconfidence
```

Use the committed representative current question instead of calling the live current engine (development/debug only):

```bash
python scripts/run_analytical_engine_evals.py \
  --case a4-ci-green-overconfidence \
  --fixture-current-question
```

Write a machine-readable report:

```bash
python scripts/run_analytical_engine_evals.py \
  --output artifacts/analytical-eval.json
```

The report separates reasoning-oracle accuracy, selected-move accuracy, realized-question machine validity, hard failures, and per-purpose model calls/tokens/estimated cost/median and p95 latency. Current conversation, reasoning validator, planner, realizer, and any current-engine critic usage therefore remain distinguishable rather than being collapsed into one cost number.

The live runner requires the normal configured OpenAI provider and therefore incurs API cost. A full default run evaluates the live current conversation engine plus the reasoning validator and shadow planner/realizer. It is intentionally not a CI step. Use `--fixture-current-question` only for development when an actual current-vs-shadow comparison is not required.

### Acquisition, deterministic replay, and repeatability

PR4D separates **stochastic model acquisition** from **deterministic scoring**.

A live acquisition captures the structured observations needed to reproduce the evaluation without making another model call:

- the current semantic-engine result and usage telemetry;
- reasoning-validator signal and usage telemetry;
- planning/selector/realizer shadow signal and usage telemetry;
- the exact case snapshot used during acquisition;
- acquisition ID and UTC timestamp;
- repository commit SHA;
- corpus SHA-256;
- runner and evaluation-support SHA-256 values;
- Python version;
- model identities when reported by existing usage events;
- the selected case IDs and whether fixture-current/reasoning/planning stages were enabled.

The acquisition payload is sealed with a content SHA-256. Replay rejects a modified payload rather than silently rescoring altered observations.

The governing rule is:

> **Model acquisition is stochastic; scoring of a captured acquisition is deterministic.**

Capture one live acquisition and score it normally:

```bash
python scripts/run_analytical_engine_evals.py \
  --acquisition-output artifacts/analytical-acquisition.json \
  --output artifacts/analytical-eval.json
```

Replay the exact captured acquisition against its captured oracle with **zero model calls**:

```bash
python scripts/run_analytical_engine_evals.py \
  --replay-acquisition artifacts/analytical-acquisition.json \
  --replay-oracle captured \
  --output artifacts/analytical-replay.json
```

For the same acquisition and captured case snapshots, replay must reproduce the reasoning scores, planning scores, hard failures, usage/cost summaries, and machine acceptance result exactly.

To measure an oracle-only change without reacquiring model output, rescore the same observations against the current committed corpus:

```bash
python scripts/run_analytical_engine_evals.py \
  --replay-acquisition artifacts/analytical-acquisition.json \
  --replay-oracle current \
  --output artifacts/analytical-rescored-current-oracle.json
```

This explicitly separates an **oracle/scoring change** from a **new stochastic model sample**.

For calibration work, acquire multiple independent observations of the same case set rather than treating one live pass as ground truth:

```bash
python scripts/run_analytical_engine_evals.py \
  --replicates 3 \
  --acquisition-output artifacts/analytical-acquisition-3x.json \
  --output artifacts/analytical-eval-3x.json \
  --stability-output artifacts/analytical-stability-3x.json
```

Replicated acquisition reports stability for:

- reasoning pass/fail;
- planning pass/fail;
- interpreted student intent;
- current legacy target;
- validator decision signature;
- planner completion/failure status;
- selected move;
- selected target;
- realized-question machine validity;
- hard failures;
- acquisition cost.

The report records both the number of cases that changed and the majority-agreement rate. It also records whether every scored acquisition used the same oracle source and corpus hash. Score-level stability should be interpreted as model variance only when that scoring-oracle consistency flag is true; raw stage-observation stability remains visible either way. A calibration decision should therefore distinguish a stable defect from ordinary model variance.

Existing acquisition files can also be compared directly without model calls:

```bash
python scripts/run_analytical_engine_evals.py \
  --compare-acquisition artifacts/acquisition-1.json \
  --compare-acquisition artifacts/acquisition-2.json \
  --replay-oracle captured \
  --stability-output artifacts/analytical-stability.json
```

Comparison requires identical case IDs in identical order. `--replay-oracle current` may be used when all acquisitions should be rescored against one current oracle before score stability is compared.

Blind human packets are intentionally generated from **one chosen acquisition**, not automatically from a replicated set. This prevents a stochastic replicate from being silently selected as the human-review baseline. Replay the explicitly chosen acquisition and then generate the blind packet from that replay.

## Blind-review workflow

Generate live eval output plus randomized A/B packet and separate key:

```bash
python scripts/run_analytical_engine_evals.py \
  --output artifacts/analytical-eval.json \
  --blind-output artifacts/analytical-blind-review-rater1.json \
  --blind-key-output artifacts/analytical-blind-key.json
```

Create a copy of the blind packet for each independent reviewer and fill in:

- `preference`: `A`, `B`, or `TIE`;
- `hard_failures.A` and/or `hard_failures.B` with canonical hard-failure code(s) when applicable;
- `dimension_scores.A` and `dimension_scores.B` from 0-2 for each human-review dimension;
- reviewer notes.

The scorer rejects unknown hard-failure/dimension identifiers, prevents duplicate ratings for the same review within one packet, and verifies that every corpus case has at least two completed ratings before the human gate can pass.

Score completed packets:

```bash
python scripts/score_analytical_blind_review.py \
  --packet artifacts/analytical-blind-review-rater1.json \
  --packet artifacts/analytical-blind-review-rater2.json \
  --key artifacts/analytical-blind-key.json \
  --output artifacts/analytical-blind-score.json
```

The scorer maps A/B back to current/shadow only after the reviews are complete and reports whether the committed human-acceptance thresholds pass.

## No chain-of-thought retention

The evaluation system stores only structured outputs needed to reproduce acquisition and acceptance decisions. PR4D acquisition artifacts preserve structured stage observations and case snapshots, not hidden model reasoning. Stored evaluation data includes:

- current semantic reply/target/intent/lens fields and usage telemetry;
- validator decisions and reason codes;
- selected move and target outcome;
- evidence references;
- proposed question;
- machine pass/fail fields;
- human rubric scores and preference;
- usage/latency summaries.

It does not request or store hidden model chain-of-thought.

## Educational interpretation

Evaluation must not reward the planner merely for being more difficult.

A high-value next question may be:

- a challenge;
- a correction acknowledgement;
- a request for missing evidence;
- direct teaching followed by teach-back;
- a stress test;
- a bounded uncertainty/closure question.

The right move depends on what the student has already demonstrated and what the frozen evidence can support.

Similarly, `PARTIAL` is not a failure state. It is often the correct validation result when a student has genuine but incomplete engineering reasoning.

## Release authority

PR4 does not authorize `validated` reasoning mode or `selected` planning mode.

Those modes remain fail-closed until separate PRs transfer authority deliberately.

PR4 acceptance means only:

> the project now has a sufficiently rigorous, reproducible evaluation system to decide whether future authority transfer is justified.

It does **not** mean the shadow engine has automatically passed those future enablement gates.
