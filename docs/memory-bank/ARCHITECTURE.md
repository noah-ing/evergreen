# System Architecture

> Detailed technical architecture for Evergreen

## Component Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              EVERGREEN SYSTEM                                │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐    │
│  │   M365       │  │   Google     │  │   Slack      │  │   Future     │    │
│  │   Connector  │  │   Connector  │  │   Connector  │  │   Connectors │    │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘    │
│         │                 │                 │                 │             │
│         └─────────────────┼─────────────────┼─────────────────┘             │
│                           │                 │                               │
│                           ▼                 ▼                               │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                     INGESTION ORCHESTRATOR                           │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌────────────┐  │   │
│  │  │ Document    │  │  Chunking   │  │  Entity     │  │  Embedding │  │   │
│  │  │ Parser      │  │  Engine     │  │  Extractor  │  │  Generator │  │   │
│  │  └─────────────┘  └─────────────┘  └─────────────┘  └────────────┘  │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                           │                                                 │
│         ┌─────────────────┼─────────────────┐                              │
│         ▼                 ▼                 ▼                              │
│  ┌─────────────┐  ┌─────────────────┐  ┌─────────────┐                     │
│  │   Qdrant    │  │    FalkorDB     │  │  Metadata   │                     │
│  │   Vector    │  │    Knowledge    │  │  Store      │                     │
│  │   Store     │  │    Graph        │  │  (Postgres) │                     │
│  └──────┬──────┘  └────────┬────────┘  └──────┬──────┘                     │
│         │                  │                  │                             │
│         └──────────────────┼──────────────────┘                             │
│                            ▼                                                │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                      RETRIEVAL ENGINE                                │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌────────────┐  │   │
│  │  │ Query       │  │  Hybrid     │  │  Graph      │  │  Reranker  │  │   │
│  │  │ Analyzer    │  │  Search     │  │  Traversal  │  │            │  │   │
│  │  └─────────────┘  └─────────────┘  └─────────────┘  └────────────┘  │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                            │                                                │
│                            ▼                                                │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                      RESPONSE LAYER                                  │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐                  │   │
│  │  │ Context     │  │  LLM        │  │  Citation   │                  │   │
│  │  │ Assembly    │  │  Synthesis  │  │  Generator  │                  │   │
│  │  └─────────────┘  └─────────────┘  └─────────────┘                  │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                            │                                                │
│                            ▼                                                │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                      API LAYER                                       │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐                  │   │
│  │  │ REST API    │  │  WebSocket  │  │  Webhooks   │                  │   │
│  │  │ (FastAPI)   │  │  (realtime) │  │  (events)   │                  │   │
│  │  └─────────────┘  └─────────────┘  └─────────────┘                  │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Data Flow

### 1. Ingestion Flow

```
┌─────────┐    ┌─────────────┐    ┌──────────┐    ┌─────────────┐
│  M365   │───▶│  Connector  │───▶│  Parser  │───▶│  Chunker    │
│  API    │    │  (delta     │    │  (email/ │    │  (semantic  │
│         │    │   sync)     │    │   docs)  │    │   aware)    │
└─────────┘    └─────────────┘    └──────────┘    └──────┬──────┘
                                                         │
                    ┌────────────────────────────────────┘
                    │
                    ▼
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│  Entity     │───▶│  Embedding  │───▶│  Storage    │
│  Extractor  │    │  Generator  │    │  (Qdrant +  │
│  (GLiNER)   │    │  (Voyage)   │    │   Falkor)   │
└─────────────┘    └─────────────┘    └─────────────┘
```

### 2. Query Flow

```
┌─────────┐    ┌─────────────┐    ┌──────────────┐    ┌──────────────┐
│  User   │───▶│  Query      │───▶│  Entity      │───▶│  Hybrid      │
│  Query  │    │  Analyzer   │    │  Detection   │    │  Search      │
└─────────┘    └─────────────┘    └──────────────┘    └──────┬───────┘
                                                              │
         ┌────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌──────────┐
│  Graph      │───▶│  Reranker   │───▶│  Context    │───▶│  LLM     │
│  Traversal  │    │  (Cohere)   │    │  Assembly   │    │  Answer  │
└─────────────┘    └─────────────┘    └─────────────┘    └──────────┘
```

---

## Module Details

### Connectors Module

