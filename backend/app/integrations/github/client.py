from __future__ import annotations

import asyncio
from typing import Any
from urllib.parse import urlparse

import httpx

from app.core.config import get_settings


GITHUB_API = "https://api.github.com"
GITHUB_OAUTH_AUTHORIZE = (
    "https://github.com/login/oauth/authorize"
)
GITHUB_OAUTH_TOKEN = (
    "https://github.com/login/oauth/access_token"
)

# Number of retries after the initial request.
# Total attempts = MAX_RETRIES + 1.
MAX_RETRIES = 3

# HTTP responses that indicate a transient server-side failure.
RETRYABLE_STATUS_CODES = frozenset(
    {
        500,
        502,
        503,
        504,
    }
)

# Network errors that are generally safe to retry.
RETRYABLE_EXCEPTIONS = (
    httpx.ConnectError,
    httpx.ReadTimeout,
    httpx.WriteTimeout,
    httpx.PoolTimeout,
)


class GitHubClient:
    """
    Async GitHub API client.

    Features:
    - Reuses one httpx.AsyncClient for connection pooling.
    - Retries transient HTTP 5xx responses.
    - Retries GitHub primary rate-limit exhaustion.
    - Retries transient connection/time-out failures.
    - Uses exponential backoff.
    - Supports repository, PR, PR-file and webhook operations.
    """

    def __init__(self, access_token: str) -> None:
        self._access_token = access_token

        self._client = httpx.AsyncClient(
            timeout=httpx.Timeout(30.0),
        )

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self._access_token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }

    async def _request(
        self,
        method: str,
        url: str,
        *,
        params: dict[str, Any] | None = None,
        json: dict[str, Any] | None = None,
    ) -> httpx.Response:
        """
        Make a GitHub API request with retry handling.

        Retries:
        - HTTP 500, 502, 503, 504
        - HTTP 403 when X-RateLimit-Remaining == 0
        - ConnectError
        - ReadTimeout
        - WriteTimeout
        - PoolTimeout

        Normal 403 responses are returned immediately.
        """

        for attempt in range(MAX_RETRIES + 1):
            try:
                response = await self._client.request(
                    method,
                    url,
                    headers=self._headers(),
                    params=params,
                    json=json,
                )

                # -----------------------------------------------------
                # Transient GitHub/server errors.
                # -----------------------------------------------------

                if response.status_code in RETRYABLE_STATUS_CODES:
                    if attempt < MAX_RETRIES:
                        delay = 2**attempt
                        await asyncio.sleep(delay)
                        continue

                    return response

                # -----------------------------------------------------
                # GitHub primary rate limit.
                # -----------------------------------------------------

                if (
                    response.status_code == 403
                    and response.headers.get(
                        "X-RateLimit-Remaining"
                    )
                    == "0"
                ):
                    if attempt < MAX_RETRIES:
                        retry_after = response.headers.get(
                            "Retry-After"
                        )

                        if retry_after is not None:
                            try:
                                delay = max(
                                    float(retry_after),
                                    0.0,
                                )
                            except (
                                TypeError,
                                ValueError,
                            ):
                                delay = float(2**attempt)
                        else:
                            delay = float(2**attempt)

                        await asyncio.sleep(delay)
                        continue

                    return response

                # -----------------------------------------------------
                # Everything else returns immediately.
                # -----------------------------------------------------

                return response

            except RETRYABLE_EXCEPTIONS:
                if attempt >= MAX_RETRIES:
                    raise

                delay = 2**attempt
                await asyncio.sleep(delay)

        raise RuntimeError(
            "GitHub request retry loop exited unexpectedly"
        )

    async def aclose(self) -> None:
        """Close the underlying HTTP connection pool."""
        await self._client.aclose()

    # ------------------------------------------------------------------
    # Authentication
    # ------------------------------------------------------------------

    async def get_authenticated_user(
        self,
    ) -> dict[str, Any]:
        response = await self._request(
            "GET",
            f"{GITHUB_API}/user",
        )

        response.raise_for_status()

        return response.json()

    # ------------------------------------------------------------------
    # Repositories
    # ------------------------------------------------------------------

    async def list_repositories(
        self,
        *,
        per_page: int = 100,
    ) -> list[dict[str, Any]]:
        repos: list[dict[str, Any]] = []
        page = 1

        while True:
            response = await self._request(
                "GET",
                f"{GITHUB_API}/user/repos",
                params={
                    "per_page": per_page,
                    "page": page,
                    "sort": "updated",
                    "affiliation": (
                        "owner,organization_member"
                    ),
                },
            )

            response.raise_for_status()

            batch = response.json()

            if not batch:
                break

            repos.extend(batch)

            if len(batch) < per_page:
                break

            page += 1

        return repos

    async def get_repository(
        self,
        owner: str,
        name: str,
    ) -> dict[str, Any]:
        response = await self._request(
            "GET",
            f"{GITHUB_API}/repos/{owner}/{name}",
        )

        response.raise_for_status()

        return response.json()

    # ------------------------------------------------------------------
    # Webhooks
    # ------------------------------------------------------------------

    @staticmethod
    def _is_public_webhook_url(
        callback_url: str,
    ) -> bool:
        """
        Validate that a GitHub webhook URL is externally reachable.

        GitHub cannot send webhooks to:
        - localhost
        - 127.0.0.1
        - ::1

        A public Cloudflare Tunnel URL is valid.
        """

        if not callback_url:
            return False

        try:
            parsed = urlparse(
                callback_url.strip()
            )
        except Exception:
            return False

        if parsed.scheme not in {
            "http",
            "https",
        }:
            return False

        hostname = (
            parsed.hostname or ""
        ).lower()

        if not hostname:
            return False

        local_hosts = {
            "localhost",
            "127.0.0.1",
            "::1",
        }

        if hostname in local_hosts:
            return False

        # Reject obvious local/private development
        # addresses as well.
        if hostname in {
            "0.0.0.0",
        }:
            return False

        return True

    async def create_repository_webhook(
        self,
        owner: str,
        name: str,
        *,
        callback_url: str,
        secret: str,
    ) -> dict[str, Any]:
        """
        Create a GitHub repository webhook.

        The callback URL must be publicly reachable.

        Example:

       https://recovered-workstation-comparative-loud.trycloudflare.com
        """

        callback_url = callback_url.strip()

        if not self._is_public_webhook_url(
            callback_url
        ):
            raise ValueError(
                "GitHub webhook callback URL must be "
                "publicly reachable. "
                f"Received: {callback_url!r}. "
                "localhost/127.0.0.1 cannot be used "
                "for GitHub webhooks."
            )

        if not secret or not secret.strip():
            raise ValueError(
                "GitHub webhook secret is required."
            )

        payload = {
            "name": "web",
            "active": True,
            "events": [
                "push",
                "pull_request",
            ],
            "config": {
                "url": callback_url,
                "content_type": "json",
                "secret": secret,
                "insecure_ssl": "0",
            },
        }

        response = await self._request(
            "POST",
            f"{GITHUB_API}/repos/{owner}/{name}/hooks",
            json=payload,
        )

        # --------------------------------------------------------------
        # GitHub webhook creation errors.
        #
        # GitHub commonly returns 422 for:
        # - invalid callback URL
        # - duplicate/incompatible webhook
        # - invalid webhook configuration
        #
        # Extract the response body so the real GitHub error is visible.
        # --------------------------------------------------------------

        if response.is_error:
            try:
                error_data = response.json()
            except ValueError:
                error_data = response.text

            if isinstance(error_data, dict):
                detail = str(
                    error_data.get(
                        "message",
                        "Unknown GitHub API error",
                    )
                )

                errors = error_data.get(
                    "errors"
                )
            else:
                detail = str(error_data)
                errors = None

            if errors:
                raise httpx.HTTPStatusError(
                    (
                        "GitHub webhook creation failed "
                        f"(HTTP {response.status_code}): "
                        f"{detail}; errors={errors}"
                    ),
                    request=response.request,
                    response=response,
                )

            raise httpx.HTTPStatusError(
                (
                    "GitHub webhook creation failed "
                    f"(HTTP {response.status_code}): "
                    f"{detail}"
                ),
                request=response.request,
                response=response,
            )

        logger_message = (
            "GitHub webhook created successfully "
            f"for {owner}/{name}: {callback_url}"
        )

        # Avoid importing a logger only for this operation.
        # The actual application logger can still record this
        # operation at the service layer.
        _ = logger_message

        return response.json()

    async def delete_repository_webhook(
        self,
        owner: str,
        name: str,
        hook_id: int,
    ) -> None:
        response = await self._request(
            "DELETE",
            f"{GITHUB_API}/repos/{owner}/{name}/hooks/{hook_id}",
        )

        # GitHub returns:
        # 204 -> successfully deleted
        # 404 -> already doesn't exist
        if response.status_code not in (
            204,
            404,
        ):
            response.raise_for_status()

    # ------------------------------------------------------------------
    # Pull requests
    # ------------------------------------------------------------------

    async def list_pull_requests(
        self,
        owner: str,
        name: str,
        *,
        state: str = "open",
    ) -> list[dict[str, Any]]:
        pull_requests: list[dict[str, Any]] = []

        page = 1
        per_page = 100

        while True:
            response = await self._request(
                "GET",
                f"{GITHUB_API}/repos/{owner}/{name}/pulls",
                params={
                    "state": state,
                    "per_page": per_page,
                    "page": page,
                },
            )

            response.raise_for_status()

            batch = response.json()

            if not batch:
                break

            pull_requests.extend(batch)

            if len(batch) < per_page:
                break

            page += 1

        return pull_requests

    async def get_pull_request(
        self,
        owner: str,
        name: str,
        number: int,
    ) -> dict[str, Any]:
        response = await self._request(
            "GET",
            f"{GITHUB_API}/repos/{owner}/{name}/pulls/{number}",
        )

        response.raise_for_status()

        return response.json()

    async def list_pull_request_files(
        self,
        owner: str,
        name: str,
        number: int,
    ) -> list[dict[str, Any]]:
        """
        Return all files changed by a pull request.

        GitHub paginates this endpoint at a maximum
        of 100 files per page.
        """

        files: list[dict[str, Any]] = []

        page = 1
        per_page = 100

        while True:
            response = await self._request(
                "GET",
                (
                    f"{GITHUB_API}/repos/"
                    f"{owner}/{name}/pulls/"
                    f"{number}/files"
                ),
                params={
                    "per_page": per_page,
                    "page": page,
                },
            )

            response.raise_for_status()

            batch = response.json()

            if not batch:
                break

            files.extend(batch)

            if len(batch) < per_page:
                break

            page += 1

        return files


