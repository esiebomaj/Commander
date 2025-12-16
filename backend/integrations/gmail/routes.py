"""
Gmail integration API routes.
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from ...models import RunResponse


router = APIRouter(prefix="/integrations/gmail", tags=["gmail"])


# --------------------------------------------------------------------------- #
# Response Models
# --------------------------------------------------------------------------- #

class GmailAuthUrlResponse(BaseModel):
    auth_url: str
    instructions: str


class GmailStatusResponse(BaseModel):
    connected: bool
    email: Optional[str] = None


class GmailSyncResponse(BaseModel):
    synced_count: int
    message: str


class GmailWebhookPayload(BaseModel):
    """Payload from Gmail Pub/Sub push notification."""
    message: dict
    subscription: str


# --------------------------------------------------------------------------- #
# Endpoints
# --------------------------------------------------------------------------- #

@router.get("/status", response_model=GmailStatusResponse)
def gmail_status():
    """Get Gmail connection status."""
    try:
        from . import get_gmail_status
        status = get_gmail_status()
        return GmailStatusResponse(**status)
    except ImportError:
        raise HTTPException(status_code=500, detail="Gmail integration not available")


@router.get("/auth-url", response_model=GmailAuthUrlResponse)
def gmail_auth_url(redirect_uri: str = Query(default="urn:ietf:wg:oauth:2.0:oob")):
    """
    Get Gmail OAuth authorization URL.
    
    For web apps, provide your callback URL as redirect_uri.
    For CLI/desktop, use the default which shows a code to copy.
    """
    try:
        from . import get_gmail
        gmail = get_gmail()
        auth_url = gmail.get_auth_url(redirect_uri=redirect_uri)
        return GmailAuthUrlResponse(
            auth_url=auth_url,
            instructions="Visit the URL to authorize, then call /integrations/gmail/auth?code=YOUR_CODE (GET)."
        )
    except FileNotFoundError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating auth URL: {str(e)}")


@router.get("/auth", response_model=GmailStatusResponse)
def gmail_auth(code: str = Query(..., description="Authorization code returned by Google"), state: Optional[str] = Query(default=None)):
    """
    Complete Gmail OAuth using query parameters from the redirect callback.
    
    Example:
    /integrations/gmail/auth?state=STATE_VALUE&code=AUTH_CODE
    """
    from . import get_gmail
    gmail = get_gmail()
    success = gmail.complete_auth(code)
    if not success:
        raise HTTPException(status_code=400, detail="Failed to complete authentication")
    return GmailStatusResponse(connected=True, email=gmail.get_user_email())


@router.post("/disconnect", response_model=GmailStatusResponse)
def gmail_disconnect():
    """Disconnect Gmail integration."""
    try:
        from . import disconnect_gmail
        disconnect_gmail()
        return GmailStatusResponse(connected=False, email=None)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error disconnecting: {str(e)}")


@router.post("/sync", response_model=GmailSyncResponse)
def gmail_sync(max_results: int = Query(default=20, le=100)):
    """
    Sync recent emails from Gmail.
    
    This performs an initial sync and stores emails as context.
    By default, does NOT generate actions (historical emails).
    """
    try:
        from . import sync_recent_emails
        
        contexts = sync_recent_emails(max_results=max_results, generate_actions=False)
        return GmailSyncResponse(
            synced_count=len(contexts),
            message=f"Synced {len(contexts)} emails as context"
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error syncing emails: {str(e)}")


@router.post("/process-new", response_model=RunResponse)
def gmail_process_new():
    """
    Process new emails since last sync.
    
    This fetches new emails and generates actions for them.
    """
    try:
        from . import process_new_emails
        
        actions = process_new_emails()
        return RunResponse(proposed_actions=actions)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing new emails: {str(e)}")


# --------------------------------------------------------------------------- #
# Webhook Endpoints
# --------------------------------------------------------------------------- #

@router.post("/webhook/setup")
def gmail_webhook_setup():
    """
    Setup Gmail webhook.
    """
    try:
        from . import setup_push_notifications
        setup_push_notifications("projects/commander-481218/topics/commander-gmail")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error setting up webhook: {str(e)}")


@router.post("/webhook")
def gmail_webhook(payload: GmailWebhookPayload):
    """
    Webhook endpoint for Gmail Pub/Sub push notifications.
    
    Configure this URL in your Google Cloud Pub/Sub subscription
    to receive notifications when new emails arrive.
    """
    try:
        import base64
        import json
        
        # Decode the Pub/Sub message
        message_data = payload.message.get("data", "")
        if message_data:
            decoded = base64.urlsafe_b64decode(message_data).decode("utf-8")
            notification = json.loads(decoded)
            
            # Process new emails
            from . import process_new_emails
            actions = process_new_emails()
            
            return {
                "status": "processed",
                "email_address": notification.get("emailAddress"),
                "history_id": notification.get("historyId"),
                "actions_created": len(actions),
            }
        
        return {"status": "no_data"}
    except Exception as e:
        # Always return 200 to acknowledge receipt (prevents retries)
        print(f"Error processing webhook: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error processing webhook")

