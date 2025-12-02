"""
FastAPI application entry point.

Main API server for Evergreen.
"""

from contextlib import asynccontextmanager
from datetime import datetime
from typing import Annotated, Any
from uuid import UUID

import structlog
from fastapi import FastAPI, HTTPException, status, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from evergreen import __version__
from evergreen.config import settings
from evergreen.models import QueryRequest, QueryResponse
from evergreen.db import init_db, close_db, get_db
from evergreen.auth.dependencies import CurrentUser, CurrentTenant
from evergreen.api.routes import auth_router, tenants_router

logger = structlog.get_logger()


# =============================================================================
# Lifespan Management
# =============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler for startup/shutdown."""
    # Startup
    logger.info(
        "Starting Evergreen",
        version=__version__,
        environment=settings.environment,
    )
    
    # Run database migrations
    try:
        import subprocess
        result = subprocess.run(
            ["alembic", "upgrade", "head"],
            capture_output=True,
            text=True,
            timeout=60
        )
        if result.returncode == 0:
            logger.info("Database migrations completed successfully")
        else:
            logger.error("Migration failed", stderr=result.stderr)
    except Exception as e:
        logger.error("Migration error", error=str(e))
    
    # Initialize database connection
    await init_db()
    logger.info("Database initialized")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Evergreen")
    await close_db()


# =============================================================================
# Application Setup
# =============================================================================

