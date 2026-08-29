# Conversation Quality and Behavioral Evals

> **Status:** Current conversation-quality contract plus v0.17 PR4 analytical evaluation boundary.


The Engineering Studio treats the reviewer conversation as an engineering apprenticeship, not a form-completion workflow. Natural-language variability is therefore a first-class product requirement.

## Core contract

The conversational layer must understand meaning rather than preferred vocabulary. Spelling, grammar, punctuation, slang, fragments, uncertainty, humor, frustration, non-native English, and speech-to-text artifacts are not evidence of weak engineering reasoning by themselves.

The reviewer must distinguish, among other conversational acts: tentative reasoning, partial answers, misconceptions, requests for clarification or simplification, requests for examples or sources, direct answer requests, disagreement, evidence disputes, frustration, hostility, meta-conversation repair, self-correction, attempts to game grading, requests to pause, and off-topic turns.

## Senior-engineer behavior

A reviewer should:

- respond to the newest student meaning first;
- remember what has already been established;
- never require a secret phrase;
- translate correct informal ideas into professional terminology;
- ask one main question at a time;
- move from challenge → reframe → nudge → scaffold → direct teaching → teach-back;
- give the answer when productive struggle has ended;
- repair its own conversational mistakes;
- welcome evidence-based disagreement;
- remain calm when the student is combative or sarcastic;
- avoid accusing a student of AI use merely because an answer is polished;
- point to verified ETIS/course guidance when the student needs a source;
- preserve student agency even when sharing a senior engineer's recommendation.

## Regression corpora

`evals/student_behavior_cases.json` contains representative novice and outlier utterances. These are behavioral regression cases, not canonical student answers. A release should be evaluated for whether the reviewer performs the expected coaching behavior across this corpus.

`evals/analytical_engine_cases.json` is the v0.17 PR4 analytical corpus. It contains 42 balanced A1-A6 cases for reasoning-transition validation and next-question planning, including evidence weakness, reviewer fallibility, legitimate uncertainty, contradictions, AI-assisted work without understanding, and uneven team understanding. These cases evaluate analytical trajectory rather than conversational intent alone.

`evals/analytical_engine_rubric.json` defines machine, blinded-human, and production-shadow acceptance gates. Optional live model evaluation is performed by `scripts/run_analytical_engine_evals.py`; by default it runs the actual current semantic conversation engine on the same synthetic case before comparing it with shadow planning. Blinded A/B packets are scored with `scripts/score_analytical_blind_review.py`. Live evals remain outside CI because they incur model cost and semantic variability.

### Analytical planner machine-vs-human scoring

The PR4 machine gate treats a selector-valid move that reaches a case-accepted Review Objective outcome as machine-acceptable even when it differs from the case author's explicit move list. Explicit and preferred move matches remain separate diagnostics. Blinded human review determines whether one reasonable move is actually higher-value than another.

## Evaluation philosophy

Exact-text assertions are inappropriate for a semantic conversation system. Evaluate trajectory and behavior instead: did the reviewer understand the intent, recognize valid reasoning, avoid repetition, teach at the right time, stay grounded in evidence, and move the student toward defensible engineering judgment?

For the v0.17 analytical control plane, also evaluate whether the independent validator grants only defensible reasoning credit and whether the planner selects a materially higher-value next move than the legacy path. Hard authority failures such as fabricated evidence, future-phase demands, hidden grading, or ignoring a correct evidence-backed student challenge are zero-tolerance even if average semantic scores are high.
