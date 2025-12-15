from __future__ import annotations

from typing import Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from .models import ListActionsResponse, RunResponse
from .orchestrator import (
    approve_action,
    get_actions as fetch_actions,
    run_ingest_and_decide,
    skip_action,
    SourceType,
)
from .storage import update_action_payload
from .integrations.gmail import setup_push_notifications


app = FastAPI(title="Commander (MVP)", version="0.1.0")

# Add CORS middleware to allow frontend to communicate with backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],  # Vite and common dev ports
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --------------------------------------------------------------------------- #
# Core Endpoints
# --------------------------------------------------------------------------- #

@app.post("/run", response_model=RunResponse)
def run(limit: int = 5, source: SourceType = "all"):
    created = run_ingest_and_decide(source=source, limit=limit)
    return RunResponse(proposed_actions=created)


@app.get("/actions", response_model=ListActionsResponse)
def get_actions(status: Optional[str] = Query(default=None)):
    if status and status not in {"pending", "executed", "skipped", "error"}:
        raise HTTPException(status_code=400, detail="Invalid status")
    actions = fetch_actions(status=status)
    return ListActionsResponse(actions=actions)


@app.post("/actions/{action_id}/approve")
def approve(action_id: int):
    try:
        updated = approve_action(action_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return updated


@app.post("/actions/{action_id}/skip")
def skip(action_id: int):
    try:
        updated = skip_action(action_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return updated


@app.patch("/actions/{action_id}")
def update_action(action_id: int, payload: dict):
    """Update an action's payload (for editing before approval)."""
    try:
        updated = update_action_payload(action_id, payload.get("payload", {}))
        if not updated:
            raise HTTPException(status_code=404, detail=f"Action {action_id} not found")
        return updated
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# --------------------------------------------------------------------------- #
# Gmail Integration Endpoints
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


@app.get("/integrations/gmail/status", response_model=GmailStatusResponse)
def gmail_status():
    """Get Gmail connection status."""
    try:
        from .integrations.gmail import get_gmail_status
        status = get_gmail_status()
        return GmailStatusResponse(**status)
    except ImportError:
        raise HTTPException(status_code=500, detail="Gmail integration not available")


@app.get("/integrations/gmail/auth-url", response_model=GmailAuthUrlResponse)
def gmail_auth_url(redirect_uri: str = Query(default="urn:ietf:wg:oauth:2.0:oob")):
    """
    Get Gmail OAuth authorization URL.
    
    For web apps, provide your callback URL as redirect_uri.
    For CLI/desktop, use the default which shows a code to copy.
    """
    try:
        from .integrations.gmail import get_gmail
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


@app.get("/integrations/gmail/auth", response_model=GmailStatusResponse)
def gmail_auth(code: str = Query(..., description="Authorization code returned by Google"), state: Optional[str] = Query(default=None)):
    """
    Complete Gmail OAuth using query parameters from the redirect callback.
    
    Example:
    /integrations/gmail/auth?state=STATE_VALUE&code=AUTH_CODE
    """
    from .integrations.gmail import get_gmail
    gmail = get_gmail()
    success = gmail.complete_auth(code)
    if not success:
        raise HTTPException(status_code=400, detail="Failed to complete authentication")
    return GmailStatusResponse(connected=True, email=gmail.get_user_email())


@app.post("/integrations/gmail/disconnect", response_model=GmailStatusResponse)
def gmail_disconnect():
    """Disconnect Gmail integration."""
    try:
        from .integrations.gmail import disconnect_gmail
        disconnect_gmail()
        return GmailStatusResponse(connected=False, email=None)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error disconnecting: {str(e)}")


@app.post("/integrations/gmail/sync", response_model=GmailSyncResponse)
def gmail_sync(max_results: int = Query(default=20, le=100)):
    """
    Sync recent emails from Gmail.
    
    This performs an initial sync and stores emails as context.
    By default, does NOT generate actions (historical emails).
    """
    try:
        from .integrations.gmail import sync_recent_emails
        
        contexts = sync_recent_emails(max_results=max_results, generate_actions=False)
        return GmailSyncResponse(
            synced_count=len(contexts),
            message=f"Synced {len(contexts)} emails as context"
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error syncing emails: {str(e)}")


@app.post("/integrations/gmail/process-new", response_model=RunResponse)
def gmail_process_new():
    """
    Process new emails since last sync.
    
    This fetches new emails and generates actions for them.
    """
    try:
        from .integrations.gmail import process_new_emails
        
        actions = process_new_emails()
        return RunResponse(proposed_actions=actions)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing new emails: {str(e)}")


# --------------------------------------------------------------------------- #
# Gmail Webhook Endpoints
# --------------------------------------------------------------------------- #
@app.post("/integrations/gmail/webhook/setup")
def gmail_webhook_setup():
    """
    Setup Gmail webhook.
    """
    try:
        setup_push_notifications("projects/commander-481218/topics/commander-gmail")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error setting up webhook: {str(e)}")


@app.post("/integrations/gmail/webhook")
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
            from .integrations.gmail import process_new_emails
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
        return {"status": "error", "message": str(e)}


