import logging
from fastapi import APIRouter, Depends, HTTPException, status, Request
from datetime import timedelta

from app.core.config import settings
from app.core.security import create_access_token, get_current_user
from app.core.ldap_auth import ldap_service
from app.core.kerberos import kerberos_manager
from app.core.acl import _check_match
from app.models.auth import LoginRequest, UserSession, TokenResponse, Role

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/auth", tags=["auth"])


def _resolve_global_role(username: str, groups: list) -> Role:
    """Определяет глобальную роль пользователя."""
    user_groups = set(groups)
    g = settings.acl.roles
    if _check_match(username, user_groups, g.admin.users, g.admin.groups):
        return Role.ADMIN
    if _check_match(username, user_groups, g.writer.users, g.writer.groups):
        return Role.WRITER
    return Role.READER


def _mock_authenticate(username: str, password: str):
    """Аутентификация через mock-пользователей."""
    for mock_user in settings.auth.mock_users:
        if mock_user.username == username and mock_user.password == password:
            role = _resolve_global_role(username, mock_user.groups)
            return UserSession(
                username=mock_user.username,
                display_name=mock_user.display_name,
                email=mock_user.email,
                groups=mock_user.groups,
                auth_method="mock",
                is_admin=(role == Role.ADMIN),
                system_role=role,
            )
    return None


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest):
    """Эндпоинт авторизации: поддержка mock, LDAP, hybrid."""
    user = None
    mode = settings.auth.mode

    # Mock auth
    if mode in ("mock", "hybrid"):
        user = _mock_authenticate(body.username, body.password)

    # LDAP auth
    if not user and mode in ("ldaps_only", "hybrid"):
        ldap_user = ldap_service.authenticate(body.username, body.password)
        if ldap_user:
            role = _resolve_global_role(ldap_user.username, ldap_user.groups)
            ldap_user.system_role = role
            ldap_user.is_admin = (role == Role.ADMIN)
            user = ldap_user

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверное имя пользователя или пароль",
        )

    token = create_access_token(
        data={"user": user.model_dump()},
        expires_delta=timedelta(minutes=settings.auth.jwt.expire_minutes),
    )

    return TokenResponse(access_token=token, user=user)


@router.post("/spnego", response_model=TokenResponse)
async def spnego_login(request: Request):
    """Kerberos SPNEGO SSO авторизация."""
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Negotiate "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Требуется заголовок Authorization: Negotiate <token>",
            headers={"WWW-Authenticate": "Negotiate"},
        )

    user = kerberos_manager.authenticate_spnego(auth_header)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Ошибка SPNEGO-аутентификации",
        )

    role = _resolve_global_role(user.username, user.groups)
    user.system_role = role
    user.is_admin = (role == Role.ADMIN)

    token = create_access_token(
        data={"user": user.model_dump()},
        expires_delta=timedelta(minutes=settings.auth.jwt.expire_minutes),
    )
    return TokenResponse(access_token=token, user=user)


@router.get("/me", response_model=UserSession)
async def get_me(user: UserSession = Depends(get_current_user)):
    """Возвращает текущего авторизованного пользователя."""
    return user


@router.post("/logout")
async def logout():
    """Выход: клиент удаляет токен самостоятельно."""
    return {"detail": "Сессия завершена"}
