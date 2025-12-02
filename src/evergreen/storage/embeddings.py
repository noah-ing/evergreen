"""
Embedding generation using Voyage AI.

Handles batching, rate limiting, and fallback options.
"""

import asyncio
from typing import Any

import structlog
import voyageai
from tenacity import retry, stop_after_attempt, wait_exponential

from evergreen.config import settings
from evergreen.models import DocumentChunk

logger = structlog.get_logger()


class EmbeddingGenerator:
    """
    Generates embeddings using Voyage AI.
    
    Features:
    - Automatic batching for efficiency
    - Rate limit handling with exponential backoff
    - Configurable model and dimensions
    """

    # Voyage AI limits
    MAX_BATCH_SIZE = 128  # Max texts per request
    MAX_TOKENS_PER_BATCH = 320000  # ~2500 tokens per text average

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        dimensions: int | None = None,
    ):
        """
        Initialize the embedding generator.
        
        Args:
            api_key: Voyage AI API key (defaults to settings)
            model: Embedding model name (defaults to settings)
            dimensions: Output dimensions (defaults to settings)
        """
        self.api_key = api_key or settings.voyage_api_key
        self.model = model or settings.embedding_model
        self.dimensions = dimensions or settings.embedding_dimensions
        
        if not self.api_key:
            raise ValueError("Voyage AI API key not configured")
        
        self._client = voyageai.AsyncClient(api_key=self.api_key)
        
        logger.info(
            "Embedding generator initialized",
            model=self.model,
            dimensions=self.dimensions,
        )

    async def embed_texts(
        self,
        texts: list[str],
        input_type: str = "document",
    ) -> list[list[float]]:
        """
        Generate embeddings for a list of texts.
        
        Args:
            texts: List of text strings to embed
            input_type: "document" for indexing, "query" for searching
            
        Returns:
            List of embedding vectors
        """
        if not texts:
            return []
        
        # Process in batches
        all_embeddings = []
        
        for i in range(0, len(texts), self.MAX_BATCH_SIZE):
            batch = texts[i:i + self.MAX_BATCH_SIZE]
            batch_embeddings = await self._embed_batch(batch, input_type)
            all_embeddings.extend(batch_embeddings)
        
        return all_embeddings

    async def embed_chunks(
        self,
        chunks: list[DocumentChunk],
    ) -> list[tuple[DocumentChunk, list[float]]]:
        """
        Generate embeddings for document chunks.
        
        Args:
            chunks: List of document chunks
            
        Returns:
            List of (chunk, embedding) tuples
        """
        texts = [chunk.content for chunk in chunks]
        embeddings = await self.embed_texts(texts, input_type="document")
        
        return list(zip(chunks, embeddings))

    async def embed_query(self, query: str) -> list[float]:
        """
        Generate embedding for a search query.
        
        Args:
            query: Search query text
            
        Returns:
            Embedding vector
        """
        embeddings = await self.embed_texts([query], input_type="query")
        return embeddings[0]

    @retry(
        stop=stop_after_attempt(5),
        wait=wait_exponential(multiplier=1, min=2, max=60),
    )
    async def _embed_batch(
        self,
        texts: list[str],
        input_type: str,
    ) -> list[list[float]]:
        """
        Embed a single batch with retry logic.
        
        Args:
            texts: Batch of texts
            input_type: Type of input (document/query)
            
        Returns:
            List of embeddings
        """
        try:
            result = await self._client.embed(
                texts=texts,
                model=self.model,
                input_type=input_type,
                output_dimension=self.dimensions,
            )
            
            logger.debug(
                "Batch embedded",
                batch_size=len(texts),
                model=self.model,
            )
            
            return result.embeddings
            
        except voyageai.error.RateLimitError as e:
            logger.warning("Rate limit hit, retrying", error=str(e))
            raise
        except Exception as e:
            logger.error("Embedding failed", error=str(e))
            raise


class LocalEmbeddingGenerator:
    """
    Local embedding generator using sentence-transformers.
    
    For development/testing without API costs, or air-gapped deployments.
    Uses EmbeddingGemma or BGE-M3 models.
    """

    def __init__(
        self,
        model_name: str = "BAAI/bge-m3",
        device: str = "auto",
    ):
        """
        Initialize local embedding generator.
        
        Args:
            model_name: HuggingFace model name
            device: Device to use (auto, cuda, cpu, mps)
        """
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError:
            raise ImportError(
                "sentence-transformers required for local embeddings. "
                "Install with: pip install sentence-transformers"
            )
        
        self.model_name = model_name
        
        # Determine device
        if device == "auto":
            import torch
            if torch.cuda.is_available():
                device = "cuda"
            elif torch.backends.mps.is_available():
                device = "mps"
            else:
                device = "cpu"
        
        self._model = SentenceTransformer(model_name, device=device)
        self.dimensions = self._model.get_sentence_embedding_dimension()
        
        logger.info(
            "Local embedding generator initialized",
            model=model_name,
            device=device,
            dimensions=self.dimensions,
        )

    async def embed_texts(
        self,
        texts: list[str],
        input_type: str = "document",
    ) -> list[list[float]]:
        """Generate embeddings locally."""
        if not texts:
            return []
        
        # sentence-transformers is sync, run in thread pool
        loop = asyncio.get_event_loop()
        embeddings = await loop.run_in_executor(
            None,
            lambda: self._model.encode(texts, normalize_embeddings=True).tolist()
        )
        
        return embeddings

    async def embed_chunks(
        self,
        chunks: list[DocumentChunk],
    ) -> list[tuple[DocumentChunk, list[float]]]:
        """Generate embeddings for document chunks."""
        texts = [chunk.content for chunk in chunks]
        embeddings = await self.embed_texts(texts)
        return list(zip(chunks, embeddings))

    async def embed_query(self, query: str) -> list[float]:
        """Generate embedding for a search query."""
        embeddings = await self.embed_texts([query], input_type="query")
        return embeddings[0]


def get_embedding_generator(
    use_local: bool = False,
    **kwargs,
) -> EmbeddingGenerator | LocalEmbeddingGenerator:
    """
    Factory function to get the appropriate embedding generator.
    
    Args:
        use_local: If True, use local model instead of Voyage AI
        **kwargs: Additional arguments passed to the generator
        
    Returns:
        Embedding generator instance
    """
    if use_local:
        return LocalEmbeddingGenerator(**kwargs)
    return EmbeddingGenerator(**kwargs)
