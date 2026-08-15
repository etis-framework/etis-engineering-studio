# Azure infrastructure starter

`main.bicep` establishes the intended Wave 1 topology but is **not blindly production-ready**. Review current Azure API versions, region availability, networking posture, PostgreSQL authentication choice, SKU/pricing, and Key Vault access before deployment.

Production hardening should move PostgreSQL to Entra/managed-identity authentication and private networking if operational complexity remains reasonable for the course deployment.
