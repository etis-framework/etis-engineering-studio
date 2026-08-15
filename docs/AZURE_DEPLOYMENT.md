# Azure Deployment Plan

## Recommended first production topology

- Azure Container Apps: one `studio-web` container (FastAPI + current bundled UI) for Wave 1.
- Azure Database for PostgreSQL Flexible Server: durable application state.
- Azure Key Vault: GitHub OAuth/App and OpenAI secrets.
- Log Analytics / Application Insights: operational telemetry.
- Azure Container Registry: application image.
- Custom DNS later: for example `studio.etisframework.org` after the first stable deployment.

This is intentionally simpler than a microservice architecture. The course population (~30 students) does not justify Kubernetes or multiple independently scaled services yet.

## Deployment sequence

1. Create a resource group such as `rg-etis-studio-prod`.
2. Deploy the Bicep in `infra/azure/main.bicep` after reviewing names/region/DB SKU.
3. Create GitHub federated credentials for deployment.
4. Store application secrets in Key Vault.
5. Build/push the container and deploy the Container App.
6. Configure GitHub OAuth callback to the production hostname.
7. Create/install the read-only GitHub App on team repositories.
8. Import the COMP330-F26 roster/team mapping.
9. Run production acceptance tests with demo and one private test repository.
10. Enable student access only after security and cost checks pass.

## Cost posture

Wave 1 should use small/serverless-capable tiers and avoid always-on resources that do not contribute student value. Create explicit Azure budgets/alerts before student rollout. Exact SKUs and pricing should be chosen at deployment time because Azure pricing/availability changes.
