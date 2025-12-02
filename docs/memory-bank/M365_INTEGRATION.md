# Microsoft 365 Integration Guide

> Complete reference for M365 connector implementation

## Implementation Status

| Feature | Status | Location |
|---------|--------|----------|
| Authentication | ✅ Implemented | `connectors/m365.py` |
| Email sync | ✅ Implemented | `connectors/m365.py` |
| Delta queries | ✅ Implemented | Uses `$deltatoken` |
| OneDrive files | ⏳ Planned | Sprint 2 |
| SharePoint | ⏳ Planned | Sprint 2 |
| Teams messages | ⏳ Planned | Sprint 2 |
| Webhooks | ⏳ Planned | Sprint 2 |

## Overview

Microsoft Graph API provides unified access to:
- **Outlook Mail** - emails, attachments
- **OneDrive/SharePoint** - files, documents
- **Teams** - channel messages, chat
- **Calendar** - events, meetings
- **Contacts** - people directory

---

## Authentication

### App Registration (Azure AD)

1. Go to Azure Portal → Azure Active Directory → App Registrations
2. New Registration:
   - Name: "Evergreen Knowledge Index"
   - Supported account types: "Accounts in any organizational directory"
   - Redirect URI: `http://localhost:8000/auth/callback` (for dev)

3. API Permissions (Application permissions for daemon/service):
```
Microsoft Graph:
- Mail.Read                    # Read all mail
- Files.Read.All               # Read all files
- Sites.Read.All               # SharePoint sites
- ChannelMessage.Read.All      # Teams messages
- Calendars.Read               # Calendar events
- User.Read.All                # User directory
- Directory.Read.All           # Org structure
```

4. Grant admin consent (required for application permissions)

5. Create client secret or certificate

### Authentication Code

```python
from azure.identity import ClientSecretCredential
from msgraph import GraphServiceClient

class M365Authenticator:
    def __init__(
        self,
        tenant_id: str,
        client_id: str,
        client_secret: str
    ):
        self.credential = ClientSecretCredential(
            tenant_id=tenant_id,
            client_id=client_id,
            client_secret=client_secret
        )
        
    def get_client(self) -> GraphServiceClient:
        return GraphServiceClient(
            credentials=self.credential,
            scopes=["https://graph.microsoft.com/.default"]
        )
```

---

## Email Ingestion

### List Messages (with pagination)

```python
async def list_messages(
    client: GraphServiceClient,
    user_id: str,
    since: datetime | None = None,
    page_size: int = 100
) -> AsyncIterator[Message]:
    """Fetch all messages for a user with pagination."""
    
    query_params = MessagesRequestBuilder.MessagesRequestBuilderGetQueryParameters(
        top=page_size,
        select=["id", "subject", "body", "from", "toRecipients", 
                "ccRecipients", "receivedDateTime", "conversationId",
                "hasAttachments", "importance"],
        orderby=["receivedDateTime desc"],
    )
    
    # Filter by date if doing incremental sync
    if since:
        query_params.filter = f"receivedDateTime ge {since.isoformat()}Z"
    
    config = MessagesRequestBuilder.MessagesRequestBuilderGetRequestConfiguration(
        query_parameters=query_params
    )
    
    # Initial request
    response = await client.users.by_user_id(user_id).messages.get(
        request_configuration=config
    )
    
    while response:
        for message in response.value:
            yield message
        
        # Handle pagination
        if response.odata_next_link:
            response = await client.users.by_user_id(user_id).messages.get(
                request_configuration=RequestConfiguration(
                    headers={"prefer": "odata.maxpagesize=100"}
                )
            )
        else:
            break
```

### Delta Sync for Messages

