from __future__ import annotations

from typing import Optional

from fastapi import FastAPI, HTTPException, Query

from .models import ListActionsResponse, RunResponse
from .orchestrator import (
    approve_action,
    get_actions as fetch_actions,
    run_ingest_and_decide,
    skip_action,
    SourceType,
)

app = FastAPI(title="Commander (MVP)", version="0.1.0")


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


