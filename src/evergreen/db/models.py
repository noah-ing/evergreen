"""
SQLAlchemy database models.

Defines all persistent entities for Evergreen.
"""

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from evergreen.db import Base

if TYPE_CHECKING:
    pass


class Tenant(Base):
    """
    Tenant (organization) model.
    
    Each SMB client is a tenant with isolated data.
    """
    __tablename__ = "tenants"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    
    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    
    # Settings stored as JSON
    settings: Mapped[dict] = mapped_column(JSONB, default=dict)
    
    # Stats (denormalized for quick access)
    documents_indexed: Mapped[int] = mapped_column(Integer, default=0)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    # Relationships
    users: Mapped[list["User"]] = relationship(back_populates="tenant")
    connections: Mapped[list["Connection"]] = relationship(back_populates="tenant")


class User(Base):
    """
    User model.
    
    Users belong to a tenant and have roles.
    """
    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    tenant_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
    )
    
    # Auth
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    
    # Profile
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(50), default="user")  # user, admin
    
    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    last_login_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Relationships
    tenant: Mapped["Tenant"] = relationship(back_populates="users")


class Connection(Base):
    """
    External service connection (M365, Google).
    
    Stores credentials and sync state per tenant.
    """
    __tablename__ = "connections"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    tenant_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
    )
    
    # Provider info
    provider: Mapped[str] = mapped_column(String(50), nullable=False)  # m365, google
    
    # Encrypted credentials (encrypt before storing!)
    credentials_encrypted: Mapped[bytes | None] = mapped_column(nullable=True)
    
    # Status
    status: Mapped[str] = mapped_column(String(50), default="pending")
    # pending, connected, error, disconnected
    
    # Sync state
    last_sync_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    sync_cursor: Mapped[dict] = mapped_column(JSONB, default=dict)
    # Stores delta tokens, page tokens, etc.
    
    # Error tracking
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_count: Mapped[int] = mapped_column(Integer, default=0)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    # Relationships
    tenant: Mapped["Tenant"] = relationship(back_populates="connections")


class SyncJob(Base):
    """
    Sync job record.
    
    Tracks sync operations for audit and debugging.
    """
    __tablename__ = "sync_jobs"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    tenant_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
    )
    connection_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("connections.id", ondelete="CASCADE"),
        nullable=False,
    )
    
    # Job info
    job_type: Mapped[str] = mapped_column(String(50), nullable=False)
    # full_sync, delta_sync, webhook
    
    status: Mapped[str] = mapped_column(String(50), default="pending")
    # pending, running, completed, failed
    
    # Progress
    documents_processed: Mapped[int] = mapped_column(Integer, default=0)
    documents_failed: Mapped[int] = mapped_column(Integer, default=0)
    
    # Timing
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    
    # Error details
    errors: Mapped[list] = mapped_column(JSONB, default=list)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )


class AuditLog(Base):
    """
    Audit log for security and compliance.
    
    Tracks all significant actions.
    """
    __tablename__ = "audit_log"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    tenant_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
    )
    
    # Actor
    user_id: Mapped[UUID | None] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
    )
    user_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    
    # Action
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    # query, sync, connect, disconnect, user_create, etc.
    
    # Resource
    resource_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    resource_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    
    # Details
    details: Mapped[dict] = mapped_column(JSONB, default=dict)
    
    # Request info
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(500), nullable=True)
    
    # Timestamp
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        index=True,
    )
