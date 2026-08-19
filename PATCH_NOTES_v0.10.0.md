# ETIS Engineering Studio v0.10.0 Overlay

## Release theme

**Evidence Intelligence, Coaching Maturity & AI Economics**

This overlay moves the Studio from a repository-aware prototype toward an operational engineering-apprenticeship system. It combines bounded evidence context, natural senior-engineer coaching, novice/outlier-language handling, response/turn safety, model routing, and measurable AI economics.

## Repository intelligence and context control

- Reviewer conversations receive a compact challenge-specific Evidence Package rather than the entire repository.
- Repository semantic analysis is reused when the repository commit and phase have not changed.
- Frozen snapshot facts remain server-side and are selectively surfaced by provenance.
- Evidence-rail artifacts can open the exact frozen GitHub source when a path is available.
- Starter-kit BASELINE content remains distinct from team-adapted/team-added evidence.

## Coaching maturity

The semantic conversation policy now explicitly handles:

- correct-but-tentative wording such as `finger pointing?`;
- spelling/grammar mistakes and speech-to-text-like input;
- non-native English and informal/slang wording;
- one-word and very short responses;
- long/rambling answers containing a valid engineering idea;
- requests to simplify the question;
- requests for an example, source, direct answer, or senior engineer perspective;
- misconceptions;
- frustration, sarcasm, hostility, or combative comments;
- evidence-based disagreement and evidence disputes;
- reviewer mistakes/repetition and meta-conversation repair;
- attempts to discover a hidden `full credit` phrase;
- requests to skip/park an issue;
- off-topic turns and disengagement;
- self-correction or changing one's engineering position;
- polished-but-ungrounded answers without assuming misconduct.

The senior reviewer remains professional and non-defensive. Productive struggle progresses through challenge → reframe → nudge → scaffold → direct teaching → teach-back. When the student is truly stuck, the reviewer is allowed to teach the answer and then verify understanding.

## Behavioral evals

- Adds `evals/student_behavior_cases.json` with 30+ representative novice/outlier cases.
- Adds `scripts/run_conversation_evals.py` for optional paid live semantic smoke-evals before release.
- Adds deterministic regression tests that ensure the semantic schema/prompt continue to cover the difficult interaction classes.
- Live model evals are intentionally not part of CI because they incur API cost and remain probabilistic.

## AI economics and latency

- Student-facing conversation remains on the configured flagship reviewer model.
- Repository interpretation and selective conversation critic default to lower-cost models.
- Prompt-cache keys are stable for repeatable prefixes.
- OpenAI usage is persisted by team, phase, session, purpose, and model.
- Usage summaries include input, cached input, cache writes, output, average latency, p95 latency, and estimated cost.
- Instructor UI shows course/team cost, cache behavior, model-call count, and average response time.
- Cost thresholds warn instructors rather than interrupting a live student conversation.

## Student UX

- Visible reviewer-processing state explains that the reviewer is working and explicitly tells students not to resend the same message.
- Turn IDs, backend locks, and idempotency controls protect against accidental duplicate responses.
- Related Guidance remains in the rail and links to the public ETIS Engineering Platform.
- Evidence and review cards are fully integrated into the Studio's dark visual system.
- Students can challenge a finding and point the board to evidence it may have missed.

## Hidden paths

This overlay contains **no hidden directories** such as `.github/`.

It contains one root-level hidden file: `.env.example`. It belongs directly in the repository root.

## Validation

Validated against a clean v0.9 baseline:

- 36 automated tests passed;
- course-model validation passed;
- Python compilation passed;
- JavaScript syntax validation passed;
- FastAPI health/startup smoke test passed.
