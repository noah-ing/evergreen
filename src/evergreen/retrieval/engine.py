"""
Retrieval engine combining vector search and graph traversal.

Implements a hybrid RAG approach:
1. Vector search for semantic similarity
2. Graph traversal for related entities
3. Reranking for relevance
4. LLM synthesis for final answer
"""

from dataclasses import dataclass, field
from typing import Any
from uuid import UUID

import structlog

from evergreen.config import settings
from evergreen.storage.embeddings import get_embedding_generator
from evergreen.storage.vector import VectorStore
from evergreen.storage.graph import GraphStore

logger = structlog.get_logger()


@dataclass
class QueryResult:
    """Result from the retrieval engine."""
    
    answer: str
    """Synthesized answer to the query."""
    
    sources: list[dict[str, Any]] = field(default_factory=list)
    """Source chunks used to generate answer."""
    
    entities: list[dict[str, Any]] = field(default_factory=list)
    """Related entities found."""
    
    confidence: float = 0.0
    """Confidence score for the answer (0-1)."""
    
    reasoning: str | None = None
    """Optional explanation of how answer was derived."""


class RetrievalEngine:
    """
    Hybrid retrieval engine combining vector and graph search.
    
    Features:
    - Semantic vector search
    - Entity-aware graph traversal
    - Reranking for improved relevance
    - LLM synthesis with citations
    """

    def __init__(
        self,
        vector_store: VectorStore | None = None,
        graph_store: GraphStore | None = None,
        embedding_generator=None,
        rerank: bool = True,
    ):
        """
        Initialize retrieval engine.
        
        Args:
            vector_store: Vector store instance
            graph_store: Graph store instance
            embedding_generator: Embedding generator
            rerank: Whether to use Cohere reranking
        """
        self.vector_store = vector_store or VectorStore()
        self.graph_store = graph_store or GraphStore()
        self.embedding_generator = embedding_generator or get_embedding_generator(
            use_local=not settings.voyage_api_key
        )
        self.use_rerank = rerank and settings.cohere_api_key
        
        self._cohere_client = None
        self._llm_client = None
        
        logger.info(
            "Retrieval engine initialized",
            reranking=self.use_rerank,
        )

    def _get_cohere_client(self):
        """Lazy load Cohere client."""
        if self._cohere_client is None and settings.cohere_api_key:
            import cohere
            self._cohere_client = cohere.AsyncClient(api_key=settings.cohere_api_key)
        return self._cohere_client

    def _get_llm_client(self):
        """Lazy load Anthropic client."""
        if self._llm_client is None:
            import anthropic
            self._llm_client = anthropic.AsyncAnthropic(
                api_key=settings.anthropic_api_key
            )
        return self._llm_client

    async def query(
        self,
        tenant_id: str,
        query: str,
        top_k: int = 10,
        filters: dict[str, Any] | None = None,
        include_graph: bool = True,
        synthesize: bool = True,
    ) -> QueryResult:
        """
        Execute a query against the knowledge base.
        
        Args:
            tenant_id: Tenant identifier
            query: Natural language query
            top_k: Number of results to retrieve
            filters: Optional metadata filters
            include_graph: Whether to include graph traversal
            synthesize: Whether to synthesize answer with LLM
            
        Returns:
            QueryResult with answer and sources
        """
        logger.info(
            "Processing query",
            tenant_id=tenant_id,
            query=query[:100],
        )
        
        # Step 1: Embed the query
        query_embedding = await self.embedding_generator.embed_query(query)
        
        # Step 2: Vector search
        vector_results = await self.vector_store.search(
            tenant_id=tenant_id,
            query_embedding=query_embedding,
            limit=top_k * 2,  # Get more for reranking
            filters=filters,
        )
        
        logger.debug(
            "Vector search complete",
            result_count=len(vector_results),
        )
        
        # Step 3: Optional reranking
        if self.use_rerank and vector_results:
            vector_results = await self._rerank(query, vector_results, top_k)
        else:
            vector_results = vector_results[:top_k]
        
        # Step 4: Graph augmentation
        entities = []
        if include_graph and vector_results:
            entities = await self._augment_with_graph(tenant_id, vector_results)
        
        # Step 5: Synthesize answer
        if synthesize:
            answer, reasoning, confidence = await self._synthesize_answer(
                query, vector_results, entities
            )
        else:
            answer = ""
            reasoning = None
            confidence = 0.0
        
        return QueryResult(
            answer=answer,
            sources=vector_results,
            entities=entities,
            confidence=confidence,
            reasoning=reasoning,
        )

    async def _rerank(
        self,
        query: str,
        results: list[dict[str, Any]],
        top_k: int,
    ) -> list[dict[str, Any]]:
        """
        Rerank results using Cohere.
        
        Args:
            query: Original query
            results: Vector search results
            top_k: Number to keep after reranking
            
        Returns:
            Reranked results
        """
        cohere = self._get_cohere_client()
        if not cohere:
            return results[:top_k]
        
        documents = [r["content"] for r in results]
        
        try:
            rerank_response = await cohere.rerank(
                model="rerank-v3.5",
                query=query,
                documents=documents,
                top_n=top_k,
            )
            
            reranked = []
            for item in rerank_response.results:
                result = results[item.index].copy()
                result["rerank_score"] = item.relevance_score
                reranked.append(result)
            
            logger.debug("Reranking complete", reranked_count=len(reranked))
            return reranked
            
        except Exception as e:
            logger.warning("Reranking failed, using original order", error=str(e))
            return results[:top_k]

    async def _augment_with_graph(
        self,
        tenant_id: str,
        results: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """
        Find related entities from graph.
        
        Args:
            tenant_id: Tenant identifier
            results: Vector search results
            
        Returns:
            List of related entities
        """
        # Extract unique document IDs
        doc_ids = set()
        for r in results:
            if doc_id := r.get("document_id"):
                doc_ids.add(doc_id)
        
        # Find entities mentioned in these documents
        entities = []
        seen_entities = set()
        
        for doc_id in list(doc_ids)[:5]:  # Limit graph queries
            try:
                # Get entities for this document
                entity_results = await self.graph_store.find_entities_by_name(
                    tenant_id, "", limit=10
                )
                
                for entity in entity_results:
                    entity_id = entity.get("id")
                    if entity_id and entity_id not in seen_entities:
                        seen_entities.add(entity_id)
                        entities.append(entity)
                        
            except Exception as e:
                logger.debug("Graph augmentation error", error=str(e))
        
        logger.debug("Graph augmentation complete", entity_count=len(entities))
        return entities

    async def _synthesize_answer(
        self,
        query: str,
        sources: list[dict[str, Any]],
        entities: list[dict[str, Any]],
    ) -> tuple[str, str | None, float]:
        """
        Synthesize answer using LLM.
        
        Args:
            query: Original query
            sources: Retrieved source chunks
            entities: Related entities
            
        Returns:
            Tuple of (answer, reasoning, confidence)
        """
        if not sources:
            return (
                "I couldn't find relevant information to answer your question.",
                None,
                0.0,
            )
        
        client = self._get_llm_client()
        
        # Build context from sources
        context_parts = []
        for i, source in enumerate(sources, 1):
            metadata = source.get("metadata", {})
            context_parts.append(f"""
[Source {i}]
Content: {source.get('content', '')}
Type: {metadata.get('source_type', 'unknown')}
Date: {metadata.get('created_at', 'unknown')}
""")
        
        context = "\n".join(context_parts)
        
        # Add entity context
        entity_context = ""
        if entities:
            entity_lines = [f"- {e['name']} ({e['type']})" for e in entities[:10]]
            entity_context = f"\nRelated entities: {', '.join(e['name'] for e in entities[:10])}"
        
        prompt = f"""You are an AI assistant helping users find information in their organization's data.

Based on the following context, answer the user's question. Be specific and cite source numbers [1], [2], etc.

Context:
{context}
{entity_context}

User Question: {query}

Instructions:
- Answer based ONLY on the provided context
- Cite sources using [1], [2], etc.
- If the context doesn't contain enough information, say so
- Be concise but complete

Answer:"""

        try:
            response = await client.messages.create(
                model=settings.llm_model,
                max_tokens=1024,
                messages=[{"role": "user", "content": prompt}],
            )
            
            answer = response.content[0].text
            
            # Estimate confidence based on sources and response
            confidence = min(0.9, 0.5 + 0.1 * len(sources))
            if "don't have enough" in answer.lower() or "cannot find" in answer.lower():
                confidence = 0.3
            
            return answer, None, confidence
            
        except Exception as e:
            logger.error("LLM synthesis failed", error=str(e))
            return (
                "I found relevant information but had trouble summarizing it. Please try again.",
                str(e),
                0.2,
            )

    async def find_similar_documents(
        self,
        tenant_id: str,
        document_id: str,
        top_k: int = 5,
    ) -> list[dict[str, Any]]:
        """
        Find documents similar to a given document.
        
        Args:
            tenant_id: Tenant identifier
            document_id: Source document ID
            top_k: Number of similar documents
            
        Returns:
            List of similar documents
        """
        # Get chunks for this document
        results = await self.vector_store.search(
            tenant_id=tenant_id,
            query_embedding=[0.0] * self.embedding_generator.dimensions,  # Placeholder
            limit=1,
            filters={"document_id": document_id},
        )
        
        if not results:
            return []
        
        # Use first chunk's embedding to find similar
        # This is a simplified approach
        return await self.vector_store.search(
            tenant_id=tenant_id,
            query_embedding=results[0].get("embedding", []),
            limit=top_k,
            filters=None,  # Don't filter, want other documents
        )

    async def get_entity_context(
        self,
        tenant_id: str,
        entity_name: str,
        entity_type: str | None = None,
    ) -> dict[str, Any]:
        """
        Get full context for an entity.
        
        Args:
            tenant_id: Tenant identifier
            entity_name: Entity name to search
            entity_type: Optional type filter
            
        Returns:
            Entity with related documents and entities
        """
        # Find the entity
        entities = await self.graph_store.find_entities_by_name(
            tenant_id, entity_name, entity_type, limit=1
        )
        
        if not entities:
            return {"found": False}
        
        entity = entities[0]
        entity_id = entity["id"]
        
        # Get subgraph
        subgraph = await self.graph_store.get_entity_subgraph(
            tenant_id, entity_id, depth=2
        )
        
        # Get related documents
        doc_ids = await self.graph_store.get_entity_documents(
            tenant_id, entity_id, limit=10
        )
        
        return {
            "found": True,
            "entity": entity,
            "related_nodes": subgraph.get("nodes", []),
            "relationships": subgraph.get("edges", []),
            "document_ids": doc_ids,
        }