```python
# evergreen/connectors/base.py
class BaseConnector(ABC):
    """Abstract base for all data source connectors."""
    
    @abstractmethod
    async def authenticate(self, credentials: dict) -> bool:
        """Authenticate with the data source."""
        pass
    
    @abstractmethod
    async def sync_delta(self, since: datetime) -> AsyncIterator[Document]:
        """Fetch documents changed since given timestamp."""
        pass
    
    @abstractmethod
    async def sync_full(self) -> AsyncIterator[Document]:
        """Full sync of all documents."""
        pass
```

**Supported connectors:**
- `M365Connector`: Email, OneDrive, SharePoint, Teams, Calendar
- `GoogleConnector`: Gmail, Drive, Calendar
- `SlackConnector`: Messages, channels, files (future)

### Ingestion Module

```python
# evergreen/ingestion/orchestrator.py
class IngestionOrchestrator:
    """Coordinates the full ingestion pipeline."""
    
    def __init__(
        self,
        parser: DocumentParser,
        chunker: SemanticChunker,
        extractor: EntityExtractor,
        embedder: EmbeddingGenerator,
        vector_store: VectorStore,
        graph_store: GraphStore,
    ):
        ...
    
    async def ingest(self, document: RawDocument) -> IndexedDocument:
        """Full ingestion pipeline for a single document."""
        parsed = await self.parser.parse(document)
        chunks = await self.chunker.chunk(parsed)
        entities = await self.extractor.extract(parsed)
        embeddings = await self.embedder.embed(chunks)
        
        await self.vector_store.upsert(chunks, embeddings)
        await self.graph_store.upsert_entities(entities)
        
        return IndexedDocument(...)
```

### Chunking Strategy

```python
# Chunking parameters by document type
CHUNKING_CONFIG = {
    "email": {
        "max_tokens": 512,
        "overlap": 50,
        "strategy": "thread_aware",  # Keep thread context
    },
    "document": {
        "max_tokens": 1024,
        "overlap": 100,
        "strategy": "section_aware",  # Respect headers
    },
    "chat_message": {
        "max_tokens": 256,
        "overlap": 0,
        "strategy": "thread_grouped",  # Group by thread
    },
    "meeting_notes": {
        "max_tokens": 1024,
        "overlap": 100,
        "strategy": "topic_segmented",
    },
}
```

### Entity Extraction

```python
# evergreen/extraction/entities.py
class EntityExtractor:
    """Hybrid entity extraction using GLiNER + LLM."""
    
    def __init__(self):
        self.gliner = GLiNER.from_pretrained("urchade/gliner_base")
        self.llm = get_llm()  # For complex cases
    
    async def extract(self, text: str) -> List[Entity]:
        # Fast extraction with GLiNER
        entities = self.gliner.predict_entities(
            text,
            labels=["person", "organization", "project", "date", "location"]
        )
        
        # LLM for topics/themes (requires semantic understanding)
        topics = await self._extract_topics_llm(text)
        
        return entities + topics
```

### Knowledge Graph Schema

```cypher
// Node types
CREATE (p:Person {
    id: STRING,
    name: STRING,
    email: STRING,
    aliases: [STRING],
    first_seen: DATETIME,
    last_seen: DATETIME
})

CREATE (o:Organization {
    id: STRING,
    name: STRING,
    type: STRING,  // client, vendor, partner
    aliases: [STRING]
})

CREATE (proj:Project {
    id: STRING,
    name: STRING,
    status: STRING,
    start_date: DATE,
    end_date: DATE
})

CREATE (doc:Document {
    id: STRING,
    source: STRING,  // email, file, chat
    title: STRING,
    created_at: DATETIME,
    chunk_ids: [STRING]  // References to vector store
})

// Relationship types
(p:Person)-[:WORKS_AT {since: DATE}]->(o:Organization)
(p:Person)-[:COLLABORATES_WITH {strength: FLOAT}]->(p:Person)
(p:Person)-[:AUTHORED]->(doc:Document)
(p:Person)-[:MENTIONED_IN]->(doc:Document)
(p:Person)-[:CONTRIBUTES_TO]->(proj:Project)
(o:Organization)-[:CLIENT_OF]->(o:Organization)
(doc:Document)-[:ABOUT]->(proj:Project)
(doc:Document)-[:REFERENCES]->(o:Organization)
```

### Retrieval Engine

