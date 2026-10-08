# Student Journey Refinement + Loopback Simulation — unreleased candidate

## Evidence / acceptance status

- **Historical baseline**: accepted v0.18.0, historical shadow/shadow deployment receipt. Not a current-production attestation.
- **Verified current source**: active frontend resides in `apps/api/app/static`. Existing application supports active/complete reviews, frozen snapshots, leave-open transitions, Review History, and a deterministic Help drawer. This candidate is incremental to the previously delivered Sam UI patch, not to a clean main checkout.
- **Observed human feedback**: Sam asked for orientation and a clear way to review updated GitHub work; Bill could not initially discover the Evidence Room's contextual help button and found the Review Room dense.
- **Proposed requirement**: intent-first entry, contextual help consolidated into one drawer, draft/snapshot lifecycle continuity, and realistic local UI evaluation without GitHub or AI.
- **Implementation**: in this candidate's changed UI files plus `tools/student_ui_simulator.py`, `tools/student_simulation_controls.js`, and synthetic tests. This is **not** a released or deployed version.

## UI architecture choices

1. In an unstarted Review Room, show a single large **Start Board Review** action, plus **Other review options** and **How reviews work**. Hide the initial empty reviewer workspace and supplementary readouts until a review starts. Expanded choices remain the original Board, Focused, and Finding workflows.
2. If student setup is incomplete, expose a clear *My Team* setup action and explicitly explain personal GitHub identity versus team repository readiness. Do not show an unusable empty conversation beneath the block.
3. **Help** in the header opens the same deterministic Help drawer as existing contextual links. It identifies the room and offers a relevant first action, plus the existing task-oriented topics. Nested topics include a return to all topics. No review call is created.
4. Make **Review repository again** visible near repository and phase context when a review is active. The existing exit dialog allows leaving the old conversation open; no premature completion is necessary.
5. Update review snapshot context after frozen evidence is rendered, not before. Capture time, commit SHA, review number, saved Evidence snapshot and relationships remain factually distinct.
6. Do not change `routers/reviews.py`, reasoning prompts, engine authority, identity or assessment logic, database migrations, production modes, release version, or Workbench.

## Isolated simulation design

The executable `python3 tools/student_ui_simulator.py` binds **127.0.0.1:8766** and serves the **actual** `index.html`, `studio.css` and `studio.js`. A small banner is injected by the separate simulator web server; the production frontend and FastAPI application do not import or enable the simulator. All endpoints are synthetic and implemented in the isolated Python standard-library HTTP server.

Synthetic scenarios: A1–A6; first review on synthetic revision `29aabbcc`; an *advance commit* control to revision `06ddeeff`; a second review preserving historical FACT; same-commit snapshot reuse; recoverable failure injection; review history and response fixture; and frozen Evidence Room source. All simulated responses and context are labeled synthetic. The synthetic scripted reviewer **is not AI coaching**, does not exercise engineering analytical correctness, and cannot establish grading, participation, identity, extra credit, or instructor phase-gate acceptance.

The simulator does not import production routers/database, holds no GitHub credentials, performs no outbound HTTP, and only serves a bounded local allowlist of assets and simulated API paths. Unknown endpoints fail closed; no real user or team data is mounted. It is not remotely network-exposed. Do not use it as a deployed product feature.

## Adversarial matrix / evidence level

- **Deterministic Python**: 6 phases × 3 repository maturities × 4 participation labels = 72 synthetic cross-product contexts. Separate tests confirm old/new snapshot immutability, same-SHA reuse, an interrupted review start, completed history, scripted response, no model calls, and blocked unknown routes. This does not evaluate model judgments.
- **Local mocked Chromium**: first review, contextual Help, Evidence and History navigation, leave-open dialog, new synthetic commit and review. No page JavaScript errors in the latest mock run. The model/network/browser sandbox prevented direct browser navigation to 127.0.0.1; HTTP server functions were verified separately, so the Chromium result is a **mocked-browser** result, not a live socket/browser integration result.
- **Still required before acceptance**: Bill's interactive local simulation review; authentic GitHub integration with a controlled test repository; real evidence ambiguity, contradictions, late claims and equivalent locations; interrupted unsent-draft recovery; browser failure injection; keyboard and actual screen-reader review; authenticated student journeys; instructor sign-off; release and documentation update. No live-model runs authorized or performed.

## Manual simulation walkthrough (for instructor/developer only)

1. Run the local simulator at `http://127.0.0.1:8766/` independently of the usual Studio local server on port 8000.
2. Observe the **SIMULATION** banner; choose A2 and **Start Board Review**. Note review ID and frozen commit.
3. Visit **Engineering Evidence** and Review History. Return to the active conversation; draft a question.
4. Click **Simulate new commit** in the banner; this changes **synthetic** repository state, not the existing session.
5. Click **Review repository again**; choose **Leave open**. Confirm the old review remains resumable from History, including its original snapshot/draft.
6. Start a new Board Review; compare revision and snapshot. Return to old History and confirm it still shows its original evidence.
7. Use **Fail next review start** before another new start and verify safe recovery. Reset all synthetic data to repeat.
8. Stop by pressing `Control+C` in the simulator Terminal. No local production or Azure service was changed.

## Deployment and document gate

The patch should be applied only to the existing `feat/studio-sam-ui-clarity` branch after `git apply --check`; do not reapply the original Sam patch. Do not commit, push, merge, tag or deploy until local instructor UI acceptance and release reviews. A full student quick-start and walkthrough should be written **after** final controls/screens and verified real integration tests. No extra-credit policy is invented here.
