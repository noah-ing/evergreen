"""
JWT token handling.

Creates and validates JWT tokens with tenant claims.
"""

from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

import structlog
from jose import JWTError, jwt
from pydantic import BaseModel

from evergreen.config import settings

logger = structlog.get_logger()


class TokenData(BaseModel):
    """Decoded token data."""
    sub: str  # User ID
    tenant_id: UUID
    email: str
    role: str = "user"
    exp: datetime
    token_type: str = "access"


class TokenError(Exception):
    """Token validation error."""
    pass


def create_access_token(
    user_id: str,
    tenant_id: UUID,
    email: str,
    role: str = "user",
    expires_delta: timedelta | None = None,
) -> str:
    """
    Create a JWT access token.
    
    Args:
        user_id: User identifier
        tenant_id: Tenant identifier
        email: User email
        role: User role (user, admin)
        expires_delta: Custom expiration time
        
    Returns:
        Encoded JWT token
    """
    if expires_delta is None:
        expires_delta = timedelta(minutes=settings.access_token_expire_minutes)
    
    expire = datetime.now(timezone.utc) + expires_delta
    
    payload = {
        "sub": str(user_id),
        "tenant_id": str(tenant_id),
        "email": email,
        "role": role,
        "exp": expire,
        "iat": datetime.now(timezone.utc),
        "token_type": "access",
    }
    
    token = jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
    
    logger.debug(
        "Access token created",
        user_id=user_id,
        tenant_id=str(tenant_id),
        expires_at=expire.isoformat(),
    )
    
    return token


def create_refresh_token(
    user_id: str,
    tenant_id: UUID,
    expires_delta: timedelta | None = None,
) -> str:
    """
    Create a JWT refresh token.
    
    Args:
        user_id: User identifier
        tenant_id: Tenant identifier
        expires_delta: Custom expiration time
        
    Returns:
        Encoded JWT refresh token
    """
    if expires_delta is None:
        expires_delta = timedelta(days=settings.refresh_token_expire_days)
    
    expire = datetime.now(timezone.utc) + expires_delta
    
    payload = {
        "sub": str(user_id),
        "tenant_id": str(tenant_id),
        "exp": expire,
        "iat": datetime.now(timezone.utc),
        "token_type": "refresh",
    }
    
    token = jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
    
    logger.debug(
        "Refresh token created",
        user_id=user_id,
        expires_at=expire.isoformat(),
    )
    
    return token


def decode_token(token: str) -> TokenData:
    """
    Decode and validate a JWT token.
    
    Args:
        token: Encoded JWT token
        
    Returns:
        Decoded token data
        
    Raises:
        TokenError: If token is invalid or expired
    """
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
        )
        
        # Validate required fields
        if not payload.get("sub"):
            raise TokenError("Token missing subject")
        
        if not payload.get("tenant_id"):
            raise TokenError("Token missing tenant_id")
        
        return TokenData(
            sub=payload["sub"],
            tenant_id=UUID(payload["tenant_id"]),
            email=payload.get("email", ""),
            role=payload.get("role", "user"),
            exp=datetime.fromtimestamp(payload["exp"], tz=timezone.utc),
            token_type=payload.get("token_type", "access"),
        )
        
    except JWTError as e:
        logger.warning("Token decode failed", error=str(e))
        raise TokenError(f"Invalid token: {str(e)}")


def verify_token_type(token_data: TokenData, expected_type: str) -> bool:
    """
    Verify that token is of expected type.
    
    Args:
        token_data: Decoded token data
        expected_type: Expected token type (access, refresh)
        
    Returns:
        True if token type matches
    """
    return token_data.token_type == expected_type
