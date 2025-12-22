"""
Gmail integration API routes.
"""
from __future__ import annotations

import traceback
from typing import Optional

from fastapi import APIRouter, HTTPException, Query, Depends
from pydantic import BaseModel

from ...auth import User, get_current_user
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
    webhook_active: bool = False
    webhook_expiration: Optional[str] = None


class GmailSyncResponse(BaseModel):
    synced_count: int
    message: str


class GmailWebhookSetupResponse(BaseModel):
    """Response for webhook setup."""
    success: bool
    expiration: Optional[str] = None
    message: str


class GmailWebhookPayload(BaseModel):
    """Payload from Gmail Pub/Sub push notification."""
    message: dict
    subscription: str


# --------------------------------------------------------------------------- #
# Endpoints
# --------------------------------------------------------------------------- #

@router.get("/status", response_model=GmailStatusResponse)
def gmail_status(user: User = Depends(get_current_user)):
    """Get Gmail connection status."""
    import time
    from .client import get_gmail
    
    gmail = get_gmail(user.id)
    gmail_status = gmail.get_gmail_status()
    return GmailStatusResponse(**gmail_status)


@router.get("/auth-url", response_model=GmailAuthUrlResponse)
def gmail_auth_url(
    redirect_uri: str = Query(default="urn:ietf:wg:oauth:2.0:oob"),
    user: User = Depends(get_current_user),
):
    """
    Get Gmail OAuth authorization URL.
    
    For web apps, provide your callback URL as redirect_uri.
    For CLI/desktop, use the default which shows a code to copy.
    """
    from .client import get_gmail
    gmail = get_gmail(user.id)
    auth_url = gmail.get_auth_url(redirect_uri=redirect_uri)
    return GmailAuthUrlResponse(
        auth_url=auth_url,
        instructions="Visit the URL to authorize, then call /integrations/gmail/auth?code=YOUR_CODE (GET)."
    )


@router.get("/auth", response_model=GmailStatusResponse)
def gmail_auth(
    code: str = Query(..., description="Authorization code returned by Google"),
    redirect_uri: str = Query(..., description="Must match the redirect_uri used in auth-url"),
    state: Optional[str] = Query(default=None),
    user: User = Depends(get_current_user),
):
    """
    Complete Gmail OAuth using query parameters from the redirect callback.
    
    Example:
    /integrations/gmail/auth?code=AUTH_CODE&redirect_uri=https://yourapp.com/callback
    """
    from .client import get_gmail
    from ...config import settings

    gmail = get_gmail(user.id)
    success = gmail.complete_auth(code, redirect_uri)
    if not success:
        raise HTTPException(status_code=400, detail="Failed to complete authentication")
    
    # Auto-setup webhook after successful auth (don't fail if this fails)
    try:
        response = gmail.setup_push_notifications(settings.gmail_push_topic_name)
    except Exception as e:
        print(f"Warning: Gmail webhook auto-setup failed for user {user.id}: {e}")
    
    return GmailStatusResponse(**gmail.get_gmail_status())


@router.post("/disconnect", response_model=GmailStatusResponse)
def gmail_disconnect(user: User = Depends(get_current_user)):
    """Disconnect Gmail integration."""
    from .client import get_gmail
    gmail = get_gmail(user.id)
    gmail.stop_push_notifications()
    gmail.disconnect()


    return GmailStatusResponse(connected=False, email=None, webhook_active=False, webhook_expiration=None)


@router.post("/sync", response_model=GmailSyncResponse)
def gmail_sync(
    max_results: int = Query(default=20, le=100),
    user: User = Depends(get_current_user),
):
    """
    Sync recent emails from Gmail.
    
    This performs an initial sync and stores emails as context.
    By default, does NOT generate actions (historical emails).
    """
    try:
        from .orchestrator import sync_recent_emails
        
        emails_count = sync_recent_emails(user.id, max_results=max_results)
        return GmailSyncResponse(
            synced_count=emails_count,
            message=f"Synced {emails_count} emails as context"
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error syncing emails: {str(e)}")


@router.post("/process-new", response_model=RunResponse)
def gmail_process_new(user: User = Depends(get_current_user)):
    """
    Process new emails since last sync.
    
    This fetches new emails and generates actions for them.
    """
    try:
        from .orchestrator import process_new_emails
        
        actions = process_new_emails(user.id)
        return RunResponse(proposed_actions=actions)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing new emails: {str(e)}")


# --------------------------------------------------------------------------- #
# Webhook Endpoints (no auth - called by Google)
# --------------------------------------------------------------------------- #

@router.post("/webhook/setup", response_model=GmailWebhookSetupResponse)
def gmail_webhook_setup(user: User = Depends(get_current_user)):
    """
    Setup Gmail webhook for push notifications.
    
    This is typically called automatically after OAuth, but can be used
    to manually set up or renew the webhook.
    """
    try:
        from .client import get_gmail
        from ...config import settings
        
        gmail = get_gmail(user.id)
        if not gmail.is_connected():
            raise HTTPException(status_code=400, detail="Gmail not connected. Authorize first.")
        
        response = gmail.setup_push_notifications(settings.gmail_push_topic_name)
        if not response:
            return GmailWebhookSetupResponse(
                success=False,
                message="Failed to set up webhook"
            )
        
        return GmailWebhookSetupResponse(
            success=True,
            expiration=response.get("expiration"),
            message="Webhook set up successfully"
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error setting up webhook: {str(e)}")


@router.post("/webhook")
def gmail_webhook(payload: GmailWebhookPayload):
    """
    Webhook endpoint for Gmail Pub/Sub push notifications.
    
    Configure this URL in your Google Cloud Pub/Sub subscription
    to receive notifications when new emails arrive.
    
    Note: This endpoint does NOT require authentication as it's called by Google.
    The webhook uses the email address in the notification to determine the user.
    """
    try:
        import base64
        import json
        
        # Decode the Pub/Sub message
        message_data = payload.message.get("data", "")
        print("New email notification received")
        if message_data:
            decoded = base64.urlsafe_b64decode(message_data).decode("utf-8")
            notification = json.loads(decoded)
            
            # TODO: Look up user by email address from notification
            # For now, webhook processing is disabled until we implement
            # a way to map email addresses to user IDs
            
            return {
                "status": "received",
                "email_address": notification.get("emailAddress"),
                "history_id": notification.get("historyId"),
                "note": "Webhook processing requires user lookup implementation",
            }
        
        return {"status": "no_data"}
    except Exception as e:
        # Always return 200 to acknowledge receipt (prevents retries)
        print(f"Error processing webhook: {str(e)}")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Error processing webhook")
