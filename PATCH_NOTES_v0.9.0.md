# ETIS Engineering Studio v0.9.0 Overlay

## Repository-intelligence release

This overlay replaces the seeded-review model with a phase-aware repository review pipeline.

### Added

- Exact COMP 330 Fall 2026 starter-kit baseline manifest with SHA-256 provenance comparison.
- `BASELINE`, `TEAM_ADAPTED`, and `TEAM_ADDED` evidence provenance.
- Phase-aware A1–A6 repository scopes and engineering findings.
- Deterministic FACT collection from repository files and GitHub workflow surfaces.
- Optional semantic repository REVIEW pass for weak evidence, contradictions, alternate evidence, traceability, ownership, AI-governance, risk, and tradeoff interpretation.
- Strengths-first review openings.
- High-value challenge ranking with review-theme diversity and history-aware deprioritization.
- Longitudinal snapshot comparison across phase reviews.
- Evidence-dispute workflow so students can correct the board with repository evidence.
- Turn IDs, session locks, and duplicate-response protection for normal, clarification, and coaching turns.
- Visible reviewer processing state and disabled controls while a turn is in flight.
- Public Engineering Platform links in Related Guidance rather than internal ETIS Markdown paths.
- Local repository analysis utility and expanded acceptance-profile tests.
- Repository intelligence / review orchestration architecture specification.

### Changed

- The seeded `working-agreements.md` example is no longer the production review driver; it remains a regression fixture.
- Untouched starter artifacts are explicitly treated as scaffold, not completed engineering evidence.
- Review questions are selected from the actual repository snapshot and current assignment phase.
- A strong repository receives a consequential judgment/tradeoff challenge instead of an empty review.
- The conversation critic is selective by default to reduce model latency.
- Semantic calls use a low conversational reasoning-effort default and bounded retry handling.
- Related guidance is rendered once in the right rail rather than repeated after every reviewer message.

### Overlay handling

This archive contains **no files inside hidden directories**. It can be extracted directly at the repository root. The baseline manifest may contain strings representing `.github/...` paths because it describes the official starter kit; it does not create or overwrite the `.github` directory.
