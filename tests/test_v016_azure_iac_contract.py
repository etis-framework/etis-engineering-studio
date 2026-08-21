import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FOUNDATION = ROOT / "infra" / "azure" / "main.bicep"
MIGRATION = ROOT / "infra" / "azure" / "migration.bicep"
APPLICATION = ROOT / "infra" / "azure" / "app.bicep"
SECRETS = ROOT / "infra" / "azure" / "secrets.bicep"
WORKFLOW = ROOT / ".github" / "workflows" / "deploy-azure.yml"
DEPLOYMENT_DOC = ROOT / "docs" / "AZURE_DEPLOYMENT.md"


def read_required(path: Path) -> str:
    assert path.exists(), f"required Gate 15 artifact is missing: {path.relative_to(ROOT)}"
    return path.read_text()


def require_all(text: str, tokens: list[str]) -> None:
    missing = [token for token in tokens if token not in text]
    assert not missing, f"missing required Gate 15 contract elements: {missing}"


def test_foundation_is_private_networked_and_independent_of_application_image():
    text = read_required(FOUNDATION)

    require_all(
        text,
        [
            "Microsoft.Network/virtualNetworks@",
            "Microsoft.Network/privateDnsZones@",
            "Microsoft.Network/privateDnsZones/virtualNetworkLinks@",
            "Microsoft.ManagedIdentity/userAssignedIdentities@",
            "Microsoft.OperationalInsights/workspaces@",
            "Microsoft.Insights/components@",
            "Microsoft.ContainerRegistry/registries@",
            "Microsoft.KeyVault/vaults@",
            "Microsoft.DBforPostgreSQL/flexibleServers@",
            "Microsoft.DBforPostgreSQL/flexibleServers/databases@",
            "Microsoft.App/managedEnvironments@",
            "Microsoft.App/environments",
            "Microsoft.DBforPostgreSQL/flexibleServers",
            "infrastructureSubnetId",
            "delegatedSubnetResourceId",
            "privateDnsZoneArmResourceId",
            "enableRbacAuthorization: true",
            "enablePurgeProtection: true",
            "adminUserEnabled: false",
        ],
    )

    assert "Microsoft.App/containerApps@" not in text, (
        "foundation deployment must not require an application image"
    )


def test_foundation_grants_runtime_identity_only_required_secret_and_image_access():
    text = read_required(FOUNDATION)

    require_all(
        text,
        [
            "Microsoft.Authorization/roleAssignments@",
            "AcrPull",
            "Key Vault Secrets User",
        ],
    )


def test_application_uses_managed_identity_acr_and_key_vault_secret_references():
    text = read_required(APPLICATION)

    require_all(
        text,
        [
            "Microsoft.App/containerApps@",
            "UserAssigned",
            "registries:",
            "identity:",
            "keyVaultUrl:",
            "secretRef:",
            "ETIS_DATABASE_URL",
            "ETIS_SESSION_SECRET",
            "ENTRA_CLIENT_SECRET",
            "GITHUB_APP_PRIVATE_KEY",
            "GITHUB_OAUTH_CLIENT_SECRET",
            "OPENAI_API_KEY",
        ],
    )

    assert "username:" not in text
    assert "passwordSecretRef:" not in text


def test_application_wires_complete_fail_closed_production_configuration():
    text = read_required(APPLICATION)

    require_all(
        text,
        [
            "ETIS_ENV",
            "production",
            "ETIS_DEV_LOGIN",
            "false",
            "ETIS_WEB_ORIGIN",
            "ETIS_COURSE_NAMESPACE",
            "ENTRA_CLIENT_ID",
            "ENTRA_CLIENT_SECRET",
            "ENTRA_REDIRECT_URI",
            "ENTRA_TENANT",
            "GITHUB_APP_ID",
            "GITHUB_APP_PRIVATE_KEY",
            "GITHUB_OAUTH_CLIENT_ID",
            "GITHUB_OAUTH_CLIENT_SECRET",
            "GITHUB_OAUTH_REDIRECT_URI",
            "OPENAI_API_KEY",
        ],
    )



def test_runtime_secrets_are_provisioned_into_key_vault_without_source_literals():
    text = read_required(SECRETS)

    require_all(
        text,
        [
            "@secure()",
            "Microsoft.KeyVault/vaults/secrets@",
            "etis-database-url",
            "etis-session-secret",
            "entra-client-secret",
            "github-app-private-key",
            "github-oauth-client-secret",
            "openai-api-key",
            "postgresql+psycopg://",
        ],
    )

    assert "dev-only-change-me" not in text
    assert "sk-proj-" not in text


def test_database_migrations_run_as_manual_container_apps_job():
    text = read_required(MIGRATION)

    require_all(
        text,
        [
            "Microsoft.App/jobs@",
            "Manual",
            "UserAssigned",
            "registries:",
            "identity:",
            "keyVaultUrl:",
            "ETIS_DATABASE_URL",
            "alembic",
            "upgrade",
            "head",
        ],
    )


