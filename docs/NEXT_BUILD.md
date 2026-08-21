# Next Build / Maintenance Backlog

> **Status:** Production is accepted and should remain frozen unless an actual defect, security issue, required course change, or deliberately scheduled enhancement justifies a new release.

The following items are **not** release blockers for the accepted 2026-08-21 production baseline.

## Priority maintenance

1. **Reconcile Container App scaling in IaC.** The accepted production runtime is `minReplicas=1`, `maxReplicas=5`, but `infra/azure/app.bicep` still defaults `minReplicas` to `0`. Make this a separate infrastructure change with CI/Bicep validation and production acceptance.
2. **Align application version metadata.** `/health` still reports `0.15.0` even though production-integration hardening followed the original v0.15 release.
3. **Monitor intermittent reload latency.** The previously observed 15–25 second load became non-reproducible. Capture the browser Network waterfall and request timing if it returns before changing code.

## Deferred product enhancements

- richer repository-onboarding audit history in the instructor UI;
- instructor GitHub diagnostics (owner, installation, scope, last verification) without exposing secrets;
- additional multi-student live acceptance scenarios when appropriate test identities exist;
- dedicated accessibility/keyboard/screen-reader pass;
- A3-A6 deep phase-specific reviewer content as those assignments approach;
- research/export tooling only after explicit privacy/data-governance review.

## Change discipline

Do not reopen production simply for polish. Use the normal branch → local validation → PR → CI → protected deployment → targeted production acceptance sequence for future changes.
