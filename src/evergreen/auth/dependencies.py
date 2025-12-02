"""
FastAPI dependencies for authentication.

Provides reusable dependencies for route protection.
"""

from typing import Annotated
from uuid import UUID

import structlog
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from evergreen.auth.jwt import TokenData, TokenError, decode_token, verify_token_type

logger = structlog.get_logger()

# HTTP Bearer token extractor
bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
) -> TokenData:
    """
    Extract and validate current user from JWT token.
    
    Usage:
        @app.get("/protected")
        async def protected(user: TokenData = Depends(get_current_user)):
            return {"user_id": user.sub}
    
    Args:
        credentials: HTTP Bearer credentials
        
    Returns:
        Decoded token data
        
    Raises:
        HTTPException: If authentication fails
    """
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    try:
        token_data = decode_token(credentials.credentials)
        
        # Ensure it's an access token, not a refresh token
        if not verify_token_type(token_data, "access"):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        logger.debug(
            "User authenticated",
            user_id=token_data.sub,
            tenant_id=str(token_data.tenant_id),
        )
        
        return token_data
        
    except TokenError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_tenant(
    user: Annotated[TokenData, Depends(get_current_user)],
) -> UUID:
    """
    Extract tenant ID from authenticated user.
    
    Usage:
        @app.get("/tenant-data")
        async def get_data(tenant_id: UUID = Depends(get_current_tenant)):
            return {"tenant_id": tenant_id}
    
    Args:
        user: Current authenticated user
        
    Returns:
        Tenant UUID
    """
    return user.tenant_id


async def require_admin(
    user: Annotated[TokenData, Depends(get_current_user)],
) -> TokenData:
    """
    Require admin role for route access.
    
    Usage:
        @app.delete("/admin/users/{user_id}")
        async def delete_user(user: TokenData = Depends(require_admin)):
            ...
    
    Args:
        user: Current authenticated user
        
    Returns:
        Token data if user is admin
        
    Raises:
        HTTPException: If user is not admin
    """
    if user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return user


# Optional auth - allows unauthenticated access but provides user if present
async def get_optional_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
) -> TokenData | None:
    """
    Get current user if authenticated, None otherwise.
    
    Useful for routes that work differently for authenticated users.
    
    Args:
        credentials: HTTP Bearer credentials (optional)
        
    Returns:
        Token data or None
    """
    if credentials is None:
        return None
    
    try:
        token_data = decode_token(credentials.credentials)
        if verify_token_type(token_data, "access"):
            return token_data
    except TokenError:
        pass
    
    return None


# Type aliases for cleaner route signatures
CurrentUser = Annotated[TokenData, Depends(get_current_user)]
CurrentTenant = Annotated[UUID, Depends(get_current_tenant)]
AdminUser = Annotated[TokenData, Depends(require_admin)]
OptionalUser = Annotated[TokenData | None, Depends(get_optional_user)]
