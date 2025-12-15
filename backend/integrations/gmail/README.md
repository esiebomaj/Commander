# Gmail Integration

Gmail integration for Commander. Provides OAuth authentication, email reading, sending, and push notifications.

## Setup

1. **Create a Google Cloud Project**
   - Go to [Google Cloud Console](https://console.cloud.google.com/)
   - Create a new project or select an existing one

2. **Enable the Gmail API**
   - Go to "APIs & Services" > "Library"
   - Search for "Gmail API" and enable it

3. **Create OAuth 2.0 Credentials**
   - Go to "APIs & Services" > "Credentials"
   - Click "Create Credentials" > "OAuth client ID"
   - Select "Desktop app" as the application type
   - Download the JSON credentials file

4. **Save Credentials**
   - Save the downloaded JSON file as `data/gmail_credentials.json`

5. **Authenticate**
   - Run the OAuth flow to authorize the application:
   
   ```python
   from integrations.gmail import connect_gmail_interactive
   
   # This opens a browser for authorization
   connect_gmail_interactive()
   ```

   Or via API:
   - GET `/integrations/gmail/auth-url` to get the authorization URL
   - Visit the URL and authorize
   - POST `/integrations/gmail/auth` with the authorization code

## Usage

### Check Connection Status
```python
from integrations.gmail import get_gmail_status

status = get_gmail_status()
print(f"Connected: {status['connected']}, Email: {status['email']}")
```

### Initial Sync (No Actions)
```python
from integrations.gmail import sync_recent_emails

# Sync last 20 emails as context (no actions generated)
contexts = sync_recent_emails(max_results=20)
```

### Process New Emails (With Actions)
```python
from integrations.gmail import process_new_emails

# Fetch new emails and generate actions
actions = process_new_emails()
```

### Send Email
```python
from integrations.gmail import send_email_action

result = send_email_action(
    to_email="recipient@example.com",
    subject="Hello",
    body="This is the email body",
    thread_id=None,  # Optional: for replies
)
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/integrations/gmail/status` | GET | Check connection status |
| `/integrations/gmail/auth-url` | GET | Get OAuth authorization URL |
| `/integrations/gmail/auth` | POST | Complete OAuth with auth code |
| `/integrations/gmail/disconnect` | POST | Disconnect Gmail |
| `/integrations/gmail/sync` | POST | Initial sync of recent emails |
| `/integrations/gmail/process-new` | POST | Process new emails with action generation |
| `/integrations/gmail/webhook` | POST | Webhook for Pub/Sub push notifications |

## Push Notifications (Optional)

For real-time email notifications, you can set up Gmail Push Notifications:

1. Create a Pub/Sub topic in Google Cloud
2. Give `gmail-api-push@system.gserviceaccount.com` publish permissions
3. Create a push subscription pointing to `/integrations/gmail/webhook`
4. Call `setup_push_notifications()` with your topic name

```python
from integrations.gmail import get_gmail

gmail = get_gmail()
gmail.setup_push_notifications("projects/your-project/topics/gmail-notifications")
```

Note: Push notifications require a publicly accessible webhook URL and must be renewed every 7 days.
