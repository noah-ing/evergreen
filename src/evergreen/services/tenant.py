"""
Tenant management service.
"""

from uuid import UUID

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from evergreen.db.models import Tenant

logger = structlog.get_logger()


class TenantService:
    """Service for tenant CRUD operations."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, name: str, slug: str) -> Tenant:
        """
        Create a new tenant.
        
        Args:
            name: Display name
            slug: URL-safe identifier (unique)
            
        Returns:
            Created tenant
            
        Raises:
            ValueError: If slug already exists
        """
        # Check slug uniqueness
        existing = await self.get_by_slug(slug)
        if existing:
            raise ValueError(f"Tenant with slug '{slug}' already exists")
        
        tenant = Tenant(name=name, slug=slug)
        self.db.add(tenant)
        await self.db.flush()
        
        logger.info("Tenant created", tenant_id=str(tenant.id), slug=slug)
        return tenant

    async def get(self, tenant_id: UUID) -> Tenant | None:
        """Get tenant by ID."""
        return await self.db.get(Tenant, tenant_id)

    async def get_by_slug(self, slug: str) -> Tenant | None:
        """Get tenant by slug."""
        result = await self.db.execute(
            select(Tenant).where(Tenant.slug == slug)
        )
        return result.scalar_one_or_none()

    async def list(
        self,
        limit: int = 50,
        offset: int = 0,
        active_only: bool = True,
    ) -> list[Tenant]:
        """List all tenants."""
        query = select(Tenant)
        if active_only:
            query = query.where(Tenant.is_active == True)
        query = query.order_by(Tenant.created_at.desc())
        query = query.limit(limit).offset(offset)
        
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def update(
        self,
        tenant_id: UUID,
        **updates,
    ) -> Tenant | None:
        """
        Update tenant fields.
        
        Args:
            tenant_id: Tenant to update
            **updates: Fields to update
            
        Returns:
            Updated tenant or None if not found
        """
        tenant = await self.get(tenant_id)
        if not tenant:
            return None
        
        allowed_fields = {"name", "settings", "is_active"}
        for key, value in updates.items():
            if key in allowed_fields:
                setattr(tenant, key, value)
        
        await self.db.flush()
        logger.info("Tenant updated", tenant_id=str(tenant_id))
        return tenant

    async def delete(self, tenant_id: UUID) -> bool:
        """
        Soft delete a tenant (set is_active=False).
        
        Args:
            tenant_id: Tenant to delete
            
        Returns:
            True if deleted, False if not found
        """
        tenant = await self.get(tenant_id)
        if not tenant:
            return False
        
        tenant.is_active = False
        await self.db.flush()
        logger.info("Tenant deleted", tenant_id=str(tenant_id))
        return True

    async def increment_documents(self, tenant_id: UUID, count: int = 1) -> None:
        """Increment document count for tenant."""
        tenant = await self.get(tenant_id)
        if tenant:
            tenant.documents_indexed += count
            await self.db.flush()
