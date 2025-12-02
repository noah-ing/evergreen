# Microsoft Graph API & Google Workspace APIs for Business Knowledge Indexing
**Research Date: December 2025**

## Executive Summary

This document provides actionable recommendations for building a business knowledge indexing system using Microsoft Graph API (for Microsoft 365) and Google Workspace APIs. Both platforms support full organizational data access via service accounts/app-only permissions with admin consent.

---

## Microsoft Graph API

### 1. Accessible Data

| Resource | Key Endpoints | Notes |
|----------|--------------|-------|
| **Email** | `/users/{id}/messages`, `/users/{id}/mailFolders` | Full mailbox access including body, attachments |
| **Files** | `/drives/{id}/items`, `/sites/{id}/drive` | OneDrive & SharePoint files |
| **Teams Messages** | `/teams/{id}/channels/{id}/messages`, `/chats/{id}/messages` | Channel & chat messages |
| **Calendar** | `/users/{id}/events`, `/users/{id}/calendars` | Events, attendees, meeting details |
| **Contacts** | `/users/{id}/contacts`, `/users/{id}/contactFolders` | Personal contacts |
| **Users/Groups** | `/users`, `/groups` | Directory information |

### 2. Authentication: App-Only vs Delegated

#### For Full Org Access → **Use App-Only (Application Permissions)**

```
┌─────────────────────────────────────────────────────────────┐
│ Authentication Flow for Org-Wide Indexing                   │
├─────────────────────────────────────────────────────────────┤
│ 1. Register app in Microsoft Entra (Azure AD)               │
│ 2. Add Application permissions (not Delegated)              │
│ 3. Admin grants tenant-wide consent                         │
│ 4. Use Client Credentials flow (client_id + secret/cert)    │
└─────────────────────────────────────────────────────────────┘
```

**Required Application Permissions for Indexing:**

| Scope | Permission | Purpose |
|-------|------------|---------|
| Mail | `Mail.Read` | Read all mailboxes |
| Files | `Files.Read.All` | Read all OneDrive/SharePoint files |
| Sites | `Sites.Read.All` | Read SharePoint site content |
| Calendar | `Calendars.Read` | Read all calendars |
| Teams | `ChannelMessage.Read.All` | Read Teams messages |
| Contacts | `Contacts.Read` | Read all contacts |
| Users | `User.Read.All` | List/read all users |

**Security Note:** Use `application access policies` to limit mailbox access to specific users if needed.

### 3. Rate Limits & Throttling

| Service | Limit | Strategy |
|---------|-------|----------|
| **Outlook (Mail/Calendar)** | 10,000 requests per 10 min per mailbox | Stagger across mailboxes |
| **Identity/Users** | 3,500-8,000 ResourceUnits per 10 sec per tenant | Use `$select`, avoid `$expand` |
| **Teams** | 30-600 rps depending on operation | Batch where possible |
| **Files/SharePoint** | See SharePoint-specific limits | Use delta queries |
| **Global** | 130,000 requests per 10 seconds total | Respect `Retry-After` header |

**Handling 429 Errors:**
```python
# Python pattern for handling throttling
import time
from msgraph import GraphServiceClient

def call_with_retry(func, max_retries=5):
    for attempt in range(max_retries):
        try:
            return func()
        except Exception as e:
            if hasattr(e, 'response') and e.response.status_code == 429:
                retry_after = int(e.response.headers.get('Retry-After', 60))
                time.sleep(retry_after)
            else:
                raise
```

### 4. Delta Queries & Webhooks (Incremental Sync)

#### Delta Queries (Pull-based)
```python
# Initial sync - get all messages
GET /users/{user-id}/mailFolders/inbox/messages/delta

# Response includes @odata.deltaLink
# Save the deltaLink, then later:
GET {deltaLink}  # Returns only changed items
```

**Supported Resources for Delta:**
- `message`, `mailFolder` - Email changes
- `event` - Calendar changes  
- `driveItem` - File changes
- `user`, `group` - Directory changes
- `chatMessage` - Teams messages

**Key Pattern:**
```python
# Delta query pattern
delta_token = None

def sync_messages(user_id: str):
    global delta_token
    
    if delta_token:
        # Incremental sync
        response = client.get(delta_token)
    else:
        # Initial full sync
        response = client.get(f"/users/{user_id}/messages/delta")
    
    # Process messages...
    
    # Store the delta link for next sync
    if '@odata.deltaLink' in response:
        delta_token = response['@odata.deltaLink']
    elif '@odata.nextLink' in response:
        # More pages - keep fetching
        pass
```

