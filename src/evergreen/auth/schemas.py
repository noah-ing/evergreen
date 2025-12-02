"""
Pydantic schemas for authentication.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


class Token(BaseModel):
    """JWT token response."""
    access_token: str
    token_type: str = "bearer"
    expires_in: int = Field(description="Token lifetime in seconds")


class TokenPair(BaseModel):
    """Access and refresh token pair."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class TokenData(BaseModel):
    """Decoded token payload."""
    sub: str  # User ID
    tenant_id: UUID
    email: str
    role: str = "user"
    exp: datetime


class UserCreate(BaseModel):
    """User registration request."""
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    name: str = Field(min_length=1, max_length=255)
    tenant_id: UUID | None = None  # If joining existing tenant


class UserLogin(BaseModel):
    """User login request."""
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    """User response (no sensitive data)."""
    model_config = {"from_attributes": True}
    
    id: UUID
    email: str
    name: str
    tenant_id: UUID
    role: str
    is_active: bool
    created_at: datetime


class TenantCreate(BaseModel):
    """Tenant creation request."""
    name: str = Field(min_length=1, max_length=255)
    slug: str = Field(min_length=1, max_length=100, pattern=r"^[a-z0-9-]+$")


class TenantResponse(BaseModel):
    """Tenant response."""
    model_config = {"from_attributes": True}
    
    id: UUID
    name: str
    slug: str
    is_active: bool
    m365_connected: bool = False
    google_connected: bool = False
    documents_indexed: int = 0
    created_at: datetime
    updated_at: datetime
