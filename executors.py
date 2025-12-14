from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Dict

from .models import ActionType, ExecutionResult, ProposedAction


def execute_action(action: ProposedAction) -> ExecutionResult:
    """
    Dummy executors: print what would happen and return a structured result.
    """
    now = datetime.utcnow()
    
    if action.type == ActionType.SEND_EMAIL:
        payload = action.payload
        print(
            f"[SEND_EMAIL] thread={payload.get('thread_id')} to_email={payload.get('to_email')} "
            f"subject={payload.get('subject')} body={payload.get('body')!r}"
        )
        return ExecutionResult(
            action_id=action.id,
            status="draft_created",
            result={"note": "Would send an email"},
            executed_at=now,
        )
    if action.type == ActionType.SCHEDULE_MEETING:
        payload = action.payload
        print(
            f"[SCHEDULE_MEETING] duration={payload.get('duration_mins')} "
            f"meeting_date={payload.get('meeting_date')} "
            f"meeting_title={payload.get('meeting_title')} "
            f"meeting_description={payload.get('meeting_description')} "
        )
        return ExecutionResult(
            action_id=action.id,
            status="draft_created",
            result={"note": "Would schedule a meeting"},
            executed_at=now,
        )
    if action.type == ActionType.CREATE_TODO:
        payload = action.payload
        print(f"[CREATE_TODO] title={payload.get('title')!r} notes={payload.get('notes')!r}")
        return ExecutionResult(
            action_id=action.id,
            status="executed",
            result={"note": "Would create a todo item"},
            executed_at=now,
        )
    if action.type == ActionType.NO_ACTION:
        payload = action.payload
        print(f"[NO_ACTION] reason={payload.get('reason')!r}")
        return ExecutionResult(
            action_id=action.id,
            status="skipped",
            result={"note": "No action taken"},
            executed_at=now,
        )
    # Unknown
    print(f"[ERROR] Unknown action type: {action.type}")
    return ExecutionResult(
        action_id=action.id,
        status="error",
        result={"error": f"Unknown action type: {action.type}"},
        executed_at=now,
    )