#### Webhooks (Push-based)
```python
# Create subscription for real-time notifications
POST /subscriptions
{
    "changeType": "created,updated,deleted",
    "notificationUrl": "https://your-endpoint/webhook",
    "resource": "/users/{user-id}/messages",
    "expirationDateTime": "2025-12-10T00:00:00Z",
    "clientState": "secretClientState"
}
```

**Best Practice:** Combine webhooks (for real-time alerts) + delta queries (for reliable catch-up sync).

### 5. Python SDK

```bash
pip install msgraph-sdk
pip install azure-identity
```

```python
from azure.identity import ClientSecretCredential
from msgraph import GraphServiceClient

# App-only authentication
credential = ClientSecretCredential(
    tenant_id="YOUR_TENANT_ID",
    client_id="YOUR_CLIENT_ID", 
    client_secret="YOUR_CLIENT_SECRET"
)

client = GraphServiceClient(credential)

# List all users
users = await client.users.get()

# Get user's messages with pagination
messages = await client.users.by_user_id("user@domain.com").messages.get(
    query_parameters=MessagesRequestBuilder.MessagesRequestBuilderGetQueryParameters(
        select=["subject", "from", "receivedDateTime", "body"],
        top=100,
        orderby=["receivedDateTime desc"]
    )
)

# Handle pagination
while messages.odata_next_link:
    messages = await client.users.by_user_id("user@domain.com").messages.get(
        request_configuration=lambda c: setattr(c, 'url', messages.odata_next_link)
    )
```

---

## Google Workspace APIs

### 1. APIs & Required Permissions

| API | OAuth Scopes | Purpose |
|-----|--------------|---------|
| **Gmail API** | `https://www.googleapis.com/auth/gmail.readonly` | Read emails |
| **Drive API** | `https://www.googleapis.com/auth/drive.readonly` | Read files |
| **Calendar API** | `https://www.googleapis.com/auth/calendar.readonly` | Read events |
| **Admin SDK** | `https://www.googleapis.com/auth/admin.directory.user.readonly` | List users |

### 2. Domain-Wide Delegation for Org Access

```
┌─────────────────────────────────────────────────────────────┐
│ Domain-Wide Delegation Setup                                │
├─────────────────────────────────────────────────────────────┤
│ 1. Create Service Account in Google Cloud Console           │
│ 2. Enable domain-wide delegation checkbox                   │
│ 3. Download JSON key file                                   │
│ 4. In Admin Console → Security → API Controls               │
│ 5. "Manage Domain Wide Delegation" → Add new                │
│ 6. Enter Service Account Client ID + OAuth scopes           │
└─────────────────────────────────────────────────────────────┘
```

**Service Account Impersonation:**
```python
from google.oauth2 import service_account
from googleapiclient.discovery import build

SCOPES = [
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/drive.readonly',
    'https://www.googleapis.com/auth/calendar.readonly'
]

# Create credentials that impersonate a user
credentials = service_account.Credentials.from_service_account_file(
    'service-account-key.json',
    scopes=SCOPES
).with_subject('user@yourdomain.com')  # Impersonate this user

gmail_service = build('gmail', 'v1', credentials=credentials)
drive_service = build('drive', 'v3', credentials=credentials)
```

### 3. Rate Limits

| API | Limit | Notes |
|-----|-------|-------|
| **Gmail** | 1,200,000 quota units/min (project), 15,000/min (per user) | messages.get = 5 units |
| **Drive** | 12,000 queries/60 sec | Per user: 12,000/60 sec |
| **Calendar** | Similar to Drive | - |

**Gmail Quota Unit Costs:**
- `messages.list` = 5 units
- `messages.get` = 5 units  
- `history.list` = 2 units (efficient for incremental!)

### 4. Push Notifications (Cloud Pub/Sub)

```python
# Setup: Create Pub/Sub topic, grant publish rights to 
# gmail-api-push@system.gserviceaccount.com

# Start watching a mailbox
POST https://www.googleapis.com/gmail/v1/users/me/watch
{
    "topicName": "projects/your-project/topics/gmail-notifications",
    "labelIds": ["INBOX"],
    "labelFilterBehavior": "INCLUDE"
}

# Response
{
    "historyId": "1234567890",
    "expiration": "1735689600000"  # Must re-watch every 7 days
}
```

