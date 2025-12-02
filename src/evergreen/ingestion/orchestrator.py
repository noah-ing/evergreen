"""
Ingestion orchestrator that coordinates the full pipeline.

Takes raw documents through parsing, chunking, embedding, and storage.
"""

from datetime import datetime
from typing import Any

import structlog

from evergreen.config import settings
from evergreen.ingestion.parser import DocumentParser
from evergreen.ingestion.chunker import SemanticChunker
from evergreen.extraction.extractor import EntityExtractor
from evergreen.storage.embeddings import EmbeddingGenerator, get_embedding_generator
from evergreen.storage.vector import VectorStore
from evergreen.storage.graph import GraphStore
from evergreen.models import (
    DocumentChunk,
    DocumentStatus,
    IndexedDocument,
    RawDocument,
)

logger = structlog.get_logger()


class IngestionOrchestrator:
    """
    Orchestrates the full document ingestion pipeline.
    
    Pipeline stages:
    1. Parse: Clean and normalize raw document text
    2. Chunk: Split into semantic segments
    3. Extract: Extract entities (people, orgs, projects, topics)
    4. Embed: Generate vector embeddings
    5. Store: Save to vector and graph databases
    """

    def __init__(
        self,
        parser: DocumentParser | None = None,
        chunker: SemanticChunker | None = None,
        extractor: EntityExtractor | None = None,
        embedder: EmbeddingGenerator | None = None,
        vector_store: VectorStore | None = None,
        graph_store: GraphStore | None = None,
    ):
        """
        Initialize the orchestrator with pipeline components.
        
        Args:
            parser: Document parser (or creates default)
            chunker: Semantic chunker (or creates default)
            extractor: Entity extractor (or creates default)
            embedder: Embedding generator (or creates default)
            vector_store: Vector store (or creates default)
            graph_store: Graph store (or creates default)
        """
        self.parser = parser or DocumentParser()
        self.chunker = chunker or SemanticChunker()
        self.extractor = extractor or EntityExtractor()
        self.embedder = embedder or get_embedding_generator(
            use_local=not settings.voyage_api_key
        )
        self.vector_store = vector_store or VectorStore()
        self.graph_store = graph_store or GraphStore()

    async def ingest(self, document: RawDocument) -> IndexedDocument:
        """
        Run the full ingestion pipeline on a document.
        
        Args:
            document: Raw document from a connector
            
        Returns:
            IndexedDocument with chunk IDs and entity IDs
        """
        logger.info(
            "Starting ingestion",
            document_id=document.id,
            source=document.source.value,
        )
        
        try:
            # Stage 1: Parse
            parsed = self.parser.parse(document)
            logger.debug("Document parsed", document_id=document.id)
            
            # Stage 2: Chunk
            chunks = self.chunker.chunk(parsed)
            logger.debug(
                "Document chunked",
                document_id=document.id,
                chunk_count=len(chunks),
            )
            
            # Stage 3: Extract entities from all chunks
            all_entities = []
            all_mentions = []
            for chunk in chunks:
                entities, mentions = await self.extractor.extract_from_chunk(chunk)
                all_entities.extend(entities)
                all_mentions.extend(mentions)
            
            logger.debug(
                "Entities extracted",
                document_id=document.id,
                entity_count=len(all_entities),
            )
            
            # Stage 4: Generate embeddings
            chunk_embeddings = await self.embedder.embed_chunks(chunks)
            logger.debug(
                "Embeddings generated",
                document_id=document.id,
                embedding_count=len(chunk_embeddings),
            )
            
            # Stage 5: Store in vector DB
            await self.vector_store.upsert(document.tenant_id, chunk_embeddings)
            chunk_ids = [chunk.id for chunk in chunks]
            
            # Stage 6: Store entities in graph DB
            await self.graph_store.ensure_schema(document.tenant_id)
            entity_ids = []
            for entity in all_entities:
                entity_id = await self.graph_store.create_entity(
                    document.tenant_id, entity
                )
                entity_ids.append(entity.id)
                
                # Link entity to document
                await self.graph_store.link_entity_to_document(
                    document.tenant_id,
                    entity_id,
                    str(document.id),
                )
            
            # Create indexed document record
            indexed = IndexedDocument(
                id=document.id,
                tenant_id=document.tenant_id,
                source=document.source,
                source_id=document.source_id,
                title=document.title,
                status=DocumentStatus.INDEXED,
                chunk_ids=chunk_ids,
                entity_ids=entity_ids,
                timestamp=document.timestamp,
                indexed_at=datetime.utcnow(),
            )
            
            logger.info(
                "Ingestion complete",
                document_id=document.id,
                chunks=len(chunks),
                entities=len(entities),
            )
            
            return indexed
            
        except Exception as e:
            logger.error(
                "Ingestion failed",
                document_id=document.id,
                error=str(e),
            )
            
            return IndexedDocument(
                id=document.id,
                tenant_id=document.tenant_id,
                source=document.source,
                source_id=document.source_id,
                title=document.title,
                status=DocumentStatus.FAILED,
                timestamp=document.timestamp,
                error_message=str(e),
            )

    async def ingest_batch(
        self,
        documents: list[RawDocument],
        max_concurrent: int = 10,
    ) -> list[IndexedDocument]:
        """
        Ingest a batch of documents with controlled concurrency.
        
        Args:
            documents: List of raw documents
            max_concurrent: Maximum concurrent ingestions
            
        Returns:
            List of IndexedDocument results
        """
        import asyncio
        
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def bounded_ingest(doc: RawDocument) -> IndexedDocument:
            async with semaphore:
                return await self.ingest(doc)
        
        results = await asyncio.gather(
            *[bounded_ingest(doc) for doc in documents],
            return_exceptions=False,
        )
        
        # Log summary
        successful = sum(1 for r in results if r.status == DocumentStatus.INDEXED)
        failed = sum(1 for r in results if r.status == DocumentStatus.FAILED)
        
        logger.info(
            "Batch ingestion complete",
            total=len(documents),
            successful=successful,
            failed=failed,
        )
        
        return results
