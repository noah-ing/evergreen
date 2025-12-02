"""
Microsoft 365 connector for email, files, Teams, and calendar.

Uses Microsoft Graph API for all M365 data access.
"""

import asyncio
from collections.abc import AsyncIterator
from datetime import datetime, timedelta
from typing import Any
from uuid import UUID

import structlog
from azure.identity.aio import ClientSecretCredential
from msgraph import GraphServiceClient
from msgraph.generated.models.message import Message
from msgraph.generated.users.item.messages.messages_request_builder import (
    MessagesRequestBuilder,
)

from evergreen.connectors.base import BaseConnector
from evergreen.models import DataSource, Participant, RawDocument, SyncState

logger = structlog.get_logger()


class M365Connector(BaseConnector):
    """
    Connector for Microsoft 365 (Outlook, OneDrive, SharePoint, Teams, Calendar).
    
    Uses Microsoft Graph API with application permissions for full organization access.
    
    Required Azure AD App Permissions (Application):
    - Mail.Read
    - Files.Read.All
    - Sites.Read.All
    - ChannelMessage.Read.All
    - Calendars.Read
    - User.Read.All
    """

    def __init__(
        self,
        tenant_id: UUID,
        credentials: dict[str, Any],
    ):
        """
        Initialize M365 connector.
        
        Args:
            tenant_id: Evergreen tenant ID
            credentials: Dict with azure_tenant_id, azure_client_id, azure_client_secret
        """
        super().__init__(tenant_id, credentials)
        
        self._azure_credential: ClientSecretCredential | None = None
        self._graph_client: GraphServiceClient | None = None
        
        # Validate required credentials
        required = ["azure_tenant_id", "azure_client_id", "azure_client_secret"]
        missing = [k for k in required if not credentials.get(k)]
        if missing:
            raise ValueError(f"Missing required credentials: {missing}")

    @property
    def source_type(self) -> DataSource:
        return DataSource.M365_EMAIL

    @property
    def supported_content_types(self) -> list[str]:
        return [
            "message/rfc822",  # Email
            "application/pdf",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "application/vnd.openxmlformats-officedocument.presentationml.presentation",
            "text/plain",
            "text/html",
        ]

    async def authenticate(self) -> bool:
        """Authenticate with Azure AD using client credentials."""
        try:
            self._azure_credential = ClientSecretCredential(
                tenant_id=self.credentials["azure_tenant_id"],
                client_id=self.credentials["azure_client_id"],
                client_secret=self.credentials["azure_client_secret"],
            )
            
            self._graph_client = GraphServiceClient(
                credentials=self._azure_credential,
                scopes=["https://graph.microsoft.com/.default"],
            )
            
            self._authenticated = True
            logger.info("M365 authentication successful", tenant_id=str(self.tenant_id))
            return True
            
        except Exception as e:
            logger.error("M365 authentication failed", error=str(e))
            self._authenticated = False
            return False

    async def test_connection(self) -> bool:
        """Test connection by fetching organization info."""
        self._ensure_authenticated()
        
        try:
            org = await self._graph_client.organization.get()  # type: ignore
            if org and org.value:
                logger.info(
                    "M365 connection test passed",
                    org_name=org.value[0].display_name,
                )
                return True
            return False
        except Exception as e:
            logger.error("M365 connection test failed", error=str(e))
            return False

    async def sync_full(
        self,
        lookback_days: int = 90,
    ) -> AsyncIterator[RawDocument]:
        """
        Full sync of all emails within the lookback period.
        
        TODO: Add support for OneDrive, SharePoint, Teams, Calendar
        """
        self._ensure_authenticated()
        
        since = datetime.utcnow() - timedelta(days=lookback_days)
        
        # Get all users in the organization
        users = await self._get_all_users()
        
        for user in users:
            user_id = user.id
            user_email = user.mail or user.user_principal_name
            
            logger.info(
                "Syncing emails for user",
                user_email=user_email,
                lookback_days=lookback_days,
            )
            
            async for doc in self._fetch_user_emails(user_id, since=since):
                yield doc

    async def sync_delta(
        self,
        state: SyncState,
    ) -> AsyncIterator[tuple[RawDocument | None, SyncState]]:
        """
        Incremental sync using delta queries.
        
        Uses Microsoft Graph delta queries to fetch only changed items.
        """
        self._ensure_authenticated()
        
        # TODO: Implement delta sync with delta tokens
        # For now, fall back to recent sync
        since = state.last_sync_at or (datetime.utcnow() - timedelta(hours=1))
        
        users = await self._get_all_users()
        
        updated_state = SyncState(
            **state.model_dump(),
            last_sync_at=datetime.utcnow(),
        )
        
        for user in users:
            async for doc in self._fetch_user_emails(user.id, since=since):
                updated_state.documents_synced += 1
                yield doc, updated_state
        
        # Final yield with updated state
        updated_state.status = "completed"
        yield None, updated_state

    async def get_document_by_id(self, source_id: str) -> RawDocument | None:
        """Fetch a specific email by ID."""
        self._ensure_authenticated()
        
        # source_id format: "user_id:message_id"
        try:
            user_id, message_id = source_id.split(":", 1)
            message = await self._graph_client.users.by_user_id(user_id).messages.by_message_id(message_id).get()  # type: ignore
            if message:
                return self._message_to_document(message, user_id)
        except Exception as e:
            logger.error("Failed to fetch message", source_id=source_id, error=str(e))
        
        return None

    async def close(self) -> None:
        """Close Azure credential."""
        if self._azure_credential:
            await self._azure_credential.close()

    # =========================================================================
    # Private Methods
    # =========================================================================

    async def _get_all_users(self) -> list[Any]:
        """Get all users in the organization."""
        users = []
        
        try:
            response = await self._graph_client.users.get()  # type: ignore
            while response:
                users.extend(response.value or [])
                
                if response.odata_next_link:
                    # TODO: Handle pagination properly
                    break
                else:
                    break
                    
        except Exception as e:
            logger.error("Failed to fetch users", error=str(e))
        
        return users

    async def _fetch_user_emails(
        self,
        user_id: str,
        since: datetime | None = None,
        page_size: int = 100,
    ) -> AsyncIterator[RawDocument]:
        """
        Fetch emails for a specific user.
        
        Args:
            user_id: The user's ID in Azure AD
            since: Only fetch emails after this date
            page_size: Number of emails per page
        """
        try:
            query_params = MessagesRequestBuilder.MessagesRequestBuilderGetQueryParameters(
                top=page_size,
                select=[
                    "id", "subject", "body", "from", "toRecipients",
                    "ccRecipients", "receivedDateTime", "conversationId",
                    "hasAttachments", "importance",
                ],
                orderby=["receivedDateTime desc"],
            )
            
            if since:
                query_params.filter = f"receivedDateTime ge {since.isoformat()}Z"
            
            config = MessagesRequestBuilder.MessagesRequestBuilderGetRequestConfiguration(
                query_parameters=query_params
            )
            
            response = await self._graph_client.users.by_user_id(user_id).messages.get(  # type: ignore
                request_configuration=config
            )
            
            while response:
                for message in response.value or []:
                    doc = self._message_to_document(message, user_id)
                    if doc:
                        yield doc
                
                # Handle pagination
                if response.odata_next_link:
                    # TODO: Implement proper pagination
                    break
                else:
                    break
                    
        except Exception as e:
            logger.error(
                "Failed to fetch emails",
                user_id=user_id,
                error=str(e),
            )

    def _message_to_document(
        self,
        message: Message,
        user_id: str,
    ) -> RawDocument | None:
        """Convert a Graph API message to a RawDocument."""
        try:
            # Extract body text
            body_text = ""
            if message.body:
                if message.body.content_type and "html" in message.body.content_type.lower():
                    # TODO: Use html2text for proper conversion
                    body_text = message.body.content or ""
                else:
                    body_text = message.body.content or ""
            
            # Build participants list
            participants = []
            
            if message.from_ and message.from_.email_address:
                participants.append(Participant(
                    email=message.from_.email_address.address or "",
                    name=message.from_.email_address.name,
                    role="from",
                ))
            
            for recipient in message.to_recipients or []:
                if recipient.email_address:
                    participants.append(Participant(
                        email=recipient.email_address.address or "",
                        name=recipient.email_address.name,
                        role="to",
                    ))
            
            for recipient in message.cc_recipients or []:
                if recipient.email_address:
                    participants.append(Participant(
                        email=recipient.email_address.address or "",
                        name=recipient.email_address.name,
                        role="cc",
                    ))
            
            return RawDocument(
                tenant_id=self.tenant_id,
                source=DataSource.M365_EMAIL,
                source_id=f"{user_id}:{message.id}",
                title=message.subject,
                body=body_text,
                participants=participants,
                thread_id=message.conversation_id,
                timestamp=message.received_date_time or datetime.utcnow(),
                metadata={
                    "has_attachments": message.has_attachments,
                    "importance": str(message.importance) if message.importance else None,
                },
            )
            
        except Exception as e:
            logger.error(
                "Failed to convert message to document",
                message_id=message.id,
                error=str(e),
            )
            return None
