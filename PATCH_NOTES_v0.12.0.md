# ETIS Engineering Studio v0.12.0

## Review Room coherence, evidence scope, and finding lifecycle

This release turns the three review entry points into distinct, coherent engineering-review workflows rather than UI toggles that can overlap during one conversation.

### Student review experience
- Exactly one review type is selected before a session: **Board Review**, **Focused Review**, or **Review Findings**.
- One **Start Review** action begins the selected workflow.
- Once a session starts, its purpose is locked. Students pause or complete it before opening another review type against the same evidence baseline.
- Board Review lets the senior board choose the most valuable phase-gate question.
- Focused Review lets the student name an engineering concern; the Studio gathers relevant evidence instead of making the student pick files.
- Review Findings lets the student understand, challenge, act on, accept/defer, or supply contrary evidence for a small coherent set of existing findings.
- Findings selected for a Finding Review enter **Under Discussion**; this does not imply the board has confirmed them.
- The launcher collapses into an explicit session-purpose banner after start.
- Evidence and finding actions remain available as context while the central conversation stays dominant.

### Evidence intelligence
- Canonical COMP 330 filenames are discovery clues, not proof and not mandatory filenames.
- Phase-expected evidence may be satisfied by semantically equivalent project-specific evidence in alternate files or locations.
- Repository-discovered relevant evidence can enter the current review even when it is outside the canonical phase path list.
- Evidence carries scope metadata such as **CURRENT PHASE**, **PROJECT SPECIFIC**, and **OUT OF SCOPE**, plus BASELINE/TEAM provenance when available.
- Future starter-kit scaffold remains visible to the evidence engine but does not become an inappropriate current-phase deficiency.
- The Evidence Rail explains why an item is in the review and exposes the exact frozen source when available.

### Finding lifecycle and review memory
Supported lifecycle states now include:
- Open
- Under Discussion
- Evidence Disputed
- Confirmed
- Corrected
- Resolved
- Accepted Risk
- Deferred

Frozen repository facts remain immutable. Validated review interpretations can evolve. Corrected/resolved findings are not selected again as active challenges for the same evidence baseline. Students can express risk/defer dispositions, while confirmed/corrected/resolved states require board evidence validation or teaching-staff/system authority.

### Conversation hardening / war-game coverage
The regression corpus now includes more than fifty novice and adversarial behaviors, including:
- tentative and fragmentary answers;
- poor spelling/grammar and speech-to-text-like input;
- agreeing with a finding but asking what to do next;
- combative rejection of an artifact while pointing to alternate evidence;
- asking to review something outside the chosen review mode;
- confusion caused by future scaffold;
- pause/resume requests;
- stale README or stale snapshot corrections;
- attempts to game finding-state controls;
- hostile comments toward reviewers;
- nonsense/accidental short messages;
- requests for a teammate's private answer;
- attempts to override the board by claiming instructor authority;
- evidence created after the frozen snapshot.

Reviewer policy remains: understand semantic intent before wording, repair misunderstandings, provide guidance when the junior engineer is lost, teach directly once struggle is no longer productive, and never confuse compliance with a canonical filename for engineering understanding.

## Overlay notes
No hidden-directory files are included in this overlay.
