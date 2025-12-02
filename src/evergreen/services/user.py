"""
User management service.
"""

from datetime import datetime, timezone
from uuid import UUID

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from evergreen.auth.password import hash_password, verify_password
from evergreen.db.models import User

logger = structlog.get_logger()


class UserService:
    """Service for user CRUD operations."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(
        self,
        tenant_id: UUID,
        email: str,
        password: str,
        name: str,
        role: str = "user",
    ) -> User:
        """
        Create a new user.
        
        Args:
            tenant_id: Tenant the user belongs to
            email: User email (unique)
            password: Plain text password (will be hashed)
            name: Display name
            role: User role (user, admin)
            
        Returns:
            Created user
            
        Raises:
            ValueError: If email already exists
        """
        # Check email uniqueness
        existing = await self.get_by_email(email)
        if existing:
            raise ValueError(f"User with email '{email}' already exists")
        
        user = User(
            tenant_id=tenant_id,
            email=email.lower(),
            hashed_password=hash_password(password),
            name=name,
            role=role,
        )
        self.db.add(user)
        await self.db.flush()
        
        logger.info(
            "User created",
            user_id=str(user.id),
            tenant_id=str(tenant_id),
            email=email,
        )
        return user

    async def get(self, user_id: UUID) -> User | None:
        """Get user by ID."""
        return await self.db.get(User, user_id)

    async def get_by_email(self, email: str) -> User | None:
        """Get user by email."""
        result = await self.db.execute(
            select(User).where(User.email == email.lower())
        )
        return result.scalar_one_or_none()

    async def authenticate(self, email: str, password: str) -> User | None:
        """
        Authenticate user by email and password.
        
        Args:
            email: User email
            password: Plain text password
            
        Returns:
            User if credentials valid, None otherwise
        """
        user = await self.get_by_email(email)
        if not user:
            return None
        
        if not user.is_active:
            logger.warning("Login attempt for inactive user", email=email)
            return None
        
        if not verify_password(password, user.hashed_password):
            logger.warning("Invalid password", email=email)
            return None
        
        # Update last login
        user.last_login_at = datetime.now(timezone.utc)
        await self.db.flush()
        
        logger.info("User authenticated", user_id=str(user.id), email=email)
        return user

    async def list_by_tenant(
        self,
        tenant_id: UUID,
        limit: int = 50,
        offset: int = 0,
    ) -> list[User]:
        """List users for a tenant."""
        result = await self.db.execute(
            select(User)
            .where(User.tenant_id == tenant_id)
            .order_by(User.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())

    async def update(
        self,
        user_id: UUID,
        **updates,
    ) -> User | None:
        """
        Update user fields.
        
        Args:
            user_id: User to update
            **updates: Fields to update
            
        Returns:
            Updated user or None if not found
        """
        user = await self.get(user_id)
        if not user:
            return None
        
        allowed_fields = {"name", "role", "is_active"}
        for key, value in updates.items():
            if key in allowed_fields:
                setattr(user, key, value)
        
        # Special handling for password
        if "password" in updates:
            user.hashed_password = hash_password(updates["password"])
        
        await self.db.flush()
        logger.info("User updated", user_id=str(user_id))
        return user

    async def delete(self, user_id: UUID) -> bool:
        """
        Soft delete a user (set is_active=False).
        
        Args:
            user_id: User to delete
            
        Returns:
            True if deleted, False if not found
        """
        user = await self.get(user_id)
        if not user:
            return False
        
        user.is_active = False
        await self.db.flush()
        logger.info("User deleted", user_id=str(user_id))
        return True
