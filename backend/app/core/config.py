import logging

from functools import lru_cache
from typing import Literal

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


logger = logging.getLogger(__name__)


INSECURE_SECRET_KEYS = frozenset(
    {
        "change-me-in-production",
        "dev-secret-change-me",
        "secret",
        "changeme",
    }
)


EnvironmentName = Literal["development", "production", "test"]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ------------------------------------------------------------------
    # Application
    # ------------------------------------------------------------------

    app_name: str = "Verion API"
    environment: EnvironmentName = "development"
    debug: bool = False
    api_v1_prefix: str = "/api/v1"
    frontend_url: str = "http://localhost:5173"

    # ------------------------------------------------------------------
    # Public URL
    # ------------------------------------------------------------------

    # Publicly reachable base URL used for GitHub webhooks.
    #
    # Local development example:
    # https://your-tunnel.trycloudflare.com
    #
    # Production:
    # https://your-domain.com
    public_url: str = ""

    # ------------------------------------------------------------------
    # Database / Infrastructure
    # ------------------------------------------------------------------

    mongodb_url: str = "mongodb://localhost:27017"
    mongodb_db: str = "verion"

    redis_url: str = "redis://localhost:6379/0"
    celery_broker_url: str = "redis://localhost:6379/0"
    celery_result_backend: str = "redis://localhost:6379/0"

    # ------------------------------------------------------------------
    # Authentication / Security
    # ------------------------------------------------------------------

    secret_key: str = "change-me-in-production"

    session_cookie_name: str = "verion_session"
    refresh_cookie_name: str = "verion_refresh"

    access_token_max_age_seconds: int = 15 * 60
    refresh_token_max_age_seconds: int = 30 * 24 * 60 * 60

    cookie_secure: bool = False
    cookie_samesite: Literal["lax", "strict", "none"] = "lax"

    # ------------------------------------------------------------------
    # CORS
    # ------------------------------------------------------------------

    cors_origins: str = "http://localhost:5173"

    # ------------------------------------------------------------------
    # GitHub
    # ------------------------------------------------------------------

    github_client_id: str = ""
    github_client_secret: str = ""

    github_redirect_uri: str = (
        "http://localhost:8000/api/v1/auth/github/callback"
    )

    github_api_url: str = "https://api.github.com"

    # Secret used to sign and verify GitHub webhook deliveries.
    github_webhook_secret: str = ""

    # REQUIRED by GitHub OAuth client
    github_oauth_scopes: str = "read:user,user:email,repo"

    # ------------------------------------------------------------------
    # Password reset
    # ------------------------------------------------------------------

    password_reset_token_max_age_seconds: int = 60 * 60

    # ------------------------------------------------------------------
    # LLM
    # ------------------------------------------------------------------

    llm_provider: str = "openai"
    llm_api_key: str = ""
    llm_base_url: str = "https://api.openai.com/v1"
    llm_model: str = "gpt-4o-mini"
    llm_timeout_seconds: float = 60.0

    # ------------------------------------------------------------------
    # Analysis
    # ------------------------------------------------------------------

    analysis_task_timeout_seconds: int = 60 * 30

    default_page_size: int = 50
    max_page_size: int = 200

    # ------------------------------------------------------------------
    # Validators
    # ------------------------------------------------------------------

    @model_validator(mode="after")
    def validate_security_settings(self) -> "Settings":
        if self.environment == "production" and not self.cookie_secure:
            logger.warning(
                "COOKIE_SECURE is disabled while running in production."
            )

        return self

    def validate_for_startup(self) -> None:
        """Validate configuration required before starting the application."""

        if not self.mongodb_url:
            raise ValueError("MONGODB_URL is required.")

        if not self.mongodb_db:
            raise ValueError("MONGODB_DB is required.")

        if not self.redis_url:
            raise ValueError("REDIS_URL is required.")

        if self.environment == "production":
            if self.secret_key.lower() in INSECURE_SECRET_KEYS:
                raise ValueError(
                    "SECRET_KEY must be changed from the default value "
                    "in production."
                )

            if not self.cookie_secure:
                logger.warning(
                    "COOKIE_SECURE is disabled while running in production."
                )

        # A webhook secret means Verion intends to create/verify
        # GitHub webhooks. GitHub must therefore have a public URL.
        if self.github_webhook_secret and not self.public_url.strip():
            raise ValueError(
                "PUBLIC_URL is required when GITHUB_WEBHOOK_SECRET "
                "is configured. GitHub webhooks cannot use localhost."
            )

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def cors_origin_list(self) -> list[str]:
        return [
            origin.strip()
            for origin in self.cors_origins.split(",")
            if origin.strip()
        ]

    @property
    def is_production(self) -> bool:
        return self.environment == "production"

    @property
    def github_configured(self) -> bool:
        return bool(
            self.github_client_id.strip()
            and self.github_client_secret.strip()
        )

    @property
    def webhook_verification_required(self) -> bool:
        """
        Webhook verification is enabled whenever a webhook secret
        is configured.

        This works in both development and production.
        """
        return bool(self.github_webhook_secret.strip())


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()