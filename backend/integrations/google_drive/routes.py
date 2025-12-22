"""
Google Drive integration API routes.

Includes:
- OAuth flow endpoints
- Webhook endpoint for push notifications
- Manual processing endpoints for testing
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, BackgroundTasks, Header, HTTPException, Query, Request, Depends
from pydantic import BaseModel

from ...auth import User, get_current_user


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
def drive_status(user: User = Depends(get_current_user)):
    """Get Google Drive connection status."""
    from .client import get_drive
    
    drive = get_drive(user.id)
    
    drive_status = drive.get_drive_status()
    return DriveStatusResponse(**drive_status)


@router.get("/integrations/drive/auth-url", response_model=DriveAuthUrlResponse)
def drive_auth_url(
    redirect_uri: str = Query(default="urn:ietf:wg:oauth:2.0:oob"),
    user: User = Depends(get_current_user),
):
    """
    Get Google Drive OAuth authorization URL.
    
    For web apps, provide your callback URL as redirect_uri.
    For CLI/desktop, use the default which shows a code to copy.
    """
    from .client import get_drive
    drive = get_drive(user.id)
    auth_url = drive.get_auth_url(redirect_uri=redirect_uri)
    return DriveAuthUrlResponse(
        auth_url=auth_url,
        instructions="Visit the URL to authorize, then call /integrations/drive/auth?code=YOUR_CODE"
    )


@router.get("/integrations/drive/auth", response_model=DriveStatusResponse)
def drive_auth(
    code: str = Query(..., description="Authorization code returned by Google"),
    redirect_uri: str = Query(..., description="Must match the redirect_uri used in auth-url"),
    state: Optional[str] = Query(default=None),
    user: User = Depends(get_current_user),
):
    """
    Complete Google Drive OAuth using query parameters from the redirect callback.
    """
    from .client import get_drive
    from ...config import settings
    
    drive = get_drive(user.id)
    success = drive.complete_auth(code, redirect_uri)
    if not success:
        raise HTTPException(status_code=400, detail="Failed to complete authentication")
    
    # Auto-setup webhook after successful auth (don't fail if this fails)
    webhook_active = False
    webhook_expiration = None
    try:
        folder = drive.find_meet_recordings_folder()
        if folder:
            webhook_url = f"{settings.backend_url}/integrations/drive/webhook"
            result = drive.setup_webhook(webhook_url, folder["id"])
        else:
            print(f"Meet Recordings folder not found for user {user.id} - skipping webhook setup")
        return DriveStatusResponse(**drive.get_drive_status())
    except Exception as e:
        print(f"Warning: Drive webhook auto-setup failed for user {user.id}: {e}")
        return DriveStatusResponse(**drive.get_drive_status())


@router.post("/integrations/drive/disconnect", response_model=DriveStatusResponse)
def drive_disconnect(user: User = Depends(get_current_user)):
    """Disconnect Google Drive integration."""
    from .client import get_drive
    drive = get_drive(user.id)
    webhook_info = drive.get_webhook_info()
    if webhook_info:
        drive.stop_webhook(webhook_info["channel_id"], webhook_info["resource_id"])
    drive.disconnect()
    return DriveStatusResponse(connected=False, email=None, webhook_active=False)


# --------------------------------------------------------------------------- #
# Webhook Endpoints
# --------------------------------------------------------------------------- #

@router.post("/integrations/drive/setup-webhook", response_model=WebhookSetupResponse)
def setup_drive_webhook(user: User = Depends(get_current_user)):
    """
    Set up a webhook to watch the Meet Recordings folder for new transcripts.
    
    Uses the configured backend URL for the webhook endpoint.
    Webhooks expire after ~1 week and need to be renewed.
    """
    try:
        from .client import get_drive
        from ...config import settings
        
        drive = get_drive(user.id)
        
        if not drive.is_connected():
            raise HTTPException(status_code=400, detail="Google Drive not connected. Authorize first.")
        
        # Find the Meet Recordings folder
        folder = drive.find_meet_recordings_folder()

        if not folder:
            return WebhookSetupResponse(
                success=False,
                message="Meet Recordings folder not found - cannot set up webhook"
            )

        webhook_url = f"{settings.backend_url}/integrations/drive/webhook"
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
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error setting up webhook: {str(e)}")



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
    
    Note: This endpoint does NOT require authentication as it's called by Google.
    """
    # Google sends a sync message first to verify the endpoint
    if x_goog_resource_state == "sync":
        print(f"Drive webhook sync received for channel: {x_goog_channel_id}")
        return {"status": "ok", "message": "Sync acknowledged"}
    
    # Log the notification
    print(f"Drive webhook notification: state={x_goog_resource_state}")

    user_id = x_goog_channel_id.split("-")[2]
    
    # For actual changes, process recent files in the background
    if x_goog_resource_state in ("change", "update", "add"):
        background_tasks.add_task(process_drive_changes, user_id=user_id, channel_id=x_goog_channel_id)


    
    # Always return 200 quickly to acknowledge the webhook
    return {"status": "ok"}


async def process_drive_changes(user_id: str, channel_id: str):
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
        results = process_recent_transcripts(
            user_id=user_id, 
            max_files=5, 
            since_hours=1
            )
        
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
    user: User = Depends(get_current_user),
):
    """
    List transcript files in the Meet Recordings folder.
    
    Useful for seeing what transcripts are available before processing.
    """
    try:
        from .client import get_drive
        from datetime import datetime, timedelta
        
        drive = get_drive(user.id)
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
    user: User = Depends(get_current_user),
):
    """
    Manually process a specific transcript file.
    
    Useful for testing the processing pipeline without setting up webhooks.
    """
    try:
        from .transcript_processor import process_new_transcript
        
        result = process_new_transcript(
            user_id=user.id,
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
    user: User = Depends(get_current_user),
):
    """
    Process recent transcript files from the Meet Recordings folder.
    
    Useful for batch processing without webhooks.
    """
    try:
        from .transcript_processor import process_recent_transcripts
        
        results = process_recent_transcripts(
            user_id=user.id,
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
