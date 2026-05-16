"""Authentication API endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_current_user, get_current_active_user
from app.schemas.auth import Token, UserCreate, UserLogin, UserResponse
from app.services.auth_service import (
    AuthService,
    AuthError,
    UserAlreadyExistsError,
    InvalidCredentialsError,
)
from app.middleware.rate_limit import limiter

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("5/hour")
async def register(request: Request, data: UserCreate, db: Session = Depends(get_db)):
    """Register a new user account."""
    service = AuthService(db)
    try:
        user = service.register(data)
        return service.get_user_response(user)
    except UserAlreadyExistsError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=e.message)


@router.post("/login", response_model=Token)
@limiter.limit("10/minute")
async def login(request: Request, data: UserLogin, db: Session = Depends(get_db)):
    """Authenticate and return JWT tokens."""
    service = AuthService(db)
    try:
        user = service.authenticate(data)
        tokens = service.create_tokens(user)
        return tokens
    except InvalidCredentialsError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=e.message)
    except AuthError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=e.message)


@router.post("/refresh", response_model=Token)
async def refresh_tokens(refresh_token: str, db: Session = Depends(get_db)):
    """Refresh access token using a valid refresh token."""
    service = AuthService(db)
    try:
        return service.refresh_tokens(refresh_token)
    except AuthError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=e.message)


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user=Depends(get_current_active_user),
):
    """Get current authenticated user info."""
    service = AuthService(None)
    return service.get_user_response(current_user)