```python
# evergreen/retrieval/engine.py
class RetrievalEngine:
    """Hybrid retrieval combining vector search + graph traversal."""
    
    async def retrieve(self, query: str, tenant_id: str) -> RetrievalResult:
        # 1. Analyze query for entities and intent
        analysis = await self.query_analyzer.analyze(query)
        
        # 2. Vector search for semantic similarity
        vector_results = await self.vector_store.search(
            query=query,
            filter={"tenant_id": tenant_id},
            limit=50
        )
        
        # 3. Graph traversal if entities detected
        if analysis.entities:
            graph_results = await self.graph_store.traverse(
                entities=analysis.entities,
                depth=2
            )
            # Merge and deduplicate
            vector_results = self._merge_results(vector_results, graph_results)
        
        # 4. Rerank with Cohere
        reranked = await self.reranker.rerank(
            query=query,
            documents=vector_results,
            top_k=10
        )
        
        return RetrievalResult(
            chunks=reranked,
            graph_context=graph_results.context if analysis.entities else None
        )
```

---

## Multi-Tenancy Architecture

Each SMB client is a "tenant" with strict data isolation:

```
┌─────────────────────────────────────────────────────────────┐
│                    TENANT ISOLATION                          │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────────┐  ┌─────────────────┐                  │
│  │   Tenant A      │  │   Tenant B      │                  │
│  │   (Acme Corp)   │  │   (Beta LLC)    │                  │
│  ├─────────────────┤  ├─────────────────┤                  │
│  │ Qdrant:         │  │ Qdrant:         │                  │
│  │  collection_a   │  │  collection_b   │                  │
│  │                 │  │                 │                  │
│  │ FalkorDB:       │  │ FalkorDB:       │                  │
│  │  graph_a        │  │  graph_b        │                  │
│  │                 │  │                 │                  │
│  │ Metadata:       │  │ Metadata:       │                  │
│  │  tenant_id=a    │  │  tenant_id=b    │                  │
│  └─────────────────┘  └─────────────────┘                  │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

**Isolation mechanisms:**
1. **Qdrant:** Separate collection per tenant
2. **FalkorDB:** Separate graph per tenant (native multi-tenancy)
3. **PostgreSQL:** All tables have tenant_id foreign key
4. **All queries:** Mandatory tenant_id filter
5. **API layer:** JWT with tenant_id claim, validated on every request

---

## Authentication & Authorization

### JWT Token Flow

```
┌──────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│  Client  │───▶│   /login    │───▶│  Validate   │───▶│  Generate   │
│          │    │   /register │    │  Credentials│    │  JWT Tokens │
└──────────┘    └─────────────┘    └─────────────┘    └──────┬──────┘
                                                              │
                                                              ▼
┌──────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│  Client  │◀───│  Response   │◀───│  Access +   │◀───│  Store in   │
│          │    │  with JWT   │    │  Refresh    │    │  Response   │
└──────────┘    └─────────────┘    └─────────────┘    └─────────────┘
```

### Token Structure

```python
# Access Token (30 min TTL)
{
    "sub": "user_uuid",
    "tenant_id": "tenant_uuid",
    "email": "user@company.com",
    "role": "admin",  # admin | member | viewer
    "exp": 1234567890,
    "iat": 1234567890,
    "token_type": "access"
}