**Notification Handling:**
```python
# Webhook receives:
{
    "message": {
        "data": "base64-encoded-json",  # {"emailAddress": "user@domain.com", "historyId": "9876543210"}
        "messageId": "...",
        "publishTime": "..."
    }
}

# Then call history.list to get actual changes
gmail.users().history().list(
    userId='me',
    startHistoryId='1234567890'  # From last known historyId
).execute()
```

### 5. Python Client Libraries

```bash
pip install google-api-python-client google-auth google-auth-oauthlib
```

```python
from googleapiclient.discovery import build
from google.oauth2 import service_account

# Gmail: List messages with pagination
def list_all_messages(service, user_id='me', query=''):
    messages = []
    page_token = None
    
    while True:
        response = service.users().messages().list(
            userId=user_id,
            q=query,
            pageToken=page_token,
            maxResults=500  # Max per page
        ).execute()
        
        messages.extend(response.get('messages', []))
        page_token = response.get('nextPageToken')
        
        if not page_token:
            break
    
    return messages

# Drive: List files with pagination
def list_all_files(service, query=''):
    files = []
    page_token = None
    
    while True:
        response = service.files().list(
            q=query,
            pageToken=page_token,
            pageSize=1000,
            fields='nextPageToken, files(id, name, mimeType, modifiedTime)'
        ).execute()
        
        files.extend(response.get('files', []))
        page_token = response.get('nextPageToken')
        
        if not page_token:
            break
    
    return files
```

---

## Practical Implementation Patterns

### Pagination for Large Mailboxes

**Microsoft Graph:**
```python
async def paginate_messages(client, user_id: str, page_size: int = 100):
    """Generator that yields all messages with proper pagination"""
    request = client.users.by_user_id(user_id).messages.get(
        query_parameters={'$top': page_size, '$select': 'id,subject,from,receivedDateTime'}
    )
    
    while True:
        response = await request
        for message in response.value:
            yield message
        
        if not response.odata_next_link:
            break
        request = client.users.by_user_id(user_id).messages.get(
            request_configuration=lambda c: setattr(c, 'url', response.odata_next_link)
        )
```

**Google Gmail:**
```python
def paginate_messages(service, user_id='me', batch_size=100):
    """Generator for Gmail messages with batched full-content fetching"""
    page_token = None
    
    while True:
        # List message IDs (lightweight)
        list_response = service.users().messages().list(
            userId=user_id,
            pageToken=page_token,
            maxResults=batch_size
        ).execute()
        
        message_ids = [m['id'] for m in list_response.get('messages', [])]
        
        # Batch get full messages (efficient)
        batch = service.new_batch_http_request()
        messages = []
        
        for msg_id in message_ids:
            batch.add(
                service.users().messages().get(userId=user_id, id=msg_id, format='full'),
                callback=lambda req_id, response, error: messages.append(response) if not error else None
            )
        
        batch.execute()
        
        for msg in messages:
            yield msg
        
        page_token = list_response.get('nextPageToken')
        if not page_token:
            break
```

### Initial Bulk Sync vs Incremental Sync

```python
# PATTERN: Initial sync with checkpoint, then incremental

class MailboxSyncer:
    def __init__(self, storage):
        self.storage = storage  # Your checkpoint storage
    
    def sync_user(self, user_id: str):
        checkpoint = self.storage.get_checkpoint(user_id)
        
        if checkpoint is None:
            # INITIAL SYNC: Fetch everything
            self._full_sync(user_id)
        else:
            # INCREMENTAL: Use delta/history
            self._incremental_sync(user_id, checkpoint)
    
    def _full_sync(self, user_id: str):
        # Microsoft: Use delta query, save deltaLink
        # Google: Fetch all, save latest historyId
        pass
    
    def _incremental_sync(self, user_id: str, checkpoint):
        # Microsoft: Call saved deltaLink
        # Google: Call history.list with startHistoryId
        pass
```

### Best Approach: Hybrid Push + Pull

