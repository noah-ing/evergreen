"""
Authentication and authorization module.

Provides JWT-based authentication with multi-tenant support.
"""

from evergreen.auth.jwt import (
    create_access_token,
    create_refresh_token,
    decode_token,
    TokenData,
)
from evergreen.auth.dependencies import (
    get_current_user,
    get_current_tenant,
    require_admin,
)
from evergreen.auth.schemas import (
    Token,
    TokenPair,
    UserCreate,
    UserLogin,
    UserResponse,
)

__all__ = [
    # JWT
    "create_access_token",
    "create_refresh_token",
    "decode_token",
    "TokenData",
    # Dependencies
    "get_current_user",
    "get_current_tenant",
    "require_admin",
    # Schemas
    "Token",
    "TokenPair",
    "UserCreate",
    "UserLogin",
    "UserResponse",
]
