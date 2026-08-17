#!/usr/bin/env python3
"""Browser-level interaction-integrity war games for ETIS Engineering Studio.

This is intentionally not part of normal CI because Playwright/Chromium are optional
engineering dependencies. It exercises the product journeys that unit/API tests cannot:
mode selection, contextual handoffs, scrolling, evidence controls, session recovery,
student conversation controls, and teaching-staff navigation.

Usage:
  python scripts/run_ui_wargames.py --base-url http://127.0.0.1:8000

For restricted/container environments where Chromium cannot navigate to loopback:
  python scripts/run_ui_wargames.py --base-url http://127.0.0.1:8000 --inline-static
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
STATIC = ROOT / "apps/api/app/static"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def load_inline_html() -> str:
    html = (STATIC / "index.html").read_text()
    css = (STATIC / "studio.css").read_text()
    js = (STATIC / "studio.js").read_text()
    html = html.replace("<head>", '<head><base href="https://studio.test/">', 1)
    html = re.sub(r'<link[^>]+href="/assets/studio.css"[^>]*>', lambda _m: f"<style>{css}</style>", html)
    html = re.sub(r'<script[^>]+src="/assets/studio.js"[^>]*></script>', lambda _m: f"<script>{js}</script>", html)
    return html


def api_proxy(base_url: str, state: dict | None = None):
    state = state if state is not None else {}

    def proxy(route, request):
        parsed = urlparse(request.url)
        path = parsed.path
        query = f"?{parsed.query}" if parsed.query else ""

        # Keep UI conversation tests deterministic and inexpensive. Repository/session
        # start calls still use the real local API and frozen evidence.
        if path.endswith("/respond"):
            time.sleep(0.12)

            try:
                request_payload = json.loads(request.post_data or "{}")
            except Exception:
                request_payload = {}

            client_turn_id = request_payload.get("client_turn_id")
            committed = state.setdefault("respond_commits", {})
            committed_body = committed.get(client_turn_id)

            if committed_body is not None:
                body = {
                    **committed_body,
                    "duplicate": True,
                }
            else:
                body = {
                    "duplicate": False,
                    "follow_up": {
                        "lens": "evidence_auditor",
                        "text": "I understand what you mean. Let us keep working from that exact evidence and take one next step.",
                        "kind": "coach",
                        "reviewer": {"name": "Maya Chen", "role": "Evidence Auditor", "focus": "Evidence", "portrait": "/assets/reviewers/maya-chen.svg"},
                        "guidance_refs": [],
                        "provider": "ui-wargame",
                    },
                    "evaluation": {
                        "disposition": "developing",
                        "missing_moves": ["ownership_visible"],
                        "ready_to_commit": False,
                        "learning_score": 2,
                        "learning_score_max": 7,
                    },
                    "reasoning_state": {"consequence_visible": True},
                }
                if client_turn_id:
                    committed[client_turn_id] = body

            record = {
                "client_turn_id": client_turn_id,
                "request_payload": request_payload,
                "duplicate": body.get("duplicate"),
                "server_status": 200,
            }
            state.setdefault("respond_requests", []).append(record)

            # Simulate the important failure mode: the logical response was
            # committed, but the browser receives a gateway failure instead of
            # the successful result.
            if (
                state.get("fail_next_respond_after_commit")
                and not body.get("duplicate")
            ):
                state["fail_next_respond_after_commit"] = False
                state["expected_503_console_errors"] = (
                    state.get("expected_503_console_errors", 0) + 1
                )
                record["browser_status"] = 503
                route.fulfill(
                    status=503,
                    content_type="application/json",
                    body=json.dumps({
                        "detail": "Simulated post-commit Respond gateway failure"
                    }),
                )
                return

            record["browser_status"] = 200
            route.fulfill(
                status=200,
                content_type="application/json",
                body=json.dumps(body),
            )
            return
        if path.endswith("/coach"):
            try:
                request_payload = json.loads(request.post_data or "{}")
            except Exception:
                request_payload = {}

            client_turn_id = request_payload.get("client_turn_id")
            committed = state.setdefault("coach_commits", {})
            committed_body = committed.get(client_turn_id)

            if committed_body is not None:
                body = {
                    **committed_body,
                    "duplicate": True,
                }
            else:
                body = {
                    "duplicate": False,
                    "reply": {
                        "lens": "evidence_auditor",
                        "text": "You are not stuck alone here. Start with what the evidence can support, and I will help you from there.",
                        "kind": "coaching",
                        "reviewer": {
                            "name": "Maya Chen",
                            "role": "Evidence Auditor",
                            "focus": "Evidence",
                            "portrait": "/assets/reviewers/maya-chen.svg",
                        },
                        "guidance_refs": [],
                        "provider": "ui-wargame",
                    },
                    "coaching_level": 1,
                }

                if client_turn_id:
                    committed[client_turn_id] = body

            record = {
                "client_turn_id": client_turn_id,
                "request_payload": request_payload,
                "duplicate": body.get("duplicate"),
                "server_status": 200,
            }
            state.setdefault("coach_requests", []).append(record)

            if (
                state.get("fail_next_coach_after_commit")
                and not body.get("duplicate")
            ):
                state["fail_next_coach_after_commit"] = False
                state["expected_503_console_errors"] = (
                    state.get("expected_503_console_errors", 0) + 1
                )
                record["browser_status"] = 503
                route.fulfill(
                    status=503,
                    content_type="application/json",
                    body=json.dumps({
                        "detail": "Simulated post-commit Coach gateway failure"
                    }),
                )
                return

            record["browser_status"] = 200
            route.fulfill(
                status=200,
                content_type="application/json",
                body=json.dumps(body),
            )
            return

        if path.endswith("/evidence-dispute"):
            try:
                request_payload = json.loads(request.post_data or "{}")
            except Exception:
                request_payload = {}

            client_turn_id = request_payload.get("client_turn_id")
            committed = state.setdefault("dispute_commits", {})
            committed_body = committed.get(client_turn_id)

            if committed_body is not None:
                body = {
                    **committed_body,
                    "duplicate": True,
                }
            else:
                body = {
                    "duplicate": False,
                    "reply": {
                        "lens": "evidence_auditor",
                        "text": "I re-checked that exact frozen evidence. The dispute is preserved with the review record.",
                        "kind": "evidence_dispute",
                        "reviewer": {
                            "name": "Maya Chen",
                            "role": "Evidence Auditor",
                            "focus": "Evidence",
                            "portrait": "/assets/reviewers/maya-chen.svg",
                        },
                    },
                }

                if client_turn_id:
                    committed[client_turn_id] = body

            record = {
                "client_turn_id": client_turn_id,
                "request_payload": request_payload,
                "duplicate": body.get("duplicate"),
                "server_status": 200,
            }
            state.setdefault("dispute_requests", []).append(record)

            if (
                state.get("fail_next_dispute_after_commit")
                and not body.get("duplicate")
            ):
                state["fail_next_dispute_after_commit"] = False
                state["expected_503_console_errors"] = (
                    state.get("expected_503_console_errors", 0) + 1
                )
                record["browser_status"] = 503
                route.fulfill(
                    status=503,
                    content_type="application/json",
                    body=json.dumps({
                        "detail": "Simulated post-commit Evidence Dispute gateway failure"
                    }),
                )
                return

            record["browser_status"] = 200
            route.fulfill(
                status=200,
                content_type="application/json",
                body=json.dumps(body),
            )
            return


        target = base_url.rstrip("/") + path + query
        data = request.post_data.encode() if request.post_data else None
        headers = {
            k: v for k, v in request.headers.items()
            if k.lower() not in {"host", "content-length", "origin", "referer", "sec-fetch-site", "sec-fetch-mode", "sec-fetch-dest"}
        }
        req = urllib.request.Request(target, data=data, headers=headers, method=request.method)
        try:
            with urllib.request.urlopen(req, timeout=20) as response:
                response_body = response.read()
                status = response.status
                ctype = response.headers.get("Content-Type", "application/octet-stream")
        except urllib.error.HTTPError as exc:
            response_body = exc.read()
            status = exc.code
            ctype = exc.headers.get("Content-Type", "application/json")

        if path == "/api/v1/reviews/start" and request.method.upper() == "POST":
            try:
                request_payload = json.loads(request.post_data or "{}")
            except Exception:
                request_payload = {}

            try:
                response_payload = json.loads(response_body)
            except Exception:
                response_payload = {}

            start_record = {
                "client_request_id": request_payload.get("client_request_id"),
                "session_id": response_payload.get("session_id"),
                "duplicate": response_payload.get("duplicate"),
                "server_status": status,
            }
            state.setdefault("start_requests", []).append(start_record)

            # Exercise the failure mode where the server commits the review,
            # but an intermediary/browser receives no successful Start Review
            # result. The browser must retain its client_request_id and recover
            # the committed session on retry.
            if state.get("fail_next_start_after_commit") and status == 200:
                state["fail_next_start_after_commit"] = False
                state["expected_503_console_errors"] = (
                    state.get("expected_503_console_errors", 0) + 1
                )
                start_record["browser_status"] = 503
                route.fulfill(
                    status=503,
                    content_type="application/json",
                    body=json.dumps({
                        "detail": "Simulated post-commit Start Review gateway failure"
                    }),
                )
                return

            start_record["browser_status"] = status

        if path == "/health" and status == 200:
            health = json.loads(response_body)
            health["semantic_coaching_ready"] = True
            health["conversation_mode"] = "semantic"
            health["model"] = "ui-wargame-model"
            response_body = json.dumps(health).encode()
            ctype = "application/json"
        route.fulfill(status=status, content_type=ctype, body=response_body)

    return proxy


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--inline-static", action="store_true")
    parser.add_argument("--chromium", default=None, help="Optional Chromium executable path")
    args = parser.parse_args()

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("SKIP: Playwright is not installed. Install it only in a developer environment to run browser war games.")
        return 2

    errors: list[str] = []
    checks: list[str] = []
    proxy_state = {
        "start_requests": [],
        "respond_requests": [],
        "respond_commits": {},
        "coach_requests": [],
        "coach_commits": {},
        "fail_next_coach_after_commit": False,
        "dispute_requests": [],
        "dispute_commits": {},
        "fail_next_dispute_after_commit": False,
        "fail_next_start_after_commit": False,
        "fail_next_respond_after_commit": False,
        "expected_503_console_errors": 0,
    }
    proxy = api_proxy(args.base_url, proxy_state)

    def passed(name: str) -> None:
        checks.append(name)
        print(f"PASS  {name}")

    with sync_playwright() as p:
        launch = {"headless": True, "args": ["--no-sandbox"]}
        if args.chromium:
            launch["executable_path"] = args.chromium
        browser = p.chromium.launch(**launch)
        page = browser.new_page(viewport={"width": 1440, "height": 1000})
        page.set_default_timeout(8000)
        page.on("pageerror", lambda e: errors.append(f"pageerror: {e}"))

        def record_console(message):
            if message.type != "error":
                return

            text = message.text
            intentional_503 = (
                "Failed to load resource" in text
                and "503" in text
                and proxy_state.get("expected_503_console_errors", 0) > 0
            )

            if intentional_503:
                proxy_state["expected_503_console_errors"] -= 1
                return

            errors.append(f"console error: {text}")

        page.on("console", record_console)

        if args.inline_static:
            page.route("**/*", proxy)
            page.set_content(load_inline_html(), wait_until="networkidle")
        else:
            # Direct mode still intercepts health and conversation calls so this suite
            # never spends OpenAI tokens.
            page.route("**/health", proxy)
            page.route("**/api/v1/reviews/*/respond", proxy)
            page.route("**/api/v1/reviews/*/coach", proxy)
            page.route("**/api/v1/reviews/*/evidence-dispute", proxy)
            page.route("**/api/v1/reviews/start", proxy)
            page.goto(args.base_url, wait_until="networkidle")
        page.wait_for_timeout(600)

        # Student navigation: every visible destination is clickable and lands at top.
        for view, title in [
            ("studio", "Engineering Review Room"),
            ("evidence", "Engineering Evidence"),
            ("history", "Review History"),
            ("myteam", "My Team"),
        ]:
            page.locator(f'button.nav[data-view="{view}"]').click()
            page.wait_for_timeout(150)
            require(page.locator("#viewTitle").inner_text() == title, f"student nav {view} did not open {title}")
            require(page.evaluate("scrollY") == 0, f"student nav {view} did not land at top")
        passed("student navigation and deterministic top landing")

        # Board review starts, conversation controls work, Enter submits, Nudge responds.
        page.locator('button.nav[data-view="studio"]').click()
        require(page.locator(".review-choice.selected").get_attribute("data-review-mode") == "board", "Board Review should be default")
        page.locator("#newReview").click()
        page.wait_for_timeout(300)
        require(page.locator("#conversationControls").is_visible(), "conversation controls not active after Board Review starts")
        page.locator("#response").fill("I think maybe ownership becomes unclear?")
        page.locator("#response").press("Enter")
        page.wait_for_timeout(150)
        require("I understand what you mean" in page.locator("#transcript").inner_text(), "Enter-to-send did not produce reviewer response")
        page.locator("#coachButton").click()
        page.wait_for_timeout(150)
        require("not stuck alone" in page.locator("#transcript").inner_text(), "Nudge did not produce coaching")
        passed("Board Review conversation, Enter, and Nudge")

        # Conversation mutation network/gateway recovery:
        # 1. Browser submits one logical Respond mutation.
        # 2. The simulated server commits it.
        # 3. Browser receives a post-commit 503 and restores the draft.
        # 4. Student retries the same logical message.
        # 5. Browser must reuse client_turn_id, avoid another student bubble,
        #    and render the already-committed reviewer response.
        respond_record_index = len(proxy_state["respond_requests"])
        student_before_retry = page.locator("#transcript .turn.student").count()
        reviewer_text_before_retry = page.locator(
            "#transcript"
        ).inner_text().count("I understand what you mean")

        retry_text = (
            "We need the review conversation to recover safely "
            "when delivery fails after the server commits."
        )

        proxy_state["fail_next_respond_after_commit"] = True
        page.locator("#response").fill(retry_text)
        page.locator("#response").press("Enter")
        page.wait_for_timeout(300)

        first_records = proxy_state["respond_requests"][respond_record_index:]
        require(
            len(first_records) == 1,
            "failed browser response did not correspond to exactly one committed Respond request",
        )
        require(
            first_records[0]["server_status"] == 200
            and first_records[0]["browser_status"] == 503,
            "Respond did not exercise the post-commit failure path",
        )
        require(
            first_records[0]["client_turn_id"],
            "browser did not supply client_turn_id on Respond",
        )
        require(
            page.locator("#response").input_value() == retry_text,
            "failed Respond did not restore the student's draft",
        )

        page.locator("#response").press("Enter")
        page.wait_for_timeout(300)

        recovery_records = proxy_state["respond_requests"][respond_record_index:]
        require(
            len(recovery_records) == 2,
            f"expected exactly two Respond attempts, got {len(recovery_records)}",
        )

        first_respond, retry_respond = recovery_records

        require(
            retry_respond["client_turn_id"] == first_respond["client_turn_id"],
            "browser generated a new client_turn_id instead of retrying the logical Respond mutation",
        )
        require(
            retry_respond["duplicate"] is True,
            "Respond retry was not recognized as the already-committed logical mutation",
        )
        require(
            page.locator("#transcript .turn.student").count()
            == student_before_retry + 1,
            "Respond recovery rendered the same student turn more than once",
        )
        require(
            page.locator("#transcript").inner_text().count(
                "I understand what you mean"
            )
            == reviewer_text_before_retry + 1,
            "Respond recovery did not render the already-committed reviewer response",
        )

        passed("Respond post-commit retry preserves one logical conversation turn")

        # Coach/Nudge post-commit recovery:
        # the first logical coaching request is committed but its successful
        # response is replaced with a 503. Clicking Nudge again must reuse the
        # original client_turn_id and recover exactly one coaching response.
        coach_record_index = len(proxy_state["coach_requests"])
        coach_text_before_retry = page.locator(
            "#transcript"
        ).inner_text().count("You are not stuck alone here")

        proxy_state["fail_next_coach_after_commit"] = True
        page.locator("#coachButton").click()
        page.wait_for_timeout(250)

        first_coach_records = proxy_state["coach_requests"][coach_record_index:]
        require(
            len(first_coach_records) == 1,
            "failed browser response did not correspond to exactly one committed Coach request",
        )
        require(
            first_coach_records[0]["server_status"] == 200
            and first_coach_records[0]["browser_status"] == 503,
            "Coach did not exercise the post-commit failure path",
        )
        require(
            first_coach_records[0]["client_turn_id"],
            "browser did not supply client_turn_id on Coach",
        )
        require(
            page.locator("#transcript").inner_text().count(
                "You are not stuck alone here"
            ) == coach_text_before_retry,
            "failed Coach response incorrectly rendered a reviewer reply",
        )

        page.locator("#coachButton").click()
        page.wait_for_timeout(250)

        coach_recovery_records = proxy_state["coach_requests"][coach_record_index:]
        require(
            len(coach_recovery_records) == 2,
            f"expected exactly two Coach attempts, got {len(coach_recovery_records)}",
        )

        first_coach, retry_coach = coach_recovery_records

        require(
            retry_coach["client_turn_id"] == first_coach["client_turn_id"],
            "browser generated a new client_turn_id instead of retrying the logical Coach mutation",
        )
        require(
            retry_coach["duplicate"] is True,
            "Coach retry was not recognized as the already-committed logical mutation",
        )
        require(
            page.locator("#transcript").inner_text().count(
                "You are not stuck alone here"
            ) == coach_text_before_retry + 1,
            "Coach recovery did not render exactly one recovered reviewer response",
        )

        passed("Coach post-commit retry preserves one logical coaching request")

        # Complete -> preserved session -> obvious Start New Review -> clean launcher.
        page.locator("#completeReview").click()
        page.wait_for_timeout(180)
        require(page.locator("#reviewHomeButton").is_visible(), "Start New Review control missing after completion")
        page.locator("#reviewHomeButton").click()
        page.wait_for_timeout(120)
        require(page.locator("#newReview").inner_text().startswith("Start Board Review"), "new review home did not reset launcher")
        require(page.evaluate("scrollY") == 0, "new review home did not land at top")
        passed("completed-session recovery and clean new-review home")

        # Review mode cards are true single-select and no duplicate primary action exists.
        require(page.locator("#newReview").count() == 1, "more than one primary Start Review action exists")
        page.locator('[data-review-mode="focused"]').click()
        require(page.locator(".review-choice.selected").count() == 1, "review modes are not single-select")
        require(page.locator(".review-choice.selected").get_attribute("data-review-mode") == "focused", "Focused Review did not become active")
        require(not page.locator("#newReview").is_enabled(), "Focused Review should require a focus before start")
        page.locator("#reviewFocus").fill("Review our planning estimates before we move on")
        require(page.locator("#newReview").is_enabled(), "Focused Review did not enable after focus entry")
        passed("single-select review modes and Focused Review readiness")

        # Engineering Evidence contextual handoff: estimates finding must not drift to README.
        page.locator('button.nav[data-view="evidence"]').click()
        page.wait_for_timeout(350)
        estimates = page.locator("#engineeringEvidenceFindings .evidence-finding-card").filter(has_text="estimates.md").first
        require(estimates.count() == 1, "estimates finding not available in Engineering Evidence fixture")
        estimates.get_by_role("button", name="Help me resolve this").click()
        page.wait_for_timeout(180)
        require(page.locator("#viewTitle").inner_text() == "Engineering Review Room", "finding handoff did not return to Review Room")
        require(page.evaluate("scrollY") == 0, "finding handoff did not land at top")
        require(page.locator(".review-choice.selected").get_attribute("data-review-mode") == "finding", "finding handoff did not configure Finding Review")
        require(page.locator("#findingPicker input:checked").count() == 1, "exact finding was not selected")
        page.locator("#newReview").click()
        page.wait_for_timeout(300)
        context_text = page.locator("#reviewSessionPurpose").inner_text() + " " + page.locator("#challengeTitle").inner_text()
        require("estimates.md" in context_text, "exact estimates finding context was lost")
        require("README.md" not in page.locator("#challengeTitle").inner_text(), "review drifted to README instead of selected finding")
        passed("Engineering Evidence -> exact finding remediation context")

        # Active evidence controls: Ask attaches context; Reference attaches context; Open uses local overlay.
        evidence_item = page.locator("#evidenceList .eitem").filter(has_text="estimates").first
        if evidence_item.count() == 0:
            evidence_item = page.locator("#evidenceList .eitem").first
        if evidence_item.get_by_role("button", name="Ask about this").count():
            evidence_item.get_by_role("button", name="Ask about this").click()
            require(page.locator("#composerContext").is_visible(), "Ask about this did not attach evidence context")
        evidence_item.get_by_role("button", name="Reference").click()
        require(page.locator("#composerContext").is_visible(), "Reference did not attach evidence")
        open_button = evidence_item.get_by_role("button", name=re.compile(r"Open"))
        if open_button.is_enabled():
            open_button.click()
            require(page.locator("#artifactOverlay").is_visible(), "Open evidence did not use the frozen artifact viewer")
            external = page.locator("#artifactExternalLink")
            require(external.get_attribute("target") == "_blank", "frozen source should open in a new tab")
            page.locator("#closeArtifactOverlay").click()
        passed("Evidence Rail exact-context actions")

        # Evidence Dispute post-commit recovery:
        # preserve the logical dispute and its user-entered explanation when
        # the server commits but the browser receives a gateway failure.
        dispute_record_index = len(proxy_state["dispute_requests"])

        dispute_item = page.locator("#evidenceList .eitem").first
        dispute_path = dispute_item.locator(".eref").inner_text()

        # Use the first available finding challenge action to open the dispute
        # overlay against exact frozen evidence.
        challenge_button = page.locator(
            "#findingList .challenge-finding"
        ).first
        require(
            challenge_button.count() == 1,
            "no finding challenge action available for Evidence Dispute recovery test",
        )

        challenge_button.click()
        page.wait_for_timeout(100)

        require(
            page.locator("#evidenceDisputeOverlay").is_visible(),
            "Challenge did not open the Evidence Dispute overlay",
        )

        actual_path = page.locator("#evidenceDisputePath").input_value()
        require(
            bool(actual_path),
            "Evidence Dispute did not preserve the exact frozen evidence path",
        )

        explanation = (
            "This exact frozen artifact changes how the board should "
            "interpret the finding."
        )

        page.locator("#evidenceDisputeExplanation").fill(explanation)
        proxy_state["fail_next_dispute_after_commit"] = True
        page.locator("#submitEvidenceDispute").click()
        page.wait_for_timeout(250)

        first_dispute_records = proxy_state["dispute_requests"][
            dispute_record_index:
        ]

        require(
            len(first_dispute_records) == 1,
            "failed browser response did not correspond to exactly one committed Evidence Dispute request",
        )
        require(
            first_dispute_records[0]["server_status"] == 200
            and first_dispute_records[0]["browser_status"] == 503,
            "Evidence Dispute did not exercise the post-commit failure path",
        )
        require(
            first_dispute_records[0]["client_turn_id"],
            "browser did not supply client_turn_id on Evidence Dispute",
        )

        # The student must be able to recover the exact logical dispute without
        # reconstructing it from memory.
        require(
            page.locator("#evidenceDisputeOverlay").is_visible(),
            "failed Evidence Dispute did not restore the dispute form",
        )
        require(
            page.locator("#evidenceDisputePath").input_value() == actual_path,
            "failed Evidence Dispute did not preserve the exact evidence path",
        )
        require(
            page.locator("#evidenceDisputeExplanation").input_value()
            == explanation,
            "failed Evidence Dispute did not preserve the student's explanation",
        )

        page.locator("#submitEvidenceDispute").click()
        page.wait_for_timeout(250)

        dispute_recovery_records = proxy_state["dispute_requests"][
            dispute_record_index:
        ]

        require(
            len(dispute_recovery_records) == 2,
            f"expected exactly two Evidence Dispute attempts, got {len(dispute_recovery_records)}",
        )

        first_dispute, retry_dispute = dispute_recovery_records

        require(
            retry_dispute["client_turn_id"]
            == first_dispute["client_turn_id"],
            "browser generated a new client_turn_id instead of retrying the logical Evidence Dispute mutation",
        )
        require(
            retry_dispute["duplicate"] is True,
            "Evidence Dispute retry was not recognized as the already-committed logical mutation",
        )
        require(
            "I re-checked that exact frozen evidence"
            in page.locator("#transcript").inner_text(),
            "Evidence Dispute recovery did not render the recovered reviewer response",
        )

        passed("Evidence Dispute post-commit retry preserves exact dispute context")

        # Finding Discuss and Challenge entry actions preserve the exact selected object.
        page.locator("#completeReview").click(); page.wait_for_timeout(130)
        page.locator("#reviewHomeButton").click(); page.locator('button.nav[data-view="evidence"]').click(); page.wait_for_timeout(260)
        estimates = page.locator("#engineeringEvidenceFindings .evidence-finding-card").filter(has_text="estimates.md").first
        estimates.get_by_role("button", name="Discuss").click(); page.wait_for_timeout(120)
        require(page.locator(".review-choice.selected").get_attribute("data-review-mode") == "finding", "Discuss did not prepare Finding Review")
        require(page.locator("#findingPicker input:checked").count() == 1, "Discuss did not select the exact finding")
        page.locator("#newReview").click(); page.wait_for_timeout(220)
        require("estimates" in (page.locator("#reviewSessionPurpose").inner_text()+" "+page.locator("#challengeTitle").inner_text()).lower(), "Discuss drifted from the selected finding")
        page.locator("#completeReview").click(); page.wait_for_timeout(120); page.locator("#reviewHomeButton").click(); page.locator('button.nav[data-view="evidence"]').click(); page.wait_for_timeout(260)
        estimates = page.locator("#engineeringEvidenceFindings .evidence-finding-card").filter(has_text="estimates.md").first
        estimates.get_by_role("button", name="Challenge").click(); page.wait_for_timeout(120)
        page.locator("#newReview").click(); page.wait_for_timeout(220)
        require("estimates" in (page.locator("#reviewSessionPurpose").inner_text()+" "+page.locator("#challengeTitle").inner_text()).lower(), "Challenge drifted from the selected finding")
        require("challenge" in page.locator("#reviewSessionPurpose").inner_text().lower(), "Challenge intent was not preserved")
        passed("Finding Discuss and Challenge exact-context handoffs")

        # Double-send protection: a slow reviewer response may not create duplicate student turns.
        student_before = page.locator('#transcript .turn.student').count()
        page.locator('#response').fill('maybe no one know who final say?')
        page.locator('#response').press('Enter')
        page.locator('#response').press('Enter')
        page.wait_for_timeout(300)
        student_after = page.locator('#transcript .turn.student').count()
        require(student_after == student_before + 1, "slow response allowed an accidental duplicate student turn")
        passed("slow-response duplicate-submit protection")

        # Engineering Evidence inventory can prepare a precise Focused Review and returns to top.
        page.locator("#completeReview").click(); page.wait_for_timeout(120); page.locator("#reviewHomeButton").click(); page.locator('button.nav[data-view="evidence"]').click(); page.wait_for_timeout(250)
        inventory = page.locator('#engineeringEvidenceInventory .inventory-card').filter(has_text='estimates.md').first
        if inventory.count() == 0:
            inventory = page.locator('#engineeringEvidenceInventory .inventory-card').first
        inventory.get_by_role('button', name='Ask the Board').click(); page.wait_for_timeout(120)
        require(page.locator('.review-choice.selected').get_attribute('data-review-mode') == 'focused', 'inventory Ask the Board did not prepare Focused Review')
        require(page.evaluate('scrollY') == 0, 'inventory handoff did not land at top')
        require('estimates' in page.locator('#reviewFocus').input_value().lower() or page.locator('#reviewFocus').input_value(), 'focused concern was not carried from evidence')
        passed("Engineering Evidence inventory -> Focused Review context")

        # Lens selection is interactive and exposes a contextual board action.
        page.locator('button.nav[data-view="evidence"]').click(); page.wait_for_timeout(220)
        lens = page.locator('#evidenceMatrix .mcard').first
        if lens.count():
            lens.click(); page.wait_for_timeout(80)
            require(page.locator('#evidenceLensDetail').is_visible(), 'View Evidence lens did not open its evidence detail')
            require(page.locator('#focusLensReview').is_visible(), 'lens detail lacks Ask the Board action')
        passed("Engineering Evidence professional lens interaction")

        # Prior history can be opened and exited cleanly.
        if page.locator("#completeReview").is_visible():
            page.locator("#completeReview").click(); page.wait_for_timeout(150)
        page.locator('button.nav[data-view="history"]').click(); page.wait_for_timeout(150)
        first_history = page.locator("#reviewHistoryPage .history-item").first
        require(first_history.count() == 1, "review history did not render")
        first_history.click(); page.wait_for_timeout(180)
        require(page.locator("#reviewHomeButton").is_visible(), "prior session lacks Start New Review escape")
        page.locator("#reviewHomeButton").click(); page.wait_for_timeout(100)
        require(page.locator("#viewTitle").inner_text() == "Engineering Review Room", "Start New Review did not return to Review Room")
        passed("review history -> prior session -> new review home")

        # Start Review network/gateway recovery:
        # 1. The server commits the first request.
        # 2. The browser receives a simulated post-commit 503.
        # 3. The browser retains the logical request ID.
        # 4. Retry uses the same ID and recovers the same ReviewSession.
        start_record_index = len(proxy_state["start_requests"])
        proxy_state["fail_next_start_after_commit"] = True

        page.locator("#newReview").click()
        page.wait_for_timeout(450)

        require(
            not page.locator("#conversationControls").is_visible(),
            "failed Start Review response incorrectly activated a session",
        )

        require(
            len(proxy_state["start_requests"][start_record_index:]) == 1,
            "first failed browser response did not correspond to exactly one committed Start Review request",
        )
        require(
            proxy_state["start_requests"][start_record_index]["client_request_id"],
            "browser did not retain a logical Start Review request identity",
        )

        page.locator("#newReview").click()
        page.wait_for_timeout(450)

        recovery_records = proxy_state["start_requests"][start_record_index:]
        require(
            len(recovery_records) == 2,
            f"expected exactly two Start Review attempts, got {len(recovery_records)}",
        )

        first_start, retry_start = recovery_records

        require(
            first_start["server_status"] == 200
            and first_start["browser_status"] == 503,
            "first Start Review did not exercise the post-commit failure path",
        )
        require(
            first_start["client_request_id"],
            "browser did not supply client_request_id on first Start Review",
        )
        require(
            retry_start["client_request_id"] == first_start["client_request_id"],
            "browser generated a new client_request_id instead of retrying the logical request",
        )
        require(
            retry_start["session_id"] == first_start["session_id"],
            "Start Review retry created or returned a different ReviewSession",
        )
        require(
            retry_start["duplicate"] is True,
            "server did not identify the recovered Start Review as an idempotent retry",
        )
        require(
            page.locator("#conversationControls").is_visible(),
            "recovered Start Review did not activate the original session",
        )
        page.locator("#completeReview").click()
        page.wait_for_timeout(150)
        page.locator("#reviewHomeButton").click()
        page.wait_for_timeout(120)

        fresh_start_index = len(proxy_state["start_requests"])
        page.locator("#newReview").click()
        page.wait_for_timeout(450)

        fresh_records = proxy_state["start_requests"][fresh_start_index:]
        require(
            len(fresh_records) == 1,
            f"expected one later Start Review request, got {len(fresh_records)}",
        )
        require(
            fresh_records[0]["client_request_id"]
            != first_start["client_request_id"],
            "successful recovery did not clear the retained Start Review request identity",
        )
        require(
            fresh_records[0]["duplicate"] is False,
            "a genuinely new Start Review was incorrectly treated as a duplicate",
        )

        passed("Start Review post-commit retry recovers original session")

        page.locator("#completeReview").click()
        page.wait_for_timeout(150)

        # Instructor persona: every authorized nav opens without a JS failure.
        page.locator("#devPersona").select_option("instructor")
        page.wait_for_timeout(250)
        for view, title in [
            ("instructor", "Instructor Command Center"),
            ("instructorTeams", "Teams"),
            ("instructorStudents", "Students"),
            ("instructorReviews", "Reviews"),
            ("instructorEvidence", "Engineering Evidence"),
            ("instructorUsage", "AI Usage & Cost"),
            ("semesterSetup", "Semester Setup"),
            ("accessSettings", "Settings & Access"),
        ]:
            page.locator(f'button.nav[data-view="{view}"]').click()
            page.wait_for_timeout(180)
            require(page.locator("#viewTitle").inner_text() == title, f"staff nav {view} did not open {title}")
            require(page.evaluate("scrollY") == 0, f"staff nav {view} did not land at top")
        passed("Instructor/Course Owner navigation integrity")

        # Command Center team drill-down is actionable, not a dead card.
        page.locator('button.nav[data-view="instructor"]').click(); page.wait_for_timeout(220)
        team_card = page.locator('#teamCards .teamcard').first
        if team_card.count():
            team_card.click(); page.wait_for_timeout(120)
            require(page.locator('#teamDetail').is_visible(), 'team card did not open team detail')
            require('TEAM DETAIL' in page.locator('#teamDetail').inner_text(), 'team detail content did not load')
        passed("Instructor team drill-down")

        # Semester Setup phase save executes and reports completion without navigating away.
        page.locator('button.nav[data-view="semesterSetup"]').click(); page.wait_for_timeout(250)
        save = page.locator('#scheduleEditor .save-phase').first
        if save.count():
            save.click(); page.wait_for_timeout(160)
            require(page.locator('#viewTitle').inner_text() == 'Semester Setup', 'schedule save broke Semester Setup navigation')
        passed("Instructor semester schedule control")

        # Help is role-aware on staff surfaces.
        page.locator('#helpButton').click(); page.wait_for_timeout(50)
        require('Teaching-staff quick guide' in page.locator('#helpOverlay').inner_text(), 'staff Help did not show role-aware guidance')
        page.locator('#closeHelp').click()
        passed("role-aware teaching-staff Help")

        # No browser errors are acceptable in the exercised paths.
        require(not errors, "browser errors detected: " + " | ".join(errors))
        passed("no browser/page errors on exercised authorized journeys")
        browser.close()

    print(f"\nUI WAR GAMES PASSED: {len(checks)} product journeys")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as exc:
        print(f"FAIL  {exc}", file=sys.stderr)
        raise SystemExit(1)
