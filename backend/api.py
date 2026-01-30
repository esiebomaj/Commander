from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, HTTPException, Query, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from .auth import User, get_current_user
from .context_storage import search_similar_contexts
from .init_qdrant import init_qdrant
from .models import ListActionsResponse, RunResponse
from .orchestrator import (
    approve_action,
    get_actions as fetch_actions,
    skip_action,
)
from .storage import update_action_payload

# Import integration routers
from .integrations.gmail.routes import router as gmail_router
from .integrations.google_calendar.routes import router as calendar_router
from .integrations.google_drive.routes import router as drive_router
from .integrations.github.routes import router as github_router
from .integrations.slack.routes import router as slack_router

# Import push notification module
from . import push
from .config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize services on startup."""
    init_qdrant()
    yield


app = FastAPI(title="Commander (MVP)", version="0.1.0", lifespan=lifespan)

# Add CORS middleware to allow frontend to communicate with backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173", 
        "http://localhost:3000", 
        settings.frontend_url
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include integration routers
app.include_router(gmail_router)
app.include_router(calendar_router)
app.include_router(drive_router)
app.include_router(github_router)
app.include_router(slack_router)


# --------------------------------------------------------------------------- #
# Health
# --------------------------------------------------------------------------- #

@app.get("/health")
def health():
    """Liveness/readiness check for load balancers and monitoring."""
    return {"status": "ok"}


# --------------------------------------------------------------------------- #
# Core Endpoints
# --------------------------------------------------------------------------- #

@app.get("/actions", response_model=ListActionsResponse)
def get_actions(
    status: Optional[str] = Query(default=None),
    user: User = Depends(get_current_user),
):
    if status and status not in {"pending", "executed", "skipped", "error"}:
        raise HTTPException(status_code=400, detail="Invalid status")
    actions = fetch_actions(user_id=user.id, status=status)
    return ListActionsResponse(actions=actions)


@app.post("/actions/{action_id}/approve")
async def approve(action_id: int, user: User = Depends(get_current_user)):
    try:
        updated = await approve_action(user_id=user.id, action_id=action_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return updated


@app.post("/actions/{action_id}/skip")
def skip(action_id: int, user: User = Depends(get_current_user)):
    try:
        updated = skip_action(user_id=user.id, action_id=action_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return updated


@app.patch("/actions/{action_id}")
def update_action(
    action_id: int,
    payload: dict,
    user: User = Depends(get_current_user),
):
    """Update an action's payload (for editing before approval)."""
    try:
        updated = update_action_payload(user.id, action_id, payload.get("payload", {}))
        if not updated:
            raise HTTPException(status_code=404, detail=f"Action {action_id} not found")
        return updated
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class DeleteActionsRequest(BaseModel):
    """Request body for bulk delete."""
    action_ids: list[int]


@app.post("/actions/delete")
def delete_multiple_actions(
    request: DeleteActionsRequest,
    user: User = Depends(get_current_user),
):
    """Delete multiple actions by their IDs."""
    from .storage import delete_actions
    
    if not request.action_ids:
        raise HTTPException(status_code=400, detail="No action IDs provided")
    
    deleted_count = delete_actions(user.id, request.action_ids)
    return {"success": True, "deleted": deleted_count}


# --------------------------------------------------------------------------- #
# Context & Similarity Search Endpoints
# --------------------------------------------------------------------------- #

class SimilaritySearchRequest(BaseModel):
    """Request for similarity search."""
    text: str
    limit: int = 10


class SimilaritySearchResult(BaseModel):
    """Result for similarity search."""
    id: str
    source_type: str
    sender: Optional[str]
    summary: Optional[str]
    context_text: str
    timestamp: str
    similarity_score: float


class SimilaritySearchResponse(BaseModel):
    """Response for similarity search."""
    results: list[SimilaritySearchResult]
    count: int


@app.post("/api/contexts/similar", response_model=SimilaritySearchResponse)
def search_similar(
    request: SimilaritySearchRequest,
    user: User = Depends(get_current_user),
):
    """
    Search for contexts similar to the given text.
    
    Uses semantic similarity search powered by embeddings and Qdrant.
    """
    try:
        results = search_similar_contexts(
            user_id=user.id,
            query_text=request.text,
            limit=request.limit,
        )
        
        search_results = [
            SimilaritySearchResult(
                id=ctx.id,
                source_type=ctx.source_type.value,
                sender=ctx.sender,
                summary=ctx.summary,
                context_text=ctx.context_text[:500],  # Truncate for response
                timestamp=ctx.timestamp.isoformat(),
                similarity_score=score,
            )
            for ctx, score in results
        ]
        
        return SimilaritySearchResponse(
            results=search_results,
            count=len(search_results),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Similarity search failed: {str(e)}")


# --------------------------------------------------------------------------- #
# Push Notification Endpoints
# --------------------------------------------------------------------------- #

class PushSubscription(BaseModel):
    """Push subscription from browser."""
    endpoint: str
    keys: dict


class PushUnsubscribe(BaseModel):
    """Unsubscribe request."""
    endpoint: str


class TestNotification(BaseModel):
    """Test notification request."""
    title: str = "Test Notification"
    body: str = "This is a test notification from Commander."


@app.get("/push/vapid-public-key")
def get_vapid_public_key():
    """Get the VAPID public key for push subscription."""
    try:
        public_key = push.get_public_key()
        return {"public_key": public_key}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/push/subscribe")
def push_subscribe(
    subscription: PushSubscription,
    user: User = Depends(get_current_user),
):
    """Subscribe to push notifications."""
    try:
        push.subscribe(user.id, subscription.model_dump())
        return {"success": True, "message": "Subscribed to push notifications"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/push/unsubscribe")
def push_unsubscribe(
    data: PushUnsubscribe,
    user: User = Depends(get_current_user),
):
    """Unsubscribe from push notifications."""
    try:
        removed = push.unsubscribe(user.id, data.endpoint)
        if removed:
            return {"success": True, "message": "Unsubscribed from push notifications"}
        return {"success": False, "message": "Subscription not found"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/push/test")
def push_test(
    data: TestNotification,
    user: User = Depends(get_current_user),
):
    """Send a test push notification (for development)."""
    try:
        result = push.send_notification(
            user_id=user.id,
            title=data.title,
            body=data.body,
            url="/actions?edit=18",
        )
        return {
            "success": True,
            "message": f"Sent {result['sent']} notification(s)",
            **result
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/push/status")
def push_status(user: User = Depends(get_current_user)):
    """Get push notification status."""
    try:
        count = push.get_subscription_count(user.id)
        return {
            "enabled": count > 0,
            "subscription_count": count,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# --------------------------------------------------------------------------- #
# User Profile Endpoint
# --------------------------------------------------------------------------- #

@app.get("/me")
def get_current_user_profile(user: User = Depends(get_current_user)):
    """Get the current user's profile."""
    return {
        "id": user.id,
        "email": user.email,
        "full_name": user.full_name,
        "avatar_url": user.avatar_url,
    }
