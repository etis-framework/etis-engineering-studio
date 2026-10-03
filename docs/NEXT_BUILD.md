# Next Build and Maintenance Backlog

**Revalidated for the v0.18.0 source candidate at main `7cc5beca327966652c1b5ef7eb3af2aff5841f7e`.** Production changes require observed defects, security/course needs or deliberately scheduled enhancements. The accepted Review Room / Engineering Evidence UX is frozen; release documentation and acceptance are the immediate work.

## Completed in current source

- Bicep scaling defaults are 1/5; the August scale-to-zero drift is historical. Continue runtime drift checks after deployment.
- Finding lifecycle/recommendation handoff explicitly separates closure from reasoning, inspection and post-snapshot work.
- Find supporting evidence exposes bounded frozen equivalent-evidence discovery with draft preservation and cross-snapshot protection.
- Two-room navigation, context disclosure, concern presentation, action authorship and keyboard dialog focus are implemented through PR #132.
- Development pytest security pin is 9.0.3 through PR #133; PyJWT is pinned 2.15.1 in production and the included development dependency graph.

## Immediate release gates

1. Validate the v0.18.0 version/documentation patch and all 12 paired manuals; require rendered page QA and green local/CI checks.
2. Deploy merged source through the protected workflow with legacy/legacy defaults, run operator acceptance and human smoke, then tag/publish with verified date/SHA.
3. Requery dependency alerts against the refreshed main graph. Do not dismiss stale-looking PyJWT alerts without verifying graph/ranges; retain unresolved alerts accurately.

## Revalidate before implementation

- **Analytical authority transfer (PR5):** deferred. Legacy accumulated reasoning is monotonic; contradiction/reopen handling and phase-grounded context warrant independent adversarial evaluation before any change. Shadow validator/planner evidence does not authorize transfer or promise a better student experience.
- **A3–A6 depth:** existing contracts and offline cases cover all phases; any additional reviewer content needs concrete phase-specific gaps and live/fixture evidence. Strong repositories should receive useful tradeoff challenges; weak evidence must not invite fabricated certainty.
- **Staff onboarding audit/diagnostics:** inspect existing instructor surfaces/endpoints before designing richer owner/installation/scope/last-verification views; expose no secrets and preserve role boundaries.
- **Multiple live students:** automated owner/non-owner propagation is not equivalent to live multi-student acceptance. Schedule only when appropriate authorized identities exist.
- **Accessibility beyond dialogs:** keyboard manager is complete for four dialog families; full screen-reader, zoom, contrast and broader workflow assessment remain separately scoped. Do not relabel the keyboard patch as whole-product accessibility certification.
- **Intermittent latency:** capture browser/request/provider timings if it recurs; the earlier 15–25 second observation was non-reproducible. No speculative latency rewrite.
- **Research/export:** requires an explicit privacy/data-governance decision and a defined use case before implementation.

## Change discipline

Branch → focused tests and adversarial cases → existing war games and complete pytest → PR → CI → merge → protected deployment → live acceptance. Preserve frozen evidence, provenance, closure authority, action authorship, private drafts, human decisions and grading boundaries. Prefer a clear next action over another dashboard or control.
