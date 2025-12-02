"""
Authentication service.

Handles login, registration, and token management.
"""

from uuid import UUID

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from evergreen.auth.jwt import (
    create_access_token,
    create_refresh_token,
    decode_token,
    verify_token_type,
    TokenError,
)
from evergreen.config import settings
from evergreen.auth.schemas import TokenPair
from evergreen.db.models import User
from evergreen.services.tenant import TenantService
from evergreen.services.user import UserService

logger = structlog.get_logger()


class AuthService:
    """Service for authentication operations."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.user_service = UserService(db)
        self.tenant_service = TenantService(db)

    async def register(
        self,
        email: str,
        password: str,
        name: str,
        tenant_name: str | None = None,
        tenant_slug: str | None = None,
        tenant_id: UUID | None = None,
    ) -> tuple[User, TokenPair]:
        """
        Register a new user.
        
        Either join existing tenant (tenant_id) or create new (tenant_name + tenant_slug).
        
        Args:
            email: User email
            password: User password
            name: User name
            tenant_name: Name for new tenant
            tenant_slug: Slug for new tenant
            tenant_id: Existing tenant to join
            
        Returns:
            Tuple of (user, tokens)
            
        Raises:
            ValueError: If registration fails
        """
        # Determine tenant
        if tenant_id:
            # Join existing tenant
            tenant = await self.tenant_service.get(tenant_id)
            if not tenant:
                raise ValueError("Tenant not found")
            role = "user"  # Non-admin when joining
        elif tenant_name and tenant_slug:
            # Create new tenant
            tenant = await self.tenant_service.create(tenant_name, tenant_slug)
            role = "admin"  # Creator is admin
        else:
            raise ValueError("Either tenant_id or (tenant_name + tenant_slug) required")
        
        # Create user
        user = await self.user_service.create(
            tenant_id=tenant.id,
            email=email,
            password=password,
            name=name,
            role=role,
        )
        
        # Generate tokens
        tokens = self._create_tokens(user)
        
        logger.info(
            "User registered",
            user_id=str(user.id),
            tenant_id=str(tenant.id),
            is_new_tenant=tenant_id is None,
        )
        
        return user, tokens

    async def login(self, email: str, password: str) -> tuple[User, TokenPair]:
        """
        Authenticate user and return tokens.
        
        Args:
            email: User email
            password: User password
            
        Returns:
            Tuple of (user, tokens)
            
        Raises:
            ValueError: If authentication fails
        """
        user = await self.user_service.authenticate(email, password)
        if not user:
            raise ValueError("Invalid email or password")
        
        tokens = self._create_tokens(user)
        
        logger.info("User logged in", user_id=str(user.id))
        return user, tokens

    async def refresh(self, refresh_token: str) -> TokenPair:
        """
        Refresh access token using refresh token.
        
        Args:
            refresh_token: Valid refresh token
            
        Returns:
            New token pair
            
        Raises:
            ValueError: If refresh token is invalid
        """
        try:
            token_data = decode_token(refresh_token)
        except TokenError as e:
            raise ValueError(f"Invalid refresh token: {e}")
        
        if not verify_token_type(token_data, "refresh"):
            raise ValueError("Invalid token type - expected refresh token")
        
        # Get user to verify still active
        user = await self.user_service.get(UUID(token_data.sub))
        if not user or not user.is_active:
            raise ValueError("User not found or inactive")
        
        tokens = self._create_tokens(user)
        
        logger.info("Token refreshed", user_id=token_data.sub)
        return tokens

    def _create_tokens(self, user: User) -> TokenPair:
        """Create access and refresh token pair for user."""
        access_token = create_access_token(
            user_id=str(user.id),
            tenant_id=user.tenant_id,
            email=user.email,
            role=user.role,
        )
        
        refresh_token = create_refresh_token(
            user_id=str(user.id),
            tenant_id=user.tenant_id,
        )
        
        return TokenPair(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=settings.access_token_expire_minutes * 60,
        )
