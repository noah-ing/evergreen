"""
Document parser for converting raw documents into clean text.

Handles HTML stripping, encoding normalization, and format-specific parsing.
"""

import re
from typing import Any

import structlog
from bs4 import BeautifulSoup
import html2text

from evergreen.models import DataSource, RawDocument

logger = structlog.get_logger()


class DocumentParser:
    """
    Parses raw documents into clean, normalized text.
    
    Handles:
    - HTML to text conversion
    - Email header cleaning
    - Character encoding normalization
    - Whitespace normalization
    """

    def __init__(self):
        """Initialize the parser with html2text settings."""
        self._html_converter = html2text.HTML2Text()
        self._html_converter.ignore_links = False
        self._html_converter.ignore_images = True
        self._html_converter.ignore_tables = False
        self._html_converter.body_width = 0  # No wrapping

    def parse(self, document: RawDocument) -> RawDocument:
        """
        Parse a raw document and return a cleaned version.
        
        Args:
            document: The raw document to parse
            
        Returns:
            A new RawDocument with cleaned body text
        """
        try:
            # Route to appropriate parser based on source type
            if document.source in [DataSource.M365_EMAIL, DataSource.GOOGLE_EMAIL]:
                cleaned_body = self._parse_email(document.body)
            elif document.source in [DataSource.M365_TEAMS, DataSource.SLACK]:
                cleaned_body = self._parse_chat(document.body)
            else:
                cleaned_body = self._parse_generic(document.body)
            
            # Create new document with cleaned body
            return RawDocument(
                **{
                    **document.model_dump(),
                    "body": cleaned_body,
                }
            )
            
        except Exception as e:
            logger.error(
                "Failed to parse document",
                document_id=document.id,
                error=str(e),
            )
            # Return original on failure
            return document

    def _parse_email(self, body: str) -> str:
        """
        Parse email body, handling HTML and quoted replies.
        
        Args:
            body: Raw email body (may be HTML or plain text)
            
        Returns:
            Cleaned plain text
        """
        # Check if HTML
        if self._is_html(body):
            text = self._html_to_text(body)
        else:
            text = body
        
        # Remove email signatures (common patterns)
        text = self._remove_email_signature(text)
        
        # Remove excessive quoted text (keep first reply only)
        text = self._trim_quoted_replies(text)
        
        # Normalize whitespace
        text = self._normalize_whitespace(text)
        
        return text

    def _parse_chat(self, body: str) -> str:
        """
        Parse chat/Teams message.
        
        Args:
            body: Raw message body
            
        Returns:
            Cleaned text
        """
        # Handle HTML (Teams often uses HTML)
        if self._is_html(body):
            text = self._html_to_text(body)
        else:
            text = body
        
        # Remove @mentions formatting but keep the names
        text = re.sub(r'<at[^>]*>([^<]*)</at>', r'@\1', text)
        
        # Normalize whitespace
        text = self._normalize_whitespace(text)
        
        return text

    def _parse_generic(self, body: str) -> str:
        """
        Generic parsing for documents.
        
        Args:
            body: Raw document body
            
        Returns:
            Cleaned text
        """
        if self._is_html(body):
            text = self._html_to_text(body)
        else:
            text = body
        
        text = self._normalize_whitespace(text)
        return text

    def _is_html(self, text: str) -> bool:
        """Check if text appears to be HTML."""
        html_patterns = [
            r'<html[^>]*>',
            r'<body[^>]*>',
            r'<div[^>]*>',
            r'<p[^>]*>',
            r'<br\s*/?>',
        ]
        return any(re.search(pattern, text, re.IGNORECASE) for pattern in html_patterns)

    def _html_to_text(self, html: str) -> str:
        """Convert HTML to plain text."""
        try:
            return self._html_converter.handle(html)
        except Exception:
            # Fallback to BeautifulSoup
            soup = BeautifulSoup(html, 'html.parser')
            return soup.get_text(separator='\n')

    def _remove_email_signature(self, text: str) -> str:
        """Remove common email signature patterns."""
        # Common signature delimiters
        signature_patterns = [
            r'\n--\s*\n.*$',  # Standard -- delimiter
            r'\nSent from my .*$',
            r'\nGet Outlook for .*$',
            r'\n_{3,}.*$',  # ___ lines
            r'\nRegards,?\s*\n.*$',
            r'\nBest,?\s*\n.*$',
            r'\nThanks,?\s*\n.*$',
        ]
        
        for pattern in signature_patterns:
            text = re.sub(pattern, '', text, flags=re.IGNORECASE | re.DOTALL)
        
        return text

    def _trim_quoted_replies(self, text: str, max_depth: int = 1) -> str:
        """
        Trim excessive quoted replies in email threads.
        
        Args:
            text: Email text with potential quotes
            max_depth: Maximum quote depth to keep
            
        Returns:
            Text with trimmed quotes
        """
        # Common quote patterns
        quote_patterns = [
            r'\n>+ ?On .* wrote:.*$',  # Gmail style
            r'\n-{3,}Original Message-{3,}.*$',  # Outlook style
            r'\nFrom: .*\nSent: .*\nTo: .*\nSubject: .*$',  # Full headers
        ]
        
        for pattern in quote_patterns:
            match = re.search(pattern, text, flags=re.IGNORECASE | re.DOTALL)
            if match:
                # Keep text before the quote
                text = text[:match.start()]
        
        return text

    def _normalize_whitespace(self, text: str) -> str:
        """Normalize whitespace in text."""
        # Replace multiple newlines with double newline
        text = re.sub(r'\n{3,}', '\n\n', text)
        
        # Replace multiple spaces with single space
        text = re.sub(r' {2,}', ' ', text)
        
        # Remove leading/trailing whitespace from lines
        lines = [line.strip() for line in text.split('\n')]
        text = '\n'.join(lines)
        
        # Remove leading/trailing whitespace from document
        text = text.strip()
        
        return text