```
┌─────────────────────────────────────────────────────────────┐
│ Recommended Architecture                                    │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  [Push Notifications]  ──trigger──>  [Incremental Sync Job] │
│   (Webhooks/Pub-Sub)                  (Delta/History API)   │
│                                                             │
│  [Scheduled Full Sync]  ──daily──>   [Catch-up for missed]  │
│   (Safety net)                        changes               │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## Common Gotchas & Pitfalls

### Microsoft Graph

| Issue | Solution |
|-------|----------|
| Delta tokens expire (7 days for directory objects) | Implement full re-sync fallback on 410 Gone |
| Message IDs can change after move/copy | Use immutable IDs: `Prefer: IdType="ImmutableId"` header |
| Throttling during bulk operations | Implement exponential backoff, respect `Retry-After` |
| Large attachments timeout | Use streaming download for attachments > 4MB |
| Teams messages require different endpoints | Use `/teams/{id}/channels/{id}/messages` for channels |

### Google Workspace

| Issue | Solution |
|-------|----------|
| Watch subscription expires in 7 days | Cron job to renew daily |
| historyId can become invalid | Full re-sync if `historyId` error |
| Message format differences | Always specify `format='full'` or `format='metadata'` |
| Domain-wide delegation setup | Must be done by Super Admin in Admin Console |
| Rate limit per user vs project | Track both, implement per-user throttling |

### Both Platforms

| Issue | Solution |
|-------|----------|
| Handling deleted items | Process `@removed` (Graph) / check message existence (Gmail) |
| Timezones in calendar data | Always store in UTC, convert for display |
| Email threading | Use `conversationId` (Graph) / `threadId` (Gmail) |
| Partial failures in batch | Process successful items, retry failed with backoff |
| Attachment encoding | Both use base64 - decode properly |

---

## Quick Reference: Key Endpoints

### Microsoft Graph
```
Base URL: https://graph.microsoft.com/v1.0

# Users
GET /users                                    # List all users
GET /users/{id}                              # Get specific user

# Mail
GET /users/{id}/messages                     # List messages
GET /users/{id}/messages/delta               # Delta query
GET /users/{id}/messages/{msgId}             # Get message
GET /users/{id}/messages/{msgId}/attachments # Get attachments

# Files
GET /users/{id}/drive/root/children          # List OneDrive files
GET /drives/{driveId}/items/{itemId}         # Get file metadata
GET /drives/{driveId}/items/{itemId}/content # Download file

# Calendar
GET /users/{id}/events                       # List events
GET /users/{id}/calendar/events/delta        # Delta query

# Teams
GET /teams/{teamId}/channels                 # List channels
GET /teams/{teamId}/channels/{channelId}/messages # Get messages
```

### Google Workspace
```
# Gmail
GET gmail/v1/users/{userId}/messages         # List messages
GET gmail/v1/users/{userId}/messages/{id}    # Get message
GET gmail/v1/users/{userId}/history          # Get changes since historyId
POST gmail/v1/users/{userId}/watch           # Start push notifications
POST gmail/v1/users/{userId}/stop            # Stop push notifications

# Drive
GET drive/v3/files                           # List files
GET drive/v3/files/{fileId}                  # Get file metadata
GET drive/v3/files/{fileId}?alt=media        # Download file
GET drive/v3/changes                         # Track changes (w/ page token)

# Calendar
GET calendar/v3/calendars/{calendarId}/events # List events
GET calendar/v3/users/me/calendarList        # List calendars

# Admin Directory
GET admin/directory/v1/users                 # List all users in domain
```

---

## Summary Recommendations

| Aspect | Microsoft 365 | Google Workspace |
|--------|---------------|------------------|
| **Auth for Org Access** | App-only permissions + Admin consent | Service Account + Domain-wide delegation |
| **Incremental Sync** | Delta queries (built-in) | history.list API |
| **Real-time Updates** | Webhooks (subscriptions) | Cloud Pub/Sub |
| **Python SDK** | `msgraph-sdk` + `azure-identity` | `google-api-python-client` |
| **Rate Limit Handling** | Check `Retry-After`, exponential backoff | Exponential backoff on 429 |
| **Pagination** | `@odata.nextLink` | `nextPageToken` |

**For Production:**
1. Start with delta queries/history API for efficient syncing
2. Implement robust checkpoint storage (Redis, DB)
3. Add push notifications for near-real-time updates
4. Include daily full-sync job as safety net
5. Monitor rate limits and implement circuit breakers
6. Use batch APIs where available to reduce API calls
