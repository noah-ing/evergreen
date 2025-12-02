"""
Core data models for Evergreen.

Pydantic models representing documents, entities, and other domain objects.
"""

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


# =============================================================================
# Enums
# =============================================================================

class DataSource(str, Enum):
    """Supported data source types."""
    M365_EMAIL = "m365_email"
    M365_FILE = "m365_file"
    M365_TEAMS = "m365_teams"
    M365_CALENDAR = "m365_calendar"
    GOOGLE_EMAIL = "google_email"
    GOOGLE_FILE = "google_file"
    GOOGLE_CALENDAR = "google_calendar"
    SLACK = "slack"


class EntityType(str, Enum):
    """Types of entities that can be extracted."""
    PERSON = "person"
    ORGANIZATION = "organization"
    PROJECT = "project"
    TOPIC = "topic"
    DATE = "date"
    LOCATION = "location"


class DocumentStatus(str, Enum):
    """Status of a document in the pipeline."""
    PENDING = "pending"
    PROCESSING = "processing"
    INDEXED = "indexed"
    FAILED = "failed"


# =============================================================================
# Base Models
# =============================================================================

class TimestampedModel(BaseModel):
    """Base model with timestamp fields."""
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class TenantModel(TimestampedModel):
    """Base model with tenant isolation."""
    tenant_id: UUID


# =============================================================================
# Document Models
# =============================================================================

class Participant(BaseModel):
    """A participant in a communication (email, chat, meeting)."""
    email: str
    name: str | None = None
    role: str  # "from", "to", "cc", "bcc", "attendee", "organizer"


class RawDocument(BaseModel):
    """A document before processing."""
    id: str = Field(default_factory=lambda: str(uuid4()))
    tenant_id: UUID
    source: DataSource
    source_id: str  # ID from the source system
    title: str | None = None
    body: str
    participants: list[Participant] = Field(default_factory=list)
    thread_id: str | None = None  # For grouping conversations
    timestamp: datetime
    metadata: dict[str, Any] = Field(default_factory=dict)


class DocumentChunk(BaseModel):
    """A chunk of a document ready for embedding."""
    id: str = Field(default_factory=lambda: str(uuid4()))
    document_id: str
    tenant_id: UUID
    content: str
    chunk_index: int
    token_count: int
    metadata: dict[str, Any] = Field(default_factory=dict)


class IndexedDocument(TenantModel):
    """A fully processed and indexed document."""
    id: str
    source: DataSource
    source_id: str
    title: str | None
    status: DocumentStatus
    chunk_ids: list[str] = Field(default_factory=list)
    entity_ids: list[str] = Field(default_factory=list)
    timestamp: datetime
    indexed_at: datetime | None = None
    error_message: str | None = None


# =============================================================================
# Entity Models
# =============================================================================

class Entity(TenantModel):
    """An extracted entity (person, company, project, etc.)."""
    id: str = Field(default_factory=lambda: str(uuid4()))
    type: EntityType
    name: str
    aliases: list[str] = Field(default_factory=list)
    confidence: float = 1.0
    metadata: dict[str, Any] = Field(default_factory=dict)
    
    # For entity resolution
    canonical_id: str | None = None  # Points to the "main" entity if this is a duplicate
    
    # Tracking
    first_seen: datetime = Field(default_factory=datetime.utcnow)
    last_seen: datetime = Field(default_factory=datetime.utcnow)
    mention_count: int = 1


class EntityMention(BaseModel):
    """A mention of an entity in a document."""
    entity_id: str
    document_id: str
    chunk_id: str
    start_char: int
    end_char: int
    context: str  # Surrounding text for context


class Relationship(TenantModel):
    """A relationship between two entities."""
    id: str = Field(default_factory=lambda: str(uuid4()))
    source_entity_id: str
    target_entity_id: str
    relationship_type: str  # "works_at", "collaborates_with", "authored", etc.
    strength: float = 1.0  # How strong is this relationship (based on co-occurrence)
    metadata: dict[str, Any] = Field(default_factory=dict)
    
    first_seen: datetime = Field(default_factory=datetime.utcnow)
    last_seen: datetime = Field(default_factory=datetime.utcnow)
    evidence_count: int = 1  # Number of documents supporting this relationship


# =============================================================================
# Query Models
# =============================================================================

class QueryFilters(BaseModel):
    """Filters for a query."""
    date_range: tuple[datetime, datetime] | None = None
    sources: list[DataSource] | None = None
    entity_ids: list[str] | None = None
    people: list[str] | None = None  # Email addresses


class QueryRequest(BaseModel):
    """A natural language query request."""
    query: str
    tenant_id: UUID
    filters: QueryFilters | None = None
    max_sources: int = 10
    include_sources: bool = True


class SourceCitation(BaseModel):
    """A source citation in a query response."""
    document_id: str
    chunk_id: str
    source: DataSource
    title: str | None
    timestamp: datetime
    snippet: str
    relevance_score: float


class QueryResponse(BaseModel):
    """Response to a natural language query."""
    query_id: str = Field(default_factory=lambda: str(uuid4()))
    answer: str
    confidence: float
    sources: list[SourceCitation] = Field(default_factory=list)
    entities_mentioned: list[Entity] = Field(default_factory=list)
    related_queries: list[str] = Field(default_factory=list)
    processing_time_ms: int


# =============================================================================
# Sync Models
# =============================================================================

class SyncState(TenantModel):
    """State of a sync operation."""
    id: str = Field(default_factory=lambda: str(uuid4()))
    source: DataSource
    delta_token: str | None = None  # For incremental sync
    last_sync_at: datetime | None = None
    documents_synced: int = 0
    status: str = "idle"  # idle, running, completed, failed
    error_message: str | None = None


# =============================================================================
# Tenant Models
# =============================================================================

class Tenant(TimestampedModel):
    """A tenant (organization) in the system."""
    id: UUID = Field(default_factory=uuid4)
    name: str
    slug: str  # URL-safe identifier
    
    # Connection status
    m365_connected: bool = False
    google_connected: bool = False
    slack_connected: bool = False
    
    # Usage
    documents_indexed: int = 0
    queries_this_month: int = 0
    
    # Settings
    settings: dict[str, Any] = Field(default_factory=dict)
