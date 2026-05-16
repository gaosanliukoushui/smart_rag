"""Tests for authentication service and JWT handling."""

import pytest
from datetime import timedelta
from uuid import uuid4

from app.core.security import (
    get_password_hash,
    verify_password,
    create_access_token,
    create_refresh_token,
    verify_token,
    decode_access_token,
    ACCESS_TOKEN_EXPIRE_MINUTES,
    REFRESH_TOKEN_EXPIRE_DAYS,
)
from app.services.auth_service import (
    AuthService,
    UserAlreadyExistsError,
    InvalidCredentialsError,
    TokenInvalidError,
)
from app.schemas.auth import UserCreate, UserLogin


class TestPasswordHashing:
    """Tests for password hashing functions."""

    def test_hash_password(self):
        password = "securepassword123"
        hashed = get_password_hash(password)
        assert hashed != password
        assert len(hashed) > 0

    def test_verify_correct_password(self):
        password = "securepassword123"
        hashed = get_password_hash(password)
        assert verify_password(password, hashed) is True

    def test_verify_wrong_password(self):
        password = "securepassword123"
        hashed = get_password_hash(password)
        assert verify_password("wrongpassword", hashed) is False

    def test_different_hashes_for_same_password(self):
        password = "securepassword123"
        hash1 = get_password_hash(password)
        hash2 = get_password_hash(password)
        assert hash1 != hash2
        assert verify_password(password, hash1) is True
        assert verify_password(password, hash2) is True


class TestJWTTokens:
    """Tests for JWT token creation and verification."""

    def test_create_access_token(self):
        data = {"sub": str(uuid4()), "username": "testuser"}
        token = create_access_token(data)
        assert isinstance(token, str)
        assert len(token) > 0

    def test_decode_access_token(self):
        user_id = str(uuid4())
        data = {"sub": user_id, "username": "testuser"}
        token = create_access_token(data)
        payload = decode_access_token(token)
        assert payload is not None
        assert payload["sub"] == user_id
        assert payload["type"] == "access"

    def test_decode_invalid_token(self):
        payload = decode_access_token("invalid.token.here")
        assert payload is None

    def test_access_token_has_correct_type(self):
        token = create_access_token({"sub": str(uuid4())})
        payload = decode_access_token(token)
        assert payload["type"] == "access"

    def test_refresh_token_has_correct_type(self):
        token = create_refresh_token({"sub": str(uuid4())})
        payload = verify_token(token, expected_type="refresh")
        assert payload is not None
        assert payload["type"] == "refresh"

    def test_verify_wrong_token_type(self):
        access_token = create_access_token({"sub": str(uuid4())})
        payload = verify_token(access_token, expected_type="refresh")
        assert payload is None

    def test_token_contains_username(self):
        data = {"sub": str(uuid4()), "username": "alice"}
        token = create_access_token(data)
        payload = decode_access_token(token)
        assert payload["username"] == "alice"

    def test_token_contains_tenant_id(self):
        tenant_id = str(uuid4())
        data = {"sub": str(uuid4()), "tenant_id": tenant_id}
        token = create_access_token(data)
        payload = decode_access_token(token)
        assert payload["tenant_id"] == tenant_id

    def test_token_expire_minutes_config(self):
        assert ACCESS_TOKEN_EXPIRE_MINUTES == 30

    def test_refresh_expire_days_config(self):
        assert REFRESH_TOKEN_EXPIRE_DAYS == 7


