# Evidence Packages and AI Economics

> **Status:** Current design contract within the production-accepted 2026-08-21 baseline.


## Purpose

The Studio must be both epistemically defensible and economically predictable. A reviewer should reason from a defined frozen evidence boundary, while the application avoids repeatedly transmitting the entire repository to an AI model.

## Control path

```text
GitHub repository
  -> frozen commit / phase snapshot
  -> deterministic evidence extraction
  -> semantic repository interpretation (bounded, cacheable)
  -> ranked review finding
  -> compact evidence package for that finding
  -> senior-reviewer conversation
  -> persisted learning state and usage telemetry
```

The compact package includes the chosen challenge, relevant FACT observations, a bounded number of artifact excerpts, relevant GitHub workflow signals, strengths, and longitudinal context. It deliberately excludes unrelated repository content.

## Model routing

- Student-facing conversation: `OPENAI_MODEL` (default `gpt-5.6-sol`).
- Repository semantic interpretation: `OPENAI_REPOSITORY_MODEL` (default `gpt-5.6-luna`).
- Selective conversation-quality critic: `OPENAI_CRITIC_MODEL` (default `gpt-5.6-luna`).
- Deterministic extraction, provenance, phase rules, and authorization never require an LLM.

The reviewer model is intentionally the highest-quality path because conversational trust and coaching quality are product-critical. Bounded background interpretation is routed for cost efficiency.

## Usage accounting

Each OpenAI request records:

- purpose;
- model;
- input tokens;
- cached input tokens;
- cache-write tokens when reported;
- output tokens;
- end-to-end API latency;
- response identifier;
- estimated USD cost using a versioned public rate card.

The instructor dashboard aggregates these by team/course. Cost thresholds are warnings; they do not terminate a junior engineer's active coaching session.

## Caching

1. Repository fetch cache prevents unnecessary GitHub re-acquisition within the refresh window.
2. A frozen evidence snapshot is reused when team, phase, and HEAD commit are unchanged.
3. OpenAI prompt-cache keys stabilize repeated system/context prefixes and expose cached-token reads.
4. Conversation turns reuse the existing compact evidence package; repository analysis is not rebuilt for each student utterance.

## Coaching language tolerance

Natural conversation is semantic, not phrase-matched. The reviewer is explicitly expected to handle:

- spelling and grammar errors;
- fragments and one-word answers;
- tentative answers framed as questions;
- slang and informal language;
- long or rambling answers containing a useful idea;
- misconceptions;
- frustration and combative comments;
- humor;
- self-correction and changed positions;
- direct requests for examples, sources, help, or the answer;
- disagreement with the board;
- evidence disputes and reviewer mistakes.

The reviewer should extract engineering meaning, acknowledge only what was actually understood, and make one useful next move. When productive struggle has ended, the reviewer teaches directly and then uses teach-back/application.

## Conversation regression testing

Natural-language coaching is probabilistic, so exact-response unit tests are insufficient. The repository includes a behavioral corpus in `evals/student_behavior_cases.json`. It covers correct-but-tentative answers, misspellings, non-native English, one-word answers, rambling responses, sarcasm, hostility, requests to simplify, requests for a hidden grading phrase, evidence disputes, direct answer requests, misconceptions, self-correction, topic shifts, and disengagement.

CI validates the presence of the behavioral policy and intent schema without incurring model cost. Before a production release, an authorized developer can run `python scripts/run_conversation_evals.py` with the semantic provider configured, then review both semantic-intent classification and the actual coaching trajectories.

## Latency and response health

Usage summaries expose average and p95 API latency in addition to model calls, token categories, cache utilization, and estimated cost. The student UI disables duplicate turn submission while a reviewer is processing and shows an active reviewer status so network/model latency never looks like an ignored click.
