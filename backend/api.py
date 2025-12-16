from __future__ import annotations

from typing import Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from .models import ListActionsResponse, RunResponse
from .orchestrator import (
    approve_action,
    get_actions as fetch_actions,
    run_ingest_and_decide,
    skip_action,
    SourceType,
)
from .storage import update_action_payload

# Import integration routers
from .integrations.gmail.routes import router as gmail_router
from .integrations.google_calendar.routes import router as calendar_router


app = FastAPI(title="Commander (MVP)", version="0.1.0")

# Add CORS middleware to allow frontend to communicate with backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],  # Vite and common dev ports
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include integration routers
app.include_router(gmail_router)
app.include_router(calendar_router)


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