```python
class EmailDeltaSync:
    """Efficient incremental sync using delta queries."""
    
    def __init__(self, client: GraphServiceClient, state_store: StateStore):
        self.client = client
        self.state_store = state_store
    
    async def sync(self, user_id: str) -> AsyncIterator[Message]:
        # Get stored delta link
        delta_link = await self.state_store.get(f"delta:{user_id}:messages")
        
        if delta_link:
            # Incremental sync - only changes
            response = await self._request_delta(delta_link)
        else:
            # Initial sync - all messages
            response = await self.client.users.by_user_id(user_id).messages.delta.get()
        
        while response:
            for message in response.value:
                # Check if deleted
                if hasattr(message, '@removed'):
                    yield DeletedMessage(id=message.id)
                else:
                    yield message
            
            # Save delta link for next sync
            if response.odata_delta_link:
                await self.state_store.set(
                    f"delta:{user_id}:messages",
                    response.odata_delta_link
                )
                break
            elif response.odata_next_link:
                response = await self._request_delta(response.odata_next_link)
            else:
                break
```

### Parse Email to Document

```python
from bs4 import BeautifulSoup
import html2text

def parse_email(message: Message) -> EmailDocument:
    """Convert Graph API message to our document format."""
    
    # Extract plain text from HTML body
    if message.body.content_type == "html":
        h = html2text.HTML2Text()
        h.ignore_links = False
        body_text = h.handle(message.body.content)
    else:
        body_text = message.body.content
    
    # Build participant list
    participants = []
    if message.from_:
        participants.append({
            "role": "from",
            "email": message.from_.email_address.address,
            "name": message.from_.email_address.name
        })
    for recipient in message.to_recipients or []:
        participants.append({
            "role": "to",
            "email": recipient.email_address.address,
            "name": recipient.email_address.name
        })
    
    return EmailDocument(
        id=f"email:{message.id}",
        source="m365_email",
        title=message.subject,
        body=body_text,
        participants=participants,
        thread_id=message.conversation_id,
        timestamp=message.received_date_time,
        has_attachments=message.has_attachments,
        metadata={
            "importance": message.importance,
            "folder": message.parent_folder_id,
        }
    )
```

---

## OneDrive/SharePoint Files

### List Files (with pagination)

```python
async def list_drive_items(
    client: GraphServiceClient,
    user_id: str,
    drive_id: str | None = None
) -> AsyncIterator[DriveItem]:
    """List all files in a user's OneDrive or specific drive."""
    
    if drive_id:
        drive = client.drives.by_drive_id(drive_id)
    else:
        drive = client.users.by_user_id(user_id).drive
    
    # Start from root, recursively get all items
    async for item in _recursive_list(drive, "root"):
        yield item

async def _recursive_list(drive, folder_id: str) -> AsyncIterator[DriveItem]:
    """Recursively list items in a folder."""
    
    response = await drive.items.by_drive_item_id(folder_id).children.get()
    
    while response:
        for item in response.value:
            yield item
            
            # Recurse into folders
            if item.folder:
                async for child in _recursive_list(drive, item.id):
                    yield child
        
        if response.odata_next_link:
            response = await drive.items.by_drive_item_id(folder_id).children.get()
        else:
            break
```

### Download and Parse Files

```python
from io import BytesIO
import docx
import PyPDF2

async def download_and_parse(
    client: GraphServiceClient,
    drive_id: str,
    item_id: str,
    mime_type: str
) -> str | None:
    """Download file and extract text content."""
    
    # Download content
    content = await client.drives.by_drive_id(drive_id).items.by_drive_item_id(item_id).content.get()
    
    if mime_type == "application/pdf":
        return _parse_pdf(BytesIO(content))
    elif mime_type in ["application/vnd.openxmlformats-officedocument.wordprocessingml.document"]:
        return _parse_docx(BytesIO(content))
    elif mime_type.startswith("text/"):
        return content.decode("utf-8")
    else:
        return None  # Unsupported format

def _parse_pdf(file: BytesIO) -> str:
    reader = PyPDF2.PdfReader(file)
    text = []
    for page in reader.pages:
        text.append(page.extract_text())
    return "\n".join(text)

def _parse_docx(file: BytesIO) -> str:
    doc = docx.Document(file)
    return "\n".join([para.text for para in doc.paragraphs])
```

---

## Teams Messages

### List Channel Messages

