# ETIS Studio — Student UI Local Acceptance Closure Candidate

**Status:** local acceptance candidate; not an accepted or deployed release. Builds **incrementally** on `ETIS_Studio_Final_UI_Refinement_20261008.patch` on the existing `feat/studio-sam-ui-clarity` feature branch. Historical version remains v0.18.0; actual deployment modes are not inferred from source defaults.

## Why this revision exists

Independent student feedback identified two related comprehension failures: the Review/Evidence two-room relationship, and the fact that several Board Reviews accumulate, with one selected at a time and each bound to a fixed repository evidence checkpoint. The prior candidate made the lifecycle visible but left two local-test deficiencies: it required a complicated manual sequence to inspect an older review against newer saved evidence, and a fixed-height transcript separated the first reviewer question from the student's response. Screenshots also showed duplicate Start Board Review actions before any review was selected.

## Implementation

1. **One initial primary action.** When a student has not selected a review and setup is complete, the selected-review orientation panel no longer offers a competing Start Board Review button. The existing first-review entry remains the primary action. Once a review is selected, the contextual Start another Board Review action remains available.
2. **Conversation height follows content.** A short transcript no longer occupies a large, fixed-height blank region. A long transcript remains internally scrollable and bounded by viewport height. The existing composer orientation, Send visibility, reading cue, and safe draft persistence remain in place.
3. **Original review evidence, one click away.** A selected review and the latest saved Evidence Room snapshot may differ. Only when snapshot IDs establish that mismatch, an action routes to the selected review's own frozen evidence rail, expands it, and focuses the section heading. The other Return action is explicitly labeled as returning to the conversation (not the original evidence rail). This does not mutate, recapture, or retrospectively update any review.
4. **Deterministic local student scenarios.** The **loopback-only** simulator now exposes a one-click **Test old review vs newer evidence** setup: open Review #41 remains tied to the old snapshot; Review #42 captures the newer synthetic commit and Evidence Room shows that newer saved snapshot. A separate one-click long-conversation fixture saves 24 pairs of synthetic turns. A fail-next-reply fixture exercises draft recovery after a rejected response. The simulator banner groups secondary controls to avoid masking the UI.
5. **No extra UI surface in Azure.** Simulator controls are served from `tools/student_simulation_controls.js` *only* by the loopback simulator. The active production FastAPI student frontend has no corresponding control or fixture endpoints.

## Frozen boundaries

- Immutable saved repository FACT stays distinct from challengeable reviewer REVIEW; later commits cannot backfill earlier checkpoints.
- Missing attributable activity is not a finding of nonparticipation. Participation decisions, individual assessment, phase-gate approval, and grades remain instructor-owned.
- No analytical mode changes, provider migration, identity reconciliation, access grants, data migration, reviewer prompt changes, Workbench changes, or production model calls.
- The simulator does not reach GitHub, Azure, a real database, or any real student data.

## Acceptance cases / evidence categories

**Deterministic source tests:** first-time action visibility, responsive short-vs-long transcript contract, mismatch-original evidence navigation, fixture isolation, request failure, idempotent review responses, A1–A6 × weak/average/strong repository × no/weak/average/strong attributable-participation combinations.

**Synthetic browser tests:** initial primary action; short transcript and fully visible response/Send; draft preserved between rooms; older selected review plus newer Evidence Room snapshot; direct return to original evidence; long transcript scrolling without unexpected jump; three screen sizes. Prior browser lifecycle, uncertain-response and keyboard/dialog suites remain release regressions.

**Still required before release:** instructor local review, uncoached student observation, actual GitHub snapshot capture against a controlled test repository, actual session/error recovery, VoiceOver/screen-reader testing, and Azure acceptance. These cannot be claimed from mocked browser tests.

## Hands-on test of the missing scenario

1. Run `python3 -u tools/student_ui_simulator.py` and open `http://127.0.0.1:8766/`.
2. Press **Test old review vs newer evidence** in the yellow simulator banner. The page reloads. Read the scenario instruction in that banner.
3. Open **Review History** and select **Review #41**. It should remain open and attached to snapshot #81 / commit `29aabbcc`.
4. Switch to **Engineering Evidence Room**. The latest saved evidence is snapshot #82 / commit `06ddeeff`. The mismatch warning must be visible.
5. Use **Inspect original evidence · Review #41**. The interface returns to the selected review and opens its original evidence rail. Its original snapshot remains unchanged.
6. From the simulator banner choose **Other simulation tests → Load long conversation**, then select Review #41 from history; assess early-message reading and the reply/Send area.
7. With a review open, choose **Other simulation tests → Fail next reply**, type an unsent response, send it, confirm the failure is understandable and the draft survives, then retry.

Do not write or distribute the final student manual until the actual UI passes human acceptance. This document is an engineering acceptance record, not a student tutorial.
