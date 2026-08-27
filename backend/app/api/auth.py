from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status

from app.api.deps import (
    clear_auth_cookies,
    get_auth_service,
    get_current_session,
    get_current_user_id_from_cookie,
    get_password_reset_service,
    set_auth_cookies,
)
from app.core.config import get_settings
from app.core.security import decode_refresh_token
from app.schemas.auth import (
    ChangePasswordRequest,
    ForgotPasswordRequest,
    LoginRequest,
    ProfileUpdateRequest,
    ResetPasswordRequest,
    SessionResponse,
    SignupRequest,
)
from app.services.auth import AuthService
from app.services.password_reset import PasswordResetService


router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/me", response_model=SessionResponse)
async def me(
    current_session: Annotated[
        SessionResponse,
        Depends(get_current_session),
    ],
) -> SessionResponse:
    return current_session


@router.patch("/me", response_model=SessionResponse)
async def update_me(
    payload: ProfileUpdateRequest,
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
    user_id: Annotated[str, Depends(get_current_user_id_from_cookie)],
) -> SessionResponse:
    try:
        return await auth_service.update_profile(
            user_id,
            name=payload.name,
            timezone=payload.timezone,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.post(
    "/change-password",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def change_password(
    payload: ChangePasswordRequest,
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
    user_id: Annotated[str, Depends(get_current_user_id_from_cookie)],
) -> None:
    try:
        await auth_service.change_password(
            user_id,
            current_password=payload.current_password,
            new_password=payload.new_password,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.post(
    "/signup",
    response_model=SessionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def signup(
    payload: SignupRequest,
    response: Response,
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> SessionResponse:
    email = str(payload.email).strip().lower()

    try:
        session = await auth_service.signup(
            name=payload.name.strip(),
            email=email,
            team=payload.team,
            password=payload.password,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    set_auth_cookies(
        response,
        session.user.id,
    )

    return session


@router.post(
    "/login",
    response_model=SessionResponse,
)
async def login(
    payload: LoginRequest,
    response: Response,
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> SessionResponse:
    """
    Authenticate a user and create access/refresh cookies.

    Authentication failures intentionally return 401.
    Internal exceptions are allowed to surface as server errors
    instead of being incorrectly reported as invalid credentials.
    """

    email = str(payload.email).strip().lower()

    if not email or not payload.password:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        )

    try:
        session = await auth_service.authenticate(
            email=email,
            password=payload.password,
        )
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        ) from None

    set_auth_cookies(
        response,
        session.user.id,
    )

    return session


@router.post(
    "/refresh",
    response_model=SessionResponse,
)
async def refresh(
    request: Request,
    response: Response,
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> SessionResponse:
    settings = get_settings()

    refresh_token = request.cookies.get(
        settings.refresh_cookie_name,
    )

    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated.",
        )

    user_id = decode_refresh_token(refresh_token)

    if not user_id:
        clear_auth_cookies(response)

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid session.",
        )

    try:
        session = await auth_service.get_session(user_id)
    except ValueError:
        clear_auth_cookies(response)

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid session.",
        ) from None

    set_auth_cookies(
        response,
        user_id,
    )

    return session


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def logout(response: Response) -> None:
    clear_auth_cookies(response)


@router.post(
    "/forgot-password",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def forgot_password(
    payload: ForgotPasswordRequest,
    service: Annotated[
        PasswordResetService,
        Depends(get_password_reset_service),
    ],
) -> None:
    await service.request_reset(
        str(payload.email).strip().lower(),
    )


@router.post(
    "/reset-password",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def reset_password(
    payload: ResetPasswordRequest,
    service: Annotated[
        PasswordResetService,
        Depends(get_password_reset_service),
    ],
) -> None:
    try:
        await service.reset_password(
            token=payload.token,
            password=payload.password,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

