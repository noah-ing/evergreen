"""
Vector storage using Qdrant.

Handles document chunk indexing and semantic search.
"""

from typing import Any
from uuid import UUID

import structlog
from qdrant_client import AsyncQdrantClient, models
from qdrant_client.models import (
    Distance,
    FieldCondition,
    Filter,
    MatchValue,
    PointStruct,
    SearchParams,
    VectorParams,
)

from evergreen.config import settings
from evergreen.models import DocumentChunk

logger = structlog.get_logger()


class VectorStore:
    """
    Qdrant-based vector storage for document chunks.
    
    Features:
    - Tenant isolation via collection prefixing
    - Hybrid search (dense + sparse when available)
    - Rich metadata filtering
    - Automatic collection management
    """

    def __init__(
        self,
        url: str | None = None,
        api_key: str | None = None,
        dimensions: int | None = None,
    ):
        """
        Initialize vector store connection.
        
        Args:
            url: Qdrant server URL (defaults to settings)
            api_key: Qdrant API key for cloud (defaults to settings)
            dimensions: Embedding dimensions (defaults to settings)
        """
        self.url = url or settings.qdrant_url
        self.api_key = api_key or settings.qdrant_api_key
        self.dimensions = dimensions or settings.embedding_dimensions
        
        # Initialize async client
        self._client = AsyncQdrantClient(
            url=self.url,
            api_key=self.api_key if self.api_key else None,
            timeout=60.0,
        )
        
        logger.info(
            "Vector store initialized",
            url=self.url,
            dimensions=self.dimensions,
        )

    def _collection_name(self, tenant_id: str) -> str:
        """Get collection name for a tenant."""
        return f"evergreen_{tenant_id}"

    async def ensure_collection(self, tenant_id: str) -> None:
        """
        Ensure collection exists for tenant.
        
        Args:
            tenant_id: Tenant identifier
        """
        collection_name = self._collection_name(tenant_id)
        
        collections = await self._client.get_collections()
        existing = [c.name for c in collections.collections]
        
        if collection_name not in existing:
            await self._client.create_collection(
                collection_name=collection_name,
                vectors_config=VectorParams(
                    size=self.dimensions,
                    distance=Distance.COSINE,
                ),
                # Enable sparse vectors for hybrid search
                sparse_vectors_config={
                    "text": models.SparseVectorParams(),
                },
                # Optimize for filtering
                optimizers_config=models.OptimizersConfigDiff(
                    indexing_threshold=20000,
                ),
            )
            
            # Create payload indices for common filters
            await self._client.create_payload_index(
                collection_name=collection_name,
                field_name="document_id",
                field_schema=models.PayloadSchemaType.KEYWORD,
            )
            await self._client.create_payload_index(
                collection_name=collection_name,
                field_name="source_type",
                field_schema=models.PayloadSchemaType.KEYWORD,
            )
            await self._client.create_payload_index(
                collection_name=collection_name,
                field_name="created_at",
                field_schema=models.PayloadSchemaType.DATETIME,
            )
            
            logger.info("Collection created", collection=collection_name)

    async def upsert(
        self,
        tenant_id: str,
        chunks: list[tuple[DocumentChunk, list[float]]],
    ) -> int:
        """
        Upsert document chunks with embeddings.
        
        Args:
            tenant_id: Tenant identifier
            chunks: List of (chunk, embedding) tuples
            
        Returns:
            Number of points upserted
        """
        if not chunks:
            return 0
        
        await self.ensure_collection(tenant_id)
        collection_name = self._collection_name(tenant_id)
        
        points = []
        for chunk, embedding in chunks:
            # Build payload from chunk metadata
            payload = {
                "document_id": chunk.document_id,
                "tenant_id": chunk.tenant_id,
                "chunk_index": chunk.chunk_index,
                "content": chunk.content,
                "source_type": chunk.metadata.get("source_type", "unknown"),
                "created_at": chunk.metadata.get("created_at"),
                "title": chunk.metadata.get("title"),
                "from_email": chunk.metadata.get("from"),
                "to_email": chunk.metadata.get("to"),
                **{k: v for k, v in chunk.metadata.items() if k not in [
                    "source_type", "created_at", "title", "from", "to"
                ]},
            }
            
            # Remove None values
            payload = {k: v for k, v in payload.items() if v is not None}
            
            point = PointStruct(
                id=str(chunk.id),
                vector=embedding,
                payload=payload,
            )
            points.append(point)
        
        # Batch upsert
        await self._client.upsert(
            collection_name=collection_name,
            points=points,
            wait=True,
        )
        
        logger.info(
            "Chunks upserted",
            tenant_id=tenant_id,
            count=len(points),
        )
        
        return len(points)

    async def search(
        self,
        tenant_id: str,
        query_embedding: list[float],
        limit: int = 10,
        score_threshold: float | None = None,
        filters: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """
        Search for similar chunks.
        
        Args:
            tenant_id: Tenant identifier
            query_embedding: Query vector
            limit: Maximum results to return
            score_threshold: Minimum similarity score
            filters: Metadata filters to apply
            
        Returns:
            List of search results with scores and payloads
        """
        collection_name = self._collection_name(tenant_id)
        
        # Build filter conditions
        filter_conditions = []
        if filters:
            for field, value in filters.items():
                if isinstance(value, list):
                    # OR condition for list values
                    filter_conditions.append(
                        FieldCondition(
                            key=field,
                            match=models.MatchAny(any=value),
                        )
                    )
                else:
                    filter_conditions.append(
                        FieldCondition(
                            key=field,
                            match=MatchValue(value=value),
                        )
                    )
        
        query_filter = Filter(must=filter_conditions) if filter_conditions else None
        
        results = await self._client.search(
            collection_name=collection_name,
            query_vector=query_embedding,
            query_filter=query_filter,
            limit=limit,
            score_threshold=score_threshold,
            with_payload=True,
            search_params=SearchParams(
                hnsw_ef=128,  # Higher for better recall
                exact=False,
            ),
        )
        
        return [
            {
                "id": result.id,
                "score": result.score,
                "content": result.payload.get("content"),
                "document_id": result.payload.get("document_id"),
                "metadata": {
                    k: v for k, v in result.payload.items()
                    if k not in ["content", "document_id", "tenant_id"]
                },
            }
            for result in results
        ]

    async def delete_by_document(
        self,
        tenant_id: str,
        document_id: str,
    ) -> int:
        """
        Delete all chunks for a document.
        
        Args:
            tenant_id: Tenant identifier
            document_id: Document ID to delete
            
        Returns:
            Number of points deleted
        """
        collection_name = self._collection_name(tenant_id)
        
        result = await self._client.delete(
            collection_name=collection_name,
            points_selector=models.FilterSelector(
                filter=Filter(
                    must=[
                        FieldCondition(
                            key="document_id",
                            match=MatchValue(value=document_id),
                        )
                    ]
                )
            ),
            wait=True,
        )
        
        logger.info(
            "Document chunks deleted",
            tenant_id=tenant_id,
            document_id=document_id,
        )
        
        return 1  # Qdrant doesn't return count

    async def delete_collection(self, tenant_id: str) -> None:
        """
        Delete entire collection for a tenant.
        
        Args:
            tenant_id: Tenant identifier
        """
        collection_name = self._collection_name(tenant_id)
        
        try:
            await self._client.delete_collection(collection_name)
            logger.info("Collection deleted", collection=collection_name)
        except Exception as e:
            logger.warning(
                "Collection delete failed",
                collection=collection_name,
                error=str(e),
            )

    async def get_collection_info(self, tenant_id: str) -> dict[str, Any] | None:
        """
        Get collection statistics.
        
        Args:
            tenant_id: Tenant identifier
            
        Returns:
            Collection info dict or None if not exists
        """
        collection_name = self._collection_name(tenant_id)
        
        try:
            info = await self._client.get_collection(collection_name)
            return {
                "name": collection_name,
                "vectors_count": info.vectors_count,
                "points_count": info.points_count,
                "status": info.status.value,
            }
        except Exception:
            return None

    async def close(self) -> None:
        """Close the client connection."""
        await self._client.close()
