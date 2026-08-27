from datetime import UTC, datetime, timedelta
from typing import Any, Literal

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import get_settings


ALGORITHM = "HS256"
TokenType = Literal["access", "refresh"]

# Keep bcrypt for compatibility with existing Verion user password hashes.
pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
)


def hash_password(password: str) -> str:
    """Hash a password using the configured password hashing scheme."""
    if not isinstance(password, str):
        raise TypeError("Password must be a string.")

    if not password:
        raise ValueError("Password cannot be empty.")

    return pwd_context.hash(password)


def verify_password(
    plain_password: str,
    hashed_password: str,
) -> bool:
    """
    Safely verify a plaintext password against a stored password hash.

    Invalid/malformed hashes return False instead of crashing authentication.
    """
    if not isinstance(plain_password, str):
        return False

    if not isinstance(hashed_password, str):
        return False

    if not plain_password or not hashed_password:
        return False

    try:
        return pwd_context.verify(
            plain_password,
            hashed_password,
        )
    except (ValueError, TypeError, KeyError):
        return False


def _create_token(
    subject: str,
    token_type: TokenType,
    expires_delta: timedelta | None = None,
) -> str:
    settings = get_settings()

    if not subject:
        raise ValueError("Token subject cannot be empty.")

    if token_type == "access":
        default_ttl = timedelta(
            seconds=settings.access_token_max_age_seconds,
        )
    else:
        default_ttl = timedelta(
            seconds=settings.refresh_token_max_age_seconds,
        )

    expire = datetime.now(UTC) + (
        expires_delta or default_ttl
    )

    payload: dict[str, Any] = {
        "sub": subject,
        "exp": expire,
        "type": token_type,
    }

    return jwt.encode(
        payload,
        settings.secret_key,
        algorithm=ALGORITHM,
    )


def create_access_token(
    subject: str,
    expires_delta: timedelta | None = None,
) -> str:
    return _create_token(
        subject,
        "access",
        expires_delta,
    )


def create_refresh_token(
    subject: str,
    expires_delta: timedelta | None = None,
) -> str:
    return _create_token(
        subject,
        "refresh",
        expires_delta,
    )


def decode_token(
    token: str,
    expected_type: TokenType,
) -> str | None:
    if not token:
        return None

    settings = get_settings()

    try:
        payload = jwt.decode(
            token,
            settings.secret_key,
            algorithms=[ALGORITHM],
        )
    except JWTError:
        return None

    if payload.get("type") != expected_type:
        return None

    subject = payload.get("sub")

    if not isinstance(subject, str):
        return None

    if not subject:
        return None

    return subject


def decode_access_token(
    token: str,
) -> str | None:
    return decode_token(
        token,
        "access",
    )


def decode_refresh_token(
    token: str,
) -> str | None:
    return decode_token(
        token,
        "refresh",
    )

