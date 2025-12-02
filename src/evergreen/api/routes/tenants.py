"""
Tenant management API routes.
"""

from typing import Annotated, Any
from uuid import UUID

import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from evergreen.auth.schemas import TenantCreate, TenantResponse
from evergreen.auth.dependencies import CurrentUser, CurrentTenant, AdminUser
from evergreen.db import get_db
from evergreen.services.tenant import TenantService

logger = structlog.get_logger()

router = APIRouter(prefix="/tenants", tags=["Tenants"])


@router.post("/", response_model=TenantResponse, status_code=status.HTTP_201_CREATED)
async def create_tenant(
    request: TenantCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: AdminUser,  # Only admins can create tenants directly
) -> TenantResponse:
    """
    Create a new tenant (admin only).
    
    For self-service tenant creation, use /auth/register instead.
    """
    tenant_service = TenantService(db)
    
    try:
        tenant = await tenant_service.create(
            name=request.name,
            slug=request.slug,
        )
        
        return TenantResponse(
            id=tenant.id,
            name=tenant.name,
            slug=tenant.slug,
            is_active=tenant.is_active,
            documents_indexed=tenant.documents_indexed,
            created_at=tenant.created_at,
            updated_at=tenant.updated_at,
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.get("/current", response_model=TenantResponse)
async def get_current_tenant(
    db: Annotated[AsyncSession, Depends(get_db)],
    tenant_id: CurrentTenant,
) -> TenantResponse:
    """
    Get the current user's tenant.
    """
    tenant_service = TenantService(db)
    tenant = await tenant_service.get(tenant_id)
    
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found",
        )
    
    # Check for connections
    m365_connected = False
    google_connected = False
    for conn in tenant.connections:
        if conn.provider == "m365" and conn.status == "connected":
            m365_connected = True
        elif conn.provider == "google" and conn.status == "connected":
            google_connected = True
    
    return TenantResponse(
        id=tenant.id,
        name=tenant.name,
        slug=tenant.slug,
        is_active=tenant.is_active,
        m365_connected=m365_connected,
        google_connected=google_connected,
        documents_indexed=tenant.documents_indexed,
        created_at=tenant.created_at,
        updated_at=tenant.updated_at,
    )


@router.get("/{tenant_id}", response_model=TenantResponse)
async def get_tenant(
    tenant_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_tenant: CurrentTenant,
) -> TenantResponse:
    """
    Get tenant by ID.
    
    Users can only access their own tenant.
    """
    # Tenant isolation: users can only see their own tenant
    if tenant_id != current_tenant:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this tenant",
        )
    
    tenant_service = TenantService(db)
    tenant = await tenant_service.get(tenant_id)
    
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found",
        )
    
    return TenantResponse(
        id=tenant.id,
        name=tenant.name,
        slug=tenant.slug,
        is_active=tenant.is_active,
        documents_indexed=tenant.documents_indexed,
        created_at=tenant.created_at,
        updated_at=tenant.updated_at,
    )


class TenantUpdate(TenantCreate):
    """Tenant update request."""
    name: str | None = None
    slug: str | None = None


@router.patch("/{tenant_id}", response_model=TenantResponse)
async def update_tenant(
    tenant_id: UUID,
    request: TenantUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: AdminUser,  # Only admins can update tenant
    current_tenant: CurrentTenant,
) -> TenantResponse:
    """
    Update tenant (admin only).
    """
    if tenant_id != current_tenant:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this tenant",
        )
    
    tenant_service = TenantService(db)
    
    updates = {k: v for k, v in request.model_dump().items() if v is not None}
    tenant = await tenant_service.update(tenant_id, **updates)
    
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found",
        )
    
    return TenantResponse(
        id=tenant.id,
        name=tenant.name,
        slug=tenant.slug,
        is_active=tenant.is_active,
        documents_indexed=tenant.documents_indexed,
        created_at=tenant.created_at,
        updated_at=tenant.updated_at,
    )
