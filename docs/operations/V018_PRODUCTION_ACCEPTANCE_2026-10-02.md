# v0.18.0 production acceptance — October 2, 2026

This record identifies the accepted deployment; it does not claim that subsequent documentation commits are already deployed or that a release tag has been published.

- Source: `6ba92bf7b4cb7acdb9228217ff243cd72172cb65`, merge of PR #134; CI passed.
- Protected deployment: [run 37081818322](https://github.com/etis-framework/etis-engineering-studio/actions/runs/37081818322), successful. Revalidation included production dependency audit, Bicep compilation, PostgreSQL migrations, production container build/smoke, backend tests and course-model validation.
- Application/resource group: `etis-studio-prod`; serving revision: `etis-studio-prod--0000102`.
- Maintainer-reported operator acceptance: all required checks PASS; cost telemetry PASS.
- Live `/health`: version `0.18.0`, production environment, semantic coaching ready, `reasoning_validation_mode=shadow`, `review_planning_mode=shadow`.
- Live `/ready`: ready, database connected, migration current; current/head revision `e81b6c2f4a90`.
- Maintainer reported all human-smoke checks passing: newly started review, frozen evidence/navigation, cited artifacts, action authorship and private drafts, keyboard dialogs and authorized read-only staff history.

An earlier same-source run [37080828880](https://github.com/etis-framework/etis-engineering-studio/actions/runs/37080828880) deployed legacy/legacy following incorrect continuation instructions. It was superseded by the explicit shadow/shadow deployment above. Do not treat that earlier legacy run as the intended current configuration.

Shadow enables internal analytical evaluation without transferring student-visible authority from the legacy engine. Workflow/application defaults remain legacy; explicitly select both shadow inputs for the accepted production configuration. Existing sessions keep their locked modes, including any reviews started during the intervening legacy deployment. Do not mutate those historical sessions; start a new review when the current configuration is required.

The Review Room / Engineering Evidence UX is frozen after this acceptance. Release publication remains pending and must reference the exact accepted source. Documentation corrections, security-alert graph reconciliation and any subsequent deployment need their own provenance; no retrospective rewriting of earlier acceptance records is authorized.
