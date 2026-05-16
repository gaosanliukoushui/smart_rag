"""Authentication service."""

import uuid
from datetime import timedelta
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.exceptions import SmartRAGException
from app.core.security import (
    get_password_hash,
    verify_password,
    create_access_token,
    create_refresh_token,
    verify_token,
    ACCESS_TOKEN_EXPIRE_MINUTES,
)
from app.models import User, Tenant, UserRole, Role
from app.schemas.auth import UserCreate, UserLogin, UserResponse
from app.core.logging import get_logger
from app.services.error_tracker import error_tracker

logger = get_logger(__name__)


class AuthError(SmartRAGException):
    """Authentication error."""

    def __init__(self, message: str):
        super().__init__(message, code="AUTH_ERROR")


class UserAlreadyExistsError(AuthError):
    """Raised when user already exists."""

    def __init__(self, identifier: str):
        super().__init__(f"User with this {identifier} already exists")
        self.code = "USER_ALREADY_EXISTS"


class InvalidCredentialsError(AuthError):
    """Raised when credentials are invalid."""

    def __init__(self):
        super().__init__("Invalid username or password")


class TokenExpiredError(AuthError):
    """Raised when token is expired."""

    def __init__(self):
        super().__init__("Token has expired")
        self.code = "TOKEN_EXPIRED"


class TokenInvalidError(AuthError):
    """Raised when token is invalid."""

    def __init__(self):
        super().__init__("Invalid token")
        self.code = "TOKEN_INVALID"


class AuthService:
    """Authentication service."""

    def __init__(self, db: Session):
        self.db = db

    def _get_user_by_username(self, username: str) -> Optional[User]:
        stmt = select(User).where(User.username == username)
        return self.db.execute(stmt).scalar_one_or_none()

    def _get_user_by_email(self, email: str) -> Optional[User]:
        stmt = select(User).where(User.email == email)
        return self.db.execute(stmt).scalar_one_or_none()

    def get_user_by_id(self, user_id: uuid.UUID) -> Optional[User]:
        stmt = select(User).where(User.id == user_id)
        return self.db.execute(stmt).scalar_one_or_none()

    def register(self, data: UserCreate) -> User:
        logger.info("auth_register_attempt", username=data.username, email=data.email)

        if self._get_user_by_username(data.username):
            logger.warning("auth_register_failed", reason="username_exists", username=data.username)
            raise UserAlreadyExistsError("username")

        if self._get_user_by_email(data.email):
            logger.warning("auth_register_failed", reason="email_exists", email=data.email)
            raise UserAlreadyExistsError("email")

        user = User(
            email=data.email,
            username=data.username,
            hashed_password=get_password_hash(data.password),
            full_name=data.full_name,
        )
        self.db.add(user)

        default_tenant = Tenant(
            name=f"{data.username}'s Workspace",
            slug=f"{data.username}-{uuid.uuid4().hex[:8]}",
        )
        self.db.add(default_tenant)
        self.db.flush()

        admin_role = (
            self.db.execute(select(Role).where(Role.name == "admin"))
            .scalar_one_or_none()
        )
        if not admin_role:
            admin_role = Role(name="admin", description="Administrator role", is_system=True)
            self.db.add(admin_role)
            self.db.flush()

        user_role = UserRole(user_id=user.id, tenant_id=default_tenant.id, role_id=admin_role.id)
        self.db.add(user_role)

        self.db.commit()
        self.db.refresh(user)
        logger.info("auth_register_success", user_id=str(user.id), username=data.username)
        return user

    def authenticate(self, data: UserLogin) -> User:
        logger.debug("auth_login_attempt", username=data.username)

        user = self._get_user_by_username(data.username)
        if not user or not verify_password(data.password, user.hashed_password):
            logger.warning("auth_login_failed", reason="invalid_credentials", username=data.username)
            raise InvalidCredentialsError()

        if not user.is_active:
            logger.warning("auth_login_failed", reason="inactive_user", user_id=str(user.id))
            raise AuthError("User account is disabled")

        logger.info("auth_login_success", user_id=str(user.id), username=data.username)
        return user

    def create_tokens(self, user: User, tenant_id: Optional[uuid.UUID] = None) -> dict:
        token_data = {"sub": str(user.id), "username": user.username}
        if tenant_id:
            token_data["tenant_id"] = str(tenant_id)

        return {
            "access_token": create_access_token(token_data),
            "refresh_token": create_refresh_token(token_data),
            "token_type": "bearer",
            "expires_in": ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        }

    def refresh_tokens(self, refresh_token: str) -> dict:
        payload = verify_token(refresh_token, expected_type="refresh")
        if not payload:
            raise TokenInvalidError()

        user_id = payload.get("sub")
        if not user_id:
            raise TokenInvalidError()

        user = self.get_user_by_id(uuid.UUID(user_id))
        if not user or not user.is_active:
            raise InvalidCredentialsError()

        tenant_id = payload.get("tenant_id")
        return self.create_tokens(user, uuid.UUID(tenant_id) if tenant_id else None)

    def get_user_response(self, user: User) -> UserResponse:
        return UserResponse.model_validate(user)


def get_auth_service(db: Session) -> AuthService:
    return AuthService(db)
