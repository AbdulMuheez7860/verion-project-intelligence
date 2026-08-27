from enum import StrEnum

from pydantic import EmailStr, Field

from app.schemas.common import APIModel


class MembershipRole(StrEnum):
    OWNER = "owner"
    ADMIN = "admin"
    MEMBER = "member"
    VIEWER = "viewer"


class UserResponse(APIModel):
    id: str
    name: str
    email: EmailStr
    avatar_url: str | None = None
    timezone: str | None = None


class OrganizationResponse(APIModel):
    id: str
    name: str
    slug: str


class MembershipResponse(APIModel):
    id: str
    organization_id: str
    role: MembershipRole


class SessionResponse(APIModel):
    user: UserResponse
    organization: OrganizationResponse
    membership: MembershipResponse


class SignupRequest(APIModel):
    name: str = Field(min_length=1, max_length=120)
    email: EmailStr
    team: str = Field(min_length=1, max_length=120)
    password: str = Field(min_length=8, max_length=128)


class LoginRequest(APIModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class ForgotPasswordRequest(APIModel):
    email: EmailStr


class ResetPasswordRequest(APIModel):
    password: str = Field(min_length=8, max_length=128)
    token: str


class ProfileUpdateRequest(APIModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    timezone: str | None = Field(default=None, min_length=1, max_length=64)


class ChangePasswordRequest(APIModel):
    current_password: str = Field(min_length=8, max_length=128)
    new_password: str = Field(min_length=8, max_length=128)
