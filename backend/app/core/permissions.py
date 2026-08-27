from typing import Literal

from app.schemas.auth import MembershipRole

Permission = Literal[
    "settings.read",
    "settings.update",
    "members.read",
    "members.invite",
    "members.update_role",
    "members.remove",
    "integrations.read",
    "integrations.manage",
    "analysis_settings.read",
    "audit.read",
    "account.update",
    "notifications.read",
    "notifications.preferences.update",
]

_VIEWER: set[Permission] = {
    "settings.read",
    "members.read",
    "integrations.read",
    "analysis_settings.read",
    "account.update",
    "notifications.read",
    "notifications.preferences.update",
}

_MEMBER: set[Permission] = _VIEWER | {
    "settings.read",
}

_ADMIN: set[Permission] = _MEMBER | {
    "settings.update",
    "members.invite",
    "members.update_role",
    "members.remove",
    "integrations.manage",
    "audit.read",
}

_ROLE_PERMISSIONS: dict[MembershipRole, set[Permission]] = {
    MembershipRole.VIEWER: _VIEWER,
    MembershipRole.MEMBER: _MEMBER,
    MembershipRole.ADMIN: _ADMIN,
    MembershipRole.OWNER: _ADMIN,
}


def can(role: MembershipRole, permission: Permission) -> bool:
    return permission in _ROLE_PERMISSIONS.get(role, set())


def is_admin_role(role: MembershipRole) -> bool:
    return role in {MembershipRole.ADMIN, MembershipRole.OWNER}
