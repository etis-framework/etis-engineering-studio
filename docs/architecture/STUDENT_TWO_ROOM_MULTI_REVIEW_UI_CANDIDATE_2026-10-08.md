# ETIS Engineering Studio — Two-Room / Multiple-Review Student Journey Candidate

**Status:** candidate for local instructor acceptance, **NOT** deployed, merged, or accepted as a new software version. 2026-10-08.

## Repository and authority boundaries

- Supplied source declares Studio **v0.18.0**. Prior historical acceptance was for shadow/shadow deployment. This candidate makes **no configuration, grade, identity, Workbench, analytics-authority, or mode changes**. Check actual deployment configuration independently from `.env.example` (whose defaults are legacy/legacy).
- Source baseline reconstructed from the original supplied Studio source plus three earlier UI patch candidates: `ETIS_Studio_Sam_UI_Candidate_20261008`, `ETIS_Studio_Student_Journey_Refinement_20261008`, and `ETIS_Studio_Reply_Visibility_Refinement_20261008`. The patch applies **only if the branch contents match that reconstructed baseline**. `git apply --check` must succeed before application; do not force or reset.
- Frozen repository FACT remains immutable per review session. REVIEW conclusions remain challengeable. A newer repository commit never backfills earlier evidence. Absence of attributable activity is not proof of nonparticipation. Instructor alone owns participation verification, assessment, grades, and phase-gate acceptance.

## Answers visible to students without Help

1. **Two rooms:** an always-visible desktop/mobile switch in the top bar and a visible paired switcher inside each room distinguish **Engineering Review Room** (talk with the **Review Board**) and **Engineering Evidence Room** (inspect saved sources). The active room is explicitly marked. Switching does not finish a conversation.
2. **Currently viewing:** a selected-review panel provides the session ID, phase, `Open` or `Finished/read-only` status, frozen snapshot, repository commit, and capture time; a persistent top-bar chip retains selected review/status while the response composer is on screen.
3. **More than one open review:** history calls them `Open`; the currently selected session is separately labeled `Currently viewing`. A student can leave one open and start another Board Review.
4. **Return to earlier conversations:** the review selector opens server-backed, bounded paginated **All your Board Reviews**. Open sessions resume; finished sessions can be read but not answered.
5. **Finish safely:** `Finish this review` requires confirmation; it closes conversation to replies without removing its history, and does not signify instructor approval. A nonempty unsent reply blocks finish until the student sends it or deliberately clears it.
6. **Review updated work:** `Start another Board Review` remains available even with an open review. The existing leave-open / finish dialog preserves intent. New review captures the repository revision available at start; if phase and commit are unchanged, frozen evidence may be reused and is explicitly labeled as such.
7. **Which evidence:** each room identifies commit and snapshot. Evidence Room shows latest **saved** phase snapshot, not live GitHub HEAD; it labels matched vs different from the selected review's frozen snapshot without rewriting the old review.

## Exact change inventory

- `apps/api/app/static/index.html`: two-room paired navigation, current review identity and lifecycle actions, full history guidance, pagination controls, persistent top workflow switch.
- `apps/api/app/static/studio.js`: explicit selected review state, safe open/finished handling, history pagination with retry and stable selection, context display, prevent sending to completed sessions from the composer and switching sessions during pending review actions, confirmation barrier for unsent drafts.
- `apps/api/app/static/studio.css`: contrast, focus, persistent navigation, scalable history, responsive layout, read-only composer styling and Help visibility on mobile.
- `apps/api/app/routers/reviews.py`: `offset` and `has_more` on the *existing authenticated* review-list endpoint, with bounded page sizes (max 50), offset cap and deterministic ordering by timestamp then ID. **Existing course/team/user access filters remain in place.** No changes to review creation, evidence retrieval, coaching engine, or grading.
- `tools/student_ui_simulator.py`, `tools/student_simulation_controls.js`: synthetic-only multi-review fixtures, 16 mixed open/finished review button, paged history, finished session replies rejected, frozen artifact commit respected after synthetic updates; remains bound to loopback with no GitHub/model/Azure/student data.
- `tests/test_student_review_lifecycle_clarity.py`: 72-case gate×maturity×attribution contract plus long history, mixed state and snapshot checks.
- `tools/student_lifecycle_mock_browser.py`: optional offline Playwright harness rendering the actual HTML/CSS/JS with an in-memory synthetic API. No external connections.

## War game and validation

**Deterministic/regression:** 298 collected focused/related tests passed. Includes A1–A6 × three repository maturity labels × four attribution labels; the labels drive only synthetic contracts and do not claim analytical model quality. A synthetic list of 65 sessions is page-retrievable beyond the prior 50-result ceiling.

**Mocked browser:** Chromium checks passed at 1440×900, 1280×650 and 390×844. Checked paired room navigation, active reply AND unobscured Send in viewport after start and after return, saved draft restored to original review, distinct commits/snapshots, match/mismatch display, finish blocked on unsent draft, completed sessions read-only, other review still open, and 18 mixed reviews available in paged history. Zero browser JavaScript errors and zero model calls in those checks.

**Loopback server:** direct HTTP smoke checks passed synthetic HTML, 16 mixed reviews, two history pages, completed-session reply rejection (409), and zero model calls. API exercises are synthetic, not live GitHub; the mock browser runs via in-memory transport because Chromium in this environment blocks direct localhost/file navigation. A separate Python curl/HTTP check has served the local simulator, but real Mac-local human acceptance remains outstanding.

**Not accepted/proven:** real authenticated course/GitHub integration, actual AI conversation quality, screen-reader operation, external accessibility audit, real student usability. Before release, test failure/retry/duplicate creation against a controlled integration backend with an explicit paid-call ceiling; no broad live-model campaign is authorized. Student documentation follows accepted UI, not this candidate.

## Remaining adversarial risks to examine locally

- A student with multiple open reviews may expect a currently unselected review to update automatically after commits. Confirm the UI does not imply this.
- Two team members can share frozen repository FACT but must not share private conversations. This needs real authorized-user integration testing; local simulation's single synthetic student cannot prove access control.
- Browser Storage disabled/private browsing: current draft guard intentionally prevents leaving with an unsaved draft. Confirm guidance is sufficient.
- Snapshot mismatch is a warning, not proof that the older review is wrong. No cross-snapshot artifact should be silently attached to a past session.
- Review list pagination provides historical access through authenticated bounded requests; it does not reveal other users' sessions when properly authorized. Server access tests and instructor/TA role smoke checks remain required.
- On narrow screens the sidebar collapses; the top bar retains room navigation, review selector, and Help. Observe this with an actual phone/screen reader.

## Human acceptance exercises (no Help)

1. From the landing UI identify both rooms. Start a Board Review. Read the Board question and find the reply box + Send.
2. Type a draft; move to Evidence and back. Confirm draft and original review identity.
3. Simulate a new commit; leave current review **open**, start another Board Review and inspect the newer captured commit.
4. Open All your Board Reviews, return to the older review; its snapshot remains the older commit. In Evidence Room, verify the mismatch is explicit.
5. With an unsent reply, try finishing. It must not silently discard your work. Clear it intentionally, finish, and confirm read-only history remains available.
6. Reopen the newer open session, then create 16 synthetic mixed reviews; access older records with Load older reviews.
7. Without committing again, start an additional review and identify the reused snapshot. Trigger `Fail next review start`; verify the earlier review and draft are recoverable.

**Release gate:** independently record a real Mac walkthrough, screen-reader result, and at least one uncoached student test. No Git commit/push/PR/Azure deployment is part of this package.
