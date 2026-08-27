from typing import Any

from app.core.security import hash_password, verify_password
from app.repositories.memberships import MembershipRepository
from app.repositories.users import OrganizationRepository, UserRepository
from app.schemas.auth import (
    MembershipResponse,
    MembershipRole,
    OrganizationResponse,
    SessionResponse,
    UserResponse,
)


class AuthService:
    def __init__(
        self,
        users: UserRepository,
        organizations: OrganizationRepository,
        memberships: MembershipRepository,
    ) -> None:
        self._users = users
        self._organizations = organizations
        self._memberships = memberships

    # ------------------------------------------------------------------
    # Signup
    # ------------------------------------------------------------------

    async def signup(
        self,
        *,
        name: str,
        email: str,
        team: str,
        password: str,
    ) -> SessionResponse:
        name = name.strip()
        email = self._normalize_email(email)
        team = team.strip()

        if not name:
            raise ValueError("Name is required.")

        if not email:
            raise ValueError("Email is required.")

        if not team:
            raise ValueError("Team name is required.")

        if not password:
            raise ValueError("Password is required.")

        if len(password) < 8:
            raise ValueError(
                "Password must contain at least 8 characters."
            )

        existing = await self._users.get_by_email(email)

        if existing:
            raise ValueError(
                "An account with this email already exists."
            )

        organization = await self._organizations.create(
            name=team,
        )

        organization_id = organization.get("id")

        if not isinstance(organization_id, str):
            raise ValueError(
                "Failed to create workspace."
            )

        user = await self._users.create(
            name=name,
            email=email,
            password=password,
            organization_id=organization_id,
        )

        user_id = user.get("id")

        if not isinstance(user_id, str):
            raise ValueError(
                "Failed to create user."
            )

        membership = await self._memberships.create(
            user_id=user_id,
            organization_id=organization_id,
            role=MembershipRole.OWNER,
        )

        if not membership:
            raise ValueError(
                "Failed to create workspace membership."
            )

        return self.to_session_response(
            user,
            organization,
            membership,
        )

    # ------------------------------------------------------------------
    # Authentication
    # ------------------------------------------------------------------

    async def authenticate(
        self,
        *,
        email: str,
        password: str,
    ) -> SessionResponse:
        """
        Authenticate an existing user.

        The repository is responsible for finding the user.
        This service verifies the stored password hash and then
        builds the complete session.
        """

        email = self._normalize_email(email)

        if not email or not password:
            raise ValueError(
                "Invalid email or password."
            )

        user = await self._users.get_by_email(email)

        if not user:
            raise ValueError(
                "Invalid email or password."
            )

        password_hash = user.get("password_hash")

        if not isinstance(password_hash, str) or not password_hash:
            raise ValueError(
                "Invalid email or password."
            )

        try:
            password_valid = verify_password(
                password,
                password_hash,
            )
        except Exception as exc:
            # Do not expose hashing-library details to the client.
            raise ValueError(
                "Invalid email or password."
            ) from exc

        if not password_valid:
            raise ValueError(
                "Invalid email or password."
            )

        user_id = user.get("id")

        if not isinstance(user_id, str) or not user_id:
            raise ValueError(
                "Invalid user account."
            )

        return await self.get_session(user_id)

    # ------------------------------------------------------------------
    # User
    # ------------------------------------------------------------------

    async def get_user(
        self,
        user_id: str,
    ) -> UserResponse | None:
        user = await self._users.get_by_id(user_id)

        if not user:
            return None

        return self.to_user_response(user)

    # ------------------------------------------------------------------
    # Session
    # ------------------------------------------------------------------

    async def get_session(
        self,
        user_id: str,
    ) -> SessionResponse:
        if not user_id:
            raise ValueError(
                "Invalid user session."
            )

        user = await self._users.get_by_id(user_id)

        if not user:
            raise ValueError(
                "User not found."
            )

        organization_id = user.get(
            "organization_id"
        )

        if not isinstance(
            organization_id,
            str,
        ) or not organization_id:
            raise ValueError(
                "No workspace found for this user."
            )

        organization = await self._organizations.get_by_id(
            organization_id
        )

        if not organization:
            raise ValueError(
                "Workspace not found."
            )

        membership = (
            await self._memberships.get_for_user_and_organization(
                user_id=user_id,
                organization_id=organization_id,
            )
        )

        if not membership:
            raise ValueError(
                "Membership not found."
            )

        return self.to_session_response(
            user,
            organization,
            membership,
        )

    # ------------------------------------------------------------------
    # Organization
    # ------------------------------------------------------------------

    async def get_organization_id(
        self,
        user_id: str,
    ) -> str | None:
        user = await self._users.get_by_id(
            user_id
        )

        if not user:
            return None

        organization_id = user.get(
            "organization_id"
        )

        return (
            organization_id
            if isinstance(organization_id, str)
            else None
        )

    # ------------------------------------------------------------------
    # Membership
    # ------------------------------------------------------------------

    async def get_membership(
        self,
        user_id: str,
        organization_id: str,
    ) -> dict[str, Any] | None:
        return await self._memberships.get_for_user_and_organization(
            user_id=user_id,
            organization_id=organization_id,
        )

    # ------------------------------------------------------------------
    # Profile
    # ------------------------------------------------------------------

    async def update_profile(
        self,
        user_id: str,
        *,
        name: str | None = None,
        timezone: str | None = None,
    ) -> SessionResponse:
        if name is not None:
            name = name.strip()

            if not name:
                raise ValueError(
                    "Name cannot be empty."
                )

        updated = await self._users.update_profile(
            user_id,
            name=name,
            timezone=timezone,
        )

        if not updated:
            raise ValueError(
                "User not found."
            )

        return await self.get_session(
            user_id
        )

    # ------------------------------------------------------------------
    # Password
    # ------------------------------------------------------------------

    async def change_password(
        self,
        user_id: str,
        *,
        current_password: str,
        new_password: str,
    ) -> None:
        user = await self._users.get_by_id(
            user_id
        )

        if not user:
            raise ValueError(
                "User not found."
            )

        password_hash = user.get(
            "password_hash"
        )

        if not isinstance(
            password_hash,
            str,
        ) or not password_hash:
            raise ValueError(
                "Current password is incorrect."
            )

        if not verify_password(
            current_password,
            password_hash,
        ):
            raise ValueError(
                "Current password is incorrect."
            )

        if not new_password:
            raise ValueError(
                "New password is required."
            )

        if len(new_password) < 8:
            raise ValueError(
                "New password must contain at least 8 characters."
            )

        if verify_password(
            new_password,
            password_hash,
        ):
            raise ValueError(
                "New password must be different from the current password."
            )

        await self._users.update_password(
            user_id,
            new_password,
        )

    # ------------------------------------------------------------------
    # Serialization
    # ------------------------------------------------------------------

    @staticmethod
    def to_user_response(
        user: dict[str, Any],
    ) -> UserResponse:
        return UserResponse(
            id=user["id"],
            name=user["name"],
            email=user["email"],
            timezone=user.get("timezone"),
        )

    @staticmethod
    def to_organization_response(
        organization: dict[str, Any],
    ) -> OrganizationResponse:
        return OrganizationResponse(
            id=organization["id"],
            name=organization["name"],
            slug=organization["slug"],
        )

    @staticmethod
    def to_membership_response(
        membership: dict[str, Any],
    ) -> MembershipResponse:
        return MembershipResponse(
            id=membership["id"],
            organization_id=membership["organization_id"],
            role=MembershipRole(
                membership["role"]
            ),
        )

    @classmethod
    def to_session_response(
        cls,
        user: dict[str, Any],
        organization: dict[str, Any],
        membership: dict[str, Any],
    ) -> SessionResponse:
        return SessionResponse(
            user=cls.to_user_response(
                user
            ),
            organization=cls.to_organization_response(
                organization
            ),
            membership=cls.to_membership_response(
                membership
            ),
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _normalize_email(
        email: str,
    ) -> str:
        return email.strip().lower()

