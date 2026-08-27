from app.core.config import get_settings
from app.repositories.password_reset_tokens import PasswordResetTokenRepository
from app.repositories.users import UserRepository


class PasswordResetService:
    def __init__(
        self,
        users: UserRepository,
        tokens: PasswordResetTokenRepository,
    ) -> None:
        self._users = users
        self._tokens = tokens

    async def request_reset(self, email: str) -> None:
        """Always succeeds from the caller's perspective — no email enumeration."""
        user = await self._users.get_by_email(email)
        if not user:
            return

        settings = get_settings()
        await self._tokens.create(
            user_id=user["id"],
            ttl_seconds=settings.password_reset_token_max_age_seconds,
        )
        # Email delivery is out of scope for Tier 0; token is stored for reset flow.

    async def reset_password(self, *, token: str, password: str) -> None:
        doc = await self._tokens.consume(token)
        if not doc:
            raise ValueError("Invalid or expired reset token.")

        user_id = doc.get("user_id")
        if not isinstance(user_id, str):
            raise ValueError("Invalid or expired reset token.")

        updated = await self._users.update_password(user_id, password)
        if not updated:
            raise ValueError("Invalid or expired reset token.")
