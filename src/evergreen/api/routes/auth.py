"""
Authentication API routes.
"""

from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from evergreen.auth.schemas import (
    TokenPair,
    UserCreate,
    UserLogin,
    UserResponse,
    TenantCreate,
    TenantResponse,
)
from evergreen.auth.dependencies import CurrentUser
from evergreen.db import get_db
from evergreen.services.auth import AuthService

logger = structlog.get_logger()

router = APIRouter(prefix="/auth", tags=["Authentication"])


class RegisterRequest(UserCreate):
    """Registration request with tenant info."""
    tenant_name: str | None = None
    tenant_slug: str | None = None


class RegisterResponse(UserResponse):
    """Registration response with tokens."""
    tokens: TokenPair


@router.post("/register", response_model=RegisterResponse, status_code=status.HTTP_201_CREATED)
async def register(
    request: RegisterRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> RegisterResponse:
    """
    Register a new user and tenant.
    
    Creates a new tenant if tenant_name and tenant_slug provided,
    or joins existing tenant if tenant_id provided.
    """
    auth_service = AuthService(db)
    
    try:
        user, tokens = await auth_service.register(
            email=request.email,
            password=request.password,
            name=request.name,
            tenant_name=request.tenant_name,
            tenant_slug=request.tenant_slug,
            tenant_id=request.tenant_id,
        )
        
        return RegisterResponse(
            id=user.id,
            email=user.email,
            name=user.name,
            tenant_id=user.tenant_id,
            role=user.role,
            is_active=user.is_active,
            created_at=user.created_at,
            tokens=tokens,
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.post("/login", response_model=TokenPair)
async def login(
    request: UserLogin,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> TokenPair:
    """
    Authenticate user and get tokens.
    """
    auth_service = AuthService(db)
    
    try:
        user, tokens = await auth_service.login(
            email=request.email,
            password=request.password,
        )
        return tokens
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        )


from pydantic import BaseModel


class RefreshRequest(BaseModel):
    """Token refresh request - only needs refresh_token."""
    refresh_token: str


@router.post("/refresh", response_model=TokenPair)
async def refresh_token(
    request: RefreshRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> TokenPair:
    """
    Refresh access token using refresh token.
    """
    auth_service = AuthService(db)
    
    try:
        tokens = await auth_service.refresh(request.refresh_token)
        return tokens
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        )


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> UserResponse:
    """
    Get current authenticated user info.
    """
    from evergreen.services.user import UserService
    from uuid import UUID
    
    user_service = UserService(db)
    user = await user_service.get(UUID(current_user.sub))
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    
    return UserResponse(
        id=user.id,
        email=user.email,
        name=user.name,
        tenant_id=user.tenant_id,
        role=user.role,
        is_active=user.is_active,
        created_at=user.created_at,
    )
