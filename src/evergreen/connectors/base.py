"""
Base connector interface for all data sources.
"""

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from datetime import datetime
from typing import Any
from uuid import UUID

from evergreen.models import DataSource, RawDocument, SyncState


class BaseConnector(ABC):
    """
    Abstract base class for all data source connectors.
    
    Each connector is responsible for:
    1. Authenticating with the data source
    2. Fetching documents (full sync and delta sync)
    3. Handling pagination and rate limiting
    4. Converting source-specific formats to RawDocument
    """

    def __init__(self, tenant_id: UUID, credentials: dict[str, Any]):
        """
        Initialize the connector.
        
        Args:
            tenant_id: The tenant this connector belongs to
            credentials: Authentication credentials for the data source
        """
        self.tenant_id = tenant_id
        self.credentials = credentials
        self._authenticated = False

    @property
    @abstractmethod
    def source_type(self) -> DataSource:
        """Return the data source type this connector handles."""
        pass

    @property
    @abstractmethod
    def supported_content_types(self) -> list[str]:
        """Return the content types this connector can process."""
        pass

    @abstractmethod
    async def authenticate(self) -> bool:
        """
        Authenticate with the data source.
        
        Returns:
            True if authentication was successful, False otherwise.
        """
        pass

    @abstractmethod
    async def test_connection(self) -> bool:
        """
        Test that the connection is valid and we can fetch data.
        
        Returns:
            True if connection is healthy, False otherwise.
        """
        pass

    @abstractmethod
    async def sync_full(
        self,
        lookback_days: int = 90,
    ) -> AsyncIterator[RawDocument]:
        """
        Perform a full sync of all documents within the lookback period.
        
        Args:
            lookback_days: How many days back to fetch documents
            
        Yields:
            RawDocument objects for each document found
        """
        pass

    @abstractmethod
    async def sync_delta(
        self,
        state: SyncState,
    ) -> AsyncIterator[tuple[RawDocument | None, SyncState]]:
        """
        Perform an incremental sync using delta tokens.
        
        Args:
            state: The current sync state with delta token
            
        Yields:
            Tuples of (document, updated_state). Document may be None for deletions.
            The final yield should have the updated SyncState with new delta token.
        """
        pass

    @abstractmethod
    async def get_document_by_id(self, source_id: str) -> RawDocument | None:
        """
        Fetch a specific document by its source ID.
        
        Args:
            source_id: The ID of the document in the source system
            
        Returns:
            The document if found, None otherwise.
        """
        pass

    async def __aenter__(self) -> "BaseConnector":
        """Async context manager entry."""
        await self.authenticate()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        await self.close()

    async def close(self) -> None:
        """
        Close any open connections. Override if needed.
        """
        pass

    def _ensure_authenticated(self) -> None:
        """Raise an error if not authenticated."""
        if not self._authenticated:
            raise RuntimeError(
                f"{self.__class__.__name__} is not authenticated. "
                "Call authenticate() first or use as async context manager."
            )