# ----------------------------------------------------------------------
# OAuth
# ----------------------------------------------------------------------


async def exchange_oauth_code(
    code: str,
) -> dict[str, Any]:
    """
    Exchange a GitHub OAuth authorization code
    for access tokens.
    """

    settings = get_settings()

    async with httpx.AsyncClient(
        timeout=httpx.Timeout(30.0),
    ) as client:
        response = await client.post(
            GITHUB_OAUTH_TOKEN,
            headers={
                "Accept": "application/json",
            },
            json={
                "client_id": settings.github_client_id,
                "client_secret": (
                    settings.github_client_secret
                ),
                "code": code,
                "redirect_uri": (
                    settings.github_redirect_uri
                ),
            },
        )

        response.raise_for_status()

        return response.json()


def build_oauth_authorize_url(
    *,
    state: str,
) -> str:
    """
    Build the GitHub OAuth authorization URL.

    httpx.QueryParams handles URL encoding correctly.
    """

    settings = get_settings()

    params = {
        "client_id": settings.github_client_id,
        "redirect_uri": settings.github_redirect_uri,
        "scope": settings.github_oauth_scopes,
        "state": state,
    }

    query = str(
        httpx.QueryParams(params)
    )

    return (
        f"{GITHUB_OAUTH_AUTHORIZE}?{query}"
    )