```python
async def list_team_messages(
    client: GraphServiceClient,
    team_id: str,
    channel_id: str,
    since: datetime | None = None
) -> AsyncIterator[ChatMessage]:
    """List messages in a Teams channel."""
    
    query_params = MessagesRequestBuilder.MessagesRequestBuilderGetQueryParameters(
        top=50,
    )
    
    if since:
        query_params.filter = f"lastModifiedDateTime ge {since.isoformat()}Z"
    
    config = MessagesRequestBuilder.MessagesRequestBuilderGetRequestConfiguration(
        query_parameters=query_params
    )
    
    response = await client.teams.by_team_id(team_id)\
        .channels.by_channel_id(channel_id)\
        .messages.get(request_configuration=config)
    
    while response:
        for message in response.value:
            yield message
            
            # Also get replies
            replies = await client.teams.by_team_id(team_id)\
                .channels.by_channel_id(channel_id)\
                .messages.by_chat_message_id(message.id)\
                .replies.get()
            
            for reply in replies.value or []:
                yield reply
        
        if response.odata_next_link:
            # Handle pagination
            pass
        else:
            break
```

---

## Calendar Events

```python
async def list_calendar_events(
    client: GraphServiceClient,
    user_id: str,
    start: datetime,
    end: datetime
) -> AsyncIterator[Event]:
    """List calendar events in a date range."""
    
    query_params = CalendarViewRequestBuilder.CalendarViewRequestBuilderGetQueryParameters(
        start_date_time=start.isoformat(),
        end_date_time=end.isoformat(),
        select=["id", "subject", "body", "start", "end", "attendees", 
                "location", "organizer", "isOnlineMeeting"],
        top=100
    )
    
    config = CalendarViewRequestBuilder.CalendarViewRequestBuilderGetRequestConfiguration(
        query_parameters=query_params
    )
    
    response = await client.users.by_user_id(user_id).calendar_view.get(
        request_configuration=config
    )
    
    while response:
        for event in response.value:
            yield event
        
        if response.odata_next_link:
            # Handle pagination
            pass
        else:
            break
```

---

## Webhooks for Real-time Updates

### Subscribe to Changes

```python
async def create_subscription(
    client: GraphServiceClient,
    resource: str,  # e.g., "/users/{id}/messages"
    webhook_url: str,
    expiration: datetime
) -> Subscription:
    """Create a webhook subscription for real-time notifications."""
    
    subscription = Subscription(
        change_type="created,updated,deleted",
        notification_url=webhook_url,
        resource=resource,
        expiration_date_time=expiration,
        client_state="evergreen_secret_token",  # For validation
    )
    
    return await client.subscriptions.post(subscription)

# Webhook handler (FastAPI example)
@app.post("/webhooks/m365")
async def handle_webhook(request: Request):
    # Validation request from Microsoft
    if "validationToken" in request.query_params:
        return PlainTextResponse(request.query_params["validationToken"])
    
    # Process notifications
    data = await request.json()
    for notification in data.get("value", []):
        resource = notification["resource"]
        change_type = notification["changeType"]
        
        # Queue for processing
        await queue.enqueue(
            "process_m365_notification",
            resource=resource,
            change_type=change_type
        )
    
    return {"status": "ok"}
```

---

## Rate Limits & Best Practices

### Rate Limits
| Resource | Limit |
|----------|-------|
| Outlook (per mailbox) | 10,000 requests / 10 min |
| OneDrive (per app) | 10,000 requests / 10 min |
| Teams | 30 requests / sec |
| Global | 130,000 requests / 10 sec |

### Best Practices

1. **Always use delta queries** for incremental sync
2. **Batch requests** when possible (up to 20 requests per batch)
3. **Handle 429 errors** - respect `Retry-After` header
4. **Use select parameter** - only request fields you need
5. **Cache access tokens** - don't request new token per API call

### Retry Logic

```python
import asyncio
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=1, min=4, max=60),
    retry=retry_if_exception_type(ThrottlingException)
)
async def api_call_with_retry(func, *args, **kwargs):
    try:
        return await func(*args, **kwargs)
    except ODataError as e:
        if e.response_status_code == 429:
            retry_after = int(e.response_headers.get("Retry-After", 60))
            await asyncio.sleep(retry_after)
            raise ThrottlingException()
        raise
```
