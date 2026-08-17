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


def api_proxy(base_url: str):
    def proxy(route, request):
        parsed = urlparse(request.url)
        path = parsed.path
        query = f"?{parsed.query}" if parsed.query else ""

        # Keep UI conversation tests deterministic and inexpensive. Repository/session
        # start calls still use the real local API and frozen evidence.
        if path.endswith("/respond"):
            time.sleep(0.12)
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
                "evaluation": {"disposition": "developing", "missing_moves": ["ownership_visible"], "ready_to_commit": False, "learning_score": 2, "learning_score_max": 7},
                "reasoning_state": {"consequence_visible": True},
            }
            route.fulfill(status=200, content_type="application/json", body=json.dumps(body))
            return
        if path.endswith("/coach"):
            body = {
                "reply": {
                    "lens": "evidence_auditor",
                    "text": "You are not stuck alone here. Start with what the evidence can support, and I will help you from there.",
                    "kind": "coaching",
                    "reviewer": {"name": "Maya Chen", "role": "Evidence Auditor", "focus": "Evidence", "portrait": "/assets/reviewers/maya-chen.svg"},
                    "guidance_refs": [],
                    "provider": "ui-wargame",
                },
                "coaching_level": 1,
            }
            route.fulfill(status=200, content_type="application/json", body=json.dumps(body))
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
        page.on("console", lambda m: errors.append(f"console error: {m.text}") if m.type == "error" else None)

        if args.inline_static:
            page.route("**/*", api_proxy(args.base_url))
            page.set_content(load_inline_html(), wait_until="networkidle")
        else:
            # Direct mode still intercepts health and conversation calls so this suite
            # never spends OpenAI tokens.
            page.route("**/health", api_proxy(args.base_url))
            page.route("**/api/v1/reviews/*/respond", api_proxy(args.base_url))
            page.route("**/api/v1/reviews/*/coach", api_proxy(args.base_url))
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
