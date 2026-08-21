# Institutional Adoption Guide

ETIS Engineering Studio is designed to be adopted and adapted by universities and other organizations that want students or engineers to practice evidence-based engineering judgment with bounded AI reviewers.

This guide separates **upstream software** from the **institution-owned deployment**. An institution should not reuse ETIS Framework production credentials, tenant identifiers, GitHub App registrations, domains, rosters, or secrets.

## 1. Decide what you are adopting

The current upstream implementation assumes:

- Python/FastAPI application runtime;
- PostgreSQL;
- Microsoft Entra for institutional authentication;
- GitHub plus a GitHub App for repository evidence access;
- OpenAI for semantic coaching/repository interpretation;
- Azure as the reference production cloud.

An institution can adopt the teaching/review model while replacing one or more providers, but those substitutions are engineering integrations, not configuration-only changes unless the upstream project explicitly supports them.

## 2. Establish institutional ownership

Create institution-owned resources for:

- cloud subscription/resource group;
- identity application registration/tenant configuration;
- GitHub organization or repository strategy;
- GitHub App and OAuth registration;
- domain/DNS/TLS;
- secret store and managed identity;
- PostgreSQL and backups;
- OpenAI project/API key/budget;
- monitoring/alerts and operations contacts.

Avoid deployments that depend on an individual faculty member's personal credentials for durable production operation.

## 3. Identity and authorization

The reference implementation uses Microsoft Entra for authentication and database-backed course authorization. Authentication alone never grants course access.

Before production use:

- register the application under the institution's approved identity tenant;
- configure the allowed institutional domain/tenant explicitly;
- preserve normal institutional MFA rather than creating a second application-managed password/MFA system;
- define who can be Course Owner, Instructor, TA, Reviewer, and Student;
- verify archived terms cannot grant current authority;
- define how rosters are imported and how withdrawn students are deactivated.

If your institution does not use Microsoft Entra, plan an identity-provider integration rather than bypassing the authorization model.

## 4. GitHub model

Create a dedicated institution-owned GitHub App. Do not reuse the ETIS Framework GitHub App.

Required security posture:

- App must be installable where student/team repositories live;
- repository access must use **Only select repositories**;
- ETIS must verify the exact nominated repository;
- installation tokens should be requested for the exact repository only;
- no PAT-based repository path;
- GitHub identity linking remains separate from team repository authorization;
- personal repository ownership is resolved by immutable GitHub account ID;
- organization-owned repositories follow GitHub's organization approval/request flow.

Set the GitHub App Setup URL to your deployment's `/github/setup-complete` endpoint and enable redirect-on-update if you use the current upstream onboarding UX.

## 5. Course model

Define:

- term namespace and dates;
- sections;
- teams;
- lifecycle/review phases;
- phase release dates;
- evidence expectations;
- staff roles;
- retention/archive policy.

The upstream COMP 330 model is an example and should not be presented as an institution-independent curriculum requirement.

## 6. AI governance

The institution should decide:

- approved model/provider;
- student disclosure/consent requirements;
- acceptable repository/context data sent to the provider;
- cost limits;
- retention/logging requirements;
- faculty responsibility for AI-generated REVIEW interpretation;
- how students may challenge or correct AI findings.

ETIS is designed so AI is advisory and students remain responsible engineers. Preserve that boundary.

## 7. Privacy and records

Before deployment, review local requirements for student records, privacy, FERPA or equivalent policy, data residency, accessibility, retention, incident response, and AI use. The upstream repository does not provide legal or compliance approval for an institution.

Do not store grades or unrelated student records merely because they are available. Collect the minimum identity/course data required for Studio authorization and learning workflows.

## 8. Production acceptance

Do not treat successful installation as production acceptance. At minimum, test:

- institutional login/MFA;
- current-role authorization;
- student/team lifecycle;
- personal and organization repository onboarding if both are permitted;
- exact selected-repository enforcement;
- evidence snapshot/review continuity;
- health/readiness and migration state;
- secret-store/managed-identity behavior;
- monitoring/alerts;
- database backup and a non-destructive restore drill;
- rollback assets/procedure;
- cost controls;
- archive/retention behavior.

Use the reference `docs/operations/POST_PROVISIONING_PRODUCTION_ACCEPTANCE.md` as a pattern, not as proof for another institution.

## 9. Operating through a semester

Maintain:

- at least one accountable operator;
- monitoring/alert recipients;
- backup/PITR coverage;
- cost budget;
- immutable deployment images;
- documented incident/recovery process;
- explicit end-of-term archive/access removal.

## 10. Contributing institutional improvements upstream

If your institution adds a generally reusable integration or workflow, consider contributing it upstream. Keep institution-specific secrets, branding, policies, and student data out of the contribution.