def test_deploy_workflow_reconciles_foundation_migrates_then_deploys_application():
    text = read_required(WORKFLOW)

    require_all(
        text,
        [
            "az deployment group create",
            "infra/azure/main.bicep",
            "infra/azure/migration.bicep",
            "az containerapp job start",
            "infra/azure/app.bicep",
            "az acr login",
            "docker push",
        ],
    )

    # The release gate now compiles every Bicep template before Azure login.
    # Deployment-order assertions therefore operate on the deploy job only,
    # not on earlier compile-only references to those same template paths.
    deploy = text[text.index("  deploy:"):]

    foundation = deploy.index("infra/azure/main.bicep")
    image_push = deploy.index("docker push")
    migration = deploy.index("infra/azure/migration.bicep")
    migration_start = deploy.index("az containerapp job start")
    application = deploy.index("infra/azure/app.bicep")

    assert foundation < image_push < migration < migration_start < application, (
        "deployment order must be foundation -> image -> migration job "
        "-> migration execution -> application"
    )



def test_ci_compiles_all_gate15_bicep_without_azure_authority():
    ci = read_required(ROOT / ".github" / "workflows" / "ci.yml")

    require_all(
        ci,
        [
            "az bicep install --version v0.46.1",
            "az bicep build --file infra/azure/main.bicep",
            "az bicep build --file infra/azure/secrets.bicep",
            "az bicep build --file infra/azure/migration.bicep",
            "az bicep build --file infra/azure/app.bicep",
        ],
    )

    assert "azure/login@" not in ci, (
        "CI Bicep compilation must not require Azure credentials or deployment authority"
    )


def test_deployment_document_explains_reproducible_gate15_sequence():
    text = read_required(DEPLOYMENT_DOC).lower()

    require_all(
        text,
        [
            "managed identity",
            "private",
            "key vault",
            "migration",
            "infrastructure",
            "application",
            "github actions",
        ],
    )


def test_production_workflow_avoids_reserved_github_prefix_for_operator_settings():
    text = read_required(WORKFLOW)

    required_operator_names = [
        "ETIS_GITHUB_APP_ID",
        "ETIS_GITHUB_APP_SLUG",
        "ETIS_GITHUB_APP_PRIVATE_KEY",
        "ETIS_GITHUB_OAUTH_CLIENT_ID",
        "ETIS_GITHUB_OAUTH_CLIENT_SECRET",
    ]
    require_all(text, required_operator_names)

    forbidden = [
        "${{ vars.GITHUB_APP_ID }}",
        "${{ vars.GITHUB_APP_SLUG }}",
        "${{ secrets.GITHUB_APP_PRIVATE_KEY }}",
        "${{ vars.GITHUB_OAUTH_CLIENT_ID }}",
        "${{ secrets.GITHUB_OAUTH_CLIENT_SECRET }}",
    ]
    for value in forbidden:
        assert value not in text

    # Runtime application configuration remains intentionally GITHUB_*.
    assert 'githubAppId="${ETIS_GITHUB_APP_ID}"' in text
    assert 'githubAppSlug="${ETIS_GITHUB_APP_SLUG}"' in text
    assert 'githubOauthClientId="${ETIS_GITHUB_OAUTH_CLIENT_ID}"' in text



def test_application_preserves_production_custom_domain_binding():
    text = read_required(APPLICATION)

    require_all(
        text,
        [
            "param customDomainName string",
            "param managedCertificateName string",
            "Microsoft.App/managedEnvironments/managedCertificates@2025-01-01",
            "parent: containerAppsEnvironment",
            "customDomains:",
            "name: customDomainName",
            "bindingType: 'SniEnabled'",
            "certificateId: managedCertificate.id",
        ],
    )



def test_production_workflow_preserves_custom_domain_binding_configuration():
    text = read_required(WORKFLOW)

    require_all(
        text,
        [
            "ETIS_CUSTOM_DOMAIN_NAME: ${{ vars.ETIS_CUSTOM_DOMAIN_NAME }}",
            "ETIS_MANAGED_CERTIFICATE_NAME: ${{ vars.ETIS_MANAGED_CERTIFICATE_NAME }}",
            'customDomainName="${ETIS_CUSTOM_DOMAIN_NAME}"',
            'managedCertificateName="${ETIS_MANAGED_CERTIFICATE_NAME}"',
        ],
    )

    assert re.search(
        r"(?m)^\s+ETIS_CUSTOM_DOMAIN_NAME\s*$",
        text,
    ), "production deployment must fail closed when custom domain is missing"

    assert re.search(
        r"(?m)^\s+ETIS_MANAGED_CERTIFICATE_NAME\s*$",
        text,
    ), "production deployment must fail closed when managed certificate is missing"

def test_github_app_slug_is_required_by_application_template():
    text = read_required(APPLICATION)
    assert "param githubAppSlug string" in text
    assert "param githubAppSlug string = ''" not in text
