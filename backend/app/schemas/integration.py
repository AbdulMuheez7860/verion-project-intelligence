from typing import Literal

from pydantic import Field

from app.schemas.common import APIModel

IntegrationStatus = Literal["not_connected", "connected", "error"]


class GitHubIntegrationResponse(APIModel):
    status: IntegrationStatus
    github_login: str | None = None
    connected_repositories: int = 0
    configured: bool = False


class GitHubConnectResponse(APIModel):
    authorize_url: str


class GitHubRepositoryOption(APIModel):
    github_id: int
    full_name: str
    name: str
    owner: str
    language: str | None = None
    private: bool = False
    default_branch: str | None = None
    html_url: str | None = None
    already_connected: bool = False


class ConnectRepositoryRequest(APIModel):
    github_id: int = Field(gt=0)