app = FastAPI(
    title="Evergreen",
    description="Institutional Memory as a Service - Cross-system knowledge retrieval for SMBs",
    version=__version__,
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.is_development else ["https://app.evergreen.ai"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth_router, prefix="/api/v1")
app.include_router(tenants_router, prefix="/api/v1")


# =============================================================================
# Health & Info Endpoints
# =============================================================================

class HealthResponse(BaseModel):
    status: str
    version: str
    environment: str
    timestamp: datetime
    database: str = "unknown"


@app.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Health check endpoint with database connectivity."""
    from sqlalchemy import text
    from evergreen.db import get_session_factory
    
    db_status = "disconnected"
    try:
        async with get_session_factory()() as session:
            await session.execute(text("SELECT 1"))
            db_status = "connected"
    except Exception as e:
        logger.error("Database health check failed", error=str(e))
        db_status = f"error: {type(e).__name__}"
    
    return HealthResponse(
        status="healthy" if db_status == "connected" else "degraded",
        version=__version__,
        environment=settings.environment,
        timestamp=datetime.utcnow(),
        database=db_status,
    )


@app.get("/healthz")
async def healthz() -> dict[str, str]:
    """Simple liveness probe - no DB check."""
    return {"status": "ok"}


@app.get("/")
async def root() -> dict[str, str]:
    """Root endpoint with basic info."""
    return {
        "name": "Evergreen",
        "version": __version__,
        "docs": "/docs",
    }


# =============================================================================
# Connection Endpoints (protected)
# =============================================================================

class M365ConnectRequest(BaseModel):
    azure_tenant_id: str
    azure_client_id: str
    azure_client_secret: str


class ConnectionResponse(BaseModel):
    success: bool
    message: str


@app.post("/api/v1/connect/m365", response_model=ConnectionResponse)
async def connect_m365(
    request: M365ConnectRequest,
    user: CurrentUser,
    tenant_id: CurrentTenant,
) -> ConnectionResponse:
    """Connect M365 to current tenant."""
    # TODO: Store encrypted credentials and initiate sync
    logger.info("M365 connection initiated", tenant_id=str(tenant_id))
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="M365 connection not yet implemented",
    )


# =============================================================================
# Query Endpoints (protected)
# =============================================================================

class QueryRequestBody(BaseModel):
    """Query request without tenant_id (taken from auth)."""
    query: str
    top_k: int = 10
    filters: dict[str, Any] | None = None
    include_entities: bool = True


@app.post("/api/v1/query", response_model=QueryResponse)
async def query_knowledge(
    request: QueryRequestBody,
    user: CurrentUser,
    tenant_id: CurrentTenant,
) -> QueryResponse:
    """
    Execute a natural language query against the knowledge base.
    
    This is the main endpoint for querying institutional knowledge.
    Tenant is automatically determined from auth token.
    """
    from evergreen.retrieval import RetrievalEngine
    
    logger.info(
        "Query received",
        tenant_id=str(tenant_id),
        user_id=user.sub,
        query=request.query[:100],
    )
    
    try:
        engine = RetrievalEngine()
        result = await engine.query(
            tenant_id=str(tenant_id),
            query=request.query,
            top_k=request.top_k,
            filters=request.filters,
            include_graph=request.include_entities,
        )
        
        return QueryResponse(
            tenant_id=tenant_id,
            answer=result.answer,
            sources=[
                {
                    "chunk_id": s.get("id"),
                    "document_id": s.get("document_id"),
                    "content": s.get("content"),
                    "score": s.get("score", 0) or s.get("rerank_score", 0),
                    "metadata": s.get("metadata", {}),
                }
                for s in result.sources
            ],
            entities=result.entities,
            confidence=result.confidence,
        )
        
    except Exception as e:
        logger.error("Query failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Query failed: {str(e)}",
        )


# =============================================================================
# Sync Endpoints (protected)
# =============================================================================

class SyncStatusResponse(BaseModel):
    tenant_id: UUID
    status: str
    last_sync_at: datetime | None
    documents_synced: int
    errors: list[str]


@app.get("/api/v1/sync/status", response_model=SyncStatusResponse)
async def get_sync_status(
    user: CurrentUser,
    tenant_id: CurrentTenant,
) -> SyncStatusResponse:
    """Get sync status for current tenant."""
    # TODO: Implement sync status from database
    return SyncStatusResponse(
        tenant_id=tenant_id,
        status="idle",
        last_sync_at=None,
        documents_synced=0,
        errors=[],
    )


@app.post("/api/v1/sync/trigger")
async def trigger_sync(
    user: CurrentUser,
    tenant_id: CurrentTenant,
) -> dict[str, str]:
    """Manually trigger a sync for current tenant."""
    # TODO: Queue sync task with Celery
    logger.info("Sync triggered", tenant_id=str(tenant_id), user_id=user.sub)
    return {"status": "queued", "message": "Sync job has been queued"}


# =============================================================================
# Entity Endpoints (protected)
# =============================================================================

@app.get("/api/v1/entities")
async def list_entities(
    user: CurrentUser,
    tenant_id: CurrentTenant,
    entity_type: str | None = None,
    search: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> dict[str, Any]:
    """List entities for current tenant."""
    from evergreen.storage.graph import GraphStore
    
    try:
        graph_store = GraphStore()
        
        # Search by name pattern if provided
        pattern = search or ""
        entities = await graph_store.find_entities_by_name(
            tenant_id=str(tenant_id),
            name_pattern=pattern,
            entity_type=entity_type,
            limit=limit,
        )
        
        return {
            "tenant_id": str(tenant_id),
            "entities": entities,
            "count": len(entities),
        }
        
    except Exception as e:
        logger.error("Entity listing failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Entity listing failed: {str(e)}",
        )


@app.get("/api/v1/entities/{entity_id}")
async def get_entity(
    entity_id: str,
    user: CurrentUser,
    tenant_id: CurrentTenant,
) -> dict[str, Any]:
    """Get entity details including relationships."""
    from evergreen.retrieval import RetrievalEngine
    
    try:
        engine = RetrievalEngine()
        result = await engine.get_entity_context(
            tenant_id=str(tenant_id),
            entity_name=entity_id,  # Can be name or ID
        )
        
        if not result.get("found"):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Entity not found: {entity_id}",
            )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Entity retrieval failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Entity retrieval failed: {str(e)}",
        )


# =============================================================================
# Run with: uvicorn evergreen.api.main:app --reload
# =============================================================================