class TestAuthService:
    """Tests for AuthService."""

    @pytest.fixture
    def auth_service(self, db):
        return AuthService(db)

    def test_register_success(self, db, auth_service: AuthService):
        data = UserCreate(
            email="alice@example.com",
            username="alice",
            password="strongpassword123",
            full_name="Alice Smith",
        )
        user = auth_service.register(data)
        assert user.email == "alice@example.com"
        assert user.username == "alice"
        assert user.full_name == "Alice Smith"
        assert user.is_active is True
        assert user.hashed_password != "strongpassword123"

    def test_register_duplicate_username(self, db, auth_service: AuthService):
        data1 = UserCreate(email="a@example.com", username="bob", password="password123")
        auth_service.register(data1)

        data2 = UserCreate(email="b@example.com", username="bob", password="password456")
        with pytest.raises(UserAlreadyExistsError) as exc_info:
            auth_service.register(data2)
        assert "username" in exc_info.value.message

    def test_register_duplicate_email(self, db, auth_service: AuthService):
        data1 = UserCreate(email="alice@example.com", username="alice1", password="password123")
        auth_service.register(data1)

        data2 = UserCreate(email="alice@example.com", username="alice2", password="password456")
        with pytest.raises(UserAlreadyExistsError) as exc_info:
            auth_service.register(data2)
        assert "email" in exc_info.value.message

    def test_authenticate_correct_credentials(self, db, auth_service: AuthService):
        data = UserCreate(email="alice@example.com", username="alice", password="mypassword123")
        auth_service.register(data)

        login_data = UserLogin(username="alice", password="mypassword123")
        user = auth_service.authenticate(login_data)
        assert user.username == "alice"

    def test_authenticate_wrong_password(self, db, auth_service: AuthService):
        data = UserCreate(email="alice@example.com", username="alice", password="correctpassword")
        auth_service.register(data)

        login_data = UserLogin(username="alice", password="wrongpassword")
        with pytest.raises(InvalidCredentialsError):
            auth_service.authenticate(login_data)

    def test_authenticate_nonexistent_user(self, db, auth_service: AuthService):
        login_data = UserLogin(username="nonexistent", password="anypassword")
        with pytest.raises(InvalidCredentialsError):
            auth_service.authenticate(login_data)

    def test_authenticate_inactive_user(self, db, auth_service: AuthService):
        data = UserCreate(email="inactive@example.com", username="inactiveuser", password="password123")
        user = auth_service.register(data)
        user.is_active = False
        db.commit()

        login_data = UserLogin(username="inactiveuser", password="password123")
        from app.services.auth_service import AuthError
        with pytest.raises(AuthError):
            auth_service.authenticate(login_data)

    def test_create_tokens(self, db, auth_service: AuthService):
        data = UserCreate(email="alice@example.com", username="alice", password="password123")
        user = auth_service.register(data)

        tokens = auth_service.create_tokens(user)
        assert "access_token" in tokens
        assert "refresh_token" in tokens
        assert tokens["token_type"] == "bearer"
        assert tokens["expires_in"] == ACCESS_TOKEN_EXPIRE_MINUTES * 60

    def test_create_tokens_with_tenant(self, db, auth_service: AuthService):
        data = UserCreate(email="alice@example.com", username="alice", password="password123")
        user = auth_service.register(data)
        tenant_id = uuid4()

        tokens = auth_service.create_tokens(user, tenant_id)
        payload = decode_access_token(tokens["access_token"])
        assert payload["tenant_id"] == str(tenant_id)

    def test_refresh_tokens(self, db, auth_service: AuthService):
        data = UserCreate(email="alice@example.com", username="alice", password="password123")
        user = auth_service.register(data)
        tokens = auth_service.create_tokens(user)
        refresh_token = tokens["refresh_token"]

        new_tokens = auth_service.refresh_tokens(refresh_token)
        assert "access_token" in new_tokens
        assert "refresh_token" in new_tokens
        assert new_tokens["access_token"] != tokens["access_token"]

    def test_refresh_with_invalid_token(self, db, auth_service: AuthService):
        with pytest.raises(TokenInvalidError):
            auth_service.refresh_tokens("invalid-refresh-token")

    def test_refresh_with_access_token(self, db, auth_service: AuthService):
        data = UserCreate(email="alice@example.com", username="alice", password="password123")
        user = auth_service.register(data)
        tokens = auth_service.create_tokens(user)
        access_token = tokens["access_token"]

        with pytest.raises(TokenInvalidError):
            auth_service.refresh_tokens(access_token)

    def test_get_user_by_id(self, db, auth_service: AuthService):
        data = UserCreate(email="alice@example.com", username="alice", password="password123")
        user = auth_service.register(data)

        found = auth_service.get_user_by_id(user.id)
        assert found is not None
        assert found.username == "alice"

    def test_get_user_by_nonexistent_id(self, db, auth_service: AuthService):
        found = auth_service.get_user_by_id(uuid4())
        assert found is None

    def test_get_user_response(self, db, auth_service: AuthService):
        data = UserCreate(email="alice@example.com", username="alice", password="password123")
        user = auth_service.register(data)

        response = auth_service.get_user_response(user)
        assert response.email == "alice@example.com"
        assert response.username == "alice"
