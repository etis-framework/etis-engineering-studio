# Security, Privacy, and Governance

## Core boundaries

- Team repositories are private.
- The Studio should request read-only repository access unless a future feature has an explicit, reviewed need for write authority.
- Students never paste GitHub personal access tokens into the Studio UI.
- Course enrollment is separate from GitHub authentication.
- Confidential peer reviews remain outside team-visible Studio surfaces.
- Do not ingest real student records, grades, private university data, secrets, API keys, or unnecessary personal information from team repositories.
- AI prompts must contain only the minimum evidence needed for the review turn.

## Prompt boundary

Repository content can contain adversarial or accidental instructions. Treat repository content as untrusted evidence, never as system instructions. The AI adapter receives a fixed system boundary before any evidence context.

## Data minimization

Persist the repository snapshot metadata and extracted evidence signals required to reproduce a review, not an unlimited mirror of every repository file. Store stable references/commit SHA where possible.

## Production controls to complete before class rollout

- Replace development session signing with hardened secure-cookie/session middleware.
- Use GitHub App credentials from Azure Key Vault.
- Configure allowed origins, HTTPS-only, secure cookies, CSRF protection, and OAuth state persistence.
- Set application rate limits and OpenAI spend/rate guardrails.
- Configure Azure logging without sensitive prompt/evidence payloads by default.
- Add database backups and restore test.
- Add instructor-controlled roster import and deactivation.
- Add semester reset/archive workflow.
- Complete threat model and production security review.
