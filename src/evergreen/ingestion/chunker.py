"""
Semantic chunking for documents.

Implements intelligent document chunking that respects semantic boundaries.
"""

from dataclasses import dataclass
from typing import Any
from uuid import UUID

import structlog

from evergreen.models import DataSource, DocumentChunk, RawDocument

logger = structlog.get_logger()


@dataclass
class ChunkingConfig:
    """Configuration for chunking strategy."""
    max_tokens: int = 512
    overlap_tokens: int = 50
    min_chunk_size: int = 100  # Minimum tokens for a chunk


# Default configs by document type
DEFAULT_CONFIGS: dict[DataSource, ChunkingConfig] = {
    DataSource.M365_EMAIL: ChunkingConfig(max_tokens=512, overlap_tokens=50),
    DataSource.GOOGLE_EMAIL: ChunkingConfig(max_tokens=512, overlap_tokens=50),
    DataSource.M365_TEAMS: ChunkingConfig(max_tokens=256, overlap_tokens=0),
    DataSource.SLACK: ChunkingConfig(max_tokens=256, overlap_tokens=0),
    DataSource.M365_FILE: ChunkingConfig(max_tokens=1024, overlap_tokens=100),
    DataSource.GOOGLE_FILE: ChunkingConfig(max_tokens=1024, overlap_tokens=100),
    DataSource.M365_CALENDAR: ChunkingConfig(max_tokens=512, overlap_tokens=50),
    DataSource.GOOGLE_CALENDAR: ChunkingConfig(max_tokens=512, overlap_tokens=50),
}