# Refresh Token (7 day TTL)
{
    "sub": "user_uuid",
    "tenant_id": "tenant_uuid",
    "exp": 1234567890,
    "iat": 1234567890,
    "token_type": "refresh"
}
```

### Protected Endpoints

All `/api/v1/*` endpoints require valid JWT:

```python
# FastAPI dependency injection
@router.get("/api/v1/query")
async def query(
    current_user: Annotated[User, Depends(get_current_user)],
    tenant_id: Annotated[UUID, Depends(get_current_tenant)],
):
    # tenant_id automatically extracted from JWT
    # All queries scoped to this tenant
    ...
```

### Database Schema

```sql
-- Tenants table
CREATE TABLE tenants (
    id UUID PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    slug VARCHAR(100) UNIQUE NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    settings JSONB DEFAULT '{}',
    documents_indexed INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Users table
CREATE TABLE users (
    id UUID PRIMARY KEY,
    tenant_id UUID REFERENCES tenants(id) ON DELETE CASCADE,
    email VARCHAR(255) UNIQUE NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    name VARCHAR(255),
    role VARCHAR(50) DEFAULT 'member',
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    last_login_at TIMESTAMPTZ
);

-- OAuth connections
CREATE TABLE connections (
    id UUID PRIMARY KEY,
    tenant_id UUID REFERENCES tenants(id) ON DELETE CASCADE,
    provider VARCHAR(50) NOT NULL,  -- m365, google
    status VARCHAR(50) DEFAULT 'pending',
    credentials_encrypted BYTEA,
    last_sync_at TIMESTAMPTZ,
    sync_cursor TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Background sync jobs
CREATE TABLE sync_jobs (
    id UUID PRIMARY KEY,
    tenant_id UUID REFERENCES tenants(id) ON DELETE CASCADE,
    connection_id UUID REFERENCES connections(id),
    job_type VARCHAR(50) NOT NULL,
    status VARCHAR(50) DEFAULT 'pending',
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    error_message TEXT,
    documents_processed INTEGER DEFAULT 0
);

-- Audit log
CREATE TABLE audit_log (
    id UUID PRIMARY KEY,
    tenant_id UUID REFERENCES tenants(id),
    user_id UUID REFERENCES users(id),
    action VARCHAR(100) NOT NULL,
    details JSONB,
    ip_address INET,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

---

## Sync Strategy

### Initial Sync
1. Full historical sync (configurable lookback: 90/180/365 days)
2. Batched processing (100 items at a time)
3. Progress tracking in metadata store
4. Resume capability if interrupted

### Incremental Sync
1. Delta queries (M365) / History API (Google)
2. Webhook subscriptions for real-time updates
3. Fallback: Polling every 5 minutes

### Sync State Machine
```
┌─────────┐    ┌───────────────┐    ┌───────────┐
│  IDLE   │───▶│  SYNCING      │───▶│  INDEXED  │
└─────────┘    └───────────────┘    └───────────┘
     ▲                │                    │
     │                ▼                    │
     │         ┌───────────┐               │
     └─────────│   ERROR   │◀──────────────┘
               └───────────┘
```

---

## API Design

### REST Endpoints

**Authentication** (public)
```
POST   /api/v1/auth/register              # Register new tenant + user
POST   /api/v1/auth/login                 # Login, get tokens
POST   /api/v1/auth/refresh               # Refresh access token
GET    /api/v1/auth/me                    # Get current user (protected)
```

**Tenant Management** (protected)
```
GET    /api/v1/tenants/me                 # Get current tenant
PUT    /api/v1/tenants/me                 # Update tenant settings
GET    /api/v1/tenants/me/users           # List tenant users
POST   /api/v1/tenants/me/users           # Invite user to tenant
```

**Data Sources** (protected)
```
POST   /api/v1/connections/m365           # Connect M365
POST   /api/v1/connections/google         # Connect Google
GET    /api/v1/connections                # List connections
DELETE /api/v1/connections/{id}           # Disconnect source
```

**Query & Search** (protected)
```
POST   /api/v1/query                      # Natural language query
GET    /api/v1/entities                   # List entities
GET    /api/v1/entities/{id}              # Entity details + relationships
GET    /api/v1/entities/{id}/timeline     # Entity activity timeline
```

**Sync Management** (protected)
```
GET    /api/v1/sync/status                # Sync status
POST   /api/v1/sync/trigger               # Trigger manual sync
```

### Query Request/Response

```python
# Request
{
    "query": "What's our full history with Acme Corp?",
    "filters": {
        "date_range": {"start": "2024-01-01", "end": "2024-12-31"},
        "sources": ["email", "files"],
        "people": ["john@company.com"]
    },
    "options": {
        "include_sources": true,
        "max_sources": 10
    }
}

# Response
{
    "answer": "Your relationship with Acme Corp began in March 2024...",
    "confidence": 0.92,
    "sources": [
        {
            "id": "email_123",
            "type": "email",
            "title": "Re: Acme Corp Partnership",
            "date": "2024-03-15",
            "snippet": "...",
            "relevance": 0.95
        }
    ],
    "entities_mentioned": [
        {"type": "person", "name": "John Smith", "id": "person_456"},
        {"type": "organization", "name": "Acme Corp", "id": "org_789"}
    ],
    "related_queries": [
        "What contracts do we have with Acme Corp?",
        "Who is our main contact at Acme Corp?"
    ]
}
```

---

## Performance Targets

| Operation | Target | Notes |
|-----------|--------|-------|
| Query latency (P95) | <3s | Including LLM synthesis |
| Retrieval latency | <500ms | Vector + graph combined |
| Embedding throughput | 1000 docs/min | Batched processing |
| Incremental sync | <30s | For single new document |
| Initial sync (10k docs) | <4 hours | Parallelized |
