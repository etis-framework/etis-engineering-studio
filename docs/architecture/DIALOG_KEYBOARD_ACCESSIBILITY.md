# Dialog keyboard accessibility

The Help, frozen artifact, finding challenge, and review-exit dialogs share a narrow keyboard manager in the production `studio.js`.

- Opening moves focus inside the dialog. Tab and Shift+Tab remain within visible, enabled controls.
- Background body children become inert while a dialog is open; prior inert values are restored. Nested dialogs preserve focus order.
- Escape invokes the existing close button, preserving lifecycle-owned behavior. Closing a pending challenge does not cancel its request. Escape during IME composition is ignored.
- Closing restores a usable opener or an available Review Room control. Delayed challenge focus cannot steal focus after closure.
- No evidence, finding lifecycle, reasoning authority, grade, prompt authorship, or draft content changes are introduced.

Validation: `python -m pytest -q tests/test_dialog_keyboard_accessibility.py tests/test_challenge_modes.py tests/test_challenge_progress.py`; `node tests/dialog_keyboard_wargame.cjs`; `node tests/review_journey_wargame.cjs`; complete pytest suite. The dependency-free DOM harness evaluates keyboard behavior, not live semantic reviewer quality. Optional real-browser validation: `node tests/dialog_keyboard_browser_wargame.cjs` (Playwright and Chromium required).

Production smoke: use Tab/Shift+Tab and Escape in each dialog, confirm focus returns to the opener, confirm finish is never triggered by Escape, and confirm a submitted challenge continues after closing. Check an unsent composer draft survives inspection/help/challenge dismissal.
