"""
Tests for the ingestion pipeline.
"""

from datetime import datetime
from uuid import uuid4

import pytest

from evergreen.ingestion.parser import DocumentParser
from evergreen.ingestion.chunker import SemanticChunker, ChunkingConfig
from evergreen.models import DataSource, RawDocument


# =============================================================================
# Parser Tests
# =============================================================================

class TestDocumentParser:
    """Tests for DocumentParser."""

    def setup_method(self):
        """Set up test fixtures."""
        self.parser = DocumentParser()
        self.tenant_id = uuid4()

    def test_parse_plain_text_email(self):
        """Test parsing a plain text email."""
        doc = RawDocument(
            tenant_id=self.tenant_id,
            source=DataSource.M365_EMAIL,
            source_id="test:123",
            title="Test Subject",
            body="Hello,\n\nThis is a test email.\n\nBest,\nJohn",
            timestamp=datetime.utcnow(),
        )
        
        result = self.parser.parse(doc)
        
        assert "test email" in result.body
        assert result.id == doc.id

    def test_parse_html_email(self):
        """Test parsing an HTML email."""
        doc = RawDocument(
            tenant_id=self.tenant_id,
            source=DataSource.M365_EMAIL,
            source_id="test:124",
            title="HTML Email",
            body="<html><body><p>Hello</p><p>This is <strong>important</strong></p></body></html>",
            timestamp=datetime.utcnow(),
        )
        
        result = self.parser.parse(doc)
        
        assert "Hello" in result.body
        assert "important" in result.body
        assert "<html>" not in result.body

    def test_removes_email_signature(self):
        """Test that email signatures are removed."""
        doc = RawDocument(
            tenant_id=self.tenant_id,
            source=DataSource.M365_EMAIL,
            source_id="test:125",
            title="With Signature",
            body="Meeting at 3pm tomorrow.\n\n--\nJohn Smith\nCEO\nAcme Corp",
            timestamp=datetime.utcnow(),
        )
        
        result = self.parser.parse(doc)
        
        assert "Meeting at 3pm" in result.body
        # Signature should be removed
        assert "CEO" not in result.body or "Acme Corp" not in result.body

    def test_normalizes_whitespace(self):
        """Test whitespace normalization."""
        doc = RawDocument(
            tenant_id=self.tenant_id,
            source=DataSource.M365_EMAIL,
            source_id="test:126",
            title="Messy Whitespace",
            body="Hello\n\n\n\n\nWorld   with    spaces",
            timestamp=datetime.utcnow(),
        )
        
        result = self.parser.parse(doc)
        
        # Should have at most 2 consecutive newlines
        assert "\n\n\n" not in result.body
        # Should have normalized spaces
        assert "   " not in result.body


# =============================================================================
# Chunker Tests
# =============================================================================

class TestSemanticChunker:
    """Tests for SemanticChunker."""

    def setup_method(self):
        """Set up test fixtures."""
        self.chunker = SemanticChunker()
        self.tenant_id = uuid4()

    def test_short_email_single_chunk(self):
        """Test that a short email stays as one chunk."""
        doc = RawDocument(
            tenant_id=self.tenant_id,
            source=DataSource.M365_EMAIL,
            source_id="test:200",
            title="Short Email",
            body="Hi, just a quick note. Thanks!",
            timestamp=datetime.utcnow(),
        )
        
        chunks = self.chunker.chunk(doc)
        
        assert len(chunks) == 1
        assert chunks[0].content == doc.body
        assert chunks[0].document_id == doc.id
        assert chunks[0].tenant_id == self.tenant_id

    def test_long_email_multiple_chunks(self):
        """Test that a long email is split into multiple chunks."""
        # Create a document that exceeds the default chunk size
        long_body = "\n\n".join([
            f"Paragraph {i}: " + "Lorem ipsum dolor sit amet. " * 50
            for i in range(10)
        ])
        
        doc = RawDocument(
            tenant_id=self.tenant_id,
            source=DataSource.M365_EMAIL,
            source_id="test:201",
            title="Long Email",
            body=long_body,
            timestamp=datetime.utcnow(),
        )
        
        chunks = self.chunker.chunk(doc)
        
        assert len(chunks) > 1
        # Check sequential indexing
        for i, chunk in enumerate(chunks):
            assert chunk.chunk_index == i
            assert chunk.document_id == doc.id

    def test_chunk_metadata_preserved(self):
        """Test that chunk metadata is properly set."""
        doc = RawDocument(
            tenant_id=self.tenant_id,
            source=DataSource.M365_EMAIL,
            source_id="test:202",
            title="Metadata Test",
            body="Test content for metadata.",
            thread_id="thread-123",
            timestamp=datetime.utcnow(),
        )
        
        chunks = self.chunker.chunk(doc)
        
        assert len(chunks) == 1
        chunk = chunks[0]
        
        assert chunk.metadata["source"] == "m365_email"
        assert chunk.metadata["source_id"] == "test:202"
        assert chunk.metadata["title"] == "Metadata Test"
        assert chunk.metadata["thread_id"] == "thread-123"

    def test_custom_config(self):
        """Test chunking with custom configuration."""
        config = ChunkingConfig(max_tokens=100, overlap_tokens=10)
        chunker = SemanticChunker(config=config)
        
        # Create document that will definitely need chunking with 100 token limit
        doc = RawDocument(
            tenant_id=self.tenant_id,
            source=DataSource.M365_EMAIL,
            source_id="test:203",
            title="Custom Config Test",
            body="Word " * 200,  # ~200 words, should exceed 100 tokens
            timestamp=datetime.utcnow(),
        )
        
        chunks = chunker.chunk(doc)
        
        # Should produce multiple chunks with the smaller limit
        assert len(chunks) > 1

    def test_chat_message_chunking(self):
        """Test chunking of chat/Teams messages."""
        doc = RawDocument(
            tenant_id=self.tenant_id,
            source=DataSource.M365_TEAMS,
            source_id="test:300",
            title=None,
            body="Hey team, quick update on the project.",
            timestamp=datetime.utcnow(),
        )
        
        chunks = self.chunker.chunk(doc)
        
        # Short chat message should be single chunk
        assert len(chunks) == 1
        assert chunks[0].metadata["source"] == "m365_teams"


# =============================================================================
# Integration Tests
# =============================================================================

class TestIngestionIntegration:
    """Integration tests for the full ingestion pipeline."""

    def setup_method(self):
        """Set up test fixtures."""
        self.parser = DocumentParser()
        self.chunker = SemanticChunker()
        self.tenant_id = uuid4()

    def test_parse_then_chunk(self):
        """Test the parse -> chunk pipeline."""
        # HTML email with signature
        doc = RawDocument(
            tenant_id=self.tenant_id,
            source=DataSource.M365_EMAIL,
            source_id="test:400",
            title="Integration Test",
            body="""
            <html>
            <body>
            <p>Hi team,</p>
            <p>Here's the update on our project progress.</p>
            <p>We've completed phase 1 and are moving to phase 2.</p>
            <p>Let me know if you have questions.</p>
            </body>
            </html>
            
            --
            John Smith
            Project Manager
            """,
            timestamp=datetime.utcnow(),
        )
        
        # Parse
        parsed = self.parser.parse(doc)
        assert "<html>" not in parsed.body
        assert "Project Manager" not in parsed.body or "--" not in parsed.body
        
        # Chunk
        chunks = self.chunker.chunk(parsed)
        assert len(chunks) >= 1
        assert all(chunk.tenant_id == self.tenant_id for chunk in chunks)