class SemanticChunker:
    """
    Chunks documents into semantically meaningful segments.
    
    Strategies:
    - Emails: Thread-aware chunking, keeps replies together
    - Chat: Thread-grouped, respects conversation boundaries
    - Documents: Section-aware, respects headers and paragraphs
    """

    def __init__(self, config: ChunkingConfig | None = None):
        """
        Initialize the chunker.
        
        Args:
            config: Default chunking configuration. If None, uses document-type defaults.
        """
        self._default_config = config

    def chunk(self, document: RawDocument) -> list[DocumentChunk]:
        """
        Chunk a document into semantic segments.
        
        Args:
            document: The parsed document to chunk
            
        Returns:
            List of DocumentChunk objects
        """
        # Get config for this document type
        config = self._default_config or DEFAULT_CONFIGS.get(
            document.source,
            ChunkingConfig()  # Default fallback
        )
        
        # Route to appropriate chunking strategy
        if document.source in [DataSource.M365_EMAIL, DataSource.GOOGLE_EMAIL]:
            return self._chunk_email(document, config)
        elif document.source in [DataSource.M365_TEAMS, DataSource.SLACK]:
            return self._chunk_chat(document, config)
        else:
            return self._chunk_generic(document, config)

    def _chunk_email(
        self,
        document: RawDocument,
        config: ChunkingConfig,
    ) -> list[DocumentChunk]:
        """
        Chunk email content.
        
        For short emails, keeps the entire email as one chunk.
        For long emails, splits at paragraph boundaries.
        """
        text = document.body
        token_count = self._estimate_tokens(text)
        
        # If email fits in one chunk, return as-is
        if token_count <= config.max_tokens:
            return [self._create_chunk(
                document=document,
                content=text,
                chunk_index=0,
                token_count=token_count,
            )]
        
        # Split at paragraph boundaries
        paragraphs = text.split('\n\n')
        chunks = []
        current_chunk = ""
        current_tokens = 0
        
        for para in paragraphs:
            para_tokens = self._estimate_tokens(para)
            
            if current_tokens + para_tokens <= config.max_tokens:
                current_chunk += ('\n\n' if current_chunk else '') + para
                current_tokens += para_tokens
            else:
                # Save current chunk
                if current_chunk:
                    chunks.append(self._create_chunk(
                        document=document,
                        content=current_chunk,
                        chunk_index=len(chunks),
                        token_count=current_tokens,
                    ))
                
                # Handle paragraph that's too long
                if para_tokens > config.max_tokens:
                    # Split the paragraph itself
                    sub_chunks = self._split_long_text(
                        para, config.max_tokens, config.overlap_tokens
                    )
                    for sub in sub_chunks:
                        chunks.append(self._create_chunk(
                            document=document,
                            content=sub,
                            chunk_index=len(chunks),
                            token_count=self._estimate_tokens(sub),
                        ))
                    current_chunk = ""
                    current_tokens = 0
                else:
                    current_chunk = para
                    current_tokens = para_tokens
        
        # Don't forget the last chunk
        if current_chunk:
            chunks.append(self._create_chunk(
                document=document,
                content=current_chunk,
                chunk_index=len(chunks),
                token_count=current_tokens,
            ))
        
        return chunks

    def _chunk_chat(
        self,
        document: RawDocument,
        config: ChunkingConfig,
    ) -> list[DocumentChunk]:
        """
        Chunk chat messages.
        
        Chat messages are usually short, so we often keep them as single chunks.
        Thread context is preserved via document metadata.
        """
        text = document.body
        token_count = self._estimate_tokens(text)
        
        # Most chat messages are short
        if token_count <= config.max_tokens:
            return [self._create_chunk(
                document=document,
                content=text,
                chunk_index=0,
                token_count=token_count,
            )]
        
        # For long messages, split at sentence boundaries
        return self._split_at_sentences(document, text, config)

    def _chunk_generic(
        self,
        document: RawDocument,
        config: ChunkingConfig,
    ) -> list[DocumentChunk]:
        """
        Generic chunking for documents.
        
        Tries to respect section headers and paragraph boundaries.
        """
        text = document.body
        token_count = self._estimate_tokens(text)
        
        if token_count <= config.max_tokens:
            return [self._create_chunk(
                document=document,
                content=text,
                chunk_index=0,
                token_count=token_count,
            )]
        
        # Try to split at section headers first
        sections = self._split_at_headers(text)
        
        if len(sections) > 1:
            chunks = []
            for section in sections:
                section_tokens = self._estimate_tokens(section)
                if section_tokens <= config.max_tokens:
                    chunks.append(self._create_chunk(
                        document=document,
                        content=section,
                        chunk_index=len(chunks),
                        token_count=section_tokens,
                    ))
                else:
                    # Section too long, split further
                    sub_chunks = self._split_long_text(
                        section, config.max_tokens, config.overlap_tokens
                    )
                    for sub in sub_chunks:
                        chunks.append(self._create_chunk(
                            document=document,
                            content=sub,
                            chunk_index=len(chunks),
                            token_count=self._estimate_tokens(sub),
                        ))
            return chunks
        
        # No headers found, fall back to paragraph splitting
        return self._chunk_email(document, config)

    def _split_at_headers(self, text: str) -> list[str]:
        """Split text at markdown-style headers."""
        import re
        
        # Match markdown headers (# Header, ## Header, etc.)
        header_pattern = r'\n(?=#{1,6}\s)'
        
        sections = re.split(header_pattern, text)
        return [s.strip() for s in sections if s.strip()]

    def _split_at_sentences(
        self,
        document: RawDocument,
        text: str,
        config: ChunkingConfig,
    ) -> list[DocumentChunk]:
        """Split text at sentence boundaries."""
        import re
        
        # Simple sentence splitting
        sentences = re.split(r'(?<=[.!?])\s+', text)
        
        chunks = []
        current_chunk = ""
        current_tokens = 0
        
        for sentence in sentences:
            sentence_tokens = self._estimate_tokens(sentence)
            
            if current_tokens + sentence_tokens <= config.max_tokens:
                current_chunk += (' ' if current_chunk else '') + sentence
                current_tokens += sentence_tokens
            else:
                if current_chunk:
                    chunks.append(self._create_chunk(
                        document=document,
                        content=current_chunk,
                        chunk_index=len(chunks),
                        token_count=current_tokens,
                    ))
                current_chunk = sentence
                current_tokens = sentence_tokens
        
        if current_chunk:
            chunks.append(self._create_chunk(
                document=document,
                content=current_chunk,
                chunk_index=len(chunks),
                token_count=current_tokens,
            ))
        
        return chunks

    def _split_long_text(
        self,
        text: str,
        max_tokens: int,
        overlap_tokens: int,
    ) -> list[str]:
        """Split text that's too long for a single chunk."""
        words = text.split()
        chunks = []
        
        # Approximate: 1 token ≈ 0.75 words (conservative)
        words_per_chunk = int(max_tokens * 0.75)
        overlap_words = int(overlap_tokens * 0.75)
        
        i = 0
        while i < len(words):
            end = min(i + words_per_chunk, len(words))
            chunk_words = words[i:end]
            chunks.append(' '.join(chunk_words))
            
            # Move forward, accounting for overlap
            i = end - overlap_words if end < len(words) else end
        
        return chunks

    def _estimate_tokens(self, text: str) -> int:
        """
        Estimate token count for text.
        
        Uses a simple heuristic: ~4 characters per token for English.
        For production, use tiktoken or model-specific tokenizer.
        """
        return len(text) // 4

    def _create_chunk(
        self,
        document: RawDocument,
        content: str,
        chunk_index: int,
        token_count: int,
    ) -> DocumentChunk:
        """Create a DocumentChunk from content."""
        return DocumentChunk(
            document_id=document.id,
            tenant_id=document.tenant_id,
            content=content,
            chunk_index=chunk_index,
            token_count=token_count,
            metadata={
                "source": document.source.value,
                "source_id": document.source_id,
                "title": document.title,
                "timestamp": document.timestamp.isoformat(),
                "thread_id": document.thread_id,
            },
        )
