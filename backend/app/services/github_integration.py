from typing import Any

from app.core.config import get_settings
from app.integrations.github.client import (
    GitHubClient,
    build_oauth_authorize_url,
    exchange_oauth_code,
)
from app.repositories.integrations import IntegrationRepository
from app.repositories.repositories import RepositoryRepository
from app.schemas.integration import GitHubIntegrationResponse, GitHubRepositoryOption
from app.utils.encryption import decrypt_value, encrypt_value


class GitHubIntegrationService:
    def __init__(
        self,
        integrations: IntegrationRepository,
        repositories: RepositoryRepository,
    ) -> None:
        self._integrations = integrations
        self._repositories = repositories

    async def get_status(self, organization_id: str) -> GitHubIntegrationResponse:
        settings = get_settings()
        if not settings.github_configured:
            return GitHubIntegrationResponse(status="not_connected", configured=False)

        integration = await self._integrations.get_github_by_organization(organization_id)
        connected_count = await self._repositories.count_by_organization(organization_id)
        if not integration or integration.get("status") != "connected":
            return GitHubIntegrationResponse(
                status="not_connected",
                connected_repositories=connected_count,
                configured=True,
            )

        return GitHubIntegrationResponse(
            status="connected",
            github_login=integration.get("github_login"),
            connected_repositories=connected_count,
            configured=True,
        )

    def build_authorize_url(self, *, state: str) -> str:
        return build_oauth_authorize_url(state=state)

    async def complete_oauth(self, *, organization_id: str, code: str) -> GitHubIntegrationResponse:
        token_payload = await exchange_oauth_code(code)
        access_token = token_payload.get("access_token")
        if not isinstance(access_token, str) or not access_token:
            raise ValueError("GitHub did not return an access token.")

        scopes_raw = token_payload.get("scope", "")
        scopes = [scope.strip() for scope in scopes_raw.split(",") if scope.strip()]

        client = GitHubClient(access_token)
        user = await client.get_authenticated_user()
        github_user_id = user.get("id")
        github_login = user.get("login")
        if not isinstance(github_user_id, int) or not isinstance(github_login, str):
            raise ValueError("Unable to read GitHub account details.")

        await self._integrations.upsert_github(
            organization_id=organization_id,
            github_user_id=github_user_id,
            github_login=github_login,
            access_token_encrypted=encrypt_value(access_token),
            scopes=scopes,
        )
        return await self.get_status(organization_id)

    async def disconnect(self, organization_id: str) -> None:
        await self._integrations.delete_github(organization_id)

    async def get_access_token(self, organization_id: str) -> str:
        integration = await self._integrations.get_github_by_organization(organization_id)
        if not integration or integration.get("status") != "connected":
            raise ValueError("GitHub is not connected for this workspace.")
        encrypted = integration.get("access_token_encrypted")
        if not isinstance(encrypted, str):
            raise ValueError("GitHub credentials are missing.")
        return decrypt_value(encrypted)

    async def list_available_repositories(self, organization_id: str) -> list[GitHubRepositoryOption]:
        access_token = await self.get_access_token(organization_id)
        client = GitHubClient(access_token)
        remote_repos = await client.list_repositories()
        connected = await self._repositories.list_by_organization(organization_id)
        connected_ids = {repo["github_id"] for repo in connected if repo.get("github_id") is not None}

        options: list[GitHubRepositoryOption] = []
        for repo in remote_repos:
            github_id = repo.get("id")
            if not isinstance(github_id, int):
                continue
            owner = repo.get("owner", {})
            owner_login = owner.get("login") if isinstance(owner, dict) else None
            options.append(
                GitHubRepositoryOption(
                    github_id=github_id,
                    full_name=repo.get("full_name", ""),
                    name=repo.get("name", ""),
                    owner=owner_login or "",
                    language=repo.get("language"),
                    private=bool(repo.get("private", False)),
                    default_branch=repo.get("default_branch"),
                    html_url=repo.get("html_url"),
                    already_connected=github_id in connected_ids,
                ),
            )
        return options

    async def get_github_client(self, organization_id: str) -> GitHubClient:
        access_token = await self.get_access_token(organization_id)
        return GitHubClient(access_token)
