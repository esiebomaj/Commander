"""
Google Drive integration API routes.

Includes:
- OAuth flow endpoints
- Webhook endpoint for push notifications
- Manual processing endpoints for testing
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, BackgroundTasks, Header, HTTPException, Query, Request
from pydantic import BaseModel


router = APIRouter(tags=["drive"])


# --------------------------------------------------------------------------- #
# Response Models
# --------------------------------------------------------------------------- #

class DriveAuthUrlResponse(BaseModel):
    auth_url: str
    instructions: str


class DriveStatusResponse(BaseModel):
    connected: bool
    email: Optional[str] = None
    webhook_active: bool = False
    webhook_expiration: Optional[str] = None


class WebhookSetupResponse(BaseModel):
    success: bool
    channel_id: Optional[str] = None
    expiration: Optional[str] = None
    message: str


class ProcessTranscriptResponse(BaseModel):
    success: bool
    context_id: Optional[str] = None
    actions_created: int = 0
    message: str


class TranscriptFileInfo(BaseModel):
    id: str
    name: str
    created_time: Optional[str] = None
    modified_time: Optional[str] = None
    web_link: Optional[str] = None


class ListTranscriptsResponse(BaseModel):
    files: List[TranscriptFileInfo]
    meet_recordings_folder_id: Optional[str] = None


# --------------------------------------------------------------------------- #
# OAuth Endpoints
# --------------------------------------------------------------------------- #

@router.get("/integrations/drive/status", response_model=DriveStatusResponse)
def drive_status():
    """Get Google Drive connection status."""
    from . import get_drive_status
    status = get_drive_status()
    return DriveStatusResponse(**status)


@router.get("/integrations/drive/auth-url", response_model=DriveAuthUrlResponse)
def drive_auth_url(redirect_uri: str = Query(default="urn:ietf:wg:oauth:2.0:oob")):
    """
    Get Google Drive OAuth authorization URL.
    
    For web apps, provide your callback URL as redirect_uri.
    For CLI/desktop, use the default which shows a code to copy.
    """
    from . import get_drive
    drive = get_drive()
    auth_url = drive.get_auth_url(redirect_uri=redirect_uri)
    return DriveAuthUrlResponse(
        auth_url=auth_url,
        instructions="Visit the URL to authorize, then call /integrations/drive/auth?code=YOUR_CODE"
    )


@router.get("/integrations/drive/auth", response_model=DriveStatusResponse)
def drive_auth(
    code: str = Query(..., description="Authorization code returned by Google"),
    state: Optional[str] = Query(default=None),
):
    """
    Complete Google Drive OAuth using query parameters from the redirect callback.
    """
    from . import get_drive
    drive = get_drive()
    success = drive.complete_auth(code)
    if not success:
        raise HTTPException(status_code=400, detail="Failed to complete authentication")
    
    return DriveStatusResponse(
        connected=True,
        email=drive.get_user_email(),
        webhook_active=False,
    )


@router.post("/integrations/drive/disconnect", response_model=DriveStatusResponse)
def drive_disconnect():
    """Disconnect Google Drive integration."""
    from . import disconnect_drive
    disconnect_drive()
    return DriveStatusResponse(connected=False, email=None, webhook_active=False)


# --------------------------------------------------------------------------- #
# Webhook Endpoints
# --------------------------------------------------------------------------- #

@router.post("/integrations/drive/setup-webhook", response_model=WebhookSetupResponse)
def setup_drive_webhook(
    webhook_url: str = Query(..., description="Public URL to receive webhook notifications"),
):
    """
    Set up a webhook to watch the Meet Recordings folder for new transcripts.
    
    The webhook_url must be publicly accessible and accept POST requests.
    Webhooks expire after ~1 week and need to be renewed.
    """
    try:
        from . import get_drive
        
        drive = get_drive()
        
        if not drive.is_connected():
            raise HTTPException(status_code=400, detail="Google Drive not connected. Authorize first.")
        
            # Find the Meet Recordings folder if not provided
        folder = drive.find_meet_recordings_folder()

        if not folder:
            return WebhookSetupResponse(
                success=False,
                message="Meet Recordings folder not found - cannot set up webhook"
            )

        result = drive.setup_webhook(webhook_url, folder["id"])
        if not result:
            return WebhookSetupResponse(
                success=False,
                message="Failed to set up webhook. Make sure the Meet Recordings folder exists."
            )
        
        webhook_info = drive.get_webhook_info()
        return WebhookSetupResponse(
            success=True,
            channel_id=result.get("id"),
            expiration=webhook_info.get("expiration") if webhook_info else None,
            message="Webhook set up successfully"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error setting up webhook: {str(e)}")


@router.post("/integrations/drive/stop-webhook")
def stop_drive_webhook():
    """Stop the current webhook watch."""
    try:
        from . import get_drive
        
        drive = get_drive()
        
        webhook_info = drive.get_webhook_info()
        if not webhook_info:
            return {"success": False, "message": "No active webhook found"}
        
        success = drive.stop_webhook(
            channel_id=webhook_info["channel_id"],
            resource_id=webhook_info["resource_id"],
        )
        
        return {
            "success": success,
            "message": "Webhook stopped" if success else "Failed to stop webhook"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error stopping webhook: {str(e)}")


@router.post("/integrations/drive/webhook")
async def receive_drive_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    x_goog_channel_id: Optional[str] = Header(None),
    x_goog_resource_state: Optional[str] = Header(None),
):
    """
    Receive push notifications from Google Drive.
    
    Google sends notifications when files change in the watched folder.
    This endpoint processes them in the background to return 200 quickly.
    """
    # Google sends a sync message first to verify the endpoint
    if x_goog_resource_state == "sync":
        print(f"Drive webhook sync received for channel: {x_goog_channel_id}")
        return {"status": "ok", "message": "Sync acknowledged"}
    
    # Log the notification
    print(f"Drive webhook notification: state={x_goog_resource_state}")
    
    # For actual changes, process recent files in the background
    if x_goog_resource_state in ("change", "update", "add"):
        background_tasks.add_task(process_drive_changes)
    
    # Always return 200 quickly to acknowledge the webhook
    return {"status": "ok"}


async def process_drive_changes():
    """
    Background task to process Drive changes.
    
    Simply checks for recent transcript files and processes any new ones.
    Relies on deduplication (context_exists) to skip already-processed files.
    """
    print("Processing Drive webhook notification")
    
    try:
        from .transcript_processor import process_recent_transcripts
        
        # Check for transcripts modified in the last hour
        # The deduplication check will skip any we've already processed
        results = process_recent_transcripts(max_files=5, since_hours=1)
        
        print(f"Processed {len(results)} new transcript(s)")
        
    except Exception as e:
        print(f"Error processing Drive changes: {e}")
        import traceback
        traceback.print_exc()


# --------------------------------------------------------------------------- #
# Manual Processing Endpoints (for testing)
# --------------------------------------------------------------------------- #

@router.get("/integrations/drive/transcripts", response_model=ListTranscriptsResponse)
def list_transcripts(
    max_results: int = Query(default=20, le=100),
    since_hours: int = Query(default=168, description="Only show files modified in last N hours"),
):
    """
    List transcript files in the Meet Recordings folder.
    
    Useful for seeing what transcripts are available before processing.
    """
    try:
        from . import get_drive
        from datetime import datetime, timedelta
        
        drive = get_drive()
        if not drive.is_connected():
            raise HTTPException(status_code=400, detail="Google Drive not connected")

        # Get transcript files
        modified_after = datetime.utcnow() - timedelta(hours=since_hours)
        files = drive.list_transcript_files(
            max_results=max_results,
            modified_after=modified_after,
        )
        
        return ListTranscriptsResponse(
            files=[
                TranscriptFileInfo(
                    id=f["id"],
                    name=f["name"],
                    created_time=f.get("createdTime"),
                    modified_time=f.get("modifiedTime"),
                    web_link=f.get("webViewLink"),
                )
                for f in files
            ],
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error listing transcripts: {str(e)}")


@router.post("/integrations/drive/process/{file_id}", response_model=ProcessTranscriptResponse)
def process_transcript(
    file_id: str,
    force: bool = Query(default=False, description="Process even if already processed"),
):
    """
    Manually process a specific transcript file.
    
    Useful for testing the processing pipeline without setting up webhooks.
    """
    try:
        from .transcript_processor import process_new_transcript
        
        result = process_new_transcript(
            file_id=file_id,
            skip_if_exists=not force,
        )
        
        if result is None:
            return ProcessTranscriptResponse(
                success=False,
                message="Transcript was skipped (already processed or error occurred)"
            )
        
        context, actions = result
        return ProcessTranscriptResponse(
            success=True,
            context_id=context.id,
            actions_created=len(actions),
            message=f"Processed transcript successfully. Created {len(actions)} proposed actions."
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing transcript: {str(e)}")


@router.post("/integrations/drive/process-recent", response_model=Dict[str, Any])
def process_recent(
    max_files: int = Query(default=5, le=20),
    since_hours: int = Query(default=24),
):
    """
    Process recent transcript files from the Meet Recordings folder.
    
    Useful for batch processing without webhooks.
    """
    try:
        from .transcript_processor import process_recent_transcripts
        
        results = process_recent_transcripts(
            max_files=max_files,
            since_hours=since_hours,
        )
        
        return {
            "success": True,
            "processed_count": len(results),
            "transcripts": [
                {
                    "context_id": ctx.id,
                    "title": ctx.content.get("title", "Unknown"),
                    "actions_created": len(actions),
                }
                for ctx, actions in results
            ],
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing transcripts: {str(e)}")

